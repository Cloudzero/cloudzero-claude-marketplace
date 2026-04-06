---
name: cost-trend-analysis
description: "Use when analyzing whether costs are growing, declining, or stable over time — for forecasting, budget planning, or understanding spending velocity"
author: CloudZero <support@cloudzero.com>
version: 1.0.0
license: Apache-2.0
---

# Cost Trend Analysis

## Purpose
This skill analyzes how cloud costs change over time, identifying patterns, growth rates, and trajectories to help with forecasting, budget planning, and understanding spending dynamics.

## When to Use
- "How are my costs trending?"
- "Are costs going up or down?"
- "What's my cost growth rate?"
- "Show me cost trends over the last [period]"
- "Forecast next month's spending"
- Budget planning and forecasting
- Quarterly or annual reviews
- Understanding spending velocity
- Keywords: trend, growth, trajectory, pattern, forecast, over time, month over month, increasing, decreasing

## Prerequisites

This skill builds on the **understand-cloudzero-organization** skill.

Before applying this procedure:
- If you haven't already in this session, load the understand-cloudzero-organization skill and follow its instructions
- Reference the cached organization context (don't reload unnecessarily)

## How This Skill Works

### Step 1: Determine Analysis Period
Clarify the time range and granularity:
- **Short-term trends (1-3 months):** Use daily granularity
- **Medium-term trends (3-6 months):** Use weekly granularity
- **Long-term trends (6+ months):** Use monthly granularity
- Default: Last 90 days with daily granularity if not specified

### Step 2: Query Overall Trend
Get total costs over time:

```
get_cost_data(
    granularity="daily",  # or "weekly" or "monthly"
    date_range="last 90 days",
    cost_type="real_cost"
)
```

From this data:
- Calculate total cost per period
- Identify overall trend direction (increasing/decreasing/stable)
- Calculate growth rate
- Identify any obvious spikes or dips

### Step 3: Calculate Growth Metrics

**Week-over-Week (WoW) Growth:**
- Compare most recent week to previous week
- Calculate percentage change
- Determine if acceleration or deceleration

**Month-over-Month (MoM) Growth:**
- Compare most recent month to previous month
- Calculate percentage change
- Identify momentum

**Compound Growth Rate:**
- Calculate average growth rate across entire period
- Project forward if trend continues

**Example Calculations:**
```
Current Week Cost: $10,000
Previous Week Cost: $9,500
WoW Growth = ((10000 - 9500) / 9500) * 100 = 5.3%

If 90-day period shows growth from $250k to $300k:
Total Growth = ((300000 - 250000) / 250000) * 100 = 20%
Monthly Growth Rate = (1 + 0.20)^(1/3) - 1 ≈ 6.3% per month
```

### Step 4: Trend by Key Dimensions
Understand which dimensions are driving trends:

**Trend by Service:**
```
get_cost_data(
    group_by=["CZ:Service"],
    granularity="daily",
    limit=10
)
```

For each top service:
- Calculate its individual growth rate
- Determine its contribution to overall trend
- Identify if it's accelerating or decelerating

**Trend by Account:**
```
get_cost_data(
    group_by=["CZ:Account"],
    granularity="daily",
    limit=10
)
```

**Trend by Custom Dimensions:**
```
get_available_dimensions(filter="User:Defined")

get_cost_data(
    group_by=["User:Defined:Team"],
    granularity="weekly",
    limit=15
)
```

### Step 5: Identify Pattern Types

**Growth Pattern:**
- Consistent upward trend
- Increasing costs each period
- Calculate if growth is linear or exponential

**Decline Pattern:**
- Consistent downward trend
- Costs decreasing over time
- Identify optimization efforts or reduced usage

**Stable Pattern:**
- Relatively flat with minor fluctuations
- Predictable, consistent spending
- Good for budgeting

**Volatile Pattern:**
- Large fluctuations up and down
- Unpredictable spending
- May indicate workload variability or cost management issues

**Seasonal Pattern:**
- Regular periodic increases/decreases
- Related to business cycles
- Compare same periods across multiple years if data available

**Step Change Pattern:**
- Sudden permanent shift in baseline
- New project launch or resource decommission
- Identify the inflection point date

### Step 6: Decompose the Trend
Break down overall trend into components:

1. **Growing services** - Services with positive growth contributing to increase
2. **Declining services** - Services with negative growth offsetting increase
3. **New services** - Services that didn't exist at start of period
4. **Stable services** - Services with minimal change

Calculate each category's contribution to overall trend.

### Step 7: Forecast Future Costs
Based on identified trends, project forward:

**Simple Linear Projection:**
```
If last 3 months show consistent $5k/month increase:
Next month projection = Current month + $5k
```

**Growth Rate Projection:**
```
If showing 6% monthly growth:
Next month = Current month * 1.06
Next quarter = Current month * (1.06)^3
```

**Provide ranges:**
- Conservative: Assuming lower growth
- Expected: Based on current trend
- High: Assuming trend accelerates

### Step 8: Identify Trend Drivers
For each significant trend, identify what's causing it:

**For increasing costs:**
- New resources provisioned?
- Scaling of existing resources?
- New teams or projects?
- Changes in usage patterns?

**For decreasing costs:**
- Optimization efforts?
- Resource decommissioning?
- Reserved Instance purchases?
- Migration to cheaper alternatives?

**For volatility:**
- Sporadic workloads?
- Development/testing activity?
- Lack of auto-scaling policies?
- Data transfer variability?

## Output Format

Provide comprehensive trend analysis:

### 1. Executive Summary
- Overall trend direction: [Increasing/Decreasing/Stable/Volatile]
- Current spending level: $X per [day/week/month]
- Growth rate: X% [MoM/WoW]
- Key driver: [Service/Account] responsible for trend
- One-sentence insight

### 2. Trend Metrics

**Current Period:**
- Total cost: $X
- Average per day: $Y
- Trajectory: [Increasing/Stable/Decreasing]

**Growth Rates:**
- Week-over-week: +X%
- Month-over-month: +Y%
- Quarter-over-quarter: +Z%
- Compound monthly growth rate: X%

**Momentum:**
- Accelerating / Decelerating / Consistent

### 3. Visual Trend Description
Describe the cost curve over time:
- Early period (first third): Pattern and level
- Middle period: How it changed
- Recent period (last third): Current state
- Overall shape: Linear growth, exponential growth, step changes, volatility

### 4. Dimensional Breakdown

**Services Driving Trend:**
| Service | Start Cost | End Cost | Change | % Growth | Contribution to Overall |
|---------|-----------|----------|---------|----------|------------------------|
| Service A | $X | $Y | +$Z | +XX% | XX% |
| ... | ... | ... | ... | ... | ... |

**Top Growing Services:**
- [Service]: +X% growth, now $Y/month
- [Service]: +A% growth, now $B/month

**Top Declining Services:**
- [Service]: -X% decline, now $Y/month

**New Services (not present at start):**
- [Service]: Now $X/month

### 5. Pattern Analysis
- **Type:** [Growth/Decline/Stable/Volatile/Seasonal/Step Change]
- **Consistency:** [Very consistent/Somewhat consistent/Irregular]
- **Predictability:** [Highly predictable/Moderately predictable/Unpredictable]
- **Seasonality:** [None detected/Weekly pattern/Monthly pattern]

### 6. Forecast

**Based on current trends:**
- Next week: $X (range: $A - $B)
- Next month: $Y (range: $C - $D)
- Next quarter: $Z (range: $E - $F)

**Confidence level:** [High/Medium/Low] based on trend consistency

**Assumptions:**
- Current growth rate continues
- No major changes to infrastructure
- Usage patterns remain similar

### 7. Insights and Recommendations

**If costs are growing:**
- Is growth aligned with business growth/revenue?
- Are there optimization opportunities?
- Should Reserved Instances or Savings Plans be considered?
- Are any services growing unusually fast?

**If costs are declining:**
- What drove the decline? (good to understand for replication)
- Is decline sustainable or one-time?
- Are there other areas to apply similar optimizations?

**If costs are volatile:**
- What's causing the variability?
- Can auto-scaling help smooth costs?
- Are there unnecessary environments being spun up/down?
- Should resources be rightsized?

**If costs are stable:**
- Is this expected given business activity?
- Are there hidden inefficiencies that could be addressed?
- Good baseline for detecting future anomalies

### 8. Action Items
1. [Specific action based on trend analysis]
2. [Monitoring recommendation]
3. [Optimization opportunity]
4. [Budget adjustment if needed]

## Skill-Specific Best Practices

1. **Choose appropriate granularity** - Match to analysis period
2. **Calculate multiple growth metrics** - WoW, MoM, QoQ for complete picture
3. **Look beyond overall trend** - Decompose by dimensions
4. **Provide forecast ranges** - Not single point estimates
5. **Compare to business metrics** - Is cost growth aligned with business growth?
6. **Identify inflection points** - When did trend direction change?
7. **Consider external factors** - Seasonal business patterns, new projects, etc.

For general cost analysis best practices, see `${CLAUDE_PLUGIN_ROOT}/references/best-practices.md`

## Advanced Techniques

### Multi-Period Comparison
Compare current trend to historical trends:

```
# Current quarter trend
get_cost_data(granularity="weekly", date_range="2024-01-01 to 2024-03-31")

# Same quarter last year
get_cost_data(granularity="weekly", date_range="2023-01-01 to 2023-03-31")
```

### Trend Decomposition
Separate trend into components:

1. **Baseline:** Stable underlying cost
2. **Growth component:** Gradual increase over time
3. **Cyclical component:** Regular patterns (weekly, monthly)
4. **Irregular component:** One-time events or noise

### Moving Averages
Smooth out noise to see underlying trend:

- 7-day moving average for daily data
- 4-week moving average for weekly data
- Helps identify true trend vs. noise

### Growth Rate by Segment
Calculate different growth rates for different cost segments:

```
# High-growth services
Services with >20% growth

# Moderate-growth services
Services with 5-20% growth

# Stable services
Services with -5% to +5% growth

# Declining services
Services with <-5% growth
```

## Common Trend Patterns and Causes

### Exponential Growth
- **Pattern:** Accelerating increase
- **Causes:** Uncontrolled auto-scaling, data accumulation, viral product growth
- **Action:** Immediate optimization review

### Linear Growth
- **Pattern:** Consistent increase
- **Causes:** Steady business growth, planned expansion
- **Action:** Monitor for alignment with business

### Step Increase
- **Pattern:** Sudden jump, then stable
- **Causes:** New project launch, migration, environment addition
- **Action:** Verify expected, then establish new baseline

### Weekly Cycle
- **Pattern:** Regular weekly peaks and troughs
- **Causes:** Weekday vs. weekend usage differences
- **Action:** Consider schedule-based auto-scaling

### Monthly Cycle
- **Pattern:** Regular monthly pattern
- **Causes:** Month-end processing, billing cycles
- **Action:** Budget for predictable peaks

### Declining Trend
- **Pattern:** Consistent decrease
- **Causes:** Optimization efforts, resource cleanup, migration to cheaper services
- **Action:** Document what worked for replication

## Tips for Effective Analysis

1. **Context matters:** A 20% increase might be great or terrible depending on business growth
2. **Look for correlations:** Does cost trend match user growth, revenue, or usage?
3. **Don't over-forecast:** Trends change, provide ranges and caveats
4. **Identify drivers:** Don't just report the trend, explain what causes it
5. **Be actionable:** Every trend analysis should suggest next steps

## See Also

- **understand-cloudzero-organization** skill - Load organization context first
- `${CLAUDE_PLUGIN_ROOT}/references/best-practices.md` - Universal cost analysis best practices
- `${CLAUDE_PLUGIN_ROOT}/references/cloudzero-tools-reference.md` - Complete tool documentation
- `${CLAUDE_PLUGIN_ROOT}/references/error-handling.md` - Troubleshooting and common errors
- `${CLAUDE_PLUGIN_ROOT}/references/dimensions-reference.md` - Dimension types and FQDIDs
- `${CLAUDE_PLUGIN_ROOT}/references/cost-types-reference.md` - When to use each cost type
