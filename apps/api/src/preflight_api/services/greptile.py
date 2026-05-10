from __future__ import annotations

import logging
import re
from typing import Any

import httpx

from preflight_api.config import Settings, get_settings
from preflight_api.schemas.evaluate import EvaluateRequest

logger = logging.getLogger(__name__)


def _parse_github_repository(url: str | None) -> tuple[str, str] | None:
    if not url:
        return None
    m = re.search(r"github\.com[:/]([^/]+)/([^/?.#]+)", url, re.IGNORECASE)
    if not m:
        return None
    org, repo = m.group(1), m.group(2)
    return org, repo.removesuffix(".git")


class GreptileClient:
    """
    Greptile exposes repository-aware natural language queries.

    This client targets the common `POST /query` shape; Greptile may evolve —
    keep payloads small and tolerate HTTP errors with mock fallbacks.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._client = httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=10.0))

    async def aclose(self) -> None:
        await self._client.aclose()

    def enabled(self) -> bool:
        return bool(self.settings.greptile_api_key and self.settings.github_token)

    def _headers(self) -> dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self.settings.greptile_api_key}",
            "Content-Type": "application/json",
        }
        if self.settings.github_token:
            headers["X-GitHub-Token"] = self.settings.github_token
        return headers

    async def query_repository(self, body: dict[str, Any]) -> dict[str, Any]:
        base = self.settings.greptile_base_url.rstrip("/")
        url = f"{base}/query"
        resp = await self._client.post(url, headers=self._headers(), json=body)
        resp.raise_for_status()
        data = resp.json()
        if not isinstance(data, dict):
            return {"raw": data}
        return data

    def _build_questions(self, request: EvaluateRequest) -> str:
        parts = [
            "You are assisting an automated preflight risk review.",
            f"Task type: {request.task_type.value}",
            f"Action summary: {request.action_summary}",
        ]
        if request.diff_text:
            parts.append(
                "Here is a unified diff. Answer succinctly with bullet points:\n"
                "- Which modules or directories are likely impacted?\n"
                "- Are there auth, crypto, or secret-handling concerns?\n"
                "- Which tests or files should a reviewer open first?\n\n"
                f"```diff\n{request.diff_text[:12000]}\n```",
            )
        else:
            parts.append(
                "No diff was supplied. Based on repository metadata, list likely risk areas "
                "and suggested checks.",
            )
        return "\n".join(parts)

    async def analyze(self, request: EvaluateRequest) -> dict[str, Any]:
        if not self.enabled():
            return self._mock(request)

        parsed = _parse_github_repository(request.repository_url or "")
        if not parsed:
            return {
                "sponsor": "greptile",
                "repo_summary": "No GitHub repository URL detected for Greptile query.",
                "affected_areas": [],
                "risk_flags": ["missing_github_repository_url"],
                "convention_warnings": [],
                "suggested_checks": ["Provide a public GitHub HTTPS URL for deeper Greptile analysis."],
                "raw": {},
            }

        org, repo = parsed
        branch = request.repository_ref or "main"
        body = {
            "messages": [{"role": "user", "content": self._build_questions(request)}],
            "repositories": [
                {
                    "remote": "github",
                    "repository": f"{org}/{repo}",
                    "branch": branch,
                },
            ],
        }

        try:
            raw = await self.query_repository(body)
            text = str(raw)
            return {
                "sponsor": "greptile",
                "repo_summary": text[:2000],
                "affected_areas": self._extract_list(raw, ["files", "paths", "impacted"]),
                "risk_flags": self._extract_risk_flags(request, raw),
                "convention_warnings": self._extract_list(raw, ["warnings", "conventions"]),
                "suggested_checks": self._extract_list(raw, ["tests", "checks", "follow ups"]),
                "raw": raw,
            }
        except Exception as exc:  # noqa: BLE001
            logger.warning("greptile_query_failed", extra={"error": str(exc)})
            mocked = self._mock(request)
            mocked["risk_flags"].append(f"greptile_http_error:{exc.__class__.__name__}")
            mocked["raw"] = {"error": str(exc)}
            return mocked

    def _extract_list(self, raw: dict[str, Any], keys: list[str]) -> list[str]:
        for key in keys:
            val = raw.get(key)
            if isinstance(val, list):
                return [str(v) for v in val][:25]
        return []

    def _extract_risk_flags(self, request: EvaluateRequest, raw: dict[str, Any]) -> list[str]:
        flags = self._extract_list(raw, ["risks", "risk_flags", "issues"])
        blob = str(raw).lower()
        if request.diff_text:
            low = request.diff_text.lower()
            if any(token in low for token in ("password", "secret", "token", "api_key")):
                flags.append("diff_touches_secret_like_strings")
            if any(token in low for token in ("auth", "jwt", "oauth", "session")):
                flags.append("diff_touches_authentication_surface")
        if "auth" in blob:
            flags.append("greptile_mentions_auth")
        return list(dict.fromkeys(flags))[:25]

    def _mock(self, request: EvaluateRequest) -> dict[str, Any]:
        flags: list[str] = []
        if request.diff_text:
            if "auth" in request.diff_text.lower():
                flags.append("mock:authentication_related_diff")
            if request.diff_text.count("\n") > 200:
                flags.append("mock:large_diff")
        return {
            "sponsor": "greptile",
            "repo_summary": "Greptile integration running in mock mode (missing API keys).",
            "affected_areas": ["unknown_without_live_query"],
            "risk_flags": flags or ["mock_mode"],
            "convention_warnings": ["Configure GREPTILE_API_KEY and GITHUB_TOKEN for live analysis."],
            "suggested_checks": [
                "Run unit and integration tests touching modified modules.",
                "Request human review for auth and payment-adjacent code.",
            ],
            "raw": {},
        }
