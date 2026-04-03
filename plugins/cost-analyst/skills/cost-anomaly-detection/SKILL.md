---
name: cost-anomaly-detection
description: Proactively scans for cost anomalies, unusual spending patterns, unexpected changes, or irregularities that may indicate waste, misconfiguration, security issues, or optimization opportunities across all dimensions
author: CloudZero <support@cloudzero.com>
version: 1.0.0
license: Apache-2.0
---

# Cost Anomaly Detection

## Purpose
This skill proactively identifies unusual cost patterns, unexpected spikes, irregular spending behaviors, and anomalies that may indicate problems, inefficiencies, or opportunities for optimization.

## When to Use
- "Are there any cost anomalies?"
- "Check for unusual spending"
- "Find cost issues"
- "What looks wrong with my costs?"
- "Detect abnormal costs"
- Proactive cost monitoring
- Weekly/monthly cost reviews
- Security incident detection
- Waste identification
- Before presenting cost reports
- Keywords: anomaly, unusual, abnormal, irregular, unexpected, odd, suspicious, detect issues

## Prerequisites

This skill builds on the **understand-cloudzero-organization** skill.

Before applying this procedure:
- If you haven't already in this session, load the understand-cloudzero-organization skill and follow its instructions
- Reference the cached organization context (don't reload unnecessarily)
- Organization context is critical for distinguishing legitimate changes from true anomalies

## How This Skill Works

### Step 1: Establish Baseline
Query historical data to establish normal patterns:

```
# Recent period
get_cost_data(
    granularity="daily",
    date_range="last 30 days",
    cost_type="real_cost"
)

# Compare to baseline period
get_cost_data(
    granularity="daily",
    date_range="30 to 60 days ago",
    cost_type="real_cost"
)
```

Calculate baseline statistics:
- Mean daily cost
- Standard deviation
- Normal range (e.g., mean ± 2 standard deviations)
- Typical day-of-week patterns
- Expected growth rate

### Step 2: Total Cost Anomaly Detection
Identify days with unusual total spending:

**Detect Outliers:**
```
For each day in recent period:
  If cost > (baseline_mean + 2 × baseline_stddev):
    Flag as high anomaly
  If cost < (baseline_mean - 2 × baseline_stddev):
    Flag as low anomaly (potential data issue or optimization)
```

**Look for:**
- Single-day spikes (unusual one-time events)
- Sustained increases (new baseline)
- Gradual drift away from normal
- Weekend vs. weekday anomalies
- Unexpected patterns

### Step 3: Service-Level Anomaly Detection
Check each service for unusual behavior:

```
# Get services with daily breakdown
get_cost_data(
    group_by=["CZ:Service"],
    granularity="daily",
    limit=20
)

# Compare recent pattern to baseline for each service
```

For each major service:
- Calculate its typical daily cost
- Identify days with unusual spending
- Detect new services that appeared
- Detect services that disappeared
- Calculate variance from expected

**Anomaly Types:**
1. **Spike:** Sudden increase then return to normal
2. **Step Change:** Sudden increase that persists
3. **Gradual Drift:** Slow increase over time
4. **Drop:** Unexpected decrease
5. **New Appearance:** Service that didn't exist before
6. **Disappearance:** Service that stopped

### Step 4: Account-Level Anomaly Detection
Identify accounts with unusual spending:

```
get_cost_data(
    group_by=["CZ:Account"],
    granularity="daily",
    limit=20
)
```

For each account:
- Compare to its historical pattern
- Flag accounts with >50% increase from baseline
- Identify new accounts with unexpected high costs
- Detect accounts with no activity (potential issue)

### Step 5: Resource-Level Anomaly Detection
Identify specific resources with unusual costs:

```
# Get top resources
get_cost_data(
    group_by=["CZ:Resource"],
    limit=50
)

# Compare to previous period
get_cost_data(
    group_by=["CZ:Resource"],
    date_range="previous period",
    limit=50
)
```

Look for:
- New high-cost resources
- Resources with sudden cost increases
- Resources that appeared recently
- Expensive resources without proper tags

### Step 6: Regional Anomaly Detection
Check for unusual regional spending patterns:

```
get_cost_data(
    group_by=["CZ:Region"],
    granularity="daily",
    limit=20
)
```

Anomalies might indicate:
- Unauthorized resource creation in unexpected regions
- Data transfer anomalies
- Failover events
- Misconfigured deployments

### Step 7: Usage Pattern Anomalies
Detect unusual usage patterns:

**Hourly Pattern Analysis (if examining recent days):**
```
get_cost_data(
    granularity="hourly",
    date_range="last 7 days"
)
```

Look for:
- 24/7 costs when should be business hours only
- Weekend activity when shouldn't exist
- Off-hours spikes (potential security issue)
- Missing expected peaks (potential outage)

**Day-of-Week Patterns:**
- Calculate average cost per day of week
- Compare recent weeks to baseline weeks
- Flag unusual weekday/weekend ratios

### Step 8: Multi-Dimensional Anomaly Detection
Cross-reference anomalies across dimensions:

```
get_cost_data(
    group_by=["CZ:Account", "CZ:Service", "CZ:Region"],
    limit=100
)
```

Find:
- Specific service in specific account with anomaly
- Regional anomalies for specific services
- Account+Service combinations that are unusual

### Step 9: Rate-of-Change Anomalies
Detect unusual growth rates:

```
Calculate for each dimension value:
  recent_rate = (cost_this_week - cost_last_week) / cost_last_week
  typical_rate = historical average growth rate

  If recent_rate > (typical_rate + threshold):
    Flag as accelerating growth anomaly
```

### Step 10: Security and Waste Indicators
Look for specific patterns indicating issues:

**Potential Security Issues:**
- New EC2 instances in unusual regions
- Sudden spike in compute or network costs
- Resources created in accounts with no recent activity
- Large data transfer spikes
- Cryptocurrency mining patterns (sustained high compute)

**Potential Waste:**
- EBS volumes without attached instances
- Old snapshots accumulating
- Unused Reserved Instances
- Idle RDS databases (consistent low cost)
- Over-provisioned resources

**Potential Misconfigurations:**
- Public S3 buckets with high request costs
- NAT Gateway traffic spikes
- Logging to expensive destinations
- Unoptimized data transfer routes

### Step 11: Cross-Reference with Tickets and Documentation
Before finalizing the anomaly report, check for existing context:

**Search for related tickets (Jira):**
```
searchJiraIssuesUsingJql(
    jql="text ~ 'cost' AND (text ~ 'anomaly' OR text ~ 'spike' OR text ~ '[affected service]') AND status != Done",
    limit=10
)
```

**Search for related tickets (DevRev):**
```
hybrid_search(
    query="cost anomaly [affected service or account]",
    namespace="ticket"
)
```

**Search for runbooks (Confluence):**
```
searchConfluenceUsingCql(
    cql="text ~ 'cost' AND (text ~ 'anomaly' OR text ~ 'runbook') AND type = 'page'",
    limit=5
)
```

For each anomaly found:
- Check if it's already tracked in an existing ticket
- Check if there's a runbook with remediation steps
- Note any related historical incidents

### Step 12: Tag-Based Anomaly Detection
Check for anomalies in tagged resources:

```
get_cost_data(
    group_by=["CZ:Tag:Environment", "CZ:Service"],
    granularity="daily",
    limit=50
)
```

Anomalies might be:
- Non-prod environments at prod scale
- Test environments with sustained high costs
- Development resources left running 24/7

## Output Format

Provide comprehensive anomaly report:

### 1. Executive Summary
- **Anomaly Count:** X anomalies detected
- **Severity:** [High: X, Medium: Y, Low: Z]
- **Potential Cost Impact:** $X,XXX/month if unaddressed
- **Most Critical:** [Brief description of #1 issue]
- **Action Required:** [Yes/No and urgency]

### 2. Anomaly Severity Classification

**HIGH SEVERITY (Immediate Action Required):**
1. [Anomaly description]
   - Detected: [Date/time]
   - Impact: $X,XXX
   - Potential cause: [Analysis]
   - Recommended action: [Specific steps]

**MEDIUM SEVERITY (Review Within 24-48 Hours):**
1. [Anomaly description]
   - [Details]

**LOW SEVERITY (Monitor or Investigate When Convenient):**
1. [Anomaly description]
   - [Details]

### 3. Detailed Anomaly Analysis

For each significant anomaly:

#### Anomaly #1: [Descriptive Title]
**Type:** [Spike / Step Change / Drift / New Resource / etc.]
**Severity:** [High / Medium / Low]
**Detected:** [Date/time first observed]
**Impact:** $X,XXX (XX% above normal)

**Details:**
- **What:** [Specific description of the anomaly]
- **Where:** [Account / Service / Region / Resource]
- **When:** [Time period]
- **Baseline:** Normal cost is $X, observed cost is $Y
- **Deviation:** XX% above/below normal (Z standard deviations)

**Pattern Analysis:**
- First observed: [Date]
- Duration: [Ongoing / X days]
- Trend: [Growing / Stable / Declining]
- Time pattern: [Constant / Hourly / Daily pattern]

**Potential Causes:**
1. [Most likely cause with reasoning]
2. [Alternative explanation]
3. [Other possibilities]

**Related Anomalies:**
- [Other anomalies that might be connected]

**Recommendations:**
1. **Immediate:** [Action to take now]
2. **Investigation:** [What to check]
3. **Remediation:** [How to fix]
4. **Prevention:** [How to avoid future occurrences]

**Estimated Impact If Not Addressed:**
- Daily: $XXX
- Monthly: $X,XXX
- Annual: $XX,XXX

### 4. Anomaly Dashboard

**Cost Anomalies by Category:**

| Category | Count | Total Impact | Avg Impact |
|----------|-------|--------------|------------|
| Compute Spikes | X | $X,XXX | $XXX |
| Storage Growth | X | $X,XXX | $XXX |
| Data Transfer | X | $X,XXX | $XXX |
| New Resources | X | $X,XXX | $XXX |
| Security Concerns | X | $X,XXX | $XXX |
| Waste/Idle | X | $X,XXX | $XXX |

**Anomalies by Dimension:**

| Dimension | Anomaly Count | Most Affected Value | Impact |
|-----------|---------------|---------------------|--------|
| Service | X | [Service name] | $X,XXX |
| Account | X | [Account ID] | $X,XXX |
| Region | X | [Region] | $X,XXX |

### 5. Time-Series Anomaly Visualization

**Cost Over Time with Anomalies Highlighted:**

```
[Describe the pattern, indicating where anomalies occurred]

Days with anomalies:
- [Date]: $X,XXX (XX% above baseline) - [Service/Account]
- [Date]: $X,XXX (XX% above baseline) - [Service/Account]
- [Date]: $X,XXX (XX% above baseline) - [Service/Account]

Baseline range: $X,XXX - $X,XXX
Normal mean: $X,XXX
Current level: $X,XXX (within/outside normal range)
```

### 6. New or Changed Resources

**New High-Cost Resources Detected:**

| Resource | Service | Account | First Seen | Current Cost | Status |
|----------|---------|---------|------------|--------------|--------|
| [Resource ID] | EC2 | [Account] | [Date] | $X,XXX/mo | ⚠️ Review |
| [Resource ID] | RDS | [Account] | [Date] | $X,XXX/mo | ⚠️ Review |

**Recently Changed Resources:**

| Resource | Service | Change Type | Date | Impact |
|----------|---------|-------------|------|--------|
| [Resource ID] | EC2 | Size increase | [Date] | +$XXX/mo |
| [Resource ID] | RDS | Multi-AZ enabled | [Date] | +$XXX/mo |

### 7. Security and Compliance Concerns

**Potential Security Issues:**
1. **[Issue description]**
   - Indicators: [What suggests this is a security issue]
   - Affected resources: [Details]
   - Recommended action: [Contact security team, isolate resource, etc.]

**Potential Compliance Issues:**
1. **[Issue description]**
   - Compliance requirement: [Which policy/standard]
   - Violation: [What's non-compliant]
   - Remediation: [Steps to fix]

### 8. Waste and Optimization Opportunities

**Identified Waste:**
1. **[Type of waste]** - $X,XXX/month
   - Description: [Details]
   - How to fix: [Steps]
   - Savings potential: $X,XXX/month

**Optimization Opportunities:**
1. **[Opportunity]** - Potential savings: $X,XXX/month
   - Current state: [Details]
   - Recommended change: [Action]
   - Implementation effort: [Low/Medium/High]

### 9. Baseline Comparison

**Current vs. Baseline:**

| Metric | Baseline | Current | Variance | Status |
|--------|----------|---------|----------|--------|
| Daily Cost | $X,XXX | $X,XXX | +XX% | ⚠️ |
| Weekday Avg | $X,XXX | $X,XXX | +XX% | ⚠️ |
| Weekend Avg | $X,XXX | $X,XXX | +XX% | ✅ |
| Top Service | $X,XXX | $X,XXX | +XX% | ⚠️ |
| Top Account | $X,XXX | $X,XXX | +XX% | ⚠️ |

**Statistical Analysis:**
- Mean: $X,XXX (baseline: $X,XXX)
- Std Dev: $XXX (baseline: $XXX)
- Current cost is X standard deviations from baseline
- Coefficient of variation: XX% (baseline: XX%)

### 10. Ticket & Documentation Cross-Reference
- **Existing related tickets:** [Jira/DevRev tickets that cover any detected anomalies]
- **Applicable runbooks:** [Confluence pages with remediation guidance]
- **Previously resolved similar anomalies:** [Historical ticket references]

### 11. Prioritized Action Plan

**Immediate Actions (Within 24 Hours):**
1. **[Action]** - Prevents $X,XXX/month
   - Severity: High
   - Effort: Low
   - Owner: [Suggested owner]
   - Ticket: [Link to existing or newly created ticket]

2. **[Action]** - Prevents $X,XXX/month
   - [Details]

**Short-Term Actions (This Week):**
1. **[Action]** - Potential savings $X,XXX/month
   - [Details]

**Monitoring and Prevention:**
1. Set up alerts for [specific anomaly type]
2. Review [dimension] daily for next week
3. Investigate [specific pattern] further
4. Implement [preventive measure]

**Tickets Created:**
For high-severity anomalies not already tracked, create tickets:

**Jira:**
```
createJiraIssue(
    projectKey="<project>",
    summary="Cost anomaly: [type] — [service/account] — [severity]",
    description="<anomaly details and recommended action>",
    issueType="Task"
)
```

**DevRev:**
```
create_ticket(
    title="Cost anomaly: [type] — [service/account] — [severity]",
    description="<anomaly details and recommended action>"
)
```

### 11. False Positive Assessment

**Likely Legitimate (Not True Anomalies):**
1. **[Item]**
   - Reason: [Why this is expected based on org context]
   - Recommendation: Update baseline expectations

**Requires Validation:**
1. **[Item]**
   - Could be legitimate or anomalous
   - Recommendation: Verify with [team/person]

## Skill-Specific Best Practices

1. **Establish proper baselines** - Need sufficient historical data
2. **Use statistical methods** - Not just absolute thresholds
3. **Consider day-of-week patterns** - Compare apples to apples
4. **Cross-reference dimensions** - Anomalies often span multiple dimensions
5. **Prioritize by impact** - Focus on highest-cost anomalies first
6. **Check for false positives** - Validate against known changes
7. **Provide context** - Explain why something is anomalous

For general cost analysis best practices, see `${CLAUDE_PLUGIN_ROOT}/references/best-practices.md`

## Anomaly Detection Techniques

### Statistical Anomaly Detection
```
For each data point:
  z_score = (value - mean) / stddev
  If abs(z_score) > 2:
    Flag as anomaly
```

### Percentage-Based Detection
```
If (current - baseline) / baseline > 0.5:
  Flag as 50%+ increase anomaly
```

### Rate-of-Change Detection
```
day_over_day_change = (today - yesterday) / yesterday
If day_over_day_change > threshold:
  Flag as rapid change anomaly
```

### Pattern Matching
- Compare recent pattern to historical patterns
- Detect when current pattern doesn't match any known pattern
- Use day-of-week, time-of-day templates

### Clustering
- Group similar cost patterns
- Identify outliers that don't fit any cluster
- Flag new clusters that emerge

## Common Anomaly Types

### Type 1: Compute Spikes
**Indicators:**
- Sudden EC2/Lambda/ECS cost increase
- Unusual instance types or sizes
- New regions with compute resources

**Causes:**
- Auto-scaling event
- New deployment
- Performance testing
- Crypto mining (security issue)

### Type 2: Storage Growth
**Indicators:**
- Gradual or sudden storage cost increase
- S3 bucket growth
- EBS volume increases

**Causes:**
- Data accumulation (expected or unexpected)
- Backup retention issues
- Log accumulation
- Snapshot proliferation

### Type 3: Data Transfer Spikes
**Indicators:**
- Network/data transfer cost spike
- Cross-region transfer increase
- Internet egress increase

**Causes:**
- Architecture change
- Data migration
- Security incident (data exfiltration)
- Misconfigured application

### Type 4: New Resource Creation
**Indicators:**
- Resources that didn't exist in baseline
- Costs in new accounts or regions
- New service usage

**Causes:**
- New project launch (legitimate)
- Developer experimentation
- Unauthorized resource creation
- Security breach

### Type 5: Idle or Waste Resources
**Indicators:**
- Resources with consistent low but non-zero cost
- Detached volumes
- Unused Reserved Instances

**Causes:**
- Forgotten test resources
- Improper cleanup after projects
- Manual provisioning without automation

## Advanced Techniques

### Machine Learning Anomaly Detection
If sufficient data:
- Build time-series models (ARIMA, Prophet)
- Predict expected costs
- Flag actual costs that deviate from prediction

### Seasonal Adjustment
Account for known seasonal patterns:
- End-of-quarter increased activity
- Holiday seasons
- Business cycle patterns

### Multi-Variate Analysis
Look for combinations of factors:
- High cost + new resource + unusual region = high priority
- Low cost + expected service + known account = low priority

### Anomaly Correlation
Find related anomalies:
- EC2 spike + data transfer spike might be same event
- Multiple services in same account might share root cause

## Tips for Effective Anomaly Detection

1. **Run regularly** - Daily or weekly, not just when problems noticed
2. **Know your baselines** - Understand normal patterns first
3. **Tune thresholds** - Adjust based on organization's tolerance
4. **Follow up** - Track which anomalies were real issues vs. false positives
5. **Automate** - Set up alerts for high-severity anomalies
6. **Document patterns** - Build knowledge base of anomaly types
7. **Close the loop** - Report back on resolution to improve detection
8. **Balance sensitivity** - Too sensitive = alert fatigue, too loose = miss issues

## See Also

- **understand-cloudzero-organization** skill - Load organization context first
- `${CLAUDE_PLUGIN_ROOT}/references/best-practices.md` - Universal cost analysis best practices
- `${CLAUDE_PLUGIN_ROOT}/references/cloudzero-tools-reference.md` - Complete tool documentation
- `${CLAUDE_PLUGIN_ROOT}/references/error-handling.md` - Troubleshooting and common errors
- `${CLAUDE_PLUGIN_ROOT}/references/dimensions-reference.md` - Dimension types and FQDIDs
- `${CLAUDE_PLUGIN_ROOT}/references/cost-types-reference.md` - When to use each cost type
