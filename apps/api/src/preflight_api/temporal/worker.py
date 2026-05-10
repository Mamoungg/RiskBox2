import asyncio
import logging

from temporalio.client import Client
from temporalio.worker import Worker

from preflight_api.config import get_settings
from preflight_api.temporal.activities import (
    activity_assemble,
    activity_execute_full,
    activity_run_allscale,
    activity_run_greptile,
    activity_run_nia,
    activity_synthesize,
)
from preflight_api.temporal.workflows import SandboxEvaluateWorkflow

logger = logging.getLogger(__name__)


async def _run_worker() -> None:
    settings = get_settings()
    if not settings.temporal_target:
        raise RuntimeError("TEMPORAL_TARGET is required for the Temporal worker")

    client = await Client.connect(
        settings.temporal_target,
        namespace=settings.temporal_namespace,
    )

    worker = Worker(
        client,
        task_queue=settings.temporal_task_queue,
        workflows=[SandboxEvaluateWorkflow],
        activities=[
            activity_run_nia,
            activity_run_greptile,
            activity_run_allscale,
            activity_synthesize,
            activity_assemble,
            activity_execute_full,
        ],
    )

    logger.info(
        "temporal_worker_started",
        extra={"task_queue": settings.temporal_task_queue, "target": settings.temporal_target},
    )
    await worker.run()


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    asyncio.run(_run_worker())


if __name__ == "__main__":
    main()
