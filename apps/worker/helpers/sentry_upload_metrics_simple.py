"""
Simplified Sentry metrics integration for immediate deployment.
Add this to existing upload tasks with minimal changes.
"""

import time
from functools import wraps

import sentry_sdk


def track_upload_simple(task_name: str):
    """
    Simple decorator to add to existing upload tasks.

    Usage:
        @track_upload_simple("upload_processor")
        def run_impl(self, ...):
            ...
    """

    def decorator(func):
        @wraps(func)
        def wrapper(self, db_session, *args, **kwargs):
            # Extract key identifiers
            repoid = kwargs.get("repoid")
            commitid = kwargs.get("commitid")
            upload_obj = kwargs.get("upload_obj")

            # Start transaction
            with sentry_sdk.start_transaction(
                op=f"upload.{task_name}",
                name=f"upload.{task_name}",
                sampled=True,
            ) as transaction:
                # Set basic tags
                if repoid:
                    sentry_sdk.set_tag("repo_id", repoid)
                if commitid:
                    sentry_sdk.set_tag("commit_sha", commitid[:7])
                if upload_obj and hasattr(upload_obj, "id"):
                    sentry_sdk.set_tag("upload_id", upload_obj.id)

                # Track timing
                start_time = time.time()

                try:
                    # Run the actual task
                    result = func(self, db_session, *args, **kwargs)
                    sentry_sdk.set_tag("status", "success")
                    return result

                except Exception as e:
                    sentry_sdk.set_tag("status", "error")
                    sentry_sdk.set_tag("error_type", type(e).__name__)
                    raise

                finally:
                    # Record duration
                    duration = time.time() - start_time
                    sentry_sdk.set_measurement(
                        f"{task_name}.duration", duration, "second"
                    )

                    # Add to breadcrumbs for debugging
                    sentry_sdk.add_breadcrumb(
                        category="upload",
                        message=f"{task_name} completed",
                        level="info",
                        data={
                            "duration": duration,
                            "repo_id": repoid,
                            "task": task_name,
                        },
                    )

        return wrapper

    return decorator


# Usage example - add to existing tasks:
"""
# In tasks/upload.py:
from helpers.sentry_upload_metrics_simple import track_upload_simple

class UploadTask(BaseCodecovTask):
    @track_upload_simple("upload_task")
    def run_impl(self, db_session, **kwargs):
        # ... existing code ...

# In tasks/upload_processor.py:
class UploadProcessorTask(BaseCodecovTask):
    @track_upload_simple("upload_processor")  
    def run_impl(self, db_session, **kwargs):
        # ... existing code ...

# In tasks/upload_finisher.py:
class UploadFinisherTask(BaseCodecovTask):
    @track_upload_simple("upload_finisher")
    def run_impl(self, db_session, **kwargs):
        # ... existing code ...
"""
