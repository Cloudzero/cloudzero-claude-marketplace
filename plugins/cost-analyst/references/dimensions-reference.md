# CloudZero Dimensions Reference

## Overview

Dimensions in CloudZero are the attributes by which you can group and filter cost data. All dimensions are identified using **FQDIDs** (Fully Qualified Dimension IDs).

## Dimension Types

### 1. Core Dimensions (`CZ:*`)
Foundational dimensions with two colon-delimited parts representing fundamental cloud resource attributes.

**Common Core Dimensions**:
- `CZ:Service` - Cloud services (EC2, RDS, S3, etc.)
- `CZ:Account` - Cloud provider accounts
- `CZ:CloudProvider` - Cloud providers (AWS, GCP, Azure)
- `CZ:Region` - Cloud regions (us-east-1, us-west-2, etc.)
- `CZ:Resource` - Specific resource identifiers
- `CZ:UsageType` - Usage type details (if available)

### 2. Kubernetes Dimensions (`CZ:K8s:*`)
Dimensions specific to Kubernetes resources.

**Examples**:
- `CZ:K8s:Cluster` - Kubernetes cluster names
- `CZ:K8s:Namespace` - Kubernetes namespaces
- `CZ:K8s:Workload` - Workload names (deployments, statefulsets)
- `CZ:K8s:Pod` - Pod identifiers

### 3. Kubernetes Labels (`CZ:K8s:Label:*`)
Labels applied to Kubernetes resources.

**Examples**:
- `CZ:K8s:Label:app` - Application labels
- `CZ:K8s:Label:environment` - Environment labels
- `CZ:K8s:Label:version` - Version labels

### 4. Resource Tags (`CZ:Tag:*`)
Cloud provider resource tags (AWS tags, GCP labels, Azure tags).

**Common Tags**:
- `CZ:Tag:Environment` - Environment (production, staging, dev)
- `CZ:Tag:Team` - Team ownership
- `CZ:Tag:Application` - Application name
- `CZ:Tag:CostCenter` - Cost center for financial allocation
- `CZ:Tag:Owner` - Resource owner
- `CZ:Tag:Project` - Project affiliation

**Note**: Specific tags depend on your organization's tagging strategy.

### 5. CloudZero Global Dimensions (`CZ:Defined:*`)
Dimensions defined and maintained by CloudZero, available across all organizations.

These are curated groupings and calculated dimensions maintained by CloudZero.

### 6. User-Defined Dimensions (`User:Defined:*`)
Custom dimensions created by your organization via CloudZero's CostFormation.

**Common Custom Dimensions**:
- `User:Defined:Team` - Engineering/business teams
- `User:Defined:Product` - Product groupings
- `User:Defined:Feature` - Feature-level attribution
- `User:Defined:CostCenter` - Custom cost centers
- `User:Defined:BusinessUnit` - Business unit groupings
- `User:Defined:Environment` - Custom environment definitions

**Note**: Exact custom dimensions vary by organization. Use `get_org_context` to discover what exists.

## FQDID Format Rules

### Format Requirements
- Case-sensitive
- Colon-delimited structure
- Specific prefixes define dimension type
- No spaces or special characters (except colons)

### Valid FQDID Examples
✅ `CZ:Service`
✅ `CZ:Tag:Environment`
✅ `User:Defined:Team`
✅ `CZ:K8s:Cluster`
✅ `CZ:K8s:Label:app`

### Invalid FQDID Examples
❌ `Service` (missing prefix)
❌ `CZ-Service` (wrong delimiter)
❌ `cz:service` (wrong case)
❌ `CZ: Service` (contains space)

## Discovering Dimensions

### Find All Available Dimensions
```
get_available_dimensions()
```

### Find Specific Dimension Types
```
# Find all tags
get_available_dimensions(filter="Tag")

# Find custom dimensions
get_available_dimensions(filter="User:Defined")

# Find Kubernetes dimensions
get_available_dimensions(filter="K8s")

# Find service dimension
get_available_dimensions(filter="Service")
```

### Get Dimension Values
```
# Get all services
get_dimension_values(dimension="CZ:Service")

# Get all accounts
get_dimension_values(dimension="CZ:Account")

# Get environment tag values
get_dimension_values(dimension="CZ:Tag:Environment")

# Get teams
get_dimension_values(dimension="User:Defined:Team")
```

## Dimension Selection Strategy

### For General Cost Analysis
Start with these dimensions:
1. `CZ:Service` - What services cost money?
2. `CZ:Account` - Which accounts are spending?
3. `CZ:CloudProvider` - How is spending distributed across clouds?
4. `CZ:Region` - Which regions are most expensive?

### For Tag-Based Analysis
Use tag dimensions for environment, ownership, and application attribution:
1. `CZ:Tag:Environment` - prod/staging/dev breakdown
2. `CZ:Tag:Team` - team attribution
3. `CZ:Tag:Application` - application-level costs
4. `CZ:Tag:CostCenter` - financial allocation

### For Custom Dimension Analysis
Use organization-specific dimensions for business-aligned analysis:
1. `User:Defined:Team` - team/product organization
2. `User:Defined:Product` - product P&L
3. `User:Defined:Feature` - feature-level costs
4. `User:Defined:BusinessUnit` - business unit breakdown

### For Kubernetes Analysis
Use Kubernetes-specific dimensions:
1. `CZ:K8s:Cluster` - cluster costs
2. `CZ:K8s:Namespace` - namespace breakdown
3. `CZ:K8s:Workload` - workload-level costs
4. `CZ:K8s:Label:*` - label-based attribution

## Common Dimension Combinations

### Service Analysis
```
# Services by account
group_by=["CZ:Account", "CZ:Service"]

# Services by region
group_by=["CZ:Region", "CZ:Service"]

# Services by cloud provider
group_by=["CZ:CloudProvider", "CZ:Service"]
```

### Environment Analysis
```
# Environments by service
group_by=["CZ:Tag:Environment", "CZ:Service"]

# Environments by account
group_by=["CZ:Tag:Environment", "CZ:Account"]
```

### Team/Product Analysis
```
# Teams by service
group_by=["User:Defined:Team", "CZ:Service"]

# Products by service
group_by=["User:Defined:Product", "CZ:Service"]

# Teams by account
group_by=["User:Defined:Team", "CZ:Account"]
```

### Comprehensive Breakdown
```
# Three-dimensional analysis
group_by=["CZ:CloudProvider", "CZ:Account", "CZ:Service"]

# Team + Environment + Service
group_by=["User:Defined:Team", "CZ:Tag:Environment", "CZ:Service"]
```

## Hidden vs. Visible Dimensions

### Visible Dimensions
- User-facing dimensions
- Directly useful for analysis
- Default when calling `get_available_dimensions()`

### Hidden Dimensions
- Internal building-block dimensions
- Used for constructing other dimensions
- Available with `get_available_dimensions(include_hidden=True)`
- Generally not needed for standard analysis

## Tips for Working with Dimensions

### Discovery
1. **Always use `get_available_dimensions`** - Don't guess FQDIDs
2. **Filter results** - Use `filter` parameter to narrow search
3. **Check organization context** - Understand custom dimensions first
4. **Use `field_selector='fqdid'`** - Get just FQDIDs for faster queries

### Usage
1. **Use exact FQDIDs** - Case-sensitive, format-specific
2. **Start with 1-2 dimensions** - Add more as needed (max 3)
3. **Combine complementary dimensions** - Service + Account, Team + Service
4. **Respect data availability** - Some dimensions may not have data for all periods

### Troubleshooting
1. **"Unknown dimension" error** - Verify FQDID with `get_available_dimensions`
2. **Empty results** - Check if dimension has data with `get_dimension_values`
3. **Too many results** - Increase `limit` or add filters
4. **Stale dimension list** - Use `force_refresh=True`

## Dimension Value Patterns

### Service Values
- Format: "AmazonEC2", "Amazon Simple Storage Service", "AWS Lambda"
- Exact names from cloud provider
- Case-sensitive

### Account Values
- Format: Account IDs or names (depending on configuration)
- AWS: "123456789012"
- GCP: Project IDs or names
- Azure: Subscription IDs or names

### Region Values
- Format: Cloud provider region codes
- AWS: "us-east-1", "us-west-2", "eu-west-1"
- GCP: "us-central1", "us-east1"
- Azure: "eastus", "westus2"

### Tag Values
- Format: Whatever values your organization uses
- Often: "production", "staging", "development", "test"
- Case varies by organization
- Check consistency with `get_dimension_values`

### Custom Dimension Values
- Format: Defined by organization
- Check `get_org_context` for meanings
- Use `get_dimension_values` to see all values

## See Also

- [CloudZero Tools Reference](${CLAUDE_PLUGIN_ROOT}/references/cloudzero-tools-reference.md)
- [Best Practices](${CLAUDE_PLUGIN_ROOT}/references/best-practices.md)
- [Understand CloudZero Organization Skill](${CLAUDE_PLUGIN_ROOT}/skills/understand-cloudzero-organization/SKILL.md)
