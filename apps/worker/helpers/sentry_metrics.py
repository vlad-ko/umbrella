"""
Sentry performance metrics for upload and notification tracking.
"""

import time
from contextlib import contextmanager
from functools import wraps
from typing import Any

import sentry_sdk
from sentry_sdk import set_measurement, set_tag


def track_upload_performance(
    repo_id: int,
    owner_id: int,
    upload_id: int | None = None,
    commit_sha: str | None = None,
):
    """
    Decorator to track upload performance metrics in Sentry.

    Usage:
        @track_upload_performance(repo_id=123, owner_id=456)
        def process_upload(...):
            ...
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            with sentry_sdk.start_transaction(
                op="upload.process",
                name=f"upload.{func.__name__}",
                sampled=True,
            ) as transaction:
                # Set context tags
                set_tag("repo_id", repo_id)
                set_tag("owner_id", owner_id)
                if upload_id:
                    set_tag("upload_id", upload_id)
                if commit_sha:
                    set_tag("commit_sha", commit_sha[:7])  # Short SHA

                # Track timing
                start_time = time.time()

                try:
                    result = func(*args, **kwargs)
                    set_tag("upload.status", "success")
                    return result
                except Exception as e:
                    set_tag("upload.status", "error")
                    set_tag("upload.error_type", type(e).__name__)
                    raise
                finally:
                    # Record duration
                    duration = time.time() - start_time
                    set_measurement("upload.duration", duration, "second")

        return wrapper

    return decorator


@contextmanager
def track_upload_stage(stage_name: str, **tags):
    """
    Context manager to track individual upload stages.

    Usage:
        with track_upload_stage("file_parsing", repo_id=123):
            # parse upload file
            ...
    """
    with sentry_sdk.start_span(op=f"upload.stage.{stage_name}") as span:
        # Set tags for this stage
        for key, value in tags.items():
            span.set_tag(key, value)

        start_time = time.time()

        try:
            yield span
        finally:
            # Record stage duration
            duration = time.time() - start_time
            span.set_data("duration_seconds", duration)
            set_measurement(f"upload.stage.{stage_name}.duration", duration, "second")


def track_notification_latency(
    upload_start_time: float, notification_type: str, repo_id: int, **extra_tags
):
    """
    Track the latency between upload start and notification sent.

    Args:
        upload_start_time: Unix timestamp when upload started
        notification_type: Type of notification (comment, status, etc.)
        repo_id: Repository ID
        **extra_tags: Additional tags to set
    """
    latency = time.time() - upload_start_time

    with sentry_sdk.start_span(op="notification.latency") as span:
        span.set_tag("notification_type", notification_type)
        span.set_tag("repo_id", repo_id)

        for key, value in extra_tags.items():
            span.set_tag(key, value)

        # Set measurements
        set_measurement("notification.latency", latency, "second")
        set_measurement(f"notification.{notification_type}.latency", latency, "second")

        # Set performance thresholds
        if latency > 300:  # 5 minutes
            span.set_tag("performance.issue", "high_latency")
        elif latency > 600:  # 10 minutes
            span.set_tag("performance.issue", "critical_latency")


def record_upload_metrics(metrics: dict[str, Any]):
    """
    Record custom upload metrics to Sentry.

    Args:
        metrics: Dictionary of metric name -> value pairs
    """
    transaction = sentry_sdk.Hub.current.scope.transaction
    if transaction:
        for metric_name, value in metrics.items():
            if isinstance(value, (int, float)):
                set_measurement(f"upload.{metric_name}", value)
            else:
                transaction.set_tag(f"upload.{metric_name}", str(value))


class UploadPerformanceTracker:
    """
    Class to track upload performance across multiple stages.
    """

    def __init__(self, repo_id: int, owner_id: int, upload_id: int | None = None):
        self.repo_id = repo_id
        self.owner_id = owner_id
        self.upload_id = upload_id
        self.start_time = time.time()
        self.stage_times = {}
        self.transaction = None

    def __enter__(self):
        self.transaction = sentry_sdk.start_transaction(
            op="upload.full_flow",
            name="upload.full_processing_flow",
            sampled=True,
        )
        self.transaction.__enter__()

        # Set base tags
        set_tag("repo_id", self.repo_id)
        set_tag("owner_id", self.owner_id)
        if self.upload_id:
            set_tag("upload_id", self.upload_id)

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            set_tag("upload.status", "error")
            set_tag("upload.error_type", exc_type.__name__)
        else:
            set_tag("upload.status", "success")

        # Record total duration
        total_duration = time.time() - self.start_time
        set_measurement("upload.total_duration", total_duration, "second")

        # Record stage breakdown
        for stage, duration in self.stage_times.items():
            set_measurement(f"upload.stage.{stage}.duration", duration, "second")

        if self.transaction:
            self.transaction.__exit__(exc_type, exc_val, exc_tb)

    def track_stage(self, stage_name: str):
        """
        Track a specific stage of upload processing.
        """
        return self._StageTracker(self, stage_name)

    class _StageTracker:
        def __init__(self, parent: "UploadPerformanceTracker", stage_name: str):
            self.parent = parent
            self.stage_name = stage_name
            self.start_time = None
            self.span = None

        def __enter__(self):
            self.start_time = time.time()
            self.span = sentry_sdk.start_span(op=f"upload.stage.{self.stage_name}")
            self.span.__enter__()
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            duration = time.time() - self.start_time
            self.parent.stage_times[self.stage_name] = duration

            if self.span:
                self.span.set_data("duration_seconds", duration)
                self.span.__exit__(exc_type, exc_val, exc_tb)
