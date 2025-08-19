# Sentry Integration Comprehensive Guide

This document provides a phased implementation guide for Sentry integration across Codecov's services, ordered from high-value/low-impact to more complex features.

## Executive Summary

Our Sentry implementation follows a phased approach, prioritizing immediate business value with minimal performance impact. Each phase builds upon the previous, allowing us to validate benefits before increasing complexity.

### Current Implementation Status

After reviewing the codebase, Codecov has a foundation of Sentry integration but with key gaps:

**What's Working Well:**
- ✅ Error tracking with basic context (repo, owner, commit)
- ✅ Performance monitoring enabled (but needs optimization)
- ✅ Frontend has session replay and profiling
- ✅ Infrastructure for distributed tracing exists

**Critical Gaps:**
- ❌ No business context (customer value, revenue impact)
- ❌ Distributed tracing not actually connected between services
- ❌ Worker has 100% sampling (performance risk!)
- ❌ No differentiation between enterprise and free customers
- ❌ Missing proactive alerting for high-value customers

### Phase Overview
- **Phase 1**: Error Tracking & Basic Monitoring - Immediate visibility, zero performance impact
- **Phase 2**: Distributed Tracing - End-to-end visibility, minimal overhead
- **Phase 3**: Critical User Journeys - Business metrics, targeted monitoring
- **Phase 4**: Performance Monitoring - Deep insights, controlled sampling
- **Phase 5**: Advanced Features - Session replay, profiling, predictive analytics

## Table of Contents

1. [Phase 1: Error Tracking & Basic Monitoring](#phase-1-error-tracking--basic-monitoring)
2. [Phase 2: Distributed Tracing](#phase-2-distributed-tracing)
3. [Phase 3: Critical User Journeys](#phase-3-critical-user-journeys)
4. [Phase 4: Performance Monitoring](#phase-4-performance-monitoring)
5. [Phase 5: Advanced Features](#phase-5-advanced-features)
6. [Performance Overhead Analysis](#performance-overhead-analysis)
7. [Configuration Reference](#configuration-reference)
8. [Success Metrics](#success-metrics)

## Phase 1: Error Tracking & Basic Monitoring

**Performance Impact**: Zero (errors are already happening)  
**Business Value**: Immediate visibility into production issues

### Current State

✅ **Already Implemented**:
- Error tracking across all services (API, Worker, Frontend)
- Basic context via LogContext (task, owner, repo, commit info)
- Sensitive data scrubbing
- Frontend error filtering and feature flag integration

⚠️ **Missing**:
- Business context (customer value, revenue impact)
- Upload-specific details (file size, type, processing stage)
- Proactive alerting based on customer tier

### Implementation

#### 1.1 Basic Setup (All Services)

```python
# Worker service example
import sentry_sdk
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.django import DjangoIntegration

sentry_sdk.init(
    dsn=os.getenv("SENTRY_DSN"),
    environment=os.getenv("CODECOV_ENV", "production"),
    release=get_current_version(),
    # Start with NO performance monitoring
    traces_sample_rate=0,  # We'll enable this in Phase 4
    integrations=[
        DjangoIntegration(),
        CeleryIntegration(),
    ],
)
```

#### 1.2 Enhanced Error Context

```python
# Add business context to errors
def process_upload(upload_id: str):
    try:
        upload = get_upload(upload_id)
        
        # Add context that helps support
        sentry_sdk.set_context("upload", {
            "id": upload_id,
            "repository": upload.repository.name,
            "owner": upload.repository.author.username,
            "plan": upload.repository.author.plan,
            "file_size": upload.file_size,
        })
        
        # Process upload...
        
    except Exception as e:
        # Sentry automatically captures with context
        sentry_sdk.capture_exception(e)
        raise
```

### Concrete Examples

#### Example 1: Upload Processing Error

**Current Implementation:**
```python
# BaseCodecovTask already sets context via LogContext:
- task_name, task_id
- owner_username, owner_service, owner_plan, owner_id
- repo_name, repo_id
- commit_sha
# These are automatically added as Sentry tags
```

**Enhancement Proposal:**
```python
# Add business-specific context for uploads
sentry_sdk.set_context("upload", {
    "id": upload_id,
    "state": upload.state,
    "file_size": upload.file_size,
    "file_type": upload.file_type,
    "provider": upload.provider,
    "error_code": upload.error_code if upload.state == "error" else None,
})

sentry_sdk.set_context("business_impact", {
    "mrr": organization.monthly_revenue,
    "is_enterprise": organization.plan == "enterprise",
    "seats": organization.activated_users.count(),
    "critical_path": True,  # Upload is always critical
})
```

**Why:** While we have basic context (repo, owner, commit), we lack upload-specific details and business impact. Adding file size, type, and revenue context helps prioritize issues affecting high-value customers or specific file types that commonly fail.

#### Example 2: API Rate Limit Error
```python
# Automatically captured with context
@sentry_sdk.monitor(monitor_slug="github-api-health")
def check_github_api():
    with sentry_sdk.set_context("api_check", {
        "remaining_quota": github.rate_limit.remaining,
        "reset_time": github.rate_limit.reset,
    }):
        # API calls that might fail
```

### Business Wins

1. **Reduced MTTR**: From hours to minutes for error diagnosis
2. **Proactive Support**: Alert enterprise customers before they complain
3. **Engineering Efficiency**: Stop diving through logs
4. **Customer Trust**: "We've already identified the issue and are working on it"

### Performance Considerations

- **Zero overhead**: Only captures errors that are already happening
- **No sampling**: Errors are rare events, capture 100%
- **Async sending**: Errors sent in background, non-blocking

### Immediate Action Required

⚠️ **Worker Service has 100% sampling** - This needs immediate attention:

```python
# Current (DANGEROUS for production):
traces_sample_rate=1.0  # 100%
profiles_sample_rate=1.0  # 100%

# Recommended immediate fix:
traces_sample_rate=float(os.environ.get("SERVICES__SENTRY__SAMPLE_RATE", "0.01"))  # 1%
profiles_sample_rate=float(os.environ.get("SERVICES__SENTRY__PROFILES_SAMPLE_RATE", "0.001"))  # 0.1%
```

## Phase 2: Distributed Tracing

**Performance Impact**: <0.1% with smart sampling  
**Business Value**: End-to-end visibility across services

### Current State

✅ **Already Implemented**:
- Tracing enabled in all services
- CORS headers configured for trace propagation
- `@sentry_sdk.trace` decorators on many functions
- Celery integration with `propagate_traces=True`

⚠️ **Missing**:
- Actual trace propagation between services
- Frontend doesn't send trace headers to API
- API doesn't propagate traces to Worker
- No connection between user action → API → Worker

### Implementation

#### 2.1 Enable Tracing with Smart Sampling

```python
# API Service
sentry_sdk.init(
    # ... existing config ...
    traces_sample_rate=0.01,  # Start with 1% baseline
    traces_sampler=smart_sampler,  # Custom sampling logic
)

def smart_sampler(sampling_context):
    """Smart sampling based on operation importance"""
    
    # Always trace errors
    if sampling_context.get("error"):
        return 1.0
    
    # Sample by transaction type
    transaction_name = sampling_context.get("transaction_context", {}).get("name", "")
    
    # Critical paths - higher sampling
    if "upload" in transaction_name:
        return 0.05  # 5% for uploads
    elif "webhook" in transaction_name:
        return 0.1   # 10% for webhooks
    
    # Default low sampling
    return 0.001  # 0.1% for everything else
```

#### 2.2 Cross-Service Tracing

```python
# Frontend (Gazebo)
const transaction = Sentry.startTransaction({
  name: "upload-coverage",
  op: "user-action",
});

// Set on hub for all requests
Sentry.getCurrentHub().configureScope(scope => scope.setSpan(transaction));

// API call automatically includes trace headers
const response = await api.post('/upload', data);

transaction.finish();
```

```python
# API receives trace and continues it
@sentry_sdk.trace
def upload_handler(request):
    # Automatically continues trace from frontend
    
    # Create worker task with trace propagation
    task = process_upload.delay(
        upload_id,
        headers={
            "sentry-trace": request.headers.get("sentry-trace"),
            "baggage": request.headers.get("baggage"),
        }
    )
```

```python
# Worker continues the trace
@shared_task(bind=True)
@sentry_sdk.trace
def process_upload(self, upload_id, **kwargs):
    # Trace continues from API
    
    with sentry_sdk.start_span(op="parse-coverage"):
        coverage = parse_coverage_file()
    
    with sentry_sdk.start_span(op="store-results"):
        store_to_database(coverage)
```

### Concrete Examples

#### Example 1: Slow Upload Diagnosis

**Current Implementation:**
```
# Manual investigation required:
- Check API logs for slow requests
- Check worker logs for processing time
- No visibility into which stage is slow
- No connection between CLI → API → Worker
```

**Enhancement Proposal:**
```
Trace: Upload Coverage (12.5s total)
├─ CI: upload sent by CLI (0.1s)
├─ API: Validate upload (0.5s)
├─ API: Create upload record (0.2s)
├─ Worker: Process upload (11.5s) ⚠️
│  ├─ Parse coverage file (8.2s) ⚠️ SLOW
│  ├─ Calculate diff (2.1s)
│  └─ Store results (1.2s)
└─ API: Return response (0.2s)

Bottleneck identified: Parsing large XML file
```

**Why:** Currently, performance issues require manual correlation across multiple service logs with no visibility into sub-operation timing. Distributed tracing provides automatic end-to-end visibility, immediately highlighting the bottleneck (XML parsing) without manual investigation.

#### Example 2: External Service Timeout

**Current Implementation:**
```
# Worker logs show timeout after 30s
ERROR: Request to GitHub timed out
# No visibility into:
- Which customers are affected
- How long GitHub has been slow
- If it's a pattern or isolated incident
```

**Enhancement Proposal:**
```
Trace: PR Comment Creation (timeout after 30s)
├─ Worker: Generate comment (2.1s)
├─ Worker: Post to GitHub (30s) ❌ TIMEOUT
│  └─ HTTP POST api.github.com (no response)

Alert: GitHub API degradation affecting enterprise customers
```

**Why:** Current implementation only shows the timeout in logs without context about customer impact or service degradation patterns. The enhancement immediately shows which external service is failing and can trigger alerts for affected enterprise customers.

### Business Wins

1. **Faster Debugging**: See exactly where time is spent
2. **External Service Monitoring**: Know when GitHub/GitLab/Bitbucket are slow
3. **Customer Impact**: Trace shows which customers are affected
4. **Performance Optimization**: Data-driven decisions on what to optimize

### Performance Considerations

```python
# Sampling configuration for minimal overhead
TRACING_CONFIG = {
    # Transaction-specific sampling
    "api.upload": 0.05,      # 5% - important but not critical
    "worker.process": 0.01,  # 1% - high volume
    "api.webhook": 0.1,      # 10% - lower volume, critical
    "frontend.pageload": 0.001,  # 0.1% - very high volume
    
    # Always sample these conditions
    "always_sample": [
        "enterprise_customer",
        "error_status",
        "slow_transaction",  # >5s
    ]
}
```

## Phase 3: Critical User Journeys

**Performance Impact**: <0.5% for targeted monitoring  
**Business Value**: Connect technical metrics to revenue impact

### What We're Building

Monitor the user journeys that directly impact revenue and retention. We're not monitoring everything - just the experiences that matter most to the business.

### Critical Journeys for Codecov

1. **Upload Processing** - Core value proposition
2. **PR Comment Generation** - Key integration point
3. **Coverage Report Viewing** - Primary user interaction
4. **Repository Onboarding** - First impression
5. **Enterprise SSO Login** - Enterprise customer access

### Implementation

#### 3.1 Define Critical Experience Class

```python
class CriticalExperience:
    """Track business-critical user journeys"""
    
    def __init__(self, name: str, organization: Owner):
        self.name = name
        self.organization = organization
        self.transaction = sentry_sdk.start_transaction(
            op=f"critical.{name}",
            name=f"Critical Experience: {name}",
            sampled=True  # Always sample critical experiences
        )
        self._add_business_context()
    
    def _add_business_context(self):
        """Add revenue and business context"""
        sentry_sdk.set_context("business", {
            "organization_id": self.organization.ownerid,
            "plan": self.organization.plan,
            "mrr": self.organization.stripe_customer.mrr if self.organization.stripe_customer else 0,
            "seats": self.organization.activated_users.count(),
            "repos": self.organization.repos.count(),
            "is_trial": self.organization.trial_status == "ongoing",
            "churn_risk": self._calculate_churn_risk(),
        })
        
        # Tag for easy filtering
        sentry_sdk.set_tag("customer.tier", self._get_tier())
        sentry_sdk.set_tag("revenue.impact", "high" if self.organization.plan == "enterprise" else "standard")
```

#### 3.2 Implement for Upload Processing

```python
@shared_task
def process_upload(upload_id: str):
    upload = get_upload(upload_id)
    org = upload.repository.author
    
    # Only track critical experiences for paying customers
    if org.plan in ["pro", "enterprise"]:
        with CriticalExperience("upload_processing", org) as experience:
            experience.set_measurement("upload.size", upload.file_size)
            experience.set_measurement("upload.lines", upload.line_count)
            
            # Track each stage
            with experience.track_stage("parse"):
                coverage = parse_coverage(upload)
            
            with experience.track_stage("calculate_diff"):
                diff = calculate_diff(coverage)
            
            with experience.track_stage("notify"):
                send_notifications(upload, diff)
            
            # Business outcome
            experience.set_outcome(
                "success",
                revenue_impact=org.stripe_customer.mrr if hasattr(org, 'stripe_customer') else 0
            )
    else:
        # Regular processing without heavy instrumentation
        _process_upload_basic(upload_id)
```

### Concrete Examples

#### Example 1: Enterprise Upload Failure Impact

**Current Implementation:**
```
# Error in worker logs
ERROR: Upload 12345 failed - parsing timeout
# Manual process:
1. Support ticket comes in hours later
2. Engineer searches logs
3. Identifies customer manually
4. No automatic escalation
```

**Enhancement Proposal:**
```
Alert: Critical Experience Failed
Journey: Upload Processing
Customer: Microsoft (Enterprise - $50k MRR)
Error: Coverage parsing timeout
Impact: CI/CD pipeline blocked
Action: Page on-call engineer + notify customer success
```

**Why:** Currently, high-value customer issues are discovered reactively through support tickets. The enhancement proactively identifies revenue impact and automatically escalates based on customer value, enabling intervention before the customer complains.

#### Example 2: Onboarding Drop-off
```
Critical Experience: Repository Onboarding
Customer: Acme Corp (Trial - High Intent)
Stage Completed: GitHub App Installed ✓
Stage Failed: First Upload ✗
Time to Failure: 45 minutes
Action: Customer success outreach with setup help
```

### Business Wins

1. **Revenue Protection**: Know immediately when high-value customers have issues
2. **Churn Prevention**: Catch problems before customers complain
3. **Customer Success**: Proactive outreach for struggling customers
4. **Product Insights**: Which features drive value for which segments

### Performance Considerations

```python
# Only monitor what matters
CRITICAL_EXPERIENCE_CRITERIA = {
    "monitor_if": [
        "plan in ['pro', 'enterprise']",  # Paying customers
        "trial_status == 'ongoing'",       # Active trials
        "repos.count() > 10",              # High usage
        "mrr > 1000",                      # High value
    ],
    "skip_if": [
        "plan == 'free'",                  # Free users
        "repos.count() == 0",              # No activity
        "created_at < 30_days_ago",        # Too new
    ]
}
```

## Phase 4: Performance Monitoring

**Performance Impact**: 0.1-2% depending on sampling  
**Business Value**: Deep performance insights for optimization

### Current State

✅ **Already Implemented**:
- Performance monitoring enabled (but with high sampling rates)
- Worker: 100% traces, 100% profiles (too high!)
- API: 10% traces, 1% profiles
- Custom performance helpers in `sentry_metrics.py`

⚠️ **Missing**:
- Adaptive sampling based on load
- Business context in performance data
- Detailed span tracking within operations
- Performance baselines and SLOs

### Implementation

#### 4.1 Selective Performance Monitoring

```python
# Worker service with performance monitoring
sentry_sdk.init(
    # ... existing config ...
    traces_sample_rate=0.01,  # Still low baseline
    profiles_sample_rate=0.001,  # Very selective profiling
    _experiments={
        "continuous_profiling_auto_start": True,
    },
)

# Custom performance monitoring decorator
def monitor_performance(
    sample_rate: float = 0.01,
    profile_rate: float = 0.001,
    alert_threshold_ms: float = 5000
):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Decide if we should monitor this execution
            should_monitor = random.random() < sample_rate
            should_profile = random.random() < profile_rate
            
            if not should_monitor:
                return func(*args, **kwargs)
            
            # Start transaction with optional profiling
            with sentry_sdk.start_transaction(
                op=f"task.{func.__name__}",
                name=func.__name__,
                sampled=True,
            ) as transaction:
                if should_profile:
                    profiler = sentry_sdk.start_profiler()
                
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    return result
                finally:
                    duration = (time.time() - start_time) * 1000
                    
                    # Alert on slow operations
                    if duration > alert_threshold_ms:
                        sentry_sdk.capture_message(
                            f"Slow operation: {func.__name__} took {duration:.0f}ms",
                            level="warning",
                        )
                    
                    if should_profile and profiler:
                        profiler.stop()
        
        return wrapper
    return decorator
```

#### 4.2 Targeted Metrics Collection

```python
# Only collect metrics for specific operations
@monitor_performance(
    sample_rate=0.05,  # 5% sampling for uploads
    profile_rate=0.001,  # 0.1% profiling
    alert_threshold_ms=10000  # Alert if >10s
)
def process_large_coverage_file(file_path: str):
    with sentry_sdk.start_span(op="parse.xml") as span:
        span.set_data("file_size", os.path.getsize(file_path))
        tree = parse_xml(file_path)
    
    with sentry_sdk.start_span(op="process.coverage") as span:
        coverage = extract_coverage(tree)
        span.set_data("line_count", len(coverage.lines))
    
    return coverage
```

### Concrete Examples

#### Example 1: Memory Leak Detection

**Current Implementation:**
```python
# No visibility into memory usage patterns
# Issues discovered only when:
- Worker OOMs and crashes
- Performance degrades significantly
- Manual profiling during incident
```

**Enhancement Proposal:**
```python
# Continuous profiling catches memory growth
Profile: process_upload memory usage
- Start: 150MB
- After 100 uploads: 450MB ⚠️
- Growth rate: 3MB per upload
- Heap snapshot shows: Cached XML parsers not released
```

**Why:** Currently, memory leaks are only discovered during production incidents. Continuous profiling detects gradual memory growth before it impacts customers, with automatic heap snapshots pinpointing the exact cause.

#### Example 2: Database Query Optimization

**Current Implementation:**
```
# Slow API responses with no visibility into why
# Investigation requires:
- Enabling Django debug toolbar locally
- Adding manual query logging
- Reproducing with production data
- No visibility into query patterns
```

**Enhancement Proposal:**
```
Transaction: fetch_repository_coverage
├─ API Handler (50ms)
├─ DB: SELECT repos (20ms)
├─ DB: SELECT commits (800ms) ⚠️ N+1 Query
│   ├─ Query 1: commit_sha=abc... (8ms)
│   ├─ Query 2: commit_sha=def... (8ms)
│   └─ ... 98 more queries
└─ Response serialization (30ms)

Fix: Add .prefetch_related('commits')
Result: 900ms → 100ms (90% improvement)
```

**Why:** Current debugging requires reproducing issues locally with production-like data. The enhancement automatically identifies N+1 queries in production with exact query counts and timing, making the fix obvious without time-consuming investigation.

### Business Wins

1. **Cost Optimization**: Identify and fix resource waste
2. **User Experience**: Faster operations = happier customers
3. **Capacity Planning**: Know when to scale before issues
4. **Engineering Productivity**: Data-driven optimization

### Performance Considerations

```python
# Adaptive sampling based on system load
class AdaptiveSampler:
    def __init__(self):
        self.base_rate = 0.01
        self.current_rate = self.base_rate
    
    def should_sample(self) -> bool:
        # Reduce sampling under high load
        cpu_usage = psutil.cpu_percent()
        if cpu_usage > 80:
            self.current_rate = self.base_rate * 0.1  # 10% of base
        elif cpu_usage > 60:
            self.current_rate = self.base_rate * 0.5  # 50% of base
        else:
            self.current_rate = self.base_rate
        
        return random.random() < self.current_rate
```

## Phase 5: Advanced Features

**Performance Impact**: Variable, feature-specific  
**Business Value**: Premium insights and predictive capabilities

### Current State

✅ **Already Implemented**:
- Session replay in frontend (configurable sampling)
- Browser profiling integration
- Spotlight for local development
- LaunchDarkly integration

⚠️ **Missing**:
- Smart sampling based on customer value
- Predictive analytics
- Custom business dashboards
- Proactive alerting

### Features

#### 5.1 Session Replay (Frontend Only)

```javascript
// Gazebo configuration
Sentry.init({
  // ... existing config ...
  replaysSessionSampleRate: 0.001,  // 0.1% of sessions
  replaysOnErrorSampleRate: 1.0,     // 100% when errors occur
  
  // Only replay for specific user segments
  beforeSendReplay(event, hint) {
    const user = Sentry.getCurrentHub().getScope().getUser();
    
    // Always replay for enterprise users with issues
    if (user?.plan === 'enterprise' && event.error_count > 0) {
      return event;
    }
    
    // Sample others based on value
    if (user?.plan === 'pro' && Math.random() < 0.01) {
      return event;
    }
    
    // Skip free users
    return null;
  }
});
```

#### 5.2 Predictive Alerts

```python
# Use historical data for predictive monitoring
class PredictiveMonitor:
    def analyze_upload_patterns(self, org_id: int):
        # Get historical performance data from Sentry
        metrics = sentry_sdk.get_metrics(
            organization_id=org_id,
            metric="upload.duration",
            period="30d"
        )
        
        # Detect anomalies
        if self.is_degrading(metrics):
            # Proactive alert before customer notices
            alert_customer_success(
                org_id,
                "Upload performance degrading - investigate before impact"
            )
```

#### 5.3 Custom Dashboards

```python
# Business-specific Sentry dashboards
CUSTOM_DASHBOARDS = {
    "customer_health": {
        "widgets": [
            {
                "title": "Revenue at Risk",
                "query": "sum(revenue_impact) by error_type",
                "display": "big_number"
            },
            {
                "title": "Enterprise Customer Errors",
                "query": "count() by organization where plan:enterprise",
                "display": "table"
            }
        ]
    },
    "upload_performance": {
        "widgets": [
            {
                "title": "P95 Upload Time by Plan",
                "query": "p95(upload.duration) by plan",
                "display": "line"
            }
        ]
    }
}
```

### Business Wins

1. **Visual Debugging**: See exactly what users did before errors
2. **Predictive Maintenance**: Fix issues before they impact customers
3. **Executive Dashboards**: Business metrics in real-time
4. **AI-Powered Insights**: Sentry's ML features for anomaly detection

## Performance Overhead Analysis

### Summary by Phase

| Phase | Feature | Performance Impact | Mitigation Strategy |
|-------|---------|-------------------|---------------------|
| 1 | Error Tracking | 0% | Errors already happening |
| 2 | Distributed Tracing | <0.1% | Smart sampling (1-5%) |
| 3 | Critical Journeys | <0.5% | Only paying customers |
| 4 | Performance Monitoring | 0.1-2% | Adaptive sampling |
| 5 | Advanced Features | Variable | Feature-specific controls |

### Detailed Analysis

#### Memory Overhead
```python
# Baseline memory usage
- Sentry SDK: ~5MB
- Transaction buffer: ~10MB (configurable)
- Span buffer: ~5MB per 1000 spans
- Total: ~20MB typical, 50MB peak

# Mitigation
sentry_sdk.init(
    max_breadcrumbs=50,  # Limit breadcrumb memory
    max_value_length=1024,  # Limit string sizes
    before_send=filter_large_events,  # Drop oversized events
)
```

#### CPU Overhead
```python
# Measured overhead by operation
- Error capture: <1ms
- Span creation: ~0.01ms
- Transaction start: ~0.1ms
- Profiling: 2-5% when active

# Critical path optimization
if is_critical_path:
    # Skip all monitoring
    return process_without_sentry()
```

#### Network Overhead
```python
# Async sending with batching
sentry_sdk.init(
    transport=HTTPTransport(
        batch_size=100,  # Batch events
        timeout=5,  # Don't block on sending
        num_pools=2,  # Parallel sending
    )
)
```

## Configuration Reference

### Environment Variables

```bash
# Core Configuration
SENTRY_DSN=https://xxx@sentry.io/xxx
CODECOV_ENV=production
SENTRY_RELEASE=v1.2.3

# Sampling Rates (per phase)
# Phase 1: Errors only
SENTRY_ERROR_SAMPLE_RATE=1.0

# Phase 2: Distributed tracing
SENTRY_TRACES_SAMPLE_RATE=0.01

# Phase 3: Critical experiences  
SENTRY_CRITICAL_EXPERIENCE_RATE=1.0
SENTRY_CRITICAL_CUSTOMER_TIERS=enterprise,pro

# Phase 4: Performance monitoring
SENTRY_PROFILES_SAMPLE_RATE=0.001
SENTRY_PERFORMANCE_SAMPLE_RATE=0.05

# Phase 5: Advanced features
SENTRY_REPLAY_SESSION_RATE=0.001
SENTRY_REPLAY_ERROR_RATE=1.0
```

### Service-Specific Configuration

```python
# API Service
SENTRY_CONFIG = {
    "dsn": os.getenv("SENTRY_DSN"),
    "environment": os.getenv("CODECOV_ENV"),
    "traces_sample_rate": 0.01,
    "profiles_sample_rate": 0.001,
    "integrations": [
        DjangoIntegration(
            transaction_style="endpoint",
            middleware_spans=False,  # Reduce overhead
        ),
    ],
}

# Worker Service
SENTRY_CONFIG = {
    "dsn": os.getenv("SENTRY_DSN"),
    "environment": os.getenv("CODECOV_ENV"),
    "traces_sample_rate": 0.005,  # Lower for high-volume
    "profiles_sample_rate": 0.0001,  # Very selective
    "integrations": [
        CeleryIntegration(
            monitor_beat_tasks=True,
            propagate_traces=True,
        ),
    ],
}

# Frontend (Gazebo)
SENTRY_CONFIG = {
    dsn: process.env.REACT_APP_SENTRY_DSN,
    environment: process.env.REACT_APP_ENV,
    tracesSampleRate: 0.001,  // Very low for frontend
    replaysSessionSampleRate: 0.0001,
    replaysOnErrorSampleRate: 1.0,
}
```

## Success Metrics

### Phase 1 Success Criteria
- [ ] All services sending errors to Sentry
- [ ] Zero performance degradation confirmed
- [ ] First error resolved using Sentry context
- [ ] Alert routing configured for critical errors

**Metric**: MTTR reduced by 50%

### Phase 2 Success Criteria
- [ ] End-to-end traces visible
- [ ] External service latency identified
- [ ] First cross-service issue diagnosed
- [ ] Performance overhead <0.1%

**Metric**: Cross-service debugging time reduced by 75%

### Phase 3 Success Criteria
- [ ] Critical journeys instrumented
- [ ] Customer success team has dashboard access
- [ ] First proactive customer outreach
- [ ] Revenue impact metrics visible

**Metric**: Customer-reported issues reduced by 30%

### Phase 4 Success Criteria
- [ ] Performance baselines established
- [ ] First optimization from profiling data
- [ ] Database query improvements identified
- [ ] Overhead remains <2% at P99

**Metric**: P95 latency improved by 20%

### Phase 5 Success Criteria
- [ ] Session replay catching UX issues
- [ ] Predictive alerts preventing outages
- [ ] Executive dashboard in use
- [ ] ROI demonstrated

**Metric**: Engineering efficiency improved by 40%

## Executive Dashboard

### Key Business Metrics

```python
# Weekly executive report from Sentry data
def generate_executive_report():
    return {
        "revenue_at_risk": sum_errors_by_mrr(period="7d"),
        "enterprise_health": {
            "affected_customers": count_affected_enterprise(),
            "error_rate": enterprise_error_rate(),
            "performance_slo": enterprise_slo_status(),
        },
        "engineering_efficiency": {
            "mttr": mean_time_to_resolve(),
            "errors_prevented": proactive_fixes_count(),
            "performance_wins": optimization_impact(),
        },
        "roi_metrics": {
            "support_tickets_prevented": estimate_prevented_tickets(),
            "engineering_hours_saved": calculate_time_savings(),
            "customer_retention_impact": churn_prevention_value(),
        }
    }
```

## Conclusion

This phased approach ensures:
1. **Immediate value** with zero risk (Phase 1)
2. **Progressive enhancement** based on proven value
3. **Minimal overhead** through smart sampling
4. **Business alignment** with revenue-focused metrics
5. **Flexibility** to adjust based on results

Each phase builds on the previous, allowing us to validate value before increasing complexity or overhead.