from __future__ import annotations

import asyncio
from datetime import timedelta
from typing import Any

from temporalio import workflow


@workflow.defn
class SandboxEvaluateWorkflow:
    @workflow.run
    async def run(self, payload: dict[str, Any]) -> dict[str, Any]:
        with workflow.unsafe.imports_passed_through():
            from preflight_api.temporal.activities import (
                activity_assemble,
                activity_run_allscale,
                activity_run_greptile,
                activity_run_nia,
                activity_synthesize,
            )

        run_id = str(payload["run_id"])
        body: dict[str, Any] = {"run_id": run_id, "request": payload["request"]}

        nia_task = workflow.execute_activity(
            activity_run_nia,
            body,
            start_to_close_timeout=timedelta(minutes=10),
        )
        greptile_task = workflow.execute_activity(
            activity_run_greptile,
            body,
            start_to_close_timeout=timedelta(minutes=10),
        )
        allscale_task = workflow.execute_activity(
            activity_run_allscale,
            body,
            start_to_close_timeout=timedelta(minutes=10),
        )

        context, code, payment = await asyncio.gather(nia_task, greptile_task, allscale_task)

        llm_payload = await workflow.execute_activity(
            activity_synthesize,
            {
                "run_id": run_id,
                "request": payload["request"],
                "context": context,
                "code": code,
                "payment": payment,
            },
            start_to_close_timeout=timedelta(minutes=8),
        )

        return await workflow.execute_activity(
            activity_assemble,
            {
                "run_id": run_id,
                "request": payload["request"],
                "context": context,
                "code": code,
                "payment": payment,
                "llm": llm_payload,
                "timings": {
                    "note": "Per-activity timings are aggregated inside each Temporal activity.",
                },
            },
            start_to_close_timeout=timedelta(minutes=2),
        )
