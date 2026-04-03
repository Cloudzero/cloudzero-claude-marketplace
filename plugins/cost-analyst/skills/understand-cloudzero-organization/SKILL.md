---
name: understand-cloudzero-organization
description: Foundational skill that retrieves and understands organization-specific CloudZero context including custom dimensions, workflows, team structures, and cost allocation policies - enriched with Confluence documentation and Jira/DevRev ticket context - must be used before any cost analysis
author: CloudZero <support@cloudzero.com>
version: 1.0.0
license: Apache-2.0
---

# Understand CloudZero Organization

## Purpose
This foundational skill retrieves organization-specific context from CloudZero that is essential for accurate cost analysis. It should be invoked once at the beginning of any cost analysis session to understand the organization's unique dimensions, workflows, and business context.

## When to Use
- **MANDATORY**: At the start of any cost analysis conversation or workflow
- Before any other cost analysis skill is invoked
- When switching to analyze a different organization
- When you need to understand available custom dimensions

**Note**: Once organization context is retrieved in a conversation, other skills should reference the cached information rather than re-reading it.

## What Organization Context Provides

Organization context from `get_org_context` includes:

### 1. Custom Dimension Definitions
- **User:Defined:** dimensions specific to this organization
- Business meanings and mappings (e.g., "User:Defined:Team" = engineering teams)
- Hierarchical relationships (Business Unit → Product → Team)
- How dimensions map to organizational structure

### 2. Organization-Specific Workflows
- Preferred analysis patterns for this organization
- Standard time periods for reporting (weekly, monthly, quarterly)
- Typical cost review processes
- Key stakeholders and reporting requirements

### 3. Team Structures and Ownership
- How teams/products are organized
- Cost center mappings
- Budget owners and accountability structure
- Showback/chargeback policies

### 4. Cost Allocation Policies
- How shared costs are allocated
- Tagging standards and requirements
- Required tags for resources
- Cost attribution rules

### 5. Important Business Context
- Seasonal factors affecting costs (e.g., year-end processing)
- Known planned changes (migrations, new projects)
- Business events that impact spending
- Growth patterns and expectations

## How to Use This Skill

### Step 1: Check if Context Already Retrieved
Before calling the MCP tool, check the conversation history:
- Has `get_org_context` been called already in this conversation?
- If YES: Reference the previously retrieved context
- If NO: Proceed to Step 2

### Step 2: Retrieve Organization Context
Call the CloudZero MCP server tool:

```
get_org_context()
```

This returns comprehensive organization-specific information.

### Step 3: Enrich with Internal Documentation
Search Confluence for customer-specific documentation to supplement the CloudZero context:

```
searchConfluenceUsingCql(
    cql="text ~ '[customer name]' AND type = 'page'",
    limit=10
)
```

Look for:
- Onboarding notes and architecture decisions
- Runbooks and known issue documentation
- Account mapping and team structure docs
- CostFormation configuration notes
- Historical context (migrations, incidents, special agreements)

If relevant pages are found, read the most important ones:
```
getConfluencePage(pageId="<page_id>")
```

### Step 4: Check for Open Customer Tickets
Query Jira and DevRev for active tickets related to this customer:

**Jira:**
```
searchJiraIssuesUsingJql(
    jql="project = '<project>' AND status != Done AND text ~ '[customer name]'",
    limit=10
)
```

**DevRev:**
```
hybrid_search(
    query="[customer name]",
    namespace="ticket"
)
```

Note any:
- Open support tickets or escalations
- In-progress feature requests
- Known issues affecting this customer
- Pending action items from previous engagements

This context helps inform analysis priorities and avoids duplicating known work.

### Step 5: Analyze and Internalize Context
Review the returned context to understand:
- What custom dimensions exist (e.g., teams, products, cost centers)
- What the organization's priorities are (optimization, allocation, governance)
- Any specific guidance or workflows for this organization
- Important context that affects cost interpretation
- What internal documentation exists for this customer
- What active tickets or known issues are in play

### Step 6: Make Context Available to Other Skills
Store key insights from organization context for reference by subsequent skills:
- List of available custom dimensions
- Key team/product names
- Cost allocation rules
- Any special considerations

## Output Format

After retrieving organization context, provide a concise summary:

### Organization Profile
**Organization Name**: [If available]
**Primary Focus**: [Optimization / Allocation / FinOps / etc.]

### Available Custom Dimensions
- **User:Defined:Team**: [Number of teams or example values]
- **User:Defined:Product**: [Number of products or example values]
- **User:Defined:CostCenter**: [If available]
- [Other custom dimensions...]

### Internal Documentation
- [Key Confluence pages found and their relevance]
- [Architecture decisions or runbooks available]
- [Any gaps in documentation]

### Active Tickets & Known Issues
- **Open tickets**: [Count and brief summary of active Jira/DevRev tickets]
- **Escalations**: [Any active escalations]
- **Pending action items**: [Items from prior engagements]

### Key Insights
- [Important context point 1]
- [Important context point 2]
- [Special considerations]

### Recommended Analysis Approach
Based on organization context:
- [Recommended dimension to start with]
- [Preferred time periods]
- [Key stakeholders or reporting needs]
- [Any analysis priorities informed by open tickets or known issues]

## Integration with Other Skills

All other cost analysis skills should follow this pattern:

```markdown
## Prerequisites
Before using this skill, ensure organization context has been retrieved via the
[Understand CloudZero Organization](../understand-cloudzero-organization/SKILL.md) skill.

If not already done in this conversation:
1. Use the understand-cloudzero-organization skill first
2. Then proceed with this skill's analysis

If organization context was already retrieved, reference that information.
```

## Efficiency Note

**Avoid redundant calls**: Once `get_org_context` is called in a conversation,
DO NOT call it again. Other skills should reference the previously retrieved context
rather than making duplicate API calls.

## Example Usage

**User request**: "Analyze my cloud costs"

**Assistant response**:
```
I'll start by understanding your CloudZero organization context, then analyze your costs.

[Calls get_org_context]

I can see your organization uses custom dimensions for Teams and Products.
You have 8 engineering teams and 3 main products. Your cost allocation
policy requires Environment and Team tags on all resources.

Now let me analyze your top cost drivers using these dimensions...
[Proceeds with cost analysis using appropriate dimensions]
```

## When Context Changes

Re-invoke this skill if:
- Switching to analyze a different CloudZero organization
- User mentions recent changes to custom dimensions or team structure
- Analysis results seem inconsistent with expected organization structure
- Explicitly requested by user

## Best Practices

1. **Call once per conversation** - Cache the results for subsequent skills
2. **Reference, don't repeat** - Other skills should reference cached context
3. **Validate assumptions** - If analysis seems off, verify context is current
4. **Respect organization conventions** - Use their terminology and preferred dimensions
5. **Consider business context** - Factor in seasonal patterns, planned changes

## See Also

- [CloudZero Tools Reference](${CLAUDE_PLUGIN_ROOT}/references/cloudzero-tools-reference.md)
- [Dimensions Reference](${CLAUDE_PLUGIN_ROOT}/references/dimensions-reference.md)
- All other cost analysis skills depend on this foundational skill
