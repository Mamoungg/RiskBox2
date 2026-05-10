from __future__ import annotations

import uuid
from typing import Any

from temporalio.client import Client

from preflight_api.config import get_settings
from preflight_api.temporal.workflows import SandboxEvaluateWorkflow


async def run_evaluate_workflow(request_dict: dict[str, Any]) -> dict[str, Any]:
    settings = get_settings()
    if not settings.temporal_target:
        raise RuntimeError("TEMPORAL_TARGET is not configured")

    client = await Client.connect(
        settings.temporal_target,
        namespace=settings.temporal_namespace,
    )

    run_id = str(uuid.uuid4())
    workflow_id = f"sandbox-evaluate-{run_id}"

    handle = await client.start_workflow(
        SandboxEvaluateWorkflow.run,
        {"run_id": run_id, "request": request_dict},
        id=workflow_id,
        task_queue=settings.temporal_task_queue,
    )
    return await handle.result()
