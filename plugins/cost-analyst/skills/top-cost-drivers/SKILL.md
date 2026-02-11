---
name: top-cost-drivers
description: Identifies and ranks the biggest contributors to cloud spending across services, accounts, teams, regions, or custom dimensions to help prioritize cost optimization efforts and understand spending distribution
author: CloudZero <support@cloudzero.com>
version: 1.0.0
license: Apache-2.0
---

# Top Cost Drivers

## Purpose
This skill identifies and ranks the highest cloud cost contributors across various dimensions to help users understand where their money is going and prioritize optimization efforts.

## When to Use
- "What are my biggest costs?"
- "Where is most of my cloud spending?"
- "What should I optimize first?"
- "Show me top spending by [service/account/team]"
- Monthly cost reviews
- Budget planning and allocation
- Identifying optimization priorities
- Keywords: top, biggest, largest, highest, most expensive, cost drivers, where is money going

## Prerequisites

This skill builds on the **understand-cloudzero-organization** skill.

Before applying this procedure:
- If you haven't already in this session, load the understand-cloudzero-organization skill and follow its instructions
- Reference the cached organization context (don't reload unnecessarily)

## How This Skill Works

### Step 1: Understand the Request
Clarify what dimensions the user wants to analyze:
- Services? Accounts? Teams? Regions?
- Specific time period? (default: last 30 days)
- Any filters to apply? (e.g., specific cloud provider, environment)

### Step 2: Query Top Costs by Primary Dimension

**Top Services:**
```
get_cost_data(
    group_by=["CZ:Service"],
    cost_type="real_cost",
    limit=20
)
```

**Top Accounts:**
```
get_cost_data(
    group_by=["CZ:Account"],
    cost_type="real_cost",
    limit=20
)
```

**Top by Cloud Provider:**
```
get_cost_data(
    group_by=["CZ:CloudProvider"],
    cost_type="real_cost",
    limit=10
)
```

**Top by Region:**
```
get_cost_data(
    group_by=["CZ:Region"],
    cost_type="real_cost",
    limit=20
)
```

### Step 3: Multi-Dimensional Breakdown
Break down top costs by multiple dimensions for deeper insights:

**Services within each Cloud Provider:**
```
get_cost_data(
    group_by=["CZ:CloudProvider", "CZ:Service"],
    cost_type="real_cost",
    limit=50
)
```

**Services within each Account:**
```
get_cost_data(
    group_by=["CZ:Account", "CZ:Service"],
    cost_type="real_cost",
    limit=50
)
```

**Services by Region:**
```
get_cost_data(
    group_by=["CZ:Region", "CZ:Service"],
    cost_type="real_cost",
    limit=50
)
```

### Step 4: Custom Dimension Analysis
Leverage organization-specific dimensions:

```
# Discover custom dimensions
get_available_dimensions(filter="User:Defined")

# Query by custom dimensions (e.g., teams, products)
get_cost_data(
    group_by=["User:Defined:Team"],
    cost_type="real_cost",
    limit=20
)

# Break down custom dimensions by service
get_cost_data(
    group_by=["User:Defined:Team", "CZ:Service"],
    cost_type="real_cost",
    limit=50
)
```

### Step 5: Tag-Based Analysis
Analyze costs by resource tags:

```
# Discover available tags
get_available_dimensions(filter="Tag")

# Top costs by environment tag
get_cost_data(
    group_by=["CZ:Tag:Environment"],
    cost_type="real_cost",
    limit=10
)

# Services within each environment
get_cost_data(
    group_by=["CZ:Tag:Environment", "CZ:Service"],
    cost_type="real_cost",
    limit=50
)
```

### Step 6: Calculate Contribution Percentages
For each result:
1. Calculate total spend across all items
2. Calculate each item's percentage of total
3. Calculate cumulative percentage (to identify 80/20 rule)
4. Identify items that together represent 80% of spend

### Step 7: Trend Context (Optional)
Show how top cost drivers are trending:

```
get_cost_data(
    group_by=["CZ:Service"],
    granularity="daily",
    cost_type="real_cost",
    limit=10
)
```

This shows whether top drivers are growing, stable, or declining.

## Output Format

Provide a clear, actionable analysis:

### 1. Executive Summary
- Total spend for period: $X
- Time period analyzed
- Top 3 cost drivers in one sentence
- Key insight or recommendation

### 2. Top Cost Drivers by Primary Dimension

**[Dimension] (Top 10-20)**

| Rank | [Dimension] | Cost | % of Total | Cumulative % |
|------|-------------|------|------------|--------------|
| 1 | [Value 1] | $X,XXX | XX% | XX% |
| 2 | [Value 2] | $X,XXX | XX% | XX% |
| ... | ... | ... | ... | ... |

**Key observations:**
- Top 5 items represent X% of total spend
- [Specific insight about distribution]
- [Notable patterns or outliers]

### 3. Multi-Dimensional Breakdown

**Top Services by [Cloud Provider/Account/Region]**

For each top-level item, show its breakdown:
- Provider/Account A:
  - Service 1: $X,XXX (XX%)
  - Service 2: $X,XXX (XX%)
  - ...

### 4. 80/20 Analysis
- **Concentration:** Top N items represent 80% of spend
- **Long tail:** Remaining M items represent 20% of spend
- **Implication:** Focus optimization on top N items for maximum impact

### 5. Custom Dimension Insights
If organization has custom dimensions (teams, products, features):
- Top costs by team/product
- Services used by each team/product
- Potential allocation or chargeback insights

### 6. Optimization Priorities
Based on top cost drivers, suggest:
1. **Quick wins:** High-cost items with obvious optimization opportunities
2. **Deep dives:** Complex services needing detailed analysis
3. **Monitoring:** Items to watch for growth
4. **Tags:** Untagged high-cost resources to label

### 7. Trend Context (if included)
- Which top drivers are growing vs. stable vs. declining
- Month-over-month or week-over-week changes
- Acceleration or deceleration patterns

## Skill-Specific Best Practices

1. **Calculate percentages** - Raw numbers need context
2. **Show cumulative percentages** - Helps identify concentration
3. **Use multiple dimensions** - Single-dimension analysis is often insufficient
4. **Leverage custom dimensions** - Use org-specific groupings when available
5. **Adjust limits appropriately** - More items for detailed analysis, fewer for summaries
6. **Look for the 80/20 rule** - Usually small number of items drive most cost

For general cost analysis best practices, see `${CLAUDE_PLUGIN_ROOT}/references/best-practices.md`

## Common Analysis Patterns

### Pattern 1: Service-First Analysis
Start with services, then break down by accounts or regions:
```
1. Top services overall
2. For each top service, show breakdown by account
3. For each top service, show breakdown by region
```

### Pattern 2: Organization-First Analysis
Start with business dimensions, then break down to technical:
```
1. Top teams/products (custom dimensions)
2. For each team/product, show top services
3. For each team/product, show top accounts
```

### Pattern 3: Account-First Analysis
Start with accounts, then break down by services:
```
1. Top accounts
2. For each account, show top services
3. For each account, show top regions
```

### Pattern 4: Environment-First Analysis
Start with environment tags, then drill down:
```
1. Costs by environment (prod, staging, dev)
2. For each environment, show top services
3. For each environment, show top accounts
```

## Advanced Techniques

### Filtering to Focus Analysis
Exclude known large costs to surface secondary drivers:

```
get_cost_data(
    group_by=["CZ:Service"],
    filters={"!CZ:Service": ["AmazonEC2"]},
    limit=20
)
```

### Partial Matching for Service Groups
Group related services together:

```
get_cost_data(
    group_by=["CZ:Account"],
    filters={"&CZ:Service": ["EC2"]},
    limit=20
)
```

### Three-Dimensional Analysis
For comprehensive breakdown:

```
get_cost_data(
    group_by=["CZ:CloudProvider", "CZ:Account", "CZ:Service"],
    limit=100
)
```

## Tips for Effective Analysis

1. **Start broad, then narrow:** Begin with single dimension, add more as needed
2. **Focus on actionable insights:** Highlight what users can optimize
3. **Provide context:** Compare to previous periods when possible
4. **Be specific:** Use exact dimension FQDIDs and values
5. **Explain distribution:** Is spend concentrated or distributed?
6. **Suggest next steps:** What should user investigate further?

## See Also

- **understand-cloudzero-organization** skill - Load organization context first
- `${CLAUDE_PLUGIN_ROOT}/references/best-practices.md` - Universal cost analysis best practices
- `${CLAUDE_PLUGIN_ROOT}/references/cloudzero-tools-reference.md` - Complete tool documentation
- `${CLAUDE_PLUGIN_ROOT}/references/error-handling.md` - Troubleshooting and common errors
- `${CLAUDE_PLUGIN_ROOT}/references/dimensions-reference.md` - Dimension types and FQDIDs
- `${CLAUDE_PLUGIN_ROOT}/references/cost-types-reference.md` - When to use each cost type
