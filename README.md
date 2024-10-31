# Sentry + Temporal issue demo


This repo is just a demo to be able to reproduce an issue between Sentry and Temporal.

The sentry interceptor was taken from the Temporal demos: https://github.com/temporalio/samples-python/blob/main/sentry/interceptor.py

# How to reproduce

0. Prerequisites: a DSN for a usable Sentry project, the Temporal cli, Python and a virtualenv
1. Install dependencies in your virtualenv: `pip install -r requirements.txt`
2. Launch the Temporal dev server: `temporal server start-dev`
3. Launch the worker: `SENTRY_DSN="https://...YOUR SENTRY DSN..." python run_worker.py`
4. Trigger the workflow: `python trigger_workflow.py`

# First problem

In the worker output, you should see an error like this:

```
Traceback (most recent call last):
  File "/home/fisa/venvs/sentry_temporal_issue/lib/python3.11/site-packages/temporalio/worker/_workflow_instance.py", line 377, in activate
    self._run_once(check_conditions=index == 1 or index == 2)
  File "/home/fisa/venvs/sentry_temporal_issue/lib/python3.11/site-packages/temporalio/worker/_workflow_instance.py", line 1790, in _run_once
    raise self._current_activation_error
  File "/home/fisa/venvs/sentry_temporal_issue/lib/python3.11/site-packages/temporalio/worker/_workflow_instance.py", line 1808, in _run_top_level_workflow_function
    await coro
  File "/home/fisa/venvs/sentry_temporal_issue/lib/python3.11/site-packages/temporalio/worker/_workflow_instance.py", line 857, in run_workflow
    result = await self._inbound.execute_workflow(input)
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/fisa/devel/sentry_temporal_issue/sentry_interceptor.py", line 51, in execute_workflow
    with Hub(Hub.current):
             ^^^^^^^^^^^
  File "/home/fisa/venvs/sentry_temporal_issue/lib/python3.11/site-packages/sentry_sdk/hub.py", line 103, in current
    with _suppress_hub_deprecation_warning():
  File "/usr/lib/python3.11/contextlib.py", line 137, in __enter__
    return next(self.gen)
           ^^^^^^^^^^^^^^
  File "/home/fisa/venvs/sentry_temporal_issue/lib/python3.11/site-packages/sentry_sdk/hub.py", line 87, in _suppress_hub_deprecation_warning
    with warnings.catch_warnings():
         ^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/lib/python3.11/warnings.py", line 450, in __init__
    self._module = sys.modules['warnings'] if module is None else module
                   ~~~~~~~~~~~^^^^^^^^^^^^
  File "/home/fisa/venvs/sentry_temporal_issue/lib/python3.11/site-packages/temporalio/worker/workflow_sandbox/_importer.py", line 393, in __getitem__
    return self.current[key]
           ~~~~~~~~~~~~^^^^^
KeyError: 'warnings'
```

# Possible solution to first problem

This sounds like deep down its stack, Sentry assumes the `warnings` module is imported (maye it imports it before).
But during the execution, Temporal sanitizes that module and it's no longer usable to Sentry, so its assumption is no longer true.

One simple solution is to re-import `warnings`. Though I'm not really sure of the consequences that can have.

You can do that by adding a simple `import warnings` in the first line of the `_SentryWorkflowInterceptor.execute_workflow` method, like this:

```python
class _SentryWorkflowInterceptor(WorkflowInboundInterceptor):
    async def execute_workflow(self, input: ExecuteWorkflowInput) -> Any:

        import warnings  # <--- HERE

        with Hub(Hub.current):
            ...
```

This solves the `KeyError: 'warnings'` issue, but a new one arises:

# Second problem

After that fix, a new error is raised when trying to use sentry:

```
Traceback (most recent call last):
  File "/home/fisa/venvs/sentry_temporal_issue/lib/python3.11/site-packages/temporalio/worker/_workflow_instance.py", line 377, in activate
    self._run_once(check_conditions=index == 1 or index == 2)
  File "/home/fisa/venvs/sentry_temporal_issue/lib/python3.11/site-packages/temporalio/worker/_workflow_instance.py", line 1790, in _run_once
    raise self._current_activation_error
  File "/home/fisa/venvs/sentry_temporal_issue/lib/python3.11/site-packages/temporalio/worker/_workflow_instance.py", line 1808, in _run_top_level_workflow_function
    await coro
  File "/home/fisa/venvs/sentry_temporal_issue/lib/python3.11/site-packages/temporalio/worker/_workflow_instance.py", line 857, in run_workflow
    result = await self._inbound.execute_workflow(input)
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/fisa/devel/sentry_temporal_issue/sentry_interceptor.py", line 69, in execute_workflow
    capture_exception()
  File "/home/fisa/venvs/sentry_temporal_issue/lib/python3.11/site-packages/sentry_sdk/api.py", line 184, in capture_exception
    return get_current_scope().capture_exception(error, scope=scope, **scope_kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/fisa/venvs/sentry_temporal_issue/lib/python3.11/site-packages/sentry_sdk/scope.py", line 1210, in capture_exception
    event, hint = event_from_exception(
                  ^^^^^^^^^^^^^^^^^^^^^
  File "/home/fisa/venvs/sentry_temporal_issue/lib/python3.11/site-packages/sentry_sdk/utils.py", line 1111, in event_from_exception
    "values": exceptions_from_error_tuple(
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/fisa/venvs/sentry_temporal_issue/lib/python3.11/site-packages/sentry_sdk/utils.py", line 979, in exceptions_from_error_tuple
    single_exception_from_error_tuple(
  File "/home/fisa/venvs/sentry_temporal_issue/lib/python3.11/site-packages/sentry_sdk/utils.py", line 797, in single_exception_from_error_tuple
    frames = [
             ^
  File "/home/fisa/venvs/sentry_temporal_issue/lib/python3.11/site-packages/sentry_sdk/utils.py", line 798, in <listcomp>
    serialize_frame(
  File "/home/fisa/venvs/sentry_temporal_issue/lib/python3.11/site-packages/sentry_sdk/utils.py", line 671, in serialize_frame
    from sentry_sdk.serializer import serialize
  File "/home/fisa/venvs/sentry_temporal_issue/lib/python3.11/site-packages/temporalio/worker/workflow_sandbox/_importer.py", line 441, in __call__
    return self.current(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/fisa/venvs/sentry_temporal_issue/lib/python3.11/site-packages/temporalio/worker/workflow_sandbox/_importer.py", line 234, in _import
    mod = importlib.__import__(name, globals, locals, fromlist, level)
          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "<frozen importlib._bootstrap>", line 1283, in __import__
  File "<frozen importlib._bootstrap>", line 1204, in _gcd_import
  File "<frozen importlib._bootstrap>", line 1176, in _find_and_load
  File "<frozen importlib._bootstrap>", line 1126, in _find_and_load_unlocked
  File "<frozen importlib._bootstrap>", line 241, in _call_with_frames_removed
  File "<frozen importlib._bootstrap>", line 1204, in _gcd_import
  File "<frozen importlib._bootstrap>", line 1176, in _find_and_load
  File "<frozen importlib._bootstrap>", line 1147, in _find_and_load_unlocked
  File "<frozen importlib._bootstrap>", line 690, in _load_unlocked
  File "<frozen importlib._bootstrap_external>", line 940, in exec_module
  File "<frozen importlib._bootstrap>", line 241, in _call_with_frames_removed
  File "/home/fisa/venvs/sentry_temporal_issue/lib/python3.11/site-packages/sentry_sdk/__init__.py", line 1, in <module>
    from sentry_sdk.scope import Scope
  File "/home/fisa/venvs/sentry_temporal_issue/lib/python3.11/site-packages/temporalio/worker/workflow_sandbox/_importer.py", line 441, in __call__
    return self.current(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/fisa/venvs/sentry_temporal_issue/lib/python3.11/site-packages/temporalio/worker/workflow_sandbox/_importer.py", line 234, in _import
    mod = importlib.__import__(name, globals, locals, fromlist, level)
          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "<frozen importlib._bootstrap>", line 1283, in __import__
  File "<frozen importlib._bootstrap>", line 1204, in _gcd_import
  File "<frozen importlib._bootstrap>", line 1176, in _find_and_load
  File "<frozen importlib._bootstrap>", line 1147, in _find_and_load_unlocked
  File "<frozen importlib._bootstrap>", line 690, in _load_unlocked
  File "<frozen importlib._bootstrap_external>", line 940, in exec_module
  File "<frozen importlib._bootstrap>", line 241, in _call_with_frames_removed
  File "/home/fisa/venvs/sentry_temporal_issue/lib/python3.11/site-packages/sentry_sdk/scope.py", line 1709, in <module>
    from sentry_sdk.client import NonRecordingClient
  File "/home/fisa/venvs/sentry_temporal_issue/lib/python3.11/site-packages/temporalio/worker/workflow_sandbox/_importer.py", line 441, in __call__
    return self.current(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/fisa/venvs/sentry_temporal_issue/lib/python3.11/site-packages/temporalio/worker/workflow_sandbox/_importer.py", line 234, in _import
    mod = importlib.__import__(name, globals, locals, fromlist, level)
          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "<frozen importlib._bootstrap>", line 1283, in __import__
  File "<frozen importlib._bootstrap>", line 1204, in _gcd_import
  File "<frozen importlib._bootstrap>", line 1176, in _find_and_load
  File "<frozen importlib._bootstrap>", line 1147, in _find_and_load_unlocked
  File "<frozen importlib._bootstrap>", line 690, in _load_unlocked
  File "<frozen importlib._bootstrap_external>", line 940, in exec_module
  File "<frozen importlib._bootstrap>", line 241, in _call_with_frames_removed
  File "/home/fisa/venvs/sentry_temporal_issue/lib/python3.11/site-packages/sentry_sdk/client.py", line 26, in <module>
    from sentry_sdk.transport import BaseHttpTransport, make_transport
  File "/home/fisa/venvs/sentry_temporal_issue/lib/python3.11/site-packages/temporalio/worker/workflow_sandbox/_importer.py", line 441, in __call__
    return self.current(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/fisa/venvs/sentry_temporal_issue/lib/python3.11/site-packages/temporalio/worker/workflow_sandbox/_importer.py", line 234, in _import
    mod = importlib.__import__(name, globals, locals, fromlist, level)
          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "<frozen importlib._bootstrap>", line 1283, in __import__
  File "<frozen importlib._bootstrap>", line 1204, in _gcd_import
  File "<frozen importlib._bootstrap>", line 1176, in _find_and_load
  File "<frozen importlib._bootstrap>", line 1147, in _find_and_load_unlocked
  File "<frozen importlib._bootstrap>", line 690, in _load_unlocked
  File "<frozen importlib._bootstrap_external>", line 940, in exec_module
  File "<frozen importlib._bootstrap>", line 241, in _call_with_frames_removed
  File "/home/fisa/venvs/sentry_temporal_issue/lib/python3.11/site-packages/sentry_sdk/transport.py", line 18, in <module>
    import urllib3
  File "/home/fisa/venvs/sentry_temporal_issue/lib/python3.11/site-packages/temporalio/worker/workflow_sandbox/_importer.py", line 441, in __call__
    return self.current(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/fisa/venvs/sentry_temporal_issue/lib/python3.11/site-packages/temporalio/worker/workflow_sandbox/_importer.py", line 234, in _import
    mod = importlib.__import__(name, globals, locals, fromlist, level)
          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "<frozen importlib._bootstrap>", line 1283, in __import__
  File "<frozen importlib._bootstrap>", line 1204, in _gcd_import
  File "<frozen importlib._bootstrap>", line 1176, in _find_and_load
  File "<frozen importlib._bootstrap>", line 1147, in _find_and_load_unlocked
  File "<frozen importlib._bootstrap>", line 690, in _load_unlocked
  File "<frozen importlib._bootstrap_external>", line 940, in exec_module
  File "<frozen importlib._bootstrap>", line 241, in _call_with_frames_removed
  File "/home/fisa/venvs/sentry_temporal_issue/lib/python3.11/site-packages/urllib3/__init__.py", line 14, in <module>
    from . import exceptions
  File "/home/fisa/venvs/sentry_temporal_issue/lib/python3.11/site-packages/temporalio/worker/workflow_sandbox/_importer.py", line 441, in __call__
    return self.current(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/fisa/venvs/sentry_temporal_issue/lib/python3.11/site-packages/temporalio/worker/workflow_sandbox/_importer.py", line 234, in _import
    mod = importlib.__import__(name, globals, locals, fromlist, level)
          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "<frozen importlib._bootstrap>", line 1303, in __import__
  File "<frozen importlib._bootstrap>", line 1232, in _handle_fromlist
  File "<frozen importlib._bootstrap>", line 241, in _call_with_frames_removed
  File "<frozen importlib._bootstrap>", line 1204, in _gcd_import
  File "<frozen importlib._bootstrap>", line 1176, in _find_and_load
  File "<frozen importlib._bootstrap>", line 1147, in _find_and_load_unlocked
  File "<frozen importlib._bootstrap>", line 690, in _load_unlocked
  File "<frozen importlib._bootstrap_external>", line 940, in exec_module
  File "<frozen importlib._bootstrap>", line 241, in _call_with_frames_removed
  File "/home/fisa/venvs/sentry_temporal_issue/lib/python3.11/site-packages/urllib3/exceptions.py", line 247, in <module>
    class IncompleteRead(HTTPError, httplib_IncompleteRead):
TypeError: metaclass conflict: the metaclass of a derived class must be a (non-strict) subclass of the metaclasses of all its bases
```

This can also be fixed in a way I'm not at all sure if it's ok:

# Possible solution to second problem

If we wrap the call to Sentry's `capture_exception()` of the `_SentryWorkflowInterceptor.execute_workflow` method with `workflow.unsafe.imports_passed_through()`, the error goes away. 
Like this:

```
class _SentryWorkflowInterceptor(WorkflowInboundInterceptor):
    async def execute_workflow(self, input: ExecuteWorkflowInput) -> Any:
        ...
        if not workflow.unsafe.is_replaying():
            with workflow.unsafe.sandbox_unrestricted():

                with workflow.unsafe.imports_passed_through():  # <--- HERE

                    capture_exception()
        ...
```
