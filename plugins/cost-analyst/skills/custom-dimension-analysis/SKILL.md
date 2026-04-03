---
name: custom-dimension-analysis
description: "Use when analyzing costs by organization-specific dimensions like teams, products, business units, or applications for showback, chargeback, or business-aligned cost reporting"
author: CloudZero <support@cloudzero.com>
version: 1.0.0
license: Apache-2.0
---

# Custom Dimension Analysis

## Purpose
This skill analyzes cloud costs through the lens of organization-specific custom dimensions (User:Defined:*) created via CloudZero's CostFormation, enabling business-aligned cost visibility, accurate attribution, and effective showback/chargeback.

## When to Use
- "Show me costs by [team/product/feature]"
- "What do our teams spend on cloud?"
- "Break down costs by business unit"
- "Analyze spending by application"
- "Which product costs the most?"
- Showback and chargeback reporting
- Business-aligned cost discussions
- Product P&L analysis
- Team budget tracking
- Keywords: team, product, feature, business unit, application, custom, showback, chargeback, by [custom dimension name]

## Prerequisites

This skill builds on the **understand-cloudzero-organization** skill.

Before applying this procedure:
- If you haven't already in this session, load the understand-cloudzero-organization skill and follow its instructions
- Reference the cached organization context (don't reload unnecessarily)
- This is especially critical for custom dimension analysis as org context defines what custom dimensions exist and their business meanings

## How This Skill Works

### Step 1: Discover Custom Dimensions
Identify all custom dimensions available:

```
get_available_dimensions(filter="User:Defined")
```

This returns organization-specific dimensions like:
- User:Defined:Team
- User:Defined:Product
- User:Defined:Feature
- User:Defined:Environment
- User:Defined:CostCenter
- User:Defined:BusinessUnit
- User:Defined:Application
- [Others specific to organization]

### Step 2: Identify Relevant Dimension
Based on user request and org context, select the appropriate dimension:

```
# If user asks about "teams"
get_dimension_values(dimension="User:Defined:Team")

# If user asks about "products"
get_dimension_values(dimension="User:Defined:Product")
```

Review values to understand:
- What values exist
- How many distinct values
- Naming conventions used

### Step 3: High-Level Cost Breakdown
Query costs by the primary custom dimension:

```
get_cost_data(
    group_by=["User:Defined:Team"],
    cost_type="real_cost",
    limit=50
)
```

From this:
- Calculate total spend per dimension value
- Calculate percentage of total for each
- Identify top and bottom spenders
- Calculate distribution statistics

### Step 4: Trend Analysis by Custom Dimension
Understand how each dimension value's costs trend over time:

```
get_cost_data(
    group_by=["User:Defined:Team"],
    granularity="daily",
    cost_type="real_cost",
    limit=15
)
```

For each dimension value:
- Calculate growth rate
- Identify trend direction
- Spot anomalies or spikes
- Compare trends across values

### Step 5: Cloud Service Breakdown
For each custom dimension value, understand what services they use:

```
get_cost_data(
    group_by=["User:Defined:Team", "CZ:Service"],
    cost_type="real_cost",
    limit=100
)
```

This reveals:
- Service mix per team/product
- Differences in architecture or technology choices
- Services contributing most to each dimension value's cost
- Optimization opportunities specific to dimension values

### Step 6: Infrastructure Distribution
Understand how dimension values map to infrastructure:

**By Account:**
```
get_cost_data(
    group_by=["User:Defined:Team", "CZ:Account"],
    limit=100
)
```

**By Region:**
```
get_cost_data(
    group_by=["User:Defined:Team", "CZ:Region"],
    limit=100
)
```

**By Environment (if separate from custom dimension):**
```
get_cost_data(
    group_by=["User:Defined:Team", "CZ:Tag:Environment"],
    limit=100
)
```

### Step 7: Multi-Dimensional Custom Analysis
Combine multiple custom dimensions for deeper insights:

```
get_cost_data(
    group_by=["User:Defined:BusinessUnit", "User:Defined:Product", "User:Defined:Team"],
    limit=100
)
```

This shows hierarchical cost relationships:
- Business Unit → Products → Teams
- Or other organizational structures

### Step 8: Unallocated Cost Analysis
Identify costs not assigned to custom dimensions:

```
# Compare total costs to costs with custom dimension
total_cost = get_cost_data()
allocated_cost = get_cost_data(group_by=["User:Defined:Team"])

unallocated = total_cost - sum(allocated_cost)
unallocated_percentage = (unallocated / total_cost) * 100
```

Find what's unallocated:
```
# For accounts, see which have high unallocated costs
get_cost_data(
    group_by=["CZ:Account", "User:Defined:Team"],
    limit=100
)

# For services, see which are commonly unallocated
get_cost_data(
    group_by=["CZ:Service", "User:Defined:Team"],
    limit=100
)
```

### Step 9: Comparative Analysis
Compare dimension values against each other:

**Efficiency Comparison:**
- Which teams/products are most cost-efficient?
- What do efficient teams do differently?
- Can best practices be shared?

**Size Comparison:**
- Relative spending levels
- Budget vs. actual comparisons (if budget data in org context)
- Growth rate comparisons

**Service Mix Comparison:**
- Do similar teams use similar services?
- Why do some teams spend more on specific services?
- Architectural differences between teams/products

## Output Format

Provide comprehensive custom dimension analysis:

### 1. Executive Summary
- Primary custom dimension analyzed: [Dimension name]
- Total costs: $X,XXX
- Number of dimension values: X
- Top spender: [Value] at $X,XXX (XX%)
- Allocation coverage: XX% (XX% unallocated)
- Key insight

### 2. Cost Distribution by Custom Dimension

**[Dimension Name] Cost Breakdown:**

| Rank | [Dimension Value] | Total Cost | % of Total | Daily Avg | Trend |
|------|-------------------|------------|------------|-----------|-------|
| 1 | [Value A] | $X,XXX | XX% | $XXX | +/-X% |
| 2 | [Value B] | $X,XXX | XX% | $XXX | +/-X% |
| 3 | [Value C] | $X,XXX | XX% | $XXX | +/-X% |
| ... | ... | ... | ... | ... | ... |

**Distribution Analysis:**
- Top 3 represent: XX% of total spend
- Most even/uneven distribution: [Analysis]
- Largest: [Value] at $X,XXX
- Smallest: [Value] at $X,XXX
- Concentration: [High/Medium/Low]

### 3. Growth and Trend Analysis

**[Dimension Value] Trends:**

| [Dimension Value] | Current | Previous Period | Change $ | Change % | Trajectory |
|-------------------|---------|-----------------|----------|----------|------------|
| [Value A] | $X,XXX | $X,XXX | +$XXX | +XX% | Growing ↗ |
| [Value B] | $X,XXX | $X,XXX | -$XXX | -XX% | Declining ↘ |
| [Value C] | $X,XXX | $X,XXX | ~$XX | ~X% | Stable → |

**Fastest Growing:** [Value] at +XX%
**Largest Decline:** [Value] at -XX%
**Most Stable:** [Value] with minimal variation

### 4. Service Mix by Dimension Value

For each major dimension value:

**[Dimension Value A] - Total: $X,XXX**

| Service | Cost | % of [Value A] | % of All [Service] |
|---------|------|----------------|---------------------|
| Service 1 | $X,XXX | XX% | XX% |
| Service 2 | $X,XXX | XX% | XX% |
| ... | ... | ... | ... |

**Key Services:**
- Primary service: [Service] at $X,XXX
- Secondary service: [Service] at $X,XXX
- Unique/notable services: [List]

**Architecture Profile:**
- Service mix: [Compute-heavy / Storage-heavy / Database-heavy / Balanced]
- Cloud provider preference: [AWS/GCP/Azure or multi-cloud]
- Specialization: [Any notable patterns]

### 5. Infrastructure Distribution

**By Account:**

| [Dimension Value] | Account A | Account B | Account C | Other |
|-------------------|-----------|-----------|-----------|-------|
| [Value A] | $X,XXX | $X,XXX | $- | $XXX |
| [Value B] | $X,XXX | $- | $X,XXX | $XXX |

**By Region:**

| [Dimension Value] | us-east-1 | us-west-2 | eu-west-1 | Other |
|-------------------|-----------|-----------|-----------|-------|
| [Value A] | $X,XXX | $X,XXX | $- | $XXX |
| [Value B] | $- | $X,XXX | $X,XXX | $XXX |

**Patterns:**
- Multi-region distribution: [Analysis]
- Account isolation strategy: [Analysis]
- Regional preferences: [Analysis]

### 6. Comparative Analysis

**Efficiency Metrics:**

| [Dimension Value] | Total Cost | [Normalized Metric]* | Efficiency Score |
|-------------------|------------|---------------------|------------------|
| [Value A] | $X,XXX | $X per [unit] | High / Medium / Low |
| [Value B] | $X,XXX | $X per [unit] | High / Medium / Low |

*If available: per user, per transaction, per feature, etc.

**Most Efficient:** [Value] achieves [outcome] at [cost]
**Least Efficient:** [Value] spends XX% more for similar outcomes

**Best Practices from Efficient [Dimension Values]:**
1. [Practice 1 observed]
2. [Practice 2 observed]
3. [Service or architecture choice]

### 7. Unallocated Cost Analysis

**Allocation Coverage:**
- Allocated to [dimension]: $X,XXX (XX%)
- **Unallocated: $X,XXX (XX%)**

**Unallocated Cost Breakdown:**

| Service | Unallocated Cost | % of Unallocated |
|---------|------------------|------------------|
| Service A | $X,XXX | XX% |
| Service B | $X,XXX | XX% |

**By Account:**
- Account A: $X,XXX unallocated
- Account B: $X,XXX unallocated

**Root Causes of Unallocated Costs:**
1. [Shared infrastructure not attributed]
2. [Resources without proper tags/rules]
3. [Service-level costs hard to allocate]

**Impact:**
- Affects showback/chargeback accuracy
- [X teams/products] have incomplete cost picture
- Recommendations for improvement: [List]

### 8. Hierarchical Analysis (if multiple custom dimensions)

If analyzing multiple levels (e.g., Business Unit → Product → Team):

**Business Unit: [BU A]**
- Total: $X,XXX (XX% of org)
- Products:
  - Product 1: $X,XXX
    - Teams:
      - Team A: $X,XXX
      - Team B: $X,XXX
  - Product 2: $X,XXX
    - Teams:
      - Team C: $X,XXX

**Insights:**
- Largest business unit: [BU] at $X,XXX
- Most expensive product: [Product] at $X,XXX
- Most expensive team: [Team] at $X,XXX
- Cost concentration at [level]

### 9. Showback/Chargeback Report

**[Dimension Value] Cost Report**

For each dimension value, provide a detailed breakdown suitable for showback:

**Team/Product: [Value A]**
**Period: [Date Range]**
**Total Cost: $X,XXX**

**Service Breakdown:**
- Compute (EC2, Lambda, etc.): $X,XXX
- Storage (S3, EBS, etc.): $X,XXX
- Database (RDS, DynamoDB, etc.): $X,XXX
- Networking: $X,XXX
- Other: $X,XXX

**By Environment:**
- Production: $X,XXX (XX%)
- Staging: $X,XXX (XX%)
- Development: $X,XXX (XX%)

**Top 5 Resources:**
1. [Resource]: $XXX
2. [Resource]: $XXX
3. [Resource]: $XXX

**Compared to Last Period:**
- Change: +/- $XXX (+/- XX%)
- Primary driver: [Explanation]

### 10. Actionable Recommendations

**For High-Spending [Dimension Values]:**
1. **[Value A] ($X,XXX/month):**
   - Primary opportunity: [Specific recommendation]
   - Potential savings: $X,XXX
   - Service to optimize: [Service]
   - Action: [Specific steps]

2. **[Value B] ($X,XXX/month):**
   - [Recommendations]

**For Growing [Dimension Values]:**
1. **[Value C] (+XX% growth):**
   - Validate growth is expected given business activity
   - Monitor: [Specific metrics]
   - Consider: [Reserved Instances, architecture changes, etc.]

**For Unallocated Costs:**
1. Create CostFormation rules for [specific resources]
2. Improve tagging for [accounts/services]
3. Define allocation for shared services

**For Showback/Chargeback:**
1. Distribute reports to [dimension value] owners
2. Set up monthly review cadence
3. Establish cost accountability
4. Consider budget alerts per [dimension value]

**Knowledge Sharing:**
1. Share best practices from efficient [dimension values]
2. Document standard architectures
3. Cross-team optimization workshops

### 11. Custom Dimension Quality

**Dimension Definition Quality:**
- Coverage: XX% of costs allocated
- Accuracy: [Assessment based on org context]
- Granularity: [Appropriate / Too broad / Too granular]
- Maintainability: [Easy / Complex]

**Improvement Opportunities:**
1. [Refine allocation rules for X]
2. [Add missing dimension values]
3. [Improve coverage for Y]

## Skill-Specific Best Practices

1. **Understand business context** - Custom dimensions have business meaning
2. **Calculate allocation coverage** - Know what % of costs are attributed
3. **Compare dimension values** - Look for efficiency patterns
4. **Provide showback-ready output** - Format suitable for finance/business teams
5. **Explain service mix** - Help business users understand technical costs
6. **Normalize when possible** - Per-user, per-transaction costs
7. **Track trends** - Growth/decline patterns matter for planning

For general cost analysis best practices, see `${CLAUDE_PLUGIN_ROOT}/references/best-practices.md`

## Common Custom Dimension Patterns

### Pattern 1: Team-Based Analysis
**Goal:** Understand which teams spend how much

**Approach:**
- Rank teams by spending
- Analyze service mix per team
- Compare efficiency across teams
- Identify growing vs. stable teams
- Share optimization wins

### Pattern 2: Product P&L
**Goal:** Attribute cloud costs to products for P&L

**Approach:**
- Full cost breakdown per product
- Include allocated shared costs
- Trend over time with revenue if available
- Calculate unit economics (cost per user, per transaction)
- Identify optimization opportunities

### Pattern 3: Environment Cost Management
**Goal:** Ensure non-prod environments are appropriately sized

**Approach:**
- Compare prod vs. staging vs. dev costs
- Calculate ratios (staging should be X% of prod)
- Identify oversized non-prod resources
- Recommend rightsizing

### Pattern 4: Business Unit Showback
**Goal:** Provide cost transparency to business units

**Approach:**
- Hierarchical breakdown (BU → Product → Team)
- Service breakdown in business terms
- Period-over-period comparison
- Budget vs. actual (if available)
- Recommendations tailored to business audience

### Pattern 5: Feature Cost Tracking
**Goal:** Understand cost of specific features

**Approach:**
- Identify infrastructure per feature
- Calculate feature costs
- Compare to feature usage/revenue
- Inform product prioritization
- Calculate ROI per feature

## Advanced Techniques

### Multi-Dimensional Custom Analysis
Combine multiple custom dimensions:
```
get_cost_data(
    group_by=["User:Defined:BusinessUnit", "User:Defined:Product"],
    limit=100
)
```

Creates matrix showing how products roll up to business units.

### Shared Cost Allocation
When costs are shared (e.g., shared data platform):

1. Identify shared costs
2. Define allocation methodology (by usage, by headcount, by revenue)
3. Apply allocation
4. Show allocated + direct costs per dimension

### Variance Analysis
Compare actual to expected/budgeted:
```
Variance = Actual Cost - Expected Cost
Variance % = (Variance / Expected Cost) * 100
```

Highlight dimension values over/under budget.

### Cost Optimization Scoring
For each dimension value:
```
Optimization Score = (
  (Tag Coverage % × 0.3) +
  (RI/SP Coverage % × 0.3) +
  (Rightsizing Adoption % × 0.2) +
  (Growth Control % × 0.2)
)
```

Rank dimension values by optimization maturity.

## Tips for Effective Analysis

1. **Speak business language** - Translate technical costs to business terms
2. **Make it actionable** - Every insight should suggest an action
3. **Context is everything** - Use org context to interpret results
4. **Benchmark internally** - Compare dimension values to each other
5. **Show allocation gaps** - Be transparent about unallocated costs
6. **Tell a story** - Don't just list numbers, explain what they mean
7. **Enable accountability** - Clear attribution enables cost ownership
8. **Link to outcomes** - Connect costs to business metrics when possible

## See Also

- **understand-cloudzero-organization** skill - Load organization context first
- `${CLAUDE_PLUGIN_ROOT}/references/best-practices.md` - Universal cost analysis best practices
- `${CLAUDE_PLUGIN_ROOT}/references/cloudzero-tools-reference.md` - Complete tool documentation
- `${CLAUDE_PLUGIN_ROOT}/references/error-handling.md` - Troubleshooting and common errors
- `${CLAUDE_PLUGIN_ROOT}/references/dimensions-reference.md` - Dimension types and FQDIDs
- `${CLAUDE_PLUGIN_ROOT}/references/cost-types-reference.md` - When to use each cost type
