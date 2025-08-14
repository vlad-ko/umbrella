# Sentry Upload Performance Dashboards

This document describes how to set up Sentry dashboards for tracking upload and notification performance.

## 1. Key Metrics to Track

### Upload Performance Metrics
- **upload.duration**: Total time to process an upload
- **upload.stage.*.duration**: Duration of each processing stage
- **upload.total_duration**: End-to-end upload flow duration
- **notification.latency**: Time from upload start to notification sent

### Upload Volume Metrics
- **upload.file_count**: Number of files per upload
- **upload.total_lines**: Total lines of coverage processed
- **upload.status**: Success/error status

## 2. Sentry Dashboard Widgets

### Widget 1: Slowest Repositories (P95 Upload Time)
```
Query: 
- Dataset: Transactions
- Query: p95(measurements.upload.duration)
- Group by: repo_id
- Filter: transaction.op:upload.process
- Display: Top 10 descending
```

### Widget 2: Upload Processing Stages
```
Query:
- Dataset: Transactions
- Query: 
  - avg(measurements.upload.stage.file_processing.duration)
  - avg(measurements.upload.stage.report_generation.duration)
  - avg(measurements.upload.stage.merge_report.duration)
- Filter: transaction.op:upload.full_flow
- Display: Stacked bar chart
```

### Widget 3: Notification Latency Distribution
```
Query:
- Dataset: Transactions
- Query: histogram(measurements.notification.latency, 60)
- Filter: transaction.op:notification.latency
- Display: Histogram with buckets [0-60s, 60-300s, 300-600s, 600s+]
```

### Widget 4: Upload Error Rate by Repository
```
Query:
- Dataset: Transactions
- Query: count()
- Group by: repo_id, upload.status
- Filter: transaction.op:upload.* AND upload.status:error
- Display: Table with error percentage
```

### Widget 5: Real-time Upload Performance
```
Query:
- Dataset: Transactions
- Query: avg(measurements.upload.duration)
- Filter: transaction.op:upload.process
- Time range: Last 1 hour
- Display: Line chart with 1-minute granularity
```

## 3. Custom Alerts

### Alert 1: High Upload Latency
```yaml
Name: High Upload Processing Time
Conditions:
  - p95(measurements.upload.duration) > 300 seconds
  - In the last 10 minutes
  - Group by: repo_id
Actions:
  - Send to #engineering-alerts Slack channel
  - Create Sentry issue
```

### Alert 2: Upload Error Spike
```yaml
Name: Upload Error Rate Spike
Conditions:
  - count() where upload.status:error > 10
  - In the last 30 minutes
  - Compared to previous 30 minutes: 200% increase
Actions:
  - Page on-call engineer
  - Send detailed breakdown by error type
```

### Alert 3: Notification Latency SLA Breach
```yaml
Name: Notification Latency SLA Breach
Conditions:
  - avg(measurements.notification.latency) > 600 seconds
  - In the last 1 hour
  - For any repository with > 5 uploads
Actions:
  - Send to repository owner
  - Log to metrics database
```

## 4. Implementation Steps

1. **Add Instrumentation** (Priority: High)
   - Import `sentry_metrics` module in upload tasks
   - Wrap key operations with performance tracking
   - Add stage tracking for detailed breakdown

2. **Deploy Gradually** (Priority: High)
   - Start with top 10 repositories by volume
   - Monitor Sentry quota usage
   - Adjust sampling rates if needed

3. **Create Dashboards** (Priority: Medium)
   - Set up main performance dashboard
   - Create per-team/per-repo dashboards
   - Share with engineering teams

4. **Set Up Alerts** (Priority: Medium)
   - Configure latency alerts
   - Set up error rate monitoring
   - Create escalation policies

5. **Optimize Based on Data** (Priority: Low)
   - Identify slowest stages
   - Focus optimization efforts
   - Track improvements over time

## 5. Sentry SDK Configuration

Update Sentry initialization to ensure performance monitoring:

```python
sentry_sdk.init(
    dsn=SENTRY_DSN,
    traces_sample_rate=0.1,  # Sample 10% of transactions
    profiles_sample_rate=0.01,  # Profile 1% of sampled transactions
    _experiments={
        "enable_metrics": True,  # Enable custom metrics
    },
    before_send_transaction=filter_transactions,
)

def filter_transactions(event, hint):
    # Sample more aggressively for high-volume repos
    repo_id = event.get("tags", {}).get("repo_id")
    if repo_id in HIGH_VOLUME_REPOS:
        # Only sample 1% of high-volume repos
        if random.random() > 0.01:
            return None
    return event
```

## 6. Example Sentry Discover Queries

### Find Slowest Uploads
```
transaction.op:upload.process 
measurements.upload.duration:>300
```

### Track Upload Volume by Owner
```
transaction.op:upload.* 
| stats count() by owner_id
```

### Identify Performance Regression
```
transaction.op:upload.process
| stats p95(measurements.upload.duration) by time(1d)
| where p95 > previous_p95 * 1.5
```

### Monitor Specific Repository
```
transaction.op:upload.* repo_id:12345
| stats 
    count(), 
    avg(measurements.upload.duration),
    count_if(upload.status:error)
```

## 7. Best Practices

1. **Tag Consistently**: Always include repo_id, owner_id, and upload_id
2. **Use Measurements**: Numeric values should be measurements, not tags
3. **Sample Wisely**: Adjust sampling based on volume and quota
4. **Monitor Overhead**: Ensure instrumentation doesn't slow down uploads
5. **Review Regularly**: Weekly review of dashboards and alerts