from __future__ import annotations

import asyncio
import time
import uuid
from typing import Any

from preflight_api.schemas.evaluate import EvaluateRequest, EvaluateResponse, Verdict
from preflight_api.services.allscale import AllscaleClient
from preflight_api.services.greptile import GreptileClient
from preflight_api.services.llm import apply_constraints, synthesize
from preflight_api.services.nia import NiaClient


async def run_nia(request: EvaluateRequest) -> dict[str, Any]:
    client = NiaClient()
    try:
        return await client.gather(request)
    finally:
        await client.aclose()


async def run_greptile(request: EvaluateRequest) -> dict[str, Any]:
    client = GreptileClient()
    try:
        return await client.analyze(request)
    finally:
        await client.aclose()


async def run_allscale(request: EvaluateRequest) -> dict[str, Any]:
    client = AllscaleClient()
    try:
        return await client.simulate_payment(request)
    finally:
        await client.aclose()


async def run_synthesis_bundle(
    request: EvaluateRequest,
    context: dict[str, Any],
    code: dict[str, Any],
    payment: dict[str, Any],
) -> dict[str, Any]:
    return await synthesize(request, context, code, payment)


def build_response(
    run_id: str,
    request: EvaluateRequest,
    context: dict[str, Any],
    code: dict[str, Any],
    payment: dict[str, Any],
    llm_payload: dict[str, Any],
    timings: dict[str, float],
) -> dict[str, Any]:
    verdict, risk_score, reasons = apply_constraints(request, llm_payload)
    raw = llm_payload.get("raw_json") or {}
    summary = str(raw.get("summary", "Evaluation complete."))
    safer = str(
        raw.get(
            "safer_alternative",
            "Reduce scope, add guardrails, and obtain explicit human approval.",
        ),
    )
    response = EvaluateResponse(
        run_id=run_id,
        status=verdict,
        risk_score=risk_score,
        summary=summary,
        reasons=reasons,
        safer_alternative=safer,
        context_assessment=context,
        code_assessment=code,
        payment_assessment=payment,
        llm_synthesis=llm_payload,
        timings=timings,
    )
    return response.model_dump()


async def execute_evaluation(request: EvaluateRequest, run_id: str | None = None) -> dict[str, Any]:
    """
    Parallel sponsor calls followed by LLM synthesis. Shared by API and Temporal.
    """
    rid = run_id or str(uuid.uuid4())
    timings: dict[str, float] = {}

    async def measure(label: str, coro: Any) -> Any:
        t0 = time.perf_counter()
        try:
            return await coro
        finally:
            timings[label] = (time.perf_counter() - t0) * 1000

    context, code, payment = await asyncio.gather(
        measure("nia_ms", run_nia(request)),
        measure("greptile_ms", run_greptile(request)),
        measure("allscale_ms", run_allscale(request)),
    )

    t0 = time.perf_counter()
    llm_payload = await run_synthesis_bundle(request, context, code, payment)
    timings["llm_ms"] = (time.perf_counter() - t0) * 1000

    return build_response(rid, request, context, code, payment, llm_payload, timings)
