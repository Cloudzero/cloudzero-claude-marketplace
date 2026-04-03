---
name: service-cost-deep-dive
description: Performs detailed analysis of specific cloud service costs, breaking down by usage types, resources, regions, accounts, and identifying service-specific optimization opportunities like rightsizing, Reserved Instances, or configuration changes
author: CloudZero <support@cloudzero.com>
version: 1.0.0
license: Apache-2.0
---

# Service Cost Deep Dive

## Purpose
This skill provides comprehensive, detailed analysis of a specific cloud service's costs, breaking it down by all relevant dimensions and identifying service-specific optimization opportunities.

## When to Use
- "Analyze my [service name] costs"
- "Deep dive into EC2 spending"
- "Break down RDS costs"
- "Why is [service] so expensive?"
- "Optimize my Lambda costs"
- Service-specific cost reviews
- Targeted optimization efforts
- Understanding service usage patterns
- Keywords: deep dive, analyze, breakdown, detailed, specific service, EC2, RDS, S3, Lambda, etc.

## Prerequisites

This skill builds on the **understand-cloudzero-organization** skill.

Before applying this procedure:
- If you haven't already in this session, load the understand-cloudzero-organization skill and follow its instructions
- Reference the cached organization context (don't reload unnecessarily)

## How This Skill Works

### Step 1: Identify the Service
Determine which service to analyze:

```
# If user mentions service name, find exact FQDID
get_available_dimensions(filter="Service")

# Get all dimension values to find exact match
get_dimension_values(dimension="CZ:Service", match="[user's service name]")
```

### Step 2: Overall Service Cost Analysis
Get high-level view of the service:

**Total Service Cost:**
```
get_cost_data(
    filters={"CZ:Service": ["[service_name]"]},
    cost_type="real_cost"
)
```

**Service Cost Trend:**
```
get_cost_data(
    filters={"CZ:Service": ["[service_name]"]},
    granularity="daily",
    cost_type="real_cost"
)
```

Calculate:
- Total cost for period
- Average daily cost
- Trend direction (growing/declining/stable)
- Percentage of total cloud spend

### Step 3: Multi-Dimensional Breakdown
Break down service costs by all relevant dimensions:

**By Account:**
```
get_cost_data(
    filters={"CZ:Service": ["[service_name]"]},
    group_by=["CZ:Account"],
    limit=20
)
```

**By Region:**
```
get_cost_data(
    filters={"CZ:Service": ["[service_name]"]},
    group_by=["CZ:Region"],
    limit=20
)
```

**By Account and Region:**
```
get_cost_data(
    filters={"CZ:Service": ["[service_name]"]},
    group_by=["CZ:Account", "CZ:Region"],
    limit=50
)
```

**By Usage Type (if available):**
```
# Discover if usage type dimension exists
get_available_dimensions(filter="UsageType")

# If available, group by it
get_cost_data(
    filters={"CZ:Service": ["[service_name]"]},
    group_by=["CZ:UsageType"],
    limit=50
)
```

**By Resource (if available):**
```
# Discover if resource dimension exists
get_available_dimensions(filter="Resource")

# If available, get top resources
get_cost_data(
    filters={"CZ:Service": ["[service_name]"]},
    group_by=["CZ:Resource"],
    limit=50
)
```

### Step 4: Tag-Based Analysis
Understand how service is used across environments and teams:

**By Environment:**
```
get_cost_data(
    filters={"CZ:Service": ["[service_name]"]},
    group_by=["CZ:Tag:Environment"],
    limit=10
)
```

**By Team (if tagged):**
```
get_cost_data(
    filters={"CZ:Service": ["[service_name]"]},
    group_by=["CZ:Tag:Team"],
    limit=20
)
```

**By Application (if tagged):**
```
get_cost_data(
    filters={"CZ:Service": ["[service_name]"]},
    group_by=["CZ:Tag:Application"],
    limit=20
)
```

### Step 5: Custom Dimension Attribution
Use organization-specific dimensions:

```
# Discover custom dimensions
get_available_dimensions(filter="User:Defined")

# Analyze by custom dimensions
get_cost_data(
    filters={"CZ:Service": ["[service_name]"]},
    group_by=["User:Defined:Team"],
    limit=20
)
```

### Step 6: Untagged Resource Analysis
Identify resources without proper tagging:

```
# Look for costs that don't have environment tags
get_cost_data(
    filters={
        "CZ:Service": ["[service_name]"],
        "CZ:Tag:Environment": [""]  # Empty/untagged
    },
    group_by=["CZ:Account", "CZ:Region"],
    limit=50
)
```

### Step 7: Time-Based Pattern Analysis
Understand usage patterns:

**Hourly patterns (if looking at short period):**
```
get_cost_data(
    filters={"CZ:Service": ["[service_name]"]},
    granularity="hourly",
    date_range="last 7 days"
)
```

**Daily patterns:**
```
get_cost_data(
    filters={"CZ:Service": ["[service_name]"]},
    granularity="daily",
    date_range="last 90 days"
)
```

Identify:
- Weekday vs. weekend patterns
- Peak usage times
- Idle periods
- Unusual spikes

### Step 8: Check Related Tickets and Documentation
Search for existing context about this service:

**Jira — existing optimization or issue tickets:**
```
searchJiraIssuesUsingJql(
    jql="text ~ '[service name]' AND (text ~ 'cost' OR text ~ 'optimization' OR text ~ 'rightsizing')",
    limit=10
)
```

**DevRev — related tickets:**
```
hybrid_search(
    query="[service name] cost optimization",
    namespace="ticket"
)
```

**Confluence — architecture and optimization docs:**
```
searchConfluenceUsingCql(
    cql="text ~ '[service name]' AND type = 'page'",
    limit=5
)
```

Note:
- Any in-progress optimization efforts (avoid duplicating work)
- Architecture decisions explaining current service usage
- Historical optimization results for this service
- Known constraints or business reasons for current configuration

### Step 9: Service-Specific Optimization Analysis

**For Compute Services (EC2, ECS, EKS, Lambda):**
- Instance type distribution
- Utilization patterns
- Rightsizing opportunities
- Spot instance eligibility
- Reserved Instance/Savings Plan coverage
- Idle/underutilized instances

**For Storage Services (S3, EBS, EFS):**
- Storage class distribution
- Growth rate
- Old/unused data
- Lifecycle policy opportunities
- Snapshot costs

**For Database Services (RDS, DynamoDB, Redshift):**
- Instance sizes and types
- Multi-AZ costs
- Backup costs
- Read replica costs
- Reserved Instance opportunities

**For Data Transfer:**
- Egress costs by destination
- Inter-region transfer
- Optimization through caching/CDN

**For Serverless (Lambda, API Gateway):**
- Request volume vs. cost
- Memory allocation efficiency
- Cold start impact
- Duration optimization opportunities

### Step 10: Cost Type Comparison
Compare different cost perspectives:

```
# Real cost (default)
get_cost_data(
    filters={"CZ:Service": ["[service_name]"]},
    cost_type="real_cost"
)

# On-demand cost (to calculate savings)
get_cost_data(
    filters={"CZ:Service": ["[service_name]"]},
    cost_type="on_demand_cost"
)
```

Calculate effective savings rate:
```
Savings Rate = ((On-Demand Cost - Real Cost) / On-Demand Cost) * 100
```

## Output Format

Provide comprehensive service analysis:

### 1. Executive Summary
- Service name
- Total cost for period: $X
- Percentage of total cloud spend: X%
- Trend: [Growing/Stable/Declining] at X% rate
- Top optimization opportunity
- Estimated savings potential: $X

### 2. Service Cost Overview

**Total Cost:** $X,XXX
**Time Period:** [dates]
**Daily Average:** $XXX
**Trend:** [Growing/Stable/Declining]
**Growth Rate:** X% [MoM/WoW]

**Cost Distribution:**
- Percentage of total cloud spend: XX%
- Rank among all services: #X

### 3. Geographic Distribution

**By Region:**

| Region | Cost | % of Service | Key Resources |
|--------|------|--------------|---------------|
| us-east-1 | $X,XXX | XX% | [Details] |
| us-west-2 | $X,XXX | XX% | [Details] |
| ... | ... | ... | ... |

**Insights:**
- Most expensive region: [Region] at $X
- Multi-region distribution: [Analysis]
- Regional efficiency differences: [Details]

### 4. Account Distribution

**By Account:**

| Account | Cost | % of Service | Trend |
|---------|------|--------------|-------|
| Account A | $X,XXX | XX% | +X% |
| Account B | $X,XXX | XX% | -X% |
| ... | ... | ... | ... |

**Insights:**
- Highest spending account: [Account]
- Fastest growing account: [Account] at +X%
- Accounts to investigate: [List with reasons]

### 5. Usage Breakdown

**By Usage Type / Resource Type:**

| Type | Cost | % of Service | Notes |
|------|------|--------------|-------|
| Type A | $X,XXX | XX% | [Details] |
| Type B | $X,XXX | XX% | [Details] |
| ... | ... | ... | ... |

**Insights:**
- Most expensive usage type: [Type]
- Unusual or unexpected usage: [Details]

### 6. Tagging and Attribution

**By Environment:**
- Production: $X,XXX (XX%)
- Staging: $X,XXX (XX%)
- Development: $X,XXX (XX%)
- Untagged: $X,XXX (XX%) ⚠️

**By Team/Application:**
- [Team/App A]: $X,XXX
- [Team/App B]: $X,XXX
- Untagged: $X,XXX ⚠️

**Tagging Issues:**
- XX% of costs are untagged
- [Specific accounts/regions with tagging gaps]

### 7. Usage Patterns

**Time-Based Patterns:**
- Peak usage time: [Time] with $X/hour
- Off-peak usage: [Time] with $X/hour
- Weekend vs. weekday: [Comparison]
- Opportunities for scheduling: [Details]

**Trend Analysis:**
- 7-day trend: [Pattern description]
- 30-day trend: [Pattern description]
- Notable events: [Spikes or dips with dates]

### 8. Service-Specific Optimization Opportunities

**[Customize based on service type]**

**For Compute (EC2 example):**
1. **Rightsizing:** [X instances appear oversized] - Potential savings: $X/month
2. **Reserved Instances:** [Coverage is X%, opportunity for Y% more] - Potential savings: $X/month
3. **Spot Instances:** [Workloads eligible for spot] - Potential savings: $X/month
4. **Idle Resources:** [X instances with <10% utilization] - Potential savings: $X/month
5. **Instance Generation:** [Old generation instances] - Upgrade for better price/performance

**For Storage (S3 example):**
1. **Storage Classes:** [X TB eligible for Glacier/IA] - Potential savings: $X/month
2. **Lifecycle Policies:** [Objects not using lifecycle rules] - Potential savings: $X/month
3. **Versioning:** [Old versions consuming storage] - Potential savings: $X/month
4. **Incomplete Multipart Uploads:** [Cleanup needed] - Potential savings: $X/month

**For Databases (RDS example):**
1. **Instance Sizing:** [Over-provisioned instances] - Potential savings: $X/month
2. **Reserved Instances:** [On-demand instances eligible] - Potential savings: $X/month
3. **Multi-AZ:** [Non-prod shouldn't use Multi-AZ] - Potential savings: $X/month
4. **Backup Retention:** [Excessive retention] - Potential savings: $X/month
5. **Read Replicas:** [Underutilized replicas] - Potential savings: $X/month

### 9. Savings Analysis

**Current Savings (if using RIs/SPs):**
- On-Demand Cost: $X,XXX
- Real Cost: $Y,YYY
- Current Savings: $Z,ZZZ (XX%)

**Additional Savings Potential:**
1. [Opportunity 1]: $X,XXX/month
2. [Opportunity 2]: $Y,YYY/month
3. [Opportunity 3]: $Z,ZZZ/month

**Total Potential Savings:** $[Sum]/month (XX% reduction)

### 10. Related Tickets & Documentation
- **Existing tickets:** [Any Jira/DevRev tickets related to this service's costs]
- **In-progress optimizations:** [Any active optimization efforts already underway]
- **Architecture docs:** [Relevant Confluence pages explaining service usage]
- **Historical context:** [Past optimization results or decisions]

### 11. Detailed Recommendations

**Immediate Actions (Quick Wins):**
1. [Action with high impact, low effort]
2. [Action with high impact, low effort]
3. [Action with high impact, low effort]

**Short-Term Actions (1-2 weeks):**
1. [Action requiring some planning]
2. [Action requiring some planning]

**Long-Term Actions (1-3 months):**
1. [Action requiring significant effort or time]
2. [Architectural changes]

**Monitoring and Governance:**
1. [Set up alerts for specific thresholds]
2. [Implement tagging policies]
3. [Regular review cadence]

**Create Optimization Ticket (if warranted):**
If significant savings opportunities are identified and not already tracked:

**Jira:**
```
createJiraIssue(
    projectKey="<project>",
    summary="[Service] optimization: potential $X/mo savings",
    description="<deep dive findings and specific recommendations>",
    issueType="Task"
)
```

**DevRev:**
```
create_ticket(
    title="[Service] optimization: potential $X/mo savings",
    description="<deep dive findings and specific recommendations>"
)
```

### 12. Comparison to Best Practices

**Industry Benchmarks:**
- Typical [service] costs for similar workloads: [Range]
- Your position: [Above/Below/Within] range
- Efficiency score: [Assessment]

**Optimization Maturity:**
- Tagging coverage: [Score]
- RI/SP coverage: [Score]
- Rightsizing implementation: [Score]
- Overall maturity: [Score]

## Skill-Specific Best Practices

1. **Use all available dimensions** - Don't stop at basic account/region
2. **Leverage service-specific knowledge** - Different services need different analysis
3. **Calculate savings potential** - Quantify all recommendations
4. **Prioritize by impact** - Focus on highest-value optimizations
5. **Consider business context** - Some "inefficiencies" may be intentional
6. **Compare cost types** - Use on_demand_cost to calculate savings
7. **Look for untagged resources** - Often indicates governance gaps

For general cost analysis best practices, see `${CLAUDE_PLUGIN_ROOT}/references/best-practices.md`

## Service-Specific Analysis Guides

### Compute Services (EC2, ECS, Lambda)
**Key Dimensions:**
- Instance type, size, family
- Purchase option (On-Demand, RI, Spot)
- Utilization metrics (if available)
- Operating system

**Key Questions:**
- Are instances rightsized?
- Is RI/SP coverage optimal?
- Are spot instances being used where appropriate?
- Are there idle instances?
- Is auto-scaling configured?

### Storage Services (S3, EBS, Glacier)
**Key Dimensions:**
- Storage class
- Request type (PUT, GET, etc.)
- Data transfer
- Region

**Key Questions:**
- Are appropriate storage classes being used?
- Are lifecycle policies implemented?
- Are old snapshots being cleaned up?
- Is versioning causing unnecessary costs?
- Are there forgotten buckets/volumes?

### Database Services (RDS, DynamoDB, Redshift)
**Key Dimensions:**
- Engine type
- Instance class
- Multi-AZ vs. Single-AZ
- Backup storage
- Read replicas

**Key Questions:**
- Are instances rightsized?
- Is RI coverage appropriate?
- Are non-prod databases too large?
- Is backup retention optimized?
- Are read replicas necessary?

### Networking (Data Transfer, VPC, NAT Gateway)
**Key Dimensions:**
- Transfer type (internet, inter-region, intra-region)
- Source and destination
- NAT Gateway data processing

**Key Questions:**
- Can traffic be routed more efficiently?
- Is CDN/CloudFront being used effectively?
- Are unnecessary cross-region transfers occurring?
- Are NAT Gateways necessary or can VPC endpoints help?

## Advanced Techniques

### Anomaly Detection Within Service
Compare service costs to its own historical patterns:
- Identify days with unusual spending
- Detect gradual drift over time
- Flag new resource types or usage patterns

### Efficiency Scoring
Create composite score based on:
- Tagging coverage (%)
- RI/SP coverage (%)
- Rightsizing adoption (%)
- Storage class optimization (%)

### What-If Scenarios
Model potential optimizations:
- "If we rightsize all oversized instances..."
- "If we increase RI coverage to 80%..."
- "If we migrate to newer instance generation..."

### Peer Comparison
Compare service usage across:
- Different accounts (why does Account A spend more?)
- Different regions (why is us-east-1 more expensive?)
- Different teams (what do efficient teams do differently?)

## Tips for Effective Analysis

1. **Be service-specific:** EC2 analysis differs from S3 analysis
2. **Quantify everything:** Every recommendation should have dollar impact
3. **Consider dependencies:** Some costs enable savings elsewhere
4. **Think holistically:** Optimization in one area may increase costs in another
5. **Provide implementation guidance:** Don't just identify issues, suggest how to fix them
6. **Follow up:** Recommend ongoing monitoring after optimization

## See Also

- **understand-cloudzero-organization** skill - Load organization context first
- `${CLAUDE_PLUGIN_ROOT}/references/best-practices.md` - Universal cost analysis best practices
- `${CLAUDE_PLUGIN_ROOT}/references/cloudzero-tools-reference.md` - Complete tool documentation
- `${CLAUDE_PLUGIN_ROOT}/references/error-handling.md` - Troubleshooting and common errors
- `${CLAUDE_PLUGIN_ROOT}/references/dimensions-reference.md` - Dimension types and FQDIDs
- `${CLAUDE_PLUGIN_ROOT}/references/cost-types-reference.md` - When to use each cost type
