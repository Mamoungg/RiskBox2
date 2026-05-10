from __future__ import annotations

import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from preflight_api.config import get_settings
from preflight_api.db import get_session
from preflight_api.deps import require_api_key
from preflight_api.models import SandboxRun
from preflight_api.redis_client import get_redis
from preflight_api.schemas.evaluate import EvaluateRequest, EvaluateResponse
from preflight_api.security import hash_api_key
from preflight_api.services.cache import get_cached_eval, set_cached_eval
from preflight_api.services.evaluation import execute_evaluation
from preflight_api.temporal.client import run_evaluate_workflow

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/sandbox", tags=["sandbox"])


@router.post("/evaluate", response_model=EvaluateResponse)
async def evaluate(
    request: Request,
    body: EvaluateRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
    _api_key: Annotated[str, Depends(require_api_key)],
) -> EvaluateResponse:
    settings = get_settings()
    redis = get_redis()

    cache_payload = body.model_dump()
    tenant = getattr(request.state, "api_key_fingerprint", None)
    cached = await get_cached_eval(redis, cache_payload, tenant)
    if cached:
        logger.info("evaluate_cache_hit")
        return EvaluateResponse.model_validate(cached)

    if settings.temporal_target:
        result = await run_evaluate_workflow(cache_payload)
    else:
        result = await execute_evaluation(body)

    await set_cached_eval(redis, cache_payload, result, tenant)

    run = SandboxRun(
        id=uuid.UUID(str(result["run_id"])),
        verdict=str(result["status"]),
        risk_score=int(result["risk_score"]),
        request_payload=cache_payload,
        response_payload=result,
        api_key_prefix=hash_api_key(_api_key)[:12],
    )
    session.add(run)
    await session.commit()

    logger.info(
        "evaluate_completed",
        extra={"run_id": result["run_id"], "status": result["status"], "risk_score": result["risk_score"]},
    )

    return EvaluateResponse.model_validate(result)
