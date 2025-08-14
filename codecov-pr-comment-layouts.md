# Codecov PR Comment Layout Examples

This document provides comprehensive examples of different Codecov PR comment layouts and their configurations.

## Overview

Codecov PR comments can be customized using the `layout` option in your `codecov.yml` file. The layout determines which sections appear in your PR comment and in what order.

## Available Layout Options

### Header Sections (displayed at top)
- **`header`** - Shows patch coverage status, project coverage comparison, and commit links
- **`newheader`** - Same as header (deprecated, use `header` instead)
- **`condensed_header`** - Compact version of header information

### Middle Sections (main content area)
- **`diff`** - Coverage diff of the pull request
- **`flags`** - List of user-defined flags and their coverage impact
- **`files`** - List of files impacted by the PR with coverage changes
- **`tree`** - Tree view of impacted files
- **`reach`** - Reachability analysis information
- **`components`** - List of user-defined components and their coverage impact
- **`announcements`** - Codecov announcements and tips

### Footer Sections (displayed at bottom)
- **`footer`** - Traditional footer with legend and links
- **`newfooter`** - Modern footer with feedback links (deprecated)
- **`condensed_footer`** - Compact footer version

### Special Sections
- **`newfiles`** - Information about new files (deprecated, auto-added with files/tree)
- **`condensed_files`** - Compact file listing

## Layout Examples

### 1. Default Layout (Condensed Header Only)

**Configuration:**
```yaml
comment:
  layout: "condensed_header"
```

**Output:**
```markdown
## Codecov Report
❌ Patch coverage is `66.66667%` with `1 line` in your changes missing coverage. Please review.
✅ Project coverage is 60.00%. Comparing base (`1234567`) to head (`2345678`).
```

### 2. Modern Condensed Layout (Recommended)

**Configuration:**
```yaml
comment:
  layout: "condensed_header, condensed_files, condensed_footer"
  hide_project_coverage: true
```

**Output:**
```markdown
## Codecov Report
❌ Patch coverage is `66.66667%` with `1 line` in your changes missing coverage. Please review.

| Files with missing lines | Patch % | Lines |
|---------------------------|---------|-------|
| file_1.go | 66.67% | 1 Missing ⚠️ |

📢 Thoughts on this report? Let us know!
```

### 3. Full Traditional Layout

**Configuration:**
```yaml
comment:
  layout: "header, reach, diff, flags, files, footer"
```

**Output:**
```markdown
## Codecov Report
❌ Patch coverage is `66.66667%` with `1 line` in your changes missing coverage. Please review.
✅ Project coverage is 60.00%. Comparing base (`1234567`) to head (`2345678`).

| Files with missing lines | Patch % | Lines |
|---------------------------|---------|-------|
| file_1.go | 66.67% | 1 Missing ⚠️ |

[![Impacted file tree graph](tree.svg)](pull/1?src=pr&el=tree)

```diff
@@              Coverage Diff              @@
##             master       #1       +/-   ##
=============================================
+ Coverage     50.00%   60.00%   +10.00%     
+ Complexity       11       10        -1     
=============================================
  Files             2        2               
  Lines             6       10        +4     
  Branches          0        1        +1     
=============================================
+ Hits              3        6        +3     
  Misses            3        3               
- Partials          0        1        +1     
```

| Flag | Coverage Δ | Complexity Δ | |
|------|------------|---------------|---|
| integration | `?` | `?` | |
| unit | `100.00% <100.00%> (?)` | `0.00 <0.00> (?)` | |

Flags with carried forward coverage won't be shown. Click here to find out more.

| Files with missing lines | Coverage Δ | Complexity Δ | |
|---------------------------|------------|---------------|---|
| file_1.go | `62.50% <66.67%> (+12.50%)` | `10.00 <0.00> (-1.00)` | ⬆️ |

... and 1 file with indirect coverage changes

------

Continue to review full report in Codecov by Sentry.
> **Legend** - Click here to learn more
> `Δ = absolute <relative> (impact)`, `ø = not affected`, `? = missing data`
> Powered by Codecov. Last update 1234567...2345678. Read the comment docs.
```

### 4. Layout with Components

**Configuration:**
```yaml
comment:
  layout: "header, components, files, newfooter"
```

**Output:**
```markdown
## Codecov Report
❌ Patch coverage is `66.66667%` with `1 line` in your changes missing coverage. Please review.
✅ Project coverage is 60.00%. Comparing base (`1234567`) to head (`2345678`).

| Components | Coverage Δ | |
|------------|-------------|---|
| go_files | `62.50% <66.67%> (+12.50%)` | ⬆️ |
| py_files | `50.00% <ø> (ø)` | |

| Files with missing lines | Coverage Δ | Complexity Δ | |
|---------------------------|------------|---------------|---|
| file_1.go | `62.50% <66.67%> (+12.50%)` | `10.00 <0.00> (-1.00)` | ⬆️ |

☂️ View full report in Codecov by Sentry.   
📢 Have feedback on the report? Share it here.
```

### 5. Layout with Announcements

**Configuration:**
```yaml
comment:
  layout: "header, announcements"
```

**Output:**
```markdown
## Codecov Report
❌ Patch coverage is `66.66667%` with `1 line` in your changes missing coverage. Please review.
✅ Project coverage is 60.00%. Comparing base (`1234567`) to head (`2345678`).
📣 Codecov offers a browser extension for seamless coverage viewing on GitHub. Try it in Chrome or Firefox today!
```

### 6. When All Tests Pass

**Configuration:**
```yaml
comment:
  layout: "header, files, footer"
```

**Output:**
```markdown
## Codecov Report
✅ All modified and coverable lines are covered by tests.
✅ Project coverage is 88.54%. Comparing base (`1234567`) to head (`2345678`).

| Files | Coverage Δ | |
|-------|-------------|---|
| file_1.go | `100.00% <100.00%> (+5.00%)` | ⬆️ |

------

Continue to review full report in Codecov by Sentry.
> **Legend** - Click here to learn more
> `Δ = absolute <relative> (impact)`, `ø = not affected`, `? = missing data`
> Powered by Codecov. Last update 1234567...2345678. Read the comment docs.
```

### 7. Warning Messages (Missing Base Report)

**Configuration:**
```yaml
comment:
  layout: "header, files, newfooter"
```

**Output:**
```markdown
## Codecov Report
❌ Patch coverage is `66.66667%` with `1 line` in your changes missing coverage. Please review.
⚠️ Please upload report for BASE (`master@cdf9aa4`). Learn more about missing BASE report.

| Files with missing lines | Patch % | Lines |
|---------------------------|---------|-------|
| file_1.go | 66.67% | 1 Missing ⚠️ |

☂️ View full report in Codecov by Sentry.   
📢 Have feedback on the report? Share it here.
```

### 8. Complex File Table Example

**Configuration:**
```yaml
comment:
  layout: "header, files, footer"
```

**Output:**
```markdown
## Codecov Report
❌ Patch coverage is `75.00%` with `3 lines` in your changes missing coverage. Please review.
✅ Project coverage is 82.45%. Comparing base (`1234567`) to head (`2345678`).

| Files with missing lines | Coverage Δ | Complexity Δ | |
|---------------------------|------------|---------------|---|
| src/components/Button.tsx | `85.71% <75.00%> (+2.15%)` | `12.00 <5.00> (+1.00)` | ⬆️ |
| src/utils/validation.js | `92.30% <100.00%> (+1.20%)` | `8.50 <2.00> (-0.50)` | ⬆️ |
| tests/unit/helpers.py | `100.00% <100.00%> (ø)` | `3.00 <1.00> (ø)` | |

... and 2 files with indirect coverage changes

------

Continue to review full report in Codecov by Sentry.
> **Legend** - Click here to learn more
> `Δ = absolute <relative> (impact)`, `ø = not affected`, `? = missing data`
> Powered by Codecov. Last update 1234567...2345678. Read the comment docs.
```

### 9. Flags Table Example

**Configuration:**
```yaml
comment:
  layout: "header, flags, footer"
```

**Output:**
```markdown
## Codecov Report
❌ Patch coverage is `66.67%` with `1 line` in your changes missing coverage. Please review.
✅ Project coverage is 60.00%. Comparing base (`1234567`) to head (`2345678`).

| Flag | Coverage Δ | Complexity Δ | |
|------|------------|---------------|---|
| backend-unit | `85.00% <75.00%> (+2.50%)` | `15.20 <3.50> (+0.80)` | ⬆️ |
| frontend-unit | `92.50% <100.00%> (+1.25%)` | `8.40 <2.00> (-0.20)` | ⬆️ |
| integration-tests | `78.30% <66.67%> (-1.10%)` | `22.10 <5.50> (+1.50)` | ⬇️ |

Flags with carried forward coverage won't be shown. Click here to find out more.

------

Continue to review full report in Codecov by Sentry.
> **Legend** - Click here to learn more
> `Δ = absolute <relative> (impact)`, `ø = not affected`, `? = missing data`
> Powered by Codecov. Last update 1234567...2345678. Read the comment docs.
```

## Common Emojis Used in Codecov Comments

- ✅ `:white_check_mark:` - Success, all tests pass, good coverage
- ❌ `:x:` - Issues, missing coverage, failed tests  
- ⚠️ `:warning:` - Warnings, missing reports, attention needed
- 📢 `:loudspeaker:` - Announcements, feedback requests
- 📣 `:mega:` - Marketing messages, feature announcements
- ☂️ `:umbrella:` - Codecov branding (umbrella logo)
- ⬆️ `:arrow_up:` - Coverage increased
- ⬇️ `:arrow_down:` - Coverage decreased
- ➡️ `:arrow_right:` - No change in coverage

## Additional Configuration Options

### Hide Project Coverage
```yaml
comment:
  layout: "condensed_header, condensed_files, condensed_footer"
  hide_project_coverage: true  # Only show patch coverage
```

### Require Changes to Post Comment
```yaml
comment:
  layout: "header, files, footer"
  require_changes: true  # Only post if coverage changes
```

### Comment Behavior
```yaml
comment:
  layout: "header, files, footer"
  behavior: "default"  # Options: default, once, new
```

### After N Builds
```yaml
comment:
  layout: "header, files, footer"
  after_n_builds: 2  # Wait for 2 builds before posting
```

## Deprecated Options

These options are still supported but deprecated:

- **`newheader`** - Use `header` instead
- **`newfooter`** - Use `condensed_footer` instead  
- **`newfiles`** - Automatically added when using `files` or `tree`

## Best Practices

1. **Use condensed layouts** for cleaner, more focused comments
2. **Hide project coverage** if you only care about patch coverage
3. **Combine multiple sections** to get the information you need
4. **Use `require_changes`** to reduce comment noise
5. **Test your layout** in a development branch first

## Complete Configuration Example

```yaml
# codecov.yml
comment:
  layout: "condensed_header, condensed_files, condensed_footer"
  hide_project_coverage: false
  require_changes: true
  behavior: default
  after_n_builds: 1
  show_carryforward_flags: false
```

This configuration provides a clean, informative comment that only appears when coverage changes.