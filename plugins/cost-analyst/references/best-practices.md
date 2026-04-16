# CloudZero Cost Analysis - Best Practices

## Universal Best Practices

These best practices apply to all CloudZero cost analysis skills.

### 1. Organization Context First
**Always ensure organization context is loaded** via the `understand-cloudzero-organization` skill before performing analysis. This provides:
- Available custom dimensions
- Organization-specific workflows
- Business context
- Cost allocation policies

**Efficiency**: Call `get_org_context` once per conversation, then reference the cached information.

### 2. Use Appropriate Cost Types
- **Default**: Use `real_cost` for engineering and optimization discussions
- **Billing reconciliation**: Use `billed_cost` to match invoices
- **Savings analysis**: Use `on_demand_cost` to calculate effective savings
- **Detailed allocation**: Use `discounted_amortized_cost` for showback/chargeback

See [Cost Types Reference](${CLAUDE_PLUGIN_ROOT}/references/cost-types-reference.md) for complete details.

### 3. Use Specific FQDIDs
- Always use exact Fully Qualified Dimension IDs (FQDIDs)
- Don't guess dimension names - use `get_available_dimensions` to discover
- Format: `CZ:Service`, `CZ:Tag:Environment`, `User:Defined:Team`
- Case-sensitive and format-specific

### 4. Query Construction

**Start Broad, Then Narrow:**
```
1. Query total costs or top-level dimension
2. Identify interesting patterns
3. Drill down with filters and additional dimensions
4. Add more dimensions for deeper analysis
```

**Use Appropriate Limits:**
- Default limit: 50 (good balance)
- Initial exploration: 20 (faster)
- Comprehensive analysis: 100+ (detailed)

**Filter Early:**
- Apply filters to reduce data volume
- Filter by account, environment, or service first
- Then add grouping dimensions

### 5. Use Code for All Calculations

**Never perform arithmetic mentally.** When you have numerical data from CloudZero API responses and need to derive any computed values, **write and execute code** to compute them. Use the Bash tool to run a Python (or JavaScript) script that processes the data and prints the results.

**Why:** LLMs are unreliable at arithmetic. Financial data demands precision — wrong totals, percentages, or growth rates erode trust and lead to bad decisions.

**Language choice:**
- **Python** (default): Use for all terminal-based analysis and reports
- **JavaScript**: Use when the user asks for a web page, HTML report, or browser-based visualization

**What must be computed in code** (not mentally):
- Totals, subtotals, averages
- Percentage of total spend, cumulative percentages (80/20 analysis)
- Period-over-period changes (WoW, MoM, QoQ growth rates)
- Compound growth rates and forecasts
- Statistical measures (mean, standard deviation, z-scores, coefficient of variation)
- Normalization for different time period lengths
- Savings rates, variance analysis, weighted scores
- Comparisons to previous periods

**Pattern:** After receiving cost data from the API, write a Python script that processes the numbers and prints formatted results. Then use those printed results in your narrative analysis.

### 6. Use Meaningful Granularity

Choose time granularity based on analysis period:
- **Hourly**: Last 1-3 days (pattern analysis)
- **Daily**: Last 7-90 days (trend analysis)
- **Weekly**: Last 3-6 months (medium-term trends)
- **Monthly**: 6+ months (long-term trends)
- **None**: For totals without time series

### 7. Leverage Organization-Specific Dimensions

Prioritize custom dimensions defined by the organization:
- `User:Defined:Team` - for team attribution
- `User:Defined:Product` - for product cost tracking
- `User:Defined:CostCenter` - for financial allocation
- These provide business-aligned visibility

### 8. Handle Multiple Dimensions

**Maximum 3 dimensions** in `group_by`:
- More dimensions = more results to process
- Choose dimensions strategically
- Start with 1-2, add third if needed

**Example combinations:**
- `[CZ:Service, CZ:Account]` - Services per account
- `[User:Defined:Team, CZ:Service]` - Team service usage
- `[CZ:CloudProvider, CZ:Region, CZ:Service]` - Full breakdown

### 9. Provide Actionable Recommendations

Every analysis should include:
- **What**: Clear description of findings
- **Why**: Explanation of what's causing the pattern
- **So What**: Business impact
- **Now What**: Specific recommended actions with dollar impacts

### 10. Respect Data Availability

- Some dimensions may not have data in all time periods
- Handle empty results gracefully
- Suggest alternative dimensions if primary ones are unavailable
- Note data gaps or incomplete coverage

## Query Optimization

### Performance Tips
1. Use `limit` parameter to control result size
2. Apply filters before grouping when possible
3. Use appropriate granularity (don't use hourly for 90-day analysis)
4. Query specific date ranges rather than defaults when possible

### Troubleshooting Slow Queries
- Reduce limit
- Use fewer group_by dimensions
- Add filters to narrow scope
- Use coarser granularity

## Data Interpretation

### Common Patterns to Recognize

**80/20 Rule:**
- Typically, 20% of resources drive 80% of costs
- Identify this concentration in your analysis
- Prioritize optimization on top contributors

**Day-of-Week Patterns:**
- Weekday vs. weekend differences
- Business hours vs. off-hours
- Batch processing schedules

**Month-End Patterns:**
- Month-end processing spikes
- Billing cycle effects
- Seasonal business patterns

**Growth Patterns:**
- Linear vs. exponential growth
- Step changes (new project launches)
- Cyclical patterns

### Red Flags to Watch For

- **Sudden spikes**: Investigate immediately
- **Weekend costs equal to weekday**: Possible waste
- **Untagged high-cost resources**: Governance issue
- **Non-prod at prod scale**: Rightsizing opportunity
- **Exponential growth**: Potential runaway costs
- **New services appearing**: May be unauthorized or unplanned

## Communication Best Practices

### For Technical Audiences
- Use service names and technical terminology
- Include instance types, configurations, regions
- Provide CLI commands or API calls for remediation
- Focus on optimization and efficiency

### For Business Audiences
- Translate to business terms (teams, products, features)
- Focus on cost per business metric (per user, per transaction)
- Highlight budget impacts and ROI
- Provide executive summaries

### For Finance Teams
- Use billing-aligned cost types (`billed_cost`, `invoiced_amortized_cost`)
- Provide reconciliation details
- Include tax and fee breakdowns
- Focus on accuracy and audit trails

## Common Pitfalls to Avoid

1. **Comparing unequal periods**: Always use same-length time ranges
2. **Ignoring business context**: Cost increases may be expected/legitimate
3. **Analysis paralysis**: Don't query every dimension - stay focused
4. **Missing the forest for the trees**: Highlight key insights, not just data
5. **Forgetting to normalize**: Compare apples to apples
6. **Over-precision**: $10,234.56 vs. ~$10K - match precision to audience
7. **Recommendation without action**: Always provide specific next steps

## Advanced Techniques

### Filter Prefixes
- **&** prefix: Partial match (case-insensitive substring)
- **!** prefix: Exclusion (invert filter)
- **!&** prefix: Exclude by partial match

### Multi-Period Analysis
Query multiple periods and compare:
- Current month vs. last month
- This year vs. last year (YoY)
- Before vs. after optimization

### Trend Decomposition
Break trends into components:
- Baseline cost (stable)
- Growth component (increasing/decreasing)
- Cyclical component (regular patterns)
- Irregular component (one-time events)

## Quality Assurance Checklist

Before finalizing any cost analysis:
- [ ] Organization context retrieved and considered
- [ ] Appropriate cost type used for the question
- [ ] Exact FQDIDs used (not guessed)
- [ ] Results interpreted with business context
- [ ] Percentages and comparisons included
- [ ] Time periods compared fairly
- [ ] Actionable recommendations with dollar impacts
- [ ] Appropriate level of detail for audience
- [ ] All numerical calculations performed via code execution (not mental math)
- [ ] Cross-checked findings for consistency
- [ ] Acknowledged limitations or data gaps

## See Also

- [CloudZero Tools Reference](${CLAUDE_PLUGIN_ROOT}/references/cloudzero-tools-reference.md)
- [Dimensions Reference](${CLAUDE_PLUGIN_ROOT}/references/dimensions-reference.md)
- [Cost Types Reference](${CLAUDE_PLUGIN_ROOT}/references/cost-types-reference.md)
- [Error Handling](${CLAUDE_PLUGIN_ROOT}/references/error-handling.md)
