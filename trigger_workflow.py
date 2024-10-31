import asyncio
from uuid import uuid4

from temporalio.client import Client, WorkflowFailureError

from workflows import FailingWorkflow


async def main():
    client = await Client.connect("localhost:7233")

    try:
        result = await client.execute_workflow(
            FailingWorkflow.run,
            id=str(uuid4()),
            task_queue="my_queue",
        )

        print(f"result: {result}")

    except WorkflowFailureError:
        print("workflow failed")


if __name__ == "__main__":
    asyncio.run(main())
