# CloudZero Cost Analysis - Error Handling

Common error scenarios and solutions when working with CloudZero cost data.

## Common Errors and Solutions

### 1. "Unknown Dimension FQDID" Error

**Error Message**: `Unknown dimension FQDID: CZ:ServiceName`

**Cause**: Dimension doesn't exist or FQDID is incorrect

**Solutions**:
```
# Find correct FQDID
get_available_dimensions(filter="Service")

# Verify exact spelling and case
get_available_dimensions()
```

**Prevention**:
- Always use `get_available_dimensions` to discover FQDIDs
- Don't guess dimension names
- Check case sensitivity (FQDIDs are case-sensitive)
- Verify colon placement in FQDID format

---

### 2. Empty Query Results

**Scenario**: Query returns no data or empty results

**Common Causes**:
1. **No data for time period**
2. **Filters too restrictive**
3. **Dimension has no values**
4. **Date range outside data availability**

**Solutions**:

**Check if dimension has data**:
```
get_dimension_values(dimension="CZ:Tag:Environment")
```

**Try broader date range**:
```
# Instead of last 7 days, try last 30
get_cost_data(
    date_range="last 30 days",
    group_by=["CZ:Service"]
)
```

**Remove or broaden filters**:
```
# If filtered query returns nothing, try without filters
get_cost_data(group_by=["CZ:Service"])
```

**Check different dimension**:
```
# If CZ:Tag:Team has no data, try another dimension
get_cost_data(group_by=["CZ:Account"])
```

---

### 3. Slow Query Performance

**Scenario**: Query takes a long time to return results

**Causes**:
- Too many dimensions in `group_by`
- High `limit` value
- Fine granularity over long period
- Unfiltered queries on large datasets

**Solutions**:

**Reduce limit**:
```
# Instead of limit=500, try limit=50
get_cost_data(
    group_by=["CZ:Service"],
    limit=50
)
```

**Use fewer dimensions**:
```
# Instead of 3 dimensions, start with 1-2
get_cost_data(
    group_by=["CZ:Service", "CZ:Account"]
    # Remove third dimension
)
```

**Add filters to narrow scope**:
```
get_cost_data(
    filters={"CZ:Account": ["123456789012"]},
    group_by=["CZ:Service"]
)
```

**Use coarser granularity**:
```
# Instead of hourly over 90 days, use daily
get_cost_data(
    granularity="daily",  # not "hourly"
    date_range="last 90 days"
)
```

---

### 4. Dimension Value Not Found

**Scenario**: You know a dimension value exists but can't find it in query results

**Causes**:
- Value doesn't have costs in specified time period
- Typo in filter value
- Case sensitivity issue
- Value exists but with different spelling

**Solutions**:

**Check exact values**:
```
get_dimension_values(dimension="CZ:Service")
```

**Use partial matching**:
```
# Use & prefix for case-insensitive substring match
get_cost_data(
    filters={"&CZ:Service": ["EC2"]},
    group_by=["CZ:Account"]
)
```

**Try different date range**:
```
get_dimension_values(
    dimension="CZ:Service",
    date_range="last 90 days"  # broader range
)
```

---

### 5. Stale Dimension List

**Scenario**: New dimensions were created but don't appear

**Cause**: Dimension list is cached (up to 1 hour)

**Solution**:
```
get_available_dimensions(force_refresh=True)
```

**When to use**:
- Immediately after creating new custom dimensions
- After CostFormation changes
- When dimension list seems outdated

---

### 6. Date Range Issues

**Scenario**: Date range not returning expected results

**Common Issues**:
- Invalid date format
- Date range outside data availability
- Different month lengths affecting comparisons

**Solutions**:

**Use standard formats**:
```
# Valid formats
date_range="2024-01-01 to 2024-01-31"
date_range="last 30 days"
date_range="last 7 days"
date_range="this month"
date_range="last month"
```

**Check data availability**:
```
# Start with broad range to verify data exists
get_cost_data(date_range="last 90 days")
```

**Normalize period lengths**:
```
# When comparing months, use same length:
# January (31 days) vs February (28 days)
# Use daily average or normalize to 30 days
```

---

### 7. Filter Not Working as Expected

**Scenario**: Filter doesn't return expected results

**Common Issues**:
- Wrong filter syntax
- Forgetting filter prefix for special behavior
- Multiple filters with AND vs OR confusion

**Solutions**:

**Verify filter syntax**:
```
# Correct - list of values
filters={"CZ:Account": ["123456789012", "987654321098"]}

# Incorrect - single value not in list
filters={"CZ:Account": "123456789012"}  # WRONG
```

**Use correct prefix**:
```
# Exact match (no prefix)
filters={"CZ:Service": ["AmazonEC2"]}

# Partial match (& prefix)
filters={"&CZ:Service": ["EC2"]}

# Exclusion (! prefix)
filters={"!CZ:Service": ["AmazonEC2"]}

# Exclude partial match (!& prefix)
filters={"!&CZ:Service": ["backup"]}
```

**Multiple filters are AND**:
```
# This means: (Account = X) AND (Environment = production)
filters={
    "CZ:Account": ["123456789012"],
    "CZ:Tag:Environment": ["production"]
}
```

For OR logic, use multiple values in one filter:
```
# This means: Environment = prod OR staging OR dev
filters={
    "CZ:Tag:Environment": ["production", "staging", "development"]
}
```

---

### 8. Too Many Results

**Scenario**: Query returns more results than you can process

**Solution**:

**Increase limit parameter**:
```
get_cost_data(
    group_by=["CZ:Service"],
    limit=100  # or higher
)
```

**Use filters to focus**:
```
# Instead of all services, focus on specific account
get_cost_data(
    filters={"CZ:Account": ["123456789012"]},
    group_by=["CZ:Service"],
    limit=50
)
```

---

### 9. Custom Dimension Not Found

**Scenario**: User mentions a custom dimension (like "Team") but it doesn't exist

**Solutions**:

**Check organization context first**:
```
get_organization_context()
```

**Discover custom dimensions**:
```
get_available_dimensions(filter="User:Defined")
```

**Suggest alternatives**:
- If "Team" dimension doesn't exist, check for `CZ:Tag:Team`
- Ask if they have custom dimensions configured
- Suggest available alternatives

---

### 10. Inconsistent Time Series Data

**Scenario**: Time series has gaps or inconsistent data points

**Causes**:
- Limit parameter causing inconsistent dimension values across time
- Resources starting/stopping during period
- New resources appearing mid-period

**Understanding Limit Behavior**:

The `limit` parameter determines which dimension value sets to include based on **total cost across the entire period**:

```
# Returns top 5 services by total cost
# Same 5 services appear in every time period
get_cost_data(
    group_by=["CZ:Service"],
    granularity="daily",
    limit=5
)
```

**Solution for comprehensive time series**:
- Increase `limit` to include all relevant dimension values
- Accept that some values may appear mid-period (new resources)
- Filter to specific dimension values if you want consistent tracking

---

## General Troubleshooting Workflow

### Step 1: Verify Basics
1. Check that dimension FQDIDs are correct
2. Verify date range is valid and has data
3. Confirm cost type is appropriate

### Step 2: Simplify Query
1. Remove all filters
2. Use single dimension in `group_by`
3. Remove granularity (query totals only)
4. Use small limit (10-20)

### Step 3: Add Complexity Gradually
1. If Step 2 works, add one element at a time
2. Add filters one by one
3. Add dimensions one at a time
4. Add granularity last

### Step 4: Check Data Availability
1. Use `get_dimension_values` to verify values exist
2. Check broader date ranges
3. Verify organization has data for requested dimensions

---

## When to Escalate

Contact CloudZero support if:
- Consistent errors with valid queries
- Data discrepancies with invoices (using `billed_cost`)
- MCP server unavailable or timing out
- Dimension values that should exist are missing
- Performance issues with reasonable queries

---

## Prevention Best Practices

1. **Always use `get_available_dimensions`** before querying
2. **Check organization context** for custom dimensions
3. **Start simple** and add complexity gradually
4. **Verify date ranges** have data before detailed analysis
5. **Use appropriate limits** for query scope
6. **Test filters** with small queries first
7. **Document assumptions** about data availability

---

## Quick Reference

| Error | Quick Fix |
|-------|-----------|
| Unknown dimension | Use `get_available_dimensions(filter="...")` |
| Empty results | Try broader date range, remove filters |
| Slow query | Reduce limit, fewer dimensions, add filters |
| Value not found | Check `get_dimension_values()`, try partial match |
| Stale dimensions | Use `force_refresh=True` |
| Filter not working | Check syntax, verify prefix usage |
| Too many results | Increase limit or add filters |
| Custom dimension missing | Check `get_organization_context()` |

---

## See Also

- [CloudZero Tools Reference](${CLAUDE_PLUGIN_ROOT}/references/cloudzero-tools-reference.md)
- [Dimensions Reference](${CLAUDE_PLUGIN_ROOT}/references/dimensions-reference.md)
- [Best Practices](${CLAUDE_PLUGIN_ROOT}/references/best-practices.md)
