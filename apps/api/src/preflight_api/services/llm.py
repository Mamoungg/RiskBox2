from __future__ import annotations

import json
import logging
import re
from typing import Any

import litellm

from preflight_api.config import get_settings
from preflight_api.schemas.evaluate import EvaluateRequest, Verdict

logger = logging.getLogger(__name__)


class LLMSynthesisError(RuntimeError):
    pass


def _extract_json_object(text: str) -> dict[str, Any]:
    text = text.strip()
    try:
        val = json.loads(text)
        if isinstance(val, dict):
            return val
    except json.JSONDecodeError:
        pass
    m = re.search(r"\{[\s\S]*\}\s*$", text)
    if m:
        val = json.loads(m.group(0))
        if isinstance(val, dict):
            return val
    raise LLMSynthesisError("unable_to_parse_json")


async def synthesize(
    request: EvaluateRequest,
    context: dict[str, Any],
    code: dict[str, Any],
    payment: dict[str, Any],
) -> dict[str, Any]:
    settings = get_settings()
    system = (
        "You are a staff-level risk officer assisting an autonomous agent preflight sandbox. "
        "Return ONLY valid JSON with keys: "
        "status (SAFE|NEEDS_APPROVAL|BLOCKED), risk_score (0-100 integer), summary (string), "
        "reasons (array of strings), safer_alternative (string), citations (array of objects "
        "with source and note). "
        "Be conservative when authentication, payments, or policy ambiguity appear."
    )
    user_payload = {
        "task_type": request.task_type.value,
        "action_summary": request.action_summary,
        "constraints": request.constraints.model_dump(),
        "nia_context": context,
        "greptile_code": code,
        "allscale_payment": payment,
    }
    user = json.dumps(user_payload, ensure_ascii=False)

    try:
        resp = await litellm.acompletion(
            model=settings.litellm_model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
        )
        content = resp.choices[0].message.content or "{}"
        parsed = _extract_json_object(content)
        return {
            "model": settings.litellm_model,
            "raw_json": parsed,
            "usage": getattr(resp, "usage", None),
        }
    except Exception as exc:  # noqa: BLE001
        logger.warning("llm_synthesis_failed", extra={"error": str(exc)})
        return {
            "model": settings.litellm_model,
            "raw_json": _mock_json_verdict(request, context, code, payment),
            "usage": None,
            "error": str(exc),
        }


def _mock_json_verdict(
    request: EvaluateRequest,
    context: dict[str, Any],
    code: dict[str, Any],
    payment: dict[str, Any],
) -> dict[str, Any]:
    score = 25
    reasons: list[str] = []

    flags = list(context.get("context_risk_flags", []))
    if flags:
        score += min(30, 5 * len(flags))
        reasons.extend(flags)

    for rf in code.get("risk_flags", [])[:5]:
        score += 8
        reasons.append(f"code:{rf}")

    settlement = int(payment.get("settlement_risk_score", 0) or 0)
    score = min(100, score + settlement // 3)

    if request.payment_request and request.payment_request.amount >= 5000:
        score += 10
        reasons.append("payment_amount_elevated")

    if "auth" in request.action_summary.lower() or "password" in request.action_summary.lower():
        score += 15
        reasons.append("authentication_surface")

    status = Verdict.SAFE.value
    if score >= 80:
        status = Verdict.BLOCKED.value
    elif score >= 55 or request.constraints.max_risk_score < score:
        status = Verdict.NEEDS_APPROVAL.value

    return {
        "status": status,
        "risk_score": int(min(100, score)),
        "summary": "Heuristic mock synthesis used because the LLM gateway call failed or keys are missing.",
        "reasons": reasons or ["no_specific_flags"],
        "safer_alternative": (
            "Narrow the change behind a feature flag, add automated tests, "
            "and require human approval before payment or auth merges."
        ),
        "citations": [
            {"source": "nia", "note": "context flags and excerpts"},
            {"source": "greptile", "note": "code risk heuristics"},
            {"source": "allscale", "note": "payment simulation"},
        ],
    }


def apply_constraints(
    request: EvaluateRequest,
    synthesis: dict[str, Any],
) -> tuple[Verdict, int, list[str]]:
    raw = synthesis.get("raw_json") or {}
    status_raw = str(raw.get("status", Verdict.NEEDS_APPROVAL.value)).upper()
    try:
        verdict = Verdict(status_raw)
    except ValueError:
        verdict = Verdict.NEEDS_APPROVAL

    risk_score = int(raw.get("risk_score", 50))
    risk_score = max(0, min(100, risk_score))

    reasons = list(raw.get("reasons", []) or [])
    if not isinstance(reasons, list):
        reasons = [str(reasons)]

    max_allowed = request.constraints.max_risk_score
    if risk_score > max_allowed and verdict == Verdict.SAFE:
        verdict = Verdict.NEEDS_APPROVAL
        reasons.append(f"risk_score_{risk_score}_exceeds_policy_max_{max_allowed}")

    if risk_score >= 90 and verdict != Verdict.BLOCKED:
        verdict = Verdict.BLOCKED
        reasons.append("automatic_block_for_extreme_score")

    if request.constraints.require_citations:
        citations = raw.get("citations") or []
        if not citations:
            if verdict == Verdict.SAFE:
                verdict = Verdict.NEEDS_APPROVAL
            reasons.append("citations_required_but_missing")

    return verdict, risk_score, [str(r) for r in reasons]
