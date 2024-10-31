import logging

from temporalio import workflow


@workflow.defn
class FailingWorkflow:
    @workflow.run
    async def run(self):
        print("Running sample failing workflow")

        1 / 0

        return "done"
