# Sentry Integration Documentation

This document provides a comprehensive overview of Sentry integration across the Codecov umbrella monorepo, including the backend services (codecov-api, worker), frontend (Gazebo), and CLI tools.

## Table of Contents
1. [Overview](#overview)
2. [Integration Strategy](#integration-strategy)
3. [Backend Services](#backend-services)
   - [codecov-api](#codecov-api)
   - [worker](#worker)
4. [Frontend (Gazebo)](#frontend-gazebo)
5. [Critical Experiences Monitoring](#critical-experiences-monitoring)
6. [Performance Monitoring](#performance-monitoring)
7. [OAuth/SSO Integration](#oauthsso-integration)
8. [CLI Integration](#cli-integration)
9. [Configuration Reference](#configuration-reference)
10. [Security & Privacy](#security--privacy)
11. [Development Setup](#development-setup)

## Overview

Codecov uses Sentry for:
- **Error Tracking**: Capturing and monitoring application errors across all services
- **Performance Monitoring**: Tracking application performance and identifying bottlenecks
- **Critical Experiences**: Monitoring business-critical user journeys with revenue impact
- **Session Replay**: Recording user sessions for debugging (frontend only)
- **User Authentication**: Supporting Sentry as an OAuth provider for SSO
- **Distributed Tracing**: Tracking requests across multiple services
- **Business Intelligence**: Connecting technical metrics to business outcomes

## Integration Strategy

Codecov employs a **dual-layer monitoring approach**:

### 1. Foundation Layer: Comprehensive Performance Monitoring
- Track all operations across services
- Maintain technical SLOs
- Provide debugging context
- Monitor infrastructure health

### 2. Focus Layer: Critical Experiences
- Identify business-critical user journeys
- Add revenue and customer context
- Enable proactive customer success
- Prioritize fixes by business impact

This blended approach ensures technical excellence while protecting business outcomes.

## Backend Services

### codecov-api

**Location**: `apps/codecov-api/codecov/settings_base.py`

#### Configuration
```python
SENTRY_ENV = os.environ.get("CODECOV_ENV", None)
SENTRY_DSN = os.environ.get("SERVICES__SENTRY__SERVER_DSN", None)
SENTRY_DENY_LIST = DEFAULT_DENYLIST + ["_headers", "token_to_use"]

if SENTRY_DSN is not None:
    SENTRY_SAMPLE_RATE = float(os.environ.get("SERVICES__SENTRY__SAMPLE_RATE", "0.1"))
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        event_scrubber=EventScrubber(denylist=SENTRY_DENY_LIST),
        _experiments={
            "enable_logs": True,
        },
        integrations=[
            DjangoIntegration(signals_spans=False),
            CeleryIntegration(),
            RedisIntegration(cache_prefixes=["cache:"]),
            HttpxIntegration(),
        ],
        environment=SENTRY_ENV,
        traces_sample_rate=SENTRY_SAMPLE_RATE,
        profiles_sample_rate=float(
            os.environ.get("SERVICES__SENTRY__PROFILE_SAMPLE_RATE", "0.01")
        ),
    )
```

#### Key Features:
- **Event Scrubbing**: Removes sensitive data using `EventScrubber` with custom deny list
- **Integrations**: Django, Celery, Redis, and HTTP client integrations
- **Sampling**: Configurable trace (10%) and profile (1%) sampling rates
- **Cluster Tagging**: Tags events with `CLUSTER_ENV` for multi-cluster deployments
- **Development Mode**: Uses Spotlight integration for local debugging

### worker

**Location**: `apps/worker/helpers/sentry.py`

#### Configuration
```python
def initialize_sentry() -> None:
    version = get_current_version()
    version_str = f"worker-{version}"
    sentry_dsn = get_config("services", "sentry", "server_dsn")
    sentry_sdk.init(
        sentry_dsn,
        sample_rate=float(os.getenv("SENTRY_PERCENTAGE", "1.0")),
        environment=os.getenv("DD_ENV", "production"),
        traces_sample_rate=float(os.environ.get("SERVICES__SENTRY__SAMPLE_RATE", "1")),
        profiles_sample_rate=float(
            os.environ.get("SERVICES__SENTRY__PROFILES_SAMPLE_RATE", "1")
        ),
        _experiments={"enable_logs": True},
        integrations=[
            CeleryIntegration(monitor_beat_tasks=True),
            DjangoIntegration(signals_spans=False),
            SqlalchemyIntegration(),
            RedisIntegration(cache_prefixes=["cache:"]),
            HttpxIntegration(),
        ],
        release=os.getenv("SENTRY_RELEASE", version_str),
    )
```

#### Key Features:
- **Conditional Initialization**: Only initializes if DSN is configured
- **Release Tracking**: Uses worker version for release identification
- **Beat Task Monitoring**: Monitors Celery beat scheduled tasks
- **SQLAlchemy Integration**: Additional database query tracking

## Frontend (Gazebo)

**Location**: `src/sentry.ts`

### Configuration

#### Environment Variables (React App)
```javascript
const defaultConfig = {
  SENTRY_ENVIRONMENT: 'staging',
  SENTRY_TRACING_SAMPLE_RATE: 1.0,
  SENTRY_PROFILING_SAMPLE_RATE: 0.1,
  SENTRY_SESSION_SAMPLE_RATE: 0.1,
  SENTRY_ERROR_SAMPLE_RATE: 1.0,
}
```

All environment variables require `REACT_APP_` prefix (e.g., `REACT_APP_SENTRY_DSN`).

### Initialization
```typescript
export const setupSentry = ({
  history,
}: {
  history: ReturnType<typeof createBrowserHistory>
}) => {
  Sentry.init({
    dsn: config.SENTRY_DSN,
    debug: config.SENTRY_ENVIRONMENT !== 'production',
    environment: config.SENTRY_ENVIRONMENT,
    integrations: [
      Sentry.replayIntegration(),
      Sentry.browserProfilingIntegration(),
      Sentry.reactRouterV5BrowserTracingIntegration({ history }),
      Sentry.thirdPartyErrorFilterIntegration({
        filterKeys: ['gazebo'],
        behaviour: 'apply-tag-if-contains-third-party-frames',
      }),
      Sentry.launchDarklyIntegration(),
      ...(config.NODE_ENV === 'development'
        ? [Sentry.spotlightBrowserIntegration()]
        : []),
    ],
    tracePropagationTargets,
    tracesSampleRate: config?.SENTRY_TRACING_SAMPLE_RATE,
    replaysSessionSampleRate: config?.SENTRY_SESSION_SAMPLE_RATE,
    replaysOnErrorSampleRate: config?.SENTRY_ERROR_SAMPLE_RATE,
    profilesSampleRate: config?.SENTRY_PROFILING_SAMPLE_RATE,
    beforeSend: filterBlockedUserAgents,
    beforeSendTransaction: filterBlockedUserAgents,
    ...deClutterConfig,
  })
}
```

### Key Features

#### 1. Session Replay
- Records user sessions for debugging
- Configurable sampling rates for all sessions and error sessions

#### 2. Browser Profiling
- Performance profiling in the browser
- Helps identify frontend performance bottlenecks

#### 3. React Router Integration
- Tracks navigation and routing events
- Provides better context for errors

#### 4. Third-Party Error Filtering
- Tags errors from browser extensions and third-party scripts
- Helps filter noise from external sources

#### 5. LaunchDarkly Integration
- Tracks feature flag errors and context

#### 6. User Agent Filtering
- Blocks specific user agents (e.g., "Bytespider") from sending events

#### 7. Error Decluttering
Custom configuration to ignore common browser errors:
```javascript
const deClutterConfig = {
  ignoreErrors: [
    'LaunchDarklyFlagFetchError',
    'top.GLOBALS',
    'originalCreateNotification',
    'canvas.contentDocument',
    // ... many more
  ],
  denyUrls: [
    /graph\.facebook\.com/i,
    /connect\.facebook\.net\/en_US\/all\.js/i,
    /extensions\//i,
    /^chrome:\/\//i,
    /^chrome-extension:\/\//i,
    // ... more patterns
  ],
}
```

### Error Boundaries

**Location**: `src/layouts/shared/ErrorBoundary/ErrorBoundary.tsx`

Gazebo uses Sentry's React Error Boundary component:
```typescript
export default function ErrorBoundary({
  sentryScopes = [],
  errorComponent = DefaultUI,
  children,
}: ErrorBoundaryProps) {
  return (
    <Sentry.ErrorBoundary
      beforeCapture={(scope) =>
        sentryScopes.forEach(([key, value]) => scope.setTag(key, value))
      }
      fallback={errorComponent}
    >
      {children}
    </Sentry.ErrorBoundary>
  )
}
```

Error boundaries are strategically placed:
- Around the entire app (`index.tsx`)
- Around layout components (`BaseLayout`, `SidebarLayout`, `EnterpriseLoginLayout`)
- With custom scoping for better error categorization

### User Feedback

Two feedback integrations are configured:

1. **Bug Reporter** (Onboarding)
```typescript
export const SentryBugReporter = Sentry.feedbackIntegration({
  colorScheme: 'light',
  showBranding: false,
  formTitle: 'Give Feedback',
  // ... custom configuration
})
```

2. **User Feedback** (Help Dropdown)
```typescript
export const SentryUserFeedback = (isDark: boolean) =>
  Sentry.feedbackIntegration({
    colorScheme: isDark ? 'dark' : 'light',
    // ... custom configuration
  })
```

### Routing Integration

Custom `SentryRoute` component wraps React Router routes:
```typescript
export const SentryRoute = Sentry.withSentryRouting(Route)
```

Used throughout the application for better error context in routing.

## OAuth/SSO Integration

**Location**: `apps/codecov-api/codecov_auth/views/sentry.py`

Codecov supports Sentry as an OAuth provider for user authentication.

### Configuration
```python
SENTRY_OAUTH_CLIENT_ID = get_config("sentry", "client_id")
SENTRY_OAUTH_CLIENT_SECRET = get_config("sentry", "client_secret")
SENTRY_OIDC_SHARED_SECRET = get_config("sentry", "oidc_shared_secret")
```

### OAuth Flow
1. Redirect to Sentry: `https://sentry.io/oauth/authorize`
2. Token exchange: `https://sentry.io/oauth/token/`
3. JWT state management for secure flow
4. User linking with Sentry user IDs

### Services
- **State Management**: JWT-based state encoding/decoding
- **User Linking**: Associates Codecov users with Sentry user IDs
- **Error Handling**: Custom exceptions for invalid states and duplicate users

## CLI Integration

**Location**: `prevent-cli/codecov-cli/codecov_cli/opentelemetry.py`

The prevent-cli includes basic Sentry integration:
```python
def init_telem(ctx):
    sentry_sdk.init(
        # configuration
    )

def close_telem():
    sentry_sdk.flush()
```

## Configuration Reference

### Environment Variables

#### Backend Services
| Variable | Description | Default |
|----------|-------------|---------|
| `SERVICES__SENTRY__SERVER_DSN` | Sentry DSN for backend services | None |
| `CODECOV_ENV` | Environment name | None |
| `SERVICES__SENTRY__SAMPLE_RATE` | Trace sampling rate | 0.1 (api), 1.0 (worker) |
| `SERVICES__SENTRY__PROFILE_SAMPLE_RATE` | Profile sampling rate | 0.01 (api), 1.0 (worker) |
| `CLUSTER_ENV` | Cluster identifier for tagging | None |
| `DD_ENV` | DataDog environment (worker) | "production" |
| `SENTRY_RELEASE` | Release version (worker) | worker version |

#### Frontend (Gazebo)
| Variable | Description | Default |
|----------|-------------|---------|
| `REACT_APP_SENTRY_DSN` | Sentry DSN for frontend | None |
| `REACT_APP_SENTRY_ENVIRONMENT` | Environment name | "staging" |
| `REACT_APP_SENTRY_TRACING_SAMPLE_RATE` | Trace sampling rate | 1.0 |
| `REACT_APP_SENTRY_PROFILING_SAMPLE_RATE` | Profile sampling rate | 0.1 |
| `REACT_APP_SENTRY_SESSION_SAMPLE_RATE` | Session replay sampling | 0.1 |
| `REACT_APP_SENTRY_ERROR_SAMPLE_RATE` | Error session replay sampling | 1.0 |

#### Build & Deployment
| Variable | Description | Default |
|----------|-------------|---------|
| `SENTRY_AUTH_TOKEN` | Auth token for source map uploads | None |
| `SENTRY_ORG` | Sentry organization | "codecov" |
| `REACT_APP_SENTRY_PROJECT` | Sentry project name | "gazebo" |
| `GAZEBO_SHA` | Git SHA for release tracking | None |

## Security & Privacy

### Data Scrubbing
Backend services use `EventScrubber` with a deny list that includes:
- Default Sentry deny list items
- `_headers` - HTTP headers
- `token_to_use` - Authentication tokens

### Frontend Filtering
- User agent blocking (e.g., web crawlers)
- Third-party error tagging
- Extensive ignore lists for browser extensions

### OAuth Security
- JWT-based state management
- Shared secret for state validation
- Secure token exchange flow

## Development Setup

### Backend Services
1. Set `SERVICES__SENTRY__SERVER_DSN` environment variable
2. Optionally set `CODECOV_ENV` for environment tagging
3. In development, Spotlight integration is automatically enabled

### Frontend (Gazebo)
1. Create `.env` file with `REACT_APP_SENTRY_DSN`
2. Set `REACT_APP_SENTRY_ENVIRONMENT` to a unique identifier (e.g., your username)
3. Spotlight browser integration available in development mode

### Testing
- Error boundaries can be tested with mock components that throw errors
- Sentry test mode available for integration testing
- Worker includes unit tests for Sentry initialization

## Best Practices

1. **Environment Naming**: Use descriptive environment names for easy filtering
2. **Sampling Rates**: Adjust based on traffic volume and quota limits
3. **Error Filtering**: Regularly review and update ignore lists
4. **Release Tracking**: Always set release versions for better debugging
5. **Scoping**: Use error boundary scopes to categorize errors
6. **User Feedback**: Enable feedback widgets for better user communication

## Critical Experiences Monitoring

### Defined Critical Experiences

1. **Upload Processing** (Revenue Protection)
   - Monitor: Processing time, success rate, queue depth
   - Business Impact: Failed uploads → customer churn
   - Key Segments: Enterprise, high-volume users, trials

2. **PR Comment Generation** (User Satisfaction)
   - Monitor: Time to comment, accuracy, formatting
   - Business Impact: Poor experience → team abandonment
   - Key Segments: Active teams, OSS projects

3. **First Upload Experience** (Growth)
   - Monitor: Time to first success, error types
   - Business Impact: Failed activation → lost conversion
   - Key Segments: Trial users, new signups

4. **Dashboard Performance** (Retention)
   - Monitor: Load times, data freshness
   - Business Impact: Slow dashboards → renewal risk
   - Key Segments: Enterprise, decision makers

### Implementation Example

```python
@CriticalExperienceMonitor.track_critical_experience(
    "upload_processing",
    organization=upload.repository.author
)
@PerformanceMonitor.track_operation("process_upload")
def process_upload(upload_id: str):
    # Dual monitoring: technical + business
    pass
```

## Performance Monitoring

### Technical Metrics Tracked

1. **Service Level Indicators**
   - Request latency (p50, p95, p99)
   - Error rates by endpoint
   - Database query performance
   - Cache hit rates

2. **Infrastructure Metrics**
   - CPU and memory usage
   - Queue depths
   - Network latency
   - Disk I/O

3. **Application Metrics**
   - Upload processing stages
   - Coverage calculation time
   - Report generation speed
   - API response times

### Distributed Tracing

Full request lifecycle tracking across:
- Gazebo (frontend) → API → Worker → External services
- Includes baggage propagation for context
- Automatic span creation for key operations

## Monitoring & Debugging

### Dashboards

1. **Technical Dashboards** (Engineering)
   - System performance overview
   - Service health metrics
   - Error analysis and trends
   - Infrastructure monitoring

2. **Business Dashboards** (Leadership & Customer Success)
   - Revenue impact analysis
   - Customer experience health
   - Trial conversion metrics
   - Churn risk indicators

3. **Operational Dashboards** (Support)
   - Active issues by customer tier
   - Recent errors with context
   - Performance degradation alerts

### Alerting Strategy

1. **Critical Alerts** (Page on-call)
   - Enterprise customer failures
   - System-wide outages
   - Security incidents

2. **High Priority** (Notify team)
   - Trial user activation issues
   - Performance SLO breaches
   - Error rate spikes

3. **Informational** (Dashboard/Slack)
   - Trending issues
   - Capacity warnings
   - Non-critical errors

### Debugging Tools

1. **Sentry Dashboard**: Monitor errors, performance, and replays
2. **Distributed Tracing**: Track requests across services
3. **Session Replays**: Debug user issues with recorded sessions
4. **Performance Profiling**: Identify bottlenecks in both frontend and backend
5. **Release Health**: Track error rates across releases
6. **Custom Queries**: Analyze specific customer segments or experiences