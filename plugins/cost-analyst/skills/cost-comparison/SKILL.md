---
name: cost-comparison
description: Use when comparing costs between time periods, environments, accounts, regions, or teams to understand spending differences and identify inefficiencies
author: CloudZero <support@cloudzero.com>
version: 1.0.0
license: Apache-2.0
---

# Cost Comparison

## Purpose
This skill performs side-by-side comparisons of cloud costs across different dimensions or time periods to identify variations, benchmark efficiency, and understand relative spending patterns.

## When to Use
- "Compare costs between [period A] and [period B]"
- "How do production costs compare to staging?"
- "Which account/team/region is more expensive?"
- "Compare this month to last month"
- "Show me differences between environments"
- Benchmarking across teams or projects
- Understanding cost variations
- Identifying inefficiencies
- Keywords: compare, comparison, versus, vs, difference, between, benchmark, relative

## Prerequisites

This skill builds on the **understand-cloudzero-organization** skill.

Before applying this procedure:
- If you haven't already in this session, load the understand-cloudzero-organization skill and follow its instructions
- Reference the cached organization context (don't reload unnecessarily)

## How This Skill Works

### Step 1: Identify Comparison Type
Determine what kind of comparison is needed:

**Time-Based Comparisons:**
- Period vs. period (this month vs. last month)
- Year-over-year (same period, different years)
- Before/after event (migration, optimization, etc.)

**Dimension-Based Comparisons:**
- Environment vs. environment (prod vs. staging vs. dev)
- Account vs. account
- Region vs. region
- Team vs. team (custom dimensions)
- Cloud provider vs. cloud provider

**Multi-Dimensional Comparisons:**
- Same service across different accounts
- Same team across different services
- Multiple dimensions combined

### Step 2: Query Data for Each Comparison Group

**Example: Time Period Comparison**
```
# Current period
get_cost_data(
    date_range="2024-02-01 to 2024-02-29",
    group_by=["CZ:Service"],
    limit=50
)

# Previous period
get_cost_data(
    date_range="2024-01-01 to 2024-01-31",
    group_by=["CZ:Service"],
    limit=50
)
```

**Example: Environment Comparison**
```
# Production environment
get_cost_data(
    filters={"CZ:Tag:Environment": ["production"]},
    group_by=["CZ:Service"],
    limit=50
)

# Staging environment
get_cost_data(
    filters={"CZ:Tag:Environment": ["staging"]},
    group_by=["CZ:Service"],
    limit=50
)

# Development environment
get_cost_data(
    filters={"CZ:Tag:Environment": ["development"]},
    group_by=["CZ:Service"],
    limit=50
)
```

**Example: Account Comparison**
```
get_cost_data(
    group_by=["CZ:Account", "CZ:Service"],
    limit=100
)
```

**Example: Team Comparison (Custom Dimensions)**
```
get_cost_data(
    group_by=["User:Defined:Team", "CZ:Service"],
    limit=100
)
```

### Step 3: Calculate Comparison Metrics
For each comparable item:

**Absolute Difference:**
```
Difference = Cost_A - Cost_B
```

**Percentage Difference:**
```
% Difference = ((Cost_A - Cost_B) / Cost_B) * 100
```

**Ratio:**
```
Ratio = Cost_A / Cost_B
```

**Per-Unit Metrics (if applicable):**
```
Cost per user, Cost per transaction, Cost per GB, etc.
```

### Step 4: Identify Key Differences
Categorize differences:

**Major Differences:**
- Items with >50% variance
- Large absolute dollar differences
- Items present in one group but not the other

**Moderate Differences:**
- Items with 20-50% variance
- Notable but not extreme

**Minor Differences:**
- Items with <20% variance
- Within normal variation

**Similarities:**
- Items with minimal difference
- Consistent across comparison groups

### Step 5: Drill Down on Significant Differences
For each major difference, investigate further:

**If Service A costs more in Environment 1 than Environment 2:**
```
# Break down by additional dimensions
get_cost_data(
    filters={"CZ:Tag:Environment": ["production"], "CZ:Service": ["AmazonEC2"]},
    group_by=["CZ:Region", "CZ:Account"],
    limit=50
)

get_cost_data(
    filters={"CZ:Tag:Environment": ["staging"], "CZ:Service": ["AmazonEC2"]},
    group_by=["CZ:Region", "CZ:Account"],
    limit=50
)
```

### Step 6: Normalize Comparisons (When Appropriate)
Make fair comparisons by normalizing for scale:

**Workload-adjusted:**
- Cost per request/transaction
- Cost per user
- Cost per GB processed

**Time-adjusted:**
- Daily average cost
- Cost per hour
- Account for different period lengths

**Resource-adjusted:**
- Cost per instance
- Cost per CPU
- Cost per GB storage

### Step 7: Identify Patterns and Insights
Look for:

**Efficiency Patterns:**
- Which group achieves similar outcomes at lower cost?
- What are the efficient groups doing differently?

**Waste Patterns:**
- Unnecessary duplication across groups?
- Over-provisioning in specific groups?
- Unused resources in certain environments?

**Architecture Patterns:**
- Different service mix between groups?
- Different regional deployments?
- Different optimization levels?

## Output Format

Provide clear, actionable comparison analysis:

### 1. Executive Summary
- What's being compared
- Overall cost difference: $X (Y%)
- Key finding in one sentence
- Primary driver of difference

### 2. High-Level Comparison

**Total Costs:**
| Group | Total Cost | Difference from [Baseline] | % Difference |
|-------|------------|---------------------------|-------------- |
| Group A | $X,XXX | +$X,XXX | +XX% |
| Group B | $X,XXX | -$X,XXX | -XX% |
| ... | ... | ... | ... |

**Summary:**
- Group A is X% more expensive than Group B
- Absolute difference: $X,XXX
- Primary reason: [Service/Factor]

### 3. Detailed Dimensional Breakdown

**By Service:**

| Service | Group A | Group B | Difference | % Diff | Notes |
|---------|---------|---------|------------|--------|-------|
| Service 1 | $X,XXX | $X,XXX | +$XXX | +XX% | [Insight] |
| Service 2 | $X,XXX | $X,XXX | -$XXX | -XX% | [Insight] |
| ... | ... | ... | ... | ... | ... |

**Top 5 Services Contributing to Difference:**
1. [Service]: $X higher in Group A (reason: [explanation])
2. [Service]: $X higher in Group B (reason: [explanation])
3. ...

### 4. Items Present in One Group Only

**Unique to Group A:**
- [Service/Resource]: $X,XXX
- [Service/Resource]: $Y,YYY
- **Implication:** [Analysis of why this matters]

**Unique to Group B:**
- [Service/Resource]: $X,XXX
- **Implication:** [Analysis]

### 5. Normalized Comparison (if applicable)

If comparing groups of different scale:

| Metric | Group A | Group B | Difference |
|--------|---------|---------|------------|
| Cost per day | $X,XXX | $X,XXX | +XX% |
| Cost per user | $X.XX | $X.XX | +XX% |
| Cost per transaction | $X.XX | $X.XX | +XX% |

**Insight:** Even after normalizing for [scale factor], Group A is X% more expensive.

### 6. Efficiency Analysis

**Most Efficient:**
- [Group] achieves [outcome] at [cost]
- [Specific practices/configurations that contribute to efficiency]

**Least Efficient:**
- [Group] spends X% more for similar outcomes
- [Specific inefficiencies identified]

**Efficiency Recommendations:**
- Apply [Group A's practices] to [Group B]
- Consider [specific optimization]

### 7. Time-Series Comparison (for period comparisons)

**How the difference evolved:**
```
Day/Week/Month | Group A | Group B | Difference
[Period 1] | $X,XXX | $X,XXX | $XXX
[Period 2] | $X,XXX | $X,XXX | $XXX
...
```

**Trend:** Difference is [growing/shrinking/stable]

### 8. Root Cause Analysis

**Why Group A costs more than Group B:**
1. **[Primary cause]:** Explains $X,XXX (XX%) of difference
   - Details: [specifics]
   - Contributing factors: [list]

2. **[Secondary cause]:** Explains $Y,YYY (YY%) of difference
   - Details: [specifics]

3. **[Other factors]:** Remaining $Z,ZZZ (ZZ%)

### 9. Recommendations

**For Higher-Cost Group:**
1. [Specific optimization opportunity]
2. [Configuration change to match efficient group]
3. [Resource rightsizing recommendation]

**For Lower-Cost Group:**
1. [Lessons to share with other groups]
2. [Monitoring to ensure no compromise on performance/reliability]

**General:**
1. [Standardization opportunities]
2. [Policy changes]
3. [Architecture recommendations]

## Skill-Specific Best Practices

1. **Use consistent time periods** - Compare equal-length periods
2. **Normalize when appropriate** - Account for scale differences
3. **Look for root causes** - Don't just report differences, explain them
4. **Consider business context** - Some differences may be justified
5. **Focus on actionable differences** - Highlight what can be optimized
6. **Use multiple dimensions** - Don't stop at top-level comparison
7. **Calculate both absolute and percentage differences** - Both matter

For general cost analysis best practices, see `${CLAUDE_PLUGIN_ROOT}/references/best-practices.md`

## Common Comparison Scenarios

### Scenario 1: This Month vs. Last Month
**Goal:** Understand month-over-month changes

**Approach:**
1. Query both months with same dimensions
2. Calculate differences for each service
3. Identify new services or removed services
4. Check for one-time charges
5. Normalize for different month lengths if needed

### Scenario 2: Production vs. Non-Production
**Goal:** Understand if non-prod is appropriately scaled

**Approach:**
1. Compare total costs by environment tag
2. Break down by service to see if mix is similar
3. Calculate ratio (e.g., staging should be 20% of prod)
4. Identify inefficiencies (oversized non-prod resources)
5. Recommend rightsizing non-prod

### Scenario 3: Team A vs. Team B
**Goal:** Benchmark efficiency across teams

**Approach:**
1. Use custom dimensions to separate teams
2. Compare total costs and service mix
3. Normalize for team size or workload if possible
4. Identify best practices from efficient team
5. Share learnings across teams

### Scenario 4: Region A vs. Region B
**Goal:** Understand regional cost differences

**Approach:**
1. Compare same services across regions
2. Account for different pricing in different regions
3. Consider data transfer costs between regions
4. Evaluate if workload distribution is optimal
5. Recommend consolidation if appropriate

### Scenario 5: Before vs. After Optimization
**Goal:** Measure impact of cost optimization effort

**Approach:**
1. Compare equal periods before and after
2. Calculate savings achieved
3. Identify which services/resources were optimized
4. Calculate ROI of optimization effort
5. Document lessons for future optimizations

## Advanced Techniques

### Multi-Group Comparison
Compare more than 2 groups simultaneously:

```
get_cost_data(
    group_by=["CZ:Tag:Environment", "CZ:Service"],
    limit=100
)
```

Create matrix showing all pairwise comparisons.

### Variance Analysis
Calculate statistical variance across groups:
- Mean cost per group
- Standard deviation
- Coefficient of variation
- Outlier detection

### Benchmark Ratios
Establish expected ratios:
- Staging should be 10-20% of production
- Development should be 5-10% of production
- Multi-region should not be >30% more than single region

Flag groups that deviate from expectations.

### Cost Per Unit Economics
When comparing teams/products:
```
Team A: $10,000 / 1000 users = $10/user
Team B: $15,000 / 2000 users = $7.50/user
```

Team B is more efficient despite higher absolute cost.

## Tips for Effective Comparison

1. **Set clear baseline:** Choose appropriate comparison baseline
2. **Explain differences:** Every difference should have an explanation
3. **Be fair:** Account for legitimate reasons for cost differences
4. **Focus on learnings:** What can each group learn from the other?
5. **Track over time:** Set up ongoing comparisons to monitor trends
6. **Combine with other skills:** Use spike investigation or trend analysis for deeper insights

## See Also

- **understand-cloudzero-organization** skill - Load organization context first
- `${CLAUDE_PLUGIN_ROOT}/references/best-practices.md` - Universal cost analysis best practices
- `${CLAUDE_PLUGIN_ROOT}/references/cloudzero-tools-reference.md` - Complete tool documentation
- `${CLAUDE_PLUGIN_ROOT}/references/error-handling.md` - Troubleshooting and common errors
- `${CLAUDE_PLUGIN_ROOT}/references/dimensions-reference.md` - Dimension types and FQDIDs
- `${CLAUDE_PLUGIN_ROOT}/references/cost-types-reference.md` - When to use each cost type
