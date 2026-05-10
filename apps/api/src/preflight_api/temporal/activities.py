from __future__ import annotations

from typing import Any

from temporalio import activity

from preflight_api.schemas.evaluate import EvaluateRequest
from preflight_api.services.evaluation import (
    build_response,
    execute_evaluation,
    run_allscale,
    run_greptile,
    run_nia,
    run_synthesis_bundle,
)


@activity.defn
async def activity_run_nia(payload: dict[str, Any]) -> dict[str, Any]:
    request = EvaluateRequest.model_validate(payload["request"])
    return await run_nia(request)


@activity.defn
async def activity_run_greptile(payload: dict[str, Any]) -> dict[str, Any]:
    request = EvaluateRequest.model_validate(payload["request"])
    return await run_greptile(request)


@activity.defn
async def activity_run_allscale(payload: dict[str, Any]) -> dict[str, Any]:
    request = EvaluateRequest.model_validate(payload["request"])
    return await run_allscale(request)


@activity.defn
async def activity_synthesize(payload: dict[str, Any]) -> dict[str, Any]:
    request = EvaluateRequest.model_validate(payload["request"])
    return await run_synthesis_bundle(
        request,
        payload["context"],
        payload["code"],
        payload["payment"],
    )


@activity.defn
async def activity_execute_full(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Single-activity fallback used when the worker should mirror the API path exactly.
    """
    request = EvaluateRequest.model_validate(payload["request"])
    run_id = str(payload.get("run_id"))
    return await execute_evaluation(request, run_id=run_id)


@activity.defn
async def activity_assemble(payload: dict[str, Any]) -> dict[str, Any]:
    request = EvaluateRequest.model_validate(payload["request"])
    return build_response(
        str(payload["run_id"]),
        request,
        payload["context"],
        payload["code"],
        payload["payment"],
        payload["llm"],
        dict(payload.get("timings") or {}),
    )
