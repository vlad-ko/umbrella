# Sentry Integration: Performance Monitoring + Critical Experiences

## Overview

This document outlines Codecov's comprehensive Sentry integration strategy that combines:
1. **Foundation**: Robust performance monitoring across all services
2. **Focus**: Critical experiences tracking for business-impacting workflows
3. **Balance**: Technical excellence with business outcomes

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Critical Experiences Layer                │
│  (Business Context, Revenue Impact, Customer Success Alerts) │
├─────────────────────────────────────────────────────────────┤
│                 Performance Monitoring Layer                 │
│    (Traces, Spans, Metrics, SLOs, Technical Dashboards)    │
├─────────────────────────────────────────────────────────────┤
│                    Infrastructure Layer                      │
│        (Distributed Tracing, Error Tracking, Logs)         │
└─────────────────────────────────────────────────────────────┘
```

## Dual-Purpose Implementation

### 1. Base Performance Monitoring (Technical Foundation)

```python
# apps/worker/helpers/performance_monitoring.py

from contextvars import ContextVar
from typing import Optional
import sentry_sdk
from sentry_sdk import set_measurement, set_tag

# Context variable for tracking nested operations
current_operation: ContextVar[Optional[str]] = ContextVar('current_operation', default=None)

class PerformanceMonitor:
    """
    Base performance monitoring for all operations.
    Provides technical metrics and traces.
    """
    
    @staticmethod
    def track_operation(
        operation_name: str,
        operation_type: str = "task",
        capture_performance: bool = True
    ):
        """Decorator for basic performance tracking"""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                with sentry_sdk.start_transaction(
                    op=f"{operation_type}.{operation_name}",
                    name=operation_name,
                    sampled=capture_performance
                ) as transaction:
                    # Set basic technical context
                    set_tag("operation.type", operation_type)
                    set_tag("operation.name", operation_name)
                    
                    # Track technical metrics
                    start_time = time.time()
                    start_memory = get_memory_usage()
                    
                    try:
                        result = func(*args, **kwargs)
                        set_tag("operation.status", "success")
                        return result
                    except Exception as e:
                        set_tag("operation.status", "error")
                        set_tag("error.type", type(e).__name__)
                        raise
                    finally:
                        # Record technical measurements
                        duration = time.time() - start_time
                        memory_delta = get_memory_usage() - start_memory
                        
                        set_measurement("operation.duration", duration, "second")
                        set_measurement("operation.memory_delta", memory_delta, "byte")
                        
                        # Check technical SLOs
                        if duration > TECHNICAL_SLOS.get(operation_name, {}).get("max_duration", float('inf')):
                            set_tag("slo.breach", "duration")
            
            return wrapper
        return decorator
    
    @staticmethod
    def track_span(span_name: str, span_type: str = "function"):
        """Context manager for tracking sub-operations"""
        class SpanTracker:
            def __enter__(self):
                self.span = sentry_sdk.start_span(
                    op=f"{span_type}.{span_name}",
                    description=span_name
                )
                self.span.__enter__()
                return self
            
            def __exit__(self, exc_type, exc_val, exc_tb):
                if exc_type:
                    self.span.set_tag("error", True)
                self.span.__exit__(exc_type, exc_val, exc_tb)
        
        return SpanTracker()
```

### 2. Critical Experiences Layer (Business Focus)

```python
# apps/worker/helpers/critical_experiences.py

from .performance_monitoring import PerformanceMonitor

class CriticalExperienceMonitor(PerformanceMonitor):
    """
    Extends base performance monitoring with business context
    for critical user experiences.
    """
    
    CRITICAL_EXPERIENCES = {
        "upload_processing": {
            "slo": {"p95": 60, "p99": 120},
            "business_impact": "revenue",
            "alert_channel": "pagerduty"
        },
        "pr_comment_generation": {
            "slo": {"p95": 15, "p99": 30},
            "business_impact": "satisfaction",
            "alert_channel": "slack"
        },
        "first_upload": {
            "slo": {"p95": 45, "p99": 90},
            "business_impact": "activation",
            "alert_channel": "growth_team"
        }
    }
    
    @classmethod
    def track_critical_experience(
        cls,
        experience_name: str,
        organization: Owner,
        add_business_context: bool = True
    ):
        """
        Decorator that combines performance monitoring with business context
        for critical experiences.
        """
        def decorator(func):
            # First apply base performance monitoring
            func = cls.track_operation(
                operation_name=experience_name,
                operation_type="critical_experience"
            )(func)
            
            if not add_business_context:
                return func
            
            @wraps(func)
            def wrapper(*args, **kwargs):
                # Add business context layer
                transaction = sentry_sdk.Hub.current.scope.transaction
                if transaction:
                    cls._enrich_with_business_context(transaction, organization, experience_name)
                
                try:
                    result = func(*args, **kwargs)
                    cls._check_business_impact(experience_name, organization, success=True)
                    return result
                except Exception as e:
                    cls._check_business_impact(experience_name, organization, success=False, error=e)
                    raise
            
            return wrapper
        return decorator
    
    @staticmethod
    def _enrich_with_business_context(transaction, organization: Owner, experience: str):
        """Add business-relevant context to existing transaction"""
        # Customer value context
        set_context("customer", {
            "organization_id": organization.ownerid,
            "organization_name": organization.username,
            "plan": organization.plan,
            "monthly_value": calculate_mrr(organization),
            "total_seats": organization.plan_user_count,
            "active_seats": len(organization.activated_users or []),
        })
        
        # Business impact assessment
        if "enterprise" in organization.plan:
            set_tag("customer.tier", "enterprise")
            set_tag("revenue.risk", "high")
        elif organization.trial_status == "ongoing":
            set_tag("customer.tier", "trial")
            set_tag("conversion.risk", "high")
        else:
            set_tag("customer.tier", "standard")
        
        # Experience-specific context
        set_tag("critical_experience", experience)
        set_tag("business_impact", cls.CRITICAL_EXPERIENCES[experience]["business_impact"])
```

### 3. Unified Monitoring Approach

```python
# apps/worker/tasks/upload.py

from helpers.performance_monitoring import PerformanceMonitor
from helpers.critical_experiences import CriticalExperienceMonitor

class UploadTask(BaseCodecovTask):
    
    @PerformanceMonitor.track_operation("upload_task", capture_performance=True)
    @CriticalExperienceMonitor.track_critical_experience(
        "upload_processing",
        organization=lambda self, *args, **kwargs: self.get_organization(kwargs),
        add_business_context=lambda self, *args, **kwargs: self.is_critical_org(kwargs)
    )
    def run(self, upload_id: str, **kwargs):
        """
        Process upload with both technical performance monitoring
        and business impact tracking for critical organizations.
        """
        upload = self.get_upload(upload_id)
        
        # Technical performance tracking
        with PerformanceMonitor.track_span("parse_coverage"):
            coverage_data = self.parse_coverage(upload)
        
        with PerformanceMonitor.track_span("validate_coverage"):
            self.validate_coverage(coverage_data)
        
        # Critical experience checkpoints for important customers
        if self.is_critical_org(upload.repository.author):
            with CriticalExperienceMonitor.checkpoint("coverage_processing", {
                "file_count": len(coverage_data.files),
                "line_count": coverage_data.total_lines,
                "complexity": coverage_data.complexity_score
            }):
                report = self.process_coverage(coverage_data)
        else:
            # Standard performance monitoring for non-critical
            with PerformanceMonitor.track_span("process_coverage"):
                report = self.process_coverage(coverage_data)
        
        # Always track technical metrics
        set_measurement("upload.file_size", upload.size, "byte")
        set_measurement("upload.processing_time", time.time() - start_time, "second")
        
        return report
```

## Dashboard Strategy: Technical + Business Views

### Technical Dashboards (Engineering Focus)

```python
TECHNICAL_DASHBOARDS = {
    "system_performance": {
        "widgets": [
            {
                "title": "Upload Processing Performance (All)",
                "query": "p50(operation.duration), p95(operation.duration), p99(operation.duration)",
                "display": "line"
            },
            {
                "title": "Service Latency Breakdown",
                "query": "avg(span.duration) by span.op",
                "display": "bar"
            },
            {
                "title": "Error Rate by Service",
                "query": "count(operation.status:error) / count() by service",
                "display": "percentage"
            }
        ]
    },
    "infrastructure_health": {
        "widgets": [
            {
                "title": "Database Query Performance",
                "query": "p95(db.query.duration) by query.type",
                "display": "table"
            },
            {
                "title": "Cache Hit Rates",
                "query": "sum(cache.hit) / (sum(cache.hit) + sum(cache.miss))",
                "display": "big_number"
            }
        ]
    }
}
```

### Business Dashboards (Leadership & Customer Success Focus)

```python
BUSINESS_DASHBOARDS = {
    "revenue_protection": {
        "widgets": [
            {
                "title": "Enterprise Customer Experience Health",
                "query": """
                    count(operation.status:error) 
                    customer.tier:enterprise 
                    group by organization_name
                """,
                "display": "table"
            },
            {
                "title": "Revenue at Risk (Failed Critical Experiences)",
                "query": """
                    sum(customer.monthly_value)
                    critical_experience:*
                    operation.status:error
                    time.range:24h
                """,
                "display": "big_number",
                "unit": "USD"
            }
        ]
    },
    "growth_metrics": {
        "widgets": [
            {
                "title": "Trial Activation Success Rate",
                "query": """
                    (count(critical_experience:first_upload operation.status:success) / 
                     count(critical_experience:first_upload)) * 100
                    customer.tier:trial
                """,
                "display": "percentage"
            },
            {
                "title": "Time to First Success (Trials)",
                "query": """
                    avg(time_to_first_success)
                    customer.tier:trial
                    group by signup_source
                """,
                "display": "bar"
            }
        ]
    }
}
```

## Alert Configuration: Tiered Approach

```python
ALERT_CONFIGURATION = {
    # Technical alerts for engineering
    "technical_alerts": [
        {
            "name": "High Error Rate",
            "condition": "error_rate > 5%",
            "window": "5m",
            "severity": "warning",
            "notify": ["engineering-oncall"]
        },
        {
            "name": "Database Latency Spike",
            "condition": "p95(db.query.duration) > 1s",
            "window": "10m",
            "severity": "critical",
            "notify": ["database-team"]
        }
    ],
    
    # Business alerts for customer impact
    "business_alerts": [
        {
            "name": "Enterprise Customer Upload Failure",
            "condition": """
                customer.tier:enterprise AND
                critical_experience:upload_processing AND
                operation.status:error
            """,
            "threshold": 1,  # Any failure
            "action": "page_oncall_and_notify_customer_success"
        },
        {
            "name": "Trial Activation Struggling",
            "condition": """
                customer.tier:trial AND
                critical_experience:first_upload AND
                attempt_count > 3
            """,
            "action": "notify_growth_team_for_proactive_outreach"
        }
    ]
}
```

## Benefits of the Blended Approach

### 1. **Comprehensive Coverage**
- Technical monitoring catches all performance issues
- Critical experiences focus on what impacts the business
- No blind spots in either dimension

### 2. **Flexible Resource Allocation**
- High sampling for critical experiences
- Standard sampling for general operations
- Cost-effective monitoring strategy

### 3. **Multiple Stakeholder Support**
- Engineers get detailed technical metrics
- Customer Success sees at-risk accounts
- Leadership understands business impact
- Support teams have debugging context

### 4. **Progressive Enhancement**
- Start with basic performance monitoring
- Layer on business context where it matters
- Gradually expand critical experience definitions

### 5. **Data-Driven Prioritization**
- Technical severity informs "can we fix it?"
- Business impact informs "should we fix it now?"
- Combined view enables smart resource allocation

## Implementation Phases

### Phase 1: Foundation (Weeks 1-2)
- Deploy base PerformanceMonitor across all services
- Set up technical dashboards and alerts
- Establish baseline metrics

### Phase 2: Critical Experiences (Weeks 3-4)
- Implement CriticalExperienceMonitor
- Add business context to key workflows
- Create business-focused dashboards

### Phase 3: Integration (Weeks 5-6)
- Connect monitoring to business systems
- Set up cross-functional alerts
- Train teams on dual dashboards

### Phase 4: Optimization (Ongoing)
- Refine critical experience definitions
- Adjust sampling rates based on value
- Continuously improve alert accuracy

## Conclusion

This blended approach provides Codecov with:
- **Technical Excellence**: Comprehensive performance monitoring for system health
- **Business Focus**: Critical experiences tracking for revenue protection
- **Balanced Investment**: Resources focused where they matter most
- **Actionable Insights**: Both technical and business teams can act on data

By combining both approaches, we ensure that Codecov maintains high technical standards while also protecting and growing the business.
