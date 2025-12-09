# CloudZero MCP Tools Reference

Complete reference for all CloudZero Model Context Protocol (MCP) server tools.

## Tool Overview

| Tool | Purpose | When to Use |
|------|---------|-------------|
| `get_organization_context` | Retrieve org-specific context | **First call** in any analysis |
| `get_available_dimensions` | Discover available dimensions | Finding what dimensions exist |
| `get_dimension_values` | Get values for a dimension | Understanding dimension contents |
| `get_cost_data` | Query actual cost data | All cost analysis queries |
| `get_reference_information` | Get detailed reference docs | When you need in-depth guidance |

---

## get_organization_context

**Purpose**: Retrieve organization-specific context including custom dimensions, workflows, and business information.

**Parameters**: None

**Returns**:
- Custom dimension definitions and meanings
- Organization-specific workflows
- Team structures and ownership
- Cost allocation policies
- Important business context

**Usage**:
```
get_organization_context()
```

**Best Practice**: Call **once** per conversation at the beginning, then reference the cached results.

**See**: [Understand CloudZero Organization](${CLAUDE_PLUGIN_ROOT}/skills/understand-cloudzero-organization/SKILL.md) skill

---

## get_available_dimensions

**Purpose**: Discover what dimensions are available for cost analysis in this organization.

**Parameters**:
- `filter` (optional): Case-insensitive substring to search dimension names
- `limit` (optional): Maximum dimensions to return
- `force_refresh` (optional): Force cache refresh (default: false)
- `include_hidden` (optional): Include internal dimensions (default: false)
- `field_selector` (optional): Return format - `'fqdid'`, `'display_name'`, or full objects

**Returns**: List of available dimensions with FQDIDs and display names

**Common Usage Patterns**:

```
# Discover all dimensions
get_available_dimensions()

# Find dimensions containing "tag"
get_available_dimensions(filter="tag")

# Find custom dimensions
get_available_dimensions(filter="User:Defined")

# Find service dimensions
get_available_dimensions(filter="Service")

# Get just FQDIDs (faster)
get_available_dimensions(field_selector="fqdid")
```

**Tips**:
- Use `filter` to narrow results
- Use `include_hidden=False` for user-facing discovery
- Use `force_refresh=True` after creating new dimensions

---

## get_dimension_values

**Purpose**: Get the distinct values that exist for a specific dimension.

**Parameters**:
- `dimension` (required): FQDID of the dimension
- `date_range` (optional): Time range to query (default: last 30 days)
- `match` (optional): Case-insensitive substring filter on values
- `limit` (optional): Maximum values to return (default: 100)

**Returns**: List of dimension values that have cost data

**Common Usage Patterns**:

```
# Get all services
get_dimension_values(dimension="CZ:Service")

# Get environment values
get_dimension_values(dimension="CZ:Tag:Environment")

# Find services matching "EC2"
get_dimension_values(dimension="CZ:Service", match="EC2")

# Get teams (custom dimension)
get_dimension_values(dimension="User:Defined:Team")

# Get accounts for specific time range
get_dimension_values(
    dimension="CZ:Account",
    date_range="2024-01-01 to 2024-01-31"
)
```

**Tips**:
- Use `match` parameter to filter values
- Increase `limit` if you need more results
- Specify `date_range` to see values for specific periods

---

## get_cost_data

**Purpose**: Query actual cost data grouped and filtered by dimensions.

**Parameters**:
- `group_by` (optional): List of 1-3 dimension FQDIDs to group by
- `filters` (optional): Dict mapping dimension FQDIDs to lists of values
- `date_range` (optional): Time range (default: last 30 days)
- `granularity` (optional): Time granularity - `hourly`, `daily`, `weekly`, `monthly`, or `None`
- `cost_type` (optional): Type of cost (default: `real_cost`)
- `limit` (optional): Maximum dimension value sets to return (default: 50)

**Returns**: Cost data grouped by specified dimensions over time

### Basic Query Patterns

**Total costs (no grouping)**:
```
get_cost_data(cost_type="real_cost")
```

**Top services**:
```
get_cost_data(
    group_by=["CZ:Service"],
    limit=20
)
```

**Top accounts**:
```
get_cost_data(
    group_by=["CZ:Account"],
    limit=20
)
```

### Multi-Dimensional Queries

**Services by account**:
```
get_cost_data(
    group_by=["CZ:Account", "CZ:Service"],
    limit=50
)
```

**Services by region**:
```
get_cost_data(
    group_by=["CZ:Region", "CZ:Service"],
    limit=50
)
```

**Three-dimensional breakdown**:
```
get_cost_data(
    group_by=["CZ:CloudProvider", "CZ:Account", "CZ:Service"],
    limit=100
)
```

### Filtering

**Filter by account**:
```
get_cost_data(
    group_by=["CZ:Service"],
    filters={"CZ:Account": ["123456789012"]},
    limit=20
)
```

**Filter by multiple values**:
```
get_cost_data(
    group_by=["CZ:Service"],
    filters={"CZ:Account": ["123456789012", "987654321098"]},
    limit=20
)
```

**Multi-dimensional filters**:
```
get_cost_data(
    group_by=["CZ:Service"],
    filters={
        "CZ:Account": ["123456789012"],
        "CZ:Tag:Environment": ["production"]
    },
    limit=20
)
```

### Filter Prefixes

**Partial match (& prefix)**:
```
get_cost_data(
    group_by=["CZ:Account"],
    filters={"&CZ:Service": ["EC2", "Lambda"]},
    limit=20
)
```
Returns costs for services *containing* "EC2" or "Lambda" (case-insensitive).

**Exclusion (! prefix)**:
```
get_cost_data(
    group_by=["CZ:Service"],
    filters={"!CZ:Tag:Environment": ["test", "dev"]},
    limit=20
)
```
Returns costs *excluding* test and dev environments.

**Combined (!& prefix)**:
```
get_cost_data(
    group_by=["CZ:Service"],
    filters={"!&CZ:Service": ["backup", "archive"]},
    limit=20
)
```
Excludes services *containing* "backup" or "archive".

### Time-Based Queries

**Daily trend**:
```
get_cost_data(
    group_by=["CZ:Service"],
    granularity="daily",
    limit=10
)
```

**Specific date range**:
```
get_cost_data(
    group_by=["CZ:Service"],
    date_range="2024-01-01 to 2024-01-31",
    limit=20
)
```

**Hourly pattern (last 7 days)**:
```
get_cost_data(
    group_by=["CZ:Service"],
    granularity="hourly",
    date_range="last 7 days",
    limit=5
)
```

### Cost Type Examples

**Real cost (default)**:
```
get_cost_data(
    group_by=["CZ:Service"],
    cost_type="real_cost"
)
```

**On-demand cost (for savings analysis)**:
```
get_cost_data(
    group_by=["CZ:Service"],
    cost_type="on_demand_cost"
)
```

**Billed cost (for invoice reconciliation)**:
```
get_cost_data(
    group_by=["CZ:Service"],
    cost_type="billed_cost"
)
```

### Custom Dimension Queries

**Costs by team**:
```
get_cost_data(
    group_by=["User:Defined:Team"],
    limit=20
)
```

**Team service breakdown**:
```
get_cost_data(
    group_by=["User:Defined:Team", "CZ:Service"],
    limit=50
)
```

### Query Optimization Tips

1. **Use appropriate limits**:
   - Start with limit=20 for exploration
   - Use limit=50 (default) for standard analysis
   - Use limit=100+ for comprehensive breakdowns

2. **Filter early**:
   - Apply filters to reduce data volume
   - Filter by account or environment first
   - Then add grouping dimensions

3. **Choose appropriate granularity**:
   - `None` for totals (fastest)
   - `daily` for last 7-90 days
   - `hourly` only for last few days
   - `monthly` for long-term trends

4. **Limit group_by dimensions**:
   - Maximum 3 dimensions
   - Start with 1-2, add third only if needed
   - More dimensions = more results to process

---

## get_reference_information

**Purpose**: Retrieve detailed reference documentation on specific topics.

**Parameters**:
- `reference_type` (required): Type of reference to retrieve

**Available Reference Types**:
- `cost_types`: Complete guide to all cost types
- `dimensions`: Detailed dimension types and FQDID reference
- `cost_analysis_workflow`: Step-by-step cost analysis workflow
- `custom_dimensions_workflow`: Workflow for analyzing custom dimensions
- `filtering_workflow`: Workflow for filtering and drilling down
- `cost_analyst_instructions`: Complete cost analyst role instructions

**Common Usage**:

```
# Learn about cost types
get_reference_information(reference_type="cost_types")

# Understand dimensions
get_reference_information(reference_type="dimensions")

# Get analysis workflow guidance
get_reference_information(reference_type="cost_analysis_workflow")
```

**When to Use**:
- User asks "which cost type should I use?"
- Need detailed explanation of FQDID formats
- Want step-by-step workflow guidance
- Need comprehensive reference material

---

## Common Query Patterns

### Top N Analysis
```
get_cost_data(
    group_by=["CZ:Service"],
    limit=10
)
```

### Time Series Analysis
```
get_cost_data(
    group_by=["CZ:Service"],
    granularity="daily",
    limit=5
)
```
Returns daily costs for top 5 services (by total across entire period).

### Filtered Breakdown
```
get_cost_data(
    filters={"CZ:Service": ["AmazonEC2"]},
    group_by=["CZ:Account", "CZ:Region"],
    limit=50
)
```

### Tag-Based Analysis
```
get_cost_data(
    group_by=["CZ:Tag:Environment", "CZ:Service"],
    limit=50
)
```

### Custom Dimension Analysis
```
get_cost_data(
    group_by=["User:Defined:Team", "CZ:Service"],
    limit=50
)
```

---

## Troubleshooting

### "Unknown dimension FQDID" Error
- Use `get_available_dimensions` to find correct FQDID
- Check spelling and case sensitivity
- Ensure dimension exists in organization

### Empty Results
- Check date range - try broader range
- Try less restrictive filters
- Verify dimension has data for time period
- Use `get_dimension_values` to confirm values exist

### Slow Queries
- Reduce `limit` parameter
- Use fewer `group_by` dimensions
- Add filters to narrow scope
- Use coarser granularity

### Stale Dimension List
- Use `force_refresh=True` on `get_available_dimensions`
- Relevant if dimensions were recently created

---

## See Also

- [Cost Types Reference](${CLAUDE_PLUGIN_ROOT}/references/cost-types-reference.md)
- [Dimensions Reference](${CLAUDE_PLUGIN_ROOT}/references/dimensions-reference.md)
- [Best Practices](${CLAUDE_PLUGIN_ROOT}/references/best-practices.md)
- [Error Handling](${CLAUDE_PLUGIN_ROOT}/references/error-handling.md)
