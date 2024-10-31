import os
import asyncio

from temporalio.client import Client
from temporalio.worker import Worker

import sentry_sdk

from workflows import FailingWorkflow
from sentry_interceptor import SentryInterceptor


async def main():
    sentry_sdk.init(
        dsn=os.environ.get("SENTRY_DSN"),
    )

    client = await Client.connect("localhost:7233", namespace="default")
    worker = Worker(
        client,
        task_queue="my_queue",
        workflows=[FailingWorkflow],
        activities=[],
        interceptors=[SentryInterceptor()],
    )
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
