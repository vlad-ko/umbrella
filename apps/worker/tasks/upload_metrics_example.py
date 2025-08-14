"""
Example of how to integrate Sentry performance metrics into upload tasks.
This shows the pattern to apply to existing upload tasks.
"""

import sentry_sdk

from database.models import Commit
from helpers.checkpoint_logger import from_kwargs
from helpers.checkpoint_logger.flows import UploadFlow
from helpers.sentry_metrics import (
    UploadPerformanceTracker,
    track_notification_latency,
    track_upload_performance,
    track_upload_stage,
)
from tasks.base import BaseCodecovTask


class UploadTaskWithMetrics(BaseCodecovTask):
    """Example of upload task with enhanced Sentry metrics."""

    def run_impl(
        self,
        db_session,
        *,
        repoid: int,
        commitid: str,
        commit_yaml,
        arguments_list=None,
        **kwargs,
    ):
        # Get repository and owner info
        commit = (
            db_session.query(Commit).filter_by(repoid=repoid, commitid=commitid).first()
        )

        # Start performance tracking for entire upload flow
        with UploadPerformanceTracker(
            repo_id=repoid,
            owner_id=commit.repository.ownerid if commit else None,
        ) as tracker:
            # Track commit preparation stage
            with tracker.track_stage("commit_preparation"):
                # Load checkpoint data
                checkpoints = from_kwargs(UploadFlow, kwargs)

                # Log upload begin
                checkpoints.log(UploadFlow.UPLOAD_TASK_BEGIN)

                # Set additional context
                sentry_sdk.set_tag("commit_sha", commitid[:7])
                sentry_sdk.set_tag(
                    "repo_name", commit.repository.name if commit else "unknown"
                )

            # Track file processing stage
            with tracker.track_stage("file_processing"):
                # Process upload files
                # ... existing upload processing logic ...
                pass

            # Track report generation stage
            with tracker.track_stage("report_generation"):
                # Generate coverage report
                # ... existing report logic ...
                pass

            # Record custom metrics
            sentry_sdk.set_measurement("upload.file_count", len(arguments_list or []))
            sentry_sdk.set_measurement("upload.total_lines", 1000)  # Example metric

            return {"success": True}


class UploadProcessorTaskWithMetrics(BaseCodecovTask):
    """Example of upload processor with stage tracking."""

    @track_upload_performance(repo_id=123, owner_id=456)  # In real code, get from args
    def run_impl(self, db_session, *, repoid, commitid, report_code, **kwargs):
        upload = kwargs.get("upload_obj")

        # Track individual processing stages
        with track_upload_stage("parse_coverage", repo_id=repoid, upload_id=upload.id):
            # Parse coverage data
            # ... existing parsing logic ...
            pass

        with track_upload_stage("merge_report", repo_id=repoid, upload_id=upload.id):
            # Merge into main report
            # ... existing merge logic ...
            pass

        # Track any errors or issues
        if upload.state == "error":
            sentry_sdk.set_tag("upload.error_code", upload.error_code)
            sentry_sdk.capture_message(
                f"Upload processing error: {upload.error_code}",
                level="warning",
            )

        return {"processed": True}


class NotificationTaskWithMetrics(BaseCodecovTask):
    """Example of notification task with latency tracking."""

    def run_impl(self, db_session, *, repoid, commitid, **kwargs):
        # Get upload start time from checkpoints
        checkpoints = from_kwargs(UploadFlow, kwargs)
        upload_start_time = checkpoints.data.get(UploadFlow.UPLOAD_TASK_BEGIN)

        if upload_start_time:
            # Track notification latency
            track_notification_latency(
                upload_start_time=upload_start_time,
                notification_type="pull_request_comment",
                repo_id=repoid,
                commit_sha=commitid[:7],
            )

        # Track notification sending
        with sentry_sdk.start_span(op="notification.send") as span:
            span.set_tag("notification_type", "pull_request_comment")
            span.set_tag("repo_id", repoid)

            # Send notification
            # ... existing notification logic ...

            # Log completion
            checkpoints.log(UploadFlow.NOTIFIED)

        return {"notified": True}


# Example of how to query these metrics in Sentry
"""
Sentry Discover Queries:

1. Slowest repos by upload processing time:
   - Transaction: upload.process
   - Group by: repo_id
   - Aggregate: p95(measurements.upload.duration)
   - Sort: p95 descending

2. Upload stages breakdown:
   - Transaction: upload.full_processing_flow
   - Measurements: upload.stage.*.duration
   - Visualize as breakdown chart

3. Notification latency by repository:
   - Transaction: notification.latency
   - Group by: repo_id
   - Aggregate: avg(measurements.notification.latency)

4. Upload error rates:
   - Transaction: upload.*
   - Filter: upload.status:error
   - Group by: repo_id, upload.error_type

5. Performance issues:
   - Filter: performance.issue:*_latency
   - Group by: repo_id, performance.issue
"""
