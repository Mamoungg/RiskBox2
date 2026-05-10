from __future__ import annotations

import logging
import re
from typing import Any

import httpx

from preflight_api.config import Settings, get_settings
from preflight_api.schemas.evaluate import EvaluateRequest

logger = logging.getLogger(__name__)


def _github_like_repo_slug(url: str) -> str | None:
    """
    Map https://github.com/org/repo(.git) -> org/repo
    """
    m = re.search(r"github\.com[:/]([^/]+)/([^/?.#]+)", url, re.IGNORECASE)
    if not m:
        return None
    org, repo = m.group(1), m.group(2)
    repo = repo.removesuffix(".git")
    return f"{org}/{repo}"


def _looks_like_unauthenticated_https(url: str | None) -> bool:
    if not url:
        return False
    u = url.strip()
    return u.startswith("https://") and "@" not in u


class NiaClient:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._client = httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=10.0))

    async def aclose(self) -> None:
        await self._client.aclose()

    def enabled(self) -> bool:
        return bool(self.settings.nia_api_key)

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.settings.nia_api_key}",
            "Content-Type": "application/json",
        }

    async def _post(self, path: str, json: dict[str, Any]) -> dict[str, Any]:
        base = self.settings.nia_base_url.rstrip("/")
        url = f"{base}{path}"
        resp = await self._client.post(url, headers=self._headers(), json=json)
        resp.raise_for_status()
        data = resp.json()
        if not isinstance(data, dict):
            return {"raw": data}
        return data

    async def create_source(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._post("/sources", payload)

    async def search(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._post("/search", payload)

    async def sandbox_search(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._post("/sandbox/search", payload)

    async def gather(self, request: EvaluateRequest) -> dict[str, Any]:
        """
        Returns normalized context_assessment structure.
        """
        if not self.enabled():
            return self._mock_context(request)

        relevant_docs: list[dict[str, Any]] = []
        policy_hits: list[dict[str, Any]] = []
        architecture_notes: list[str] = []
        context_risk_flags: list[str] = []
        raw_traces: list[dict[str, Any]] = []

        try:
            for doc_url in request.documentation_urls:
                try:
                    created = await self.create_source(
                        {"type": "documentation", "url": doc_url},
                    )
                    raw_traces.append({"kind": "nia_source_doc", "url": doc_url, "response": created})
                except Exception as exc:  # noqa: BLE001
                    logger.warning("nia_doc_source_failed", extra={"url": doc_url, "error": str(exc)})
                    context_risk_flags.append(f"documentation_index_failed:{doc_url}")

            for pol_url in request.policy_urls:
                try:
                    created = await self.create_source(
                        {"type": "documentation", "url": pol_url},
                    )
                    raw_traces.append({"kind": "nia_source_policy", "url": pol_url, "response": created})
                except Exception as exc:  # noqa: BLE001
                    logger.warning("nia_policy_source_failed", extra={"url": pol_url, "error": str(exc)})
                    context_risk_flags.append(f"policy_index_failed:{pol_url}")

            query = (
                "You are assisting a risk preflight for an autonomous agent.\n"
                f"Task type: {request.task_type.value}\n"
                f"Proposed action: {request.action_summary}\n"
                "Summarize relevant architecture, compliance, and policy considerations. "
                "Call out missing citations or unclear governance."
            )

            if request.repository_url and _looks_like_unauthenticated_https(request.repository_url):
                sandbox_body: dict[str, Any] = {
                    "repository": request.repository_url,
                    "ref": request.repository_ref or "main",
                    "query": query,
                }
                try:
                    sres = await self.sandbox_search(sandbox_body)
                    raw_traces.append({"kind": "nia_sandbox_search", "response": sres})
                    text_blob = str(sres)
                    architecture_notes.append("sandbox_search_completed")
                    relevant_docs.append(
                        {
                            "title": "sandbox_search",
                            "excerpt": text_blob[:4000],
                            "source": request.repository_url,
                        },
                    )
                except Exception as exc:  # noqa: BLE001
                    logger.warning("nia_sandbox_search_failed", extra={"error": str(exc)})
                    context_risk_flags.append("sandbox_search_failed")
                    await self._fallback_search(request, query, relevant_docs, raw_traces)
            elif request.repository_url:
                await self._fallback_search(request, query, relevant_docs, raw_traces)

            if request.policy_urls or request.documentation_urls:
                try:
                    search_payload: dict[str, Any] = {
                        "mode": "query",
                        "messages": [{"role": "user", "content": query}],
                        "search_mode": "unified",
                    }
                    slug = _github_like_repo_slug(request.repository_url or "")
                    if slug:
                        search_payload["repositories"] = [slug]
                    sres = await self.search(search_payload)
                    raw_traces.append({"kind": "nia_search", "response": sres})
                    policy_hits.append({"label": "unified_search", "details": sres})
                except Exception as exc:  # noqa: BLE001
                    logger.warning("nia_search_failed", extra={"error": str(exc)})
                    context_risk_flags.append("unified_search_failed")

        except Exception as exc:  # noqa: BLE001
            logger.exception("nia_gather_unexpected", extra={"error": str(exc)})
            context_risk_flags.append(f"nia_client_error:{exc.__class__.__name__}")

        return {
            "sponsor": "nia",
            "relevant_docs": relevant_docs,
            "policy_hits": policy_hits,
            "architecture_notes": architecture_notes,
            "context_risk_flags": context_risk_flags,
            "raw_traces": raw_traces,
        }

    async def _fallback_search(
        self,
        request: EvaluateRequest,
        query: str,
        relevant_docs: list[dict[str, Any]],
        raw_traces: list[dict[str, Any]],
    ) -> None:
        search_payload: dict[str, Any] = {
            "mode": "query",
            "messages": [{"role": "user", "content": query}],
            "search_mode": "unified",
        }
        slug = _github_like_repo_slug(request.repository_url or "")
        if slug:
            search_payload["repositories"] = [slug]
        try:
            sres = await self.search(search_payload)
            raw_traces.append({"kind": "nia_search_fallback", "response": sres})
            relevant_docs.append({"title": "nia_search", "excerpt": str(sres)[:4000]})
        except Exception as exc:  # noqa: BLE001
            logger.warning("nia_fallback_search_failed", extra={"error": str(exc)})
            raw_traces.append({"kind": "nia_search_fallback_error", "error": str(exc)})

    def _mock_context(self, request: EvaluateRequest) -> dict[str, Any]:
        flags: list[str] = []
        if request.policy_urls:
            flags.append("policies_declared_but_nia_disabled")
        if "auth" in request.action_summary.lower():
            flags.append("authentication_surface_mentioned")
        return {
            "sponsor": "nia",
            "relevant_docs": [
                {
                    "title": "mock_grounding",
                    "excerpt": "NIA_API_KEY not configured; returning deterministic mock grounding.",
                },
            ],
            "policy_hits": [{"label": "mock", "details": request.policy_urls}],
            "architecture_notes": [
                "Mock: prefer live Nia for repository and documentation-grounded answers.",
            ],
            "context_risk_flags": flags,
            "raw_traces": [{"kind": "nia_mock"}],
        }
