---
name: cost-spike-investigation
description: Investigates sudden cost increases, spikes, or anomalies by comparing recent spending to baseline periods and identifying which services, accounts, or resources are responsible for unexpected changes in cloud spending
author: CloudZero <support@cloudzero.com>
version: 1.0.0
license: Apache-2.0
---

# Cost Spike Investigation

## Purpose
This skill helps identify and explain sudden increases in cloud costs by comparing recent spending patterns to historical baselines and pinpointing the specific resources, services, or dimensions responsible for the spike.

## When to Use
- User reports unexpected cost increases
- Monthly bills show significant jumps
- Alerts indicate spending anomalies
- Need to explain "why did costs go up?"
- Investigating budget overruns
- Keywords: spike, increase, jump, surge, anomaly, unexpected, sudden change

## Prerequisites

This skill builds on the **understand-cloudzero-organization** skill.

Before applying this procedure:
- If you haven't already in this session, load the understand-cloudzero-organization skill and follow its instructions
- Reference the cached organization context (don't reload unnecessarily)

## How This Skill Works

### Step 1: Understand the Spike Period
- Clarify when the spike occurred (specific date, week, month)
- Define baseline period for comparison (e.g., previous month, same period last year)
- Default to comparing last 7 days vs. previous 7 days if not specified

### Step 2: Identify Top-Level Changes
Query total costs for both periods:
```
# Recent period (where spike occurred)
get_cost_data(
    date_range="2024-01-15 to 2024-01-21",
    granularity=None,
    cost_type="real_cost"
)

# Baseline period (for comparison)
get_cost_data(
    date_range="2024-01-08 to 2024-01-14",
    granularity=None,
    cost_type="real_cost"
)
```

Calculate:
- Absolute dollar change
- Percentage increase
- Cost per day in each period

### Step 3: Drill Down by Key Dimensions
Systematically check common cost drivers to identify where the spike originated:

**Check by Cloud Provider:**
```
get_cost_data(
    group_by=["CZ:CloudProvider"],
    date_range="<spike_period>",
    limit=10
)
```

**Check by Service:**
```
get_cost_data(
    group_by=["CZ:Service"],
    date_range="<spike_period>",
    limit=20
)
```

**Check by Account:**
```
get_cost_data(
    group_by=["CZ:Account"],
    date_range="<spike_period>",
    limit=20
)
```

Compare results from spike period vs. baseline period to identify:
- Services with largest absolute increases
- Services with largest percentage increases
- New services that appeared during spike period

### Step 4: Multi-Dimensional Analysis
Once you identify the primary dimension responsible, drill deeper:

```
# Example: If EC2 showed the spike, break down by account and region
get_cost_data(
    group_by=["CZ:Account", "CZ:Region"],
    filters={"CZ:Service": ["Amazon Elastic Compute Cloud - Compute"]},
    date_range="<spike_period>",
    limit=50
)
```

### Step 5: Time-Series Analysis
Show how costs evolved during the spike period:

```
get_cost_data(
    group_by=["CZ:Service"],
    granularity="daily",
    date_range="<extended_period_including_spike>",
    limit=5
)
```

This reveals:
- When exactly the spike started
- Whether it's sustained or temporary
- If it's still ongoing

### Step 6: Check for New Resources
Identify if new resources were provisioned:

```
# Compare dimension values between periods
get_dimension_values(
    dimension="CZ:Resource",
    date_range="<spike_period>"
)

get_dimension_values(
    dimension="CZ:Resource",
    date_range="<baseline_period>"
)
```

### Step 7: Investigate Tags and Custom Dimensions
Use organization-specific dimensions to attribute costs:

```
# Discover available custom dimensions
get_available_dimensions(filter="User:Defined")

# Query by relevant custom dimensions
get_cost_data(
    group_by=["User:Defined:Team", "CZ:Service"],
    date_range="<spike_period>",
    limit=30
)
```

Check tag-based attribution:
```
get_available_dimensions(filter="Tag")

get_cost_data(
    group_by=["CZ:Tag:Environment", "CZ:Service"],
    date_range="<spike_period>",
    limit=30
)
```

### Step 8: Check for Related Tickets
Before reporting findings, check if this spike is already tracked:

**Jira:**
```
searchJiraIssuesUsingJql(
    jql="text ~ '[service or account from spike]' AND text ~ 'cost' AND status != Done",
    limit=5
)
```

**DevRev:**
```
hybrid_search(
    query="cost spike [service or account from spike]",
    namespace="ticket"
)
```

**Confluence — check for runbooks:**
```
searchConfluenceUsingCql(
    cql="text ~ '[service]' AND text ~ 'runbook' AND type = 'page'",
    limit=5
)
```

If related tickets exist, reference them in the report. If runbooks exist, follow their guidance.

### Step 9: Create or Update Ticket (When Appropriate)
If the spike warrants action and no existing ticket covers it:

**Jira:**
```
createJiraIssue(
    projectKey="<project>",
    summary="Cost spike: [service] +$X (+Y%) — [date range]",
    description="<investigation findings summary>",
    issueType="Task"
)
```

**DevRev:**
```
create_ticket(
    title="Cost spike: [service] +$X (+Y%) — [date range]",
    description="<investigation findings summary>"
)
```

Only create tickets for spikes that are:
- Significant (>20% increase or >$X threshold per org context)
- Not already tracked
- Actionable (not explained by known planned changes)

## Output Format

Provide a clear, structured investigation report:

### 1. Executive Summary
- Total cost increase ($ and %)
- Time period analyzed
- Primary root cause in one sentence

### 2. Spike Metrics
- Baseline period cost: $X
- Spike period cost: $Y
- Absolute increase: $Z
- Percentage increase: W%
- Cost per day comparison

### 3. Root Cause Analysis
- **Primary driver:** [Service/Account/Resource] responsible for X% of increase
- **Contributing factors:** Secondary drivers ranked by impact
- **New resources:** Any newly provisioned resources

### 4. Detailed Breakdown
- Top 5-10 cost changes by relevant dimensions
- Time-series visualization (describe the pattern)
- Multi-dimensional attribution (e.g., which team, which account)

### 5. Related Tickets & Documentation
- **Existing tickets:** [Any related Jira/DevRev tickets found, with links]
- **Runbooks:** [Any relevant Confluence runbooks found]
- **New ticket created:** [Link to ticket if one was created]

### 6. Recommendations
- Is this spike expected/legitimate or potentially wasteful?
- Immediate actions to investigate further
- Potential optimization opportunities
- Monitoring recommendations to prevent future surprises

## Skill-Specific Best Practices

1. **Compare apples to apples** - Use same date range lengths for baseline and spike periods
2. **Check multiple dimensions** - Don't stop at just service-level analysis
3. **Look for new resources** - Spikes often come from new provisioning
4. **Consider seasonality** - Compare to same period last year if relevant
5. **Show your work** - Explain which queries you ran and why
6. **Be specific** - Provide exact numbers, dimension values, and time periods

For general cost analysis best practices, see `${CLAUDE_PLUGIN_ROOT}/references/best-practices.md`

## Common Spike Patterns

- **New resource provisioning:** Large instances, databases, or storage volumes
- **Scaling events:** Auto-scaling responding to traffic
- **Data transfer spikes:** Unusual egress or cross-region transfer
- **Reserved Instance expiration:** Reverting to on-demand pricing
- **Development/testing:** Teams spinning up test environments
- **Crypto mining/security incidents:** Unauthorized resource usage

## See Also

- **understand-cloudzero-organization** skill - Load organization context first
- `${CLAUDE_PLUGIN_ROOT}/references/best-practices.md` - Universal cost analysis best practices
- `${CLAUDE_PLUGIN_ROOT}/references/cloudzero-tools-reference.md` - Complete tool documentation
- `${CLAUDE_PLUGIN_ROOT}/references/error-handling.md` - Troubleshooting and common errors
- `${CLAUDE_PLUGIN_ROOT}/references/dimensions-reference.md` - Dimension types and FQDIDs
- `${CLAUDE_PLUGIN_ROOT}/references/cost-types-reference.md` - When to use each cost type
