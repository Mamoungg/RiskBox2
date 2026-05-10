from __future__ import annotations

import logging
from typing import Any

import httpx

from preflight_api.config import Settings, get_settings
from preflight_api.schemas.evaluate import EvaluateRequest

logger = logging.getLogger(__name__)


class AllscaleClient:
    """
    Payment and settlement risk simulation.

    AllScale public HTTP contracts vary by tenant; this client posts a structured
    simulation payload to `/v1/preflight/payments/simulate` when configured, otherwise
    returns a deterministic sandbox result (no funds moved).
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._client = httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=10.0))

    async def aclose(self) -> None:
        await self._client.aclose()

    def enabled(self) -> bool:
        return bool(self.settings.allscale_api_key)

    async def simulate_payment(self, request: EvaluateRequest) -> dict[str, Any]:
        if request.payment_request is None:
            return {
                "sponsor": "allscale",
                "simulation_status": "skipped",
                "notes": ["No payment_request supplied; payment simulation skipped."],
                "settlement_risk_score": 0,
                "compliance_flags": [],
                "counterparty_signals": {},
                "fraud_heuristics": [],
                "raw": {},
            }

        if not self.enabled():
            return self._mock(request)

        base = self.settings.allscale_base_url.rstrip("/")
        url = f"{base}/v1/preflight/payments/simulate"
        body = {
            "dry_run": True,
            "task_type": request.task_type.value,
            "action_summary": request.action_summary,
            "payment": request.payment_request.model_dump(),
            "repository_url": request.repository_url,
        }
        headers = {
            "Authorization": f"Bearer {self.settings.allscale_api_key}",
            "Content-Type": "application/json",
        }

        try:
            resp = await self._client.post(url, headers=headers, json=body)
            resp.raise_for_status()
            data = resp.json()
            if not isinstance(data, dict):
                return self._mock(request, live_error="non_object_response")
            return self._normalize(data)
        except Exception as exc:  # noqa: BLE001
            logger.warning("allscale_simulation_failed", extra={"error": str(exc)})
            mocked = self._mock(request)
            mocked["compliance_flags"].append(f"allscale_http_error:{exc.__class__.__name__}")
            mocked["raw"] = {"error": str(exc)}
            return mocked

    def _normalize(self, data: dict[str, Any]) -> dict[str, Any]:
        return {
            "sponsor": "allscale",
            "simulation_status": str(data.get("status", "completed")),
            "notes": list(data.get("notes", []) or []),
            "settlement_risk_score": int(data.get("settlement_risk_score", 0)),
            "compliance_flags": list(data.get("compliance_flags", []) or []),
            "counterparty_signals": dict(data.get("counterparty_signals", {}) or {}),
            "fraud_heuristics": list(data.get("fraud_heuristics", []) or []),
            "raw": data,
        }

    def _mock(self, request: EvaluateRequest, live_error: str | None = None) -> dict[str, Any]:
        pr = request.payment_request
        assert pr is not None
        flags: list[str] = []
        if pr.amount >= 10_000:
            flags.append("high_amount_requires_additional_approval")
        if pr.currency.upper() != "USD":
            flags.append("non_usd_flow_extra_fx_checks")
        if "@" in pr.recipient and pr.recipient.endswith((".ru", ".cn")):
            flags.append("counterparty_domain_extra_scrutiny")
        notes = [
            "ALLSCALE_API_KEY not configured; returning deterministic simulation only.",
            "No funds are moved in mock mode.",
        ]
        if live_error:
            notes.append(f"Live call issue: {live_error}")
        score = min(100, int(10 + pr.amount / 500 + (20 if flags else 0)))
        return {
            "sponsor": "allscale",
            "simulation_status": "mock_completed",
            "notes": notes,
            "settlement_risk_score": score,
            "compliance_flags": flags,
            "counterparty_signals": {"recipient": pr.recipient, "invoice": pr.invoice_reference},
            "fraud_heuristics": ["velocity_not_evaluated_in_mock", "bank_holidays_not_evaluated_in_mock"],
            "raw": {},
        }
