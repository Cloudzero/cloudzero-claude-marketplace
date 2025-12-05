# CloudZero Cost Types Reference

## Quick Selection Guide

**Default choice**: Use `real_cost` - Most commonly used and appropriate for general cost analysis and engineering discussions.

**For invoice reconciliation**: Use `billed_cost`

**For understanding savings**: Use `on_demand_cost` (compare with actual costs)

**For detailed cost allocation/showback**: Use `discounted_amortized_cost`

**For usage trends (not cost)**: Use `usage_amount`

**When user mentions "actual" or "real" costs**: Use `real_cost`

**When user mentions "invoice" or "billing statement"**: Use `billed_cost`

---

## All Cost Types Explained

### 1. Billed Cost (`billed_cost`)

**What it is**: The exact prices that appear on your cloud provider invoice.

**How it's calculated**: Includes all discounts, Reserved Instance (RI), and Savings Plan (SP) charges as separate line items, exactly as they appear on the invoice.

**When to use**:
- Reconciling CloudZero data with invoices
- Financial reporting that must match billing statements
- When you need to see discounts and commitment purchases as separate line items

**Best for**: Finance teams, billing reconciliation

---

### 2. Discounted Cost (`discounted_cost`)

**What it is**: Similar to Billed Cost, but with discounts allocated directly to the resources that benefit from them.

**How it's calculated**: Incorporates EDP Discounts, Private Rate Discounts, and RI Volume Discounts directly into resource charges, rather than showing them separately.

**When to use**:
- Understanding net costs after standard discounts
- When you want discounts attributed to specific resources
- Comparing pre-discount vs. post-discount costs

**Best for**: Cost analysis with discount attribution

---

### 3. Amortized Cost (`amortized_cost`)

**What it is**: Distributes Reserved Instance and Savings Plan upfront and recurring charges across the applicable resources based on their usage.

**How it's calculated**: Starts with Billed Cost, then amortizes RI/SP commitments across resources that use them.

**When to use**:
- Understanding the effective hourly/daily rate of committed resources
- Spreading one-time RI/SP payments across their usage period
- When you need amortization but want to keep original pricing (without discount adjustments)

**Best for**: Understanding commitment cost distribution without discount normalization

---

### 4. Discounted Amortized Cost (`discounted_amortized_cost`)

**What it is**: Combines discount attribution with amortization of RI/SP commitments.

**How it's calculated**: Starts with Discounted Cost, then amortizes RI and Savings Plan charges to show the effective reduced rates across applicable resources.

**When to use**:
- Analyzing true consumption costs with commitment benefits included
- Comparing costs across resources with different commitment types
- Most accurate representation of per-resource effective costs

**Best for**: Detailed cost analysis, budget allocation, showback/chargeback

---

### 5. Real Cost (`real_cost`) - **DEFAULT RECOMMENDED**

**What it is**: Consumption-focused cost that filters Discounted Amortized Cost to show only charges directly related to resource usage.

**How it's calculated**: Starts with Discounted Amortized Cost, then excludes:
- Taxes
- Support charges
- Unused RI/SP capacity costs

Includes GCP committed use discounts.

**When to use**:
- Engineering-focused cost analysis
- Analyzing consumption trends and patterns
- Optimization discussions (shows actual resource usage costs)
- **This is the default view in CloudZero Explorer**

**Best for**: Engineering teams, optimization analysis, day-to-day cost monitoring

---

### 6. On-Demand Cost (`on_demand_cost`)

**What it is**: Hypothetical cost if all resources were priced at public on-demand rates (no discounts, RIs, or Savings Plans).

**How it's calculated**: Uses public on-demand pricing for resources; falls back to Billed Cost for items without on-demand equivalents.

**When to use**:
- Calculating effective savings rates from commitments and discounts
- Understanding potential costs without optimization
- Benchmarking savings across teams or projects

**Limitations**: Not available for Azure resources

**Best for**: Savings analysis, ROI calculations for commitments

**Example Calculation**:
```
On-Demand Cost: $10,000
Real Cost: $7,500
Effective Savings: ($10,000 - $7,500) / $10,000 = 25%
```

---

### 7. Invoiced Amortized Cost (`invoiced_amortized_cost`)

**What it is**: Similar to Discounted Amortized Cost but only amortizes the recurring portion of RI/SP charges, keeping upfront payments as separate line items.

**How it's calculated**: Treats upfront portions of commitments as distinct charges; amortizes only the recurring monthly fees.

**When to use**:
- AWS billing periods where upfront charges must remain distinct
- Specific financial reporting requirements that separate one-time vs. recurring costs

**Best for**: Specialized financial reporting scenarios

---

### 8. Custom Cost (`custom_cost`)

**What it is**: Organization-specific cost calculations defined through CloudZero's custom cost configuration.

**When to use**:
- When you have configured custom cost calculations in CloudZero
- Applying organization-specific pricing models or allocation rules

**Best for**: Advanced users with custom cost models configured

---

### 9. Usage Amount (`usage_amount`)

**What it is**: Quantity metrics instead of cost (e.g., GB-hours, compute-hours).

**When to use**:
- Analyzing resource consumption independent of pricing
- Tracking usage trends without cost fluctuations
- Capacity planning

**Best for**: Usage analysis, capacity planning

**Note**: This is not a cost metric but a usage metric.

---

## Cost Type Comparison Matrix

| Cost Type | Includes Discounts | Amortizes RI/SP | Excludes Non-Usage | Use Case |
|-----------|-------------------|-----------------|-------------------|----------|
| `billed_cost` | Separate line items | No | No | Invoice reconciliation |
| `discounted_cost` | Yes | No | No | Discount attribution |
| `amortized_cost` | Separate line items | Yes | No | RI/SP distribution |
| `discounted_amortized_cost` | Yes | Yes | No | Detailed allocation |
| `real_cost` ✅ | Yes | Yes | Yes | Engineering analysis (DEFAULT) |
| `on_demand_cost` | No | No | No | Savings calculation |
| `invoiced_amortized_cost` | Yes | Partial | No | Specialized reporting |
| `custom_cost` | Varies | Varies | Varies | Custom models |
| `usage_amount` | N/A (usage metric) | N/A | N/A | Capacity planning |

---

## Common Scenarios

### Scenario 1: Monthly Cost Review with Engineering Team
**Use**: `real_cost`
**Why**: Shows actual consumption costs, excludes support/taxes, includes commitment benefits

### Scenario 2: Reconciling with AWS Invoice
**Use**: `billed_cost`
**Why**: Matches invoice line-by-line

### Scenario 3: Calculating ROI of Reserved Instances
**Use**: Both `on_demand_cost` and `real_cost`
**Why**: Compare to calculate effective savings

### Scenario 4: Showback/Chargeback to Teams
**Use**: `discounted_amortized_cost` or `real_cost`
**Why**: Accurately attributes costs including commitment benefits

### Scenario 5: Understanding RI Coverage
**Use**: `amortized_cost`
**Why**: Shows how RI benefits are distributed

### Scenario 6: Capacity Planning
**Use**: `usage_amount`
**Why**: Track usage independent of pricing

---

## Cost Type Selection Flowchart

```
START: What's your goal?
│
├─ Reconcile with invoice?
│  └─> Use billed_cost
│
├─ Engineering optimization?
│  └─> Use real_cost (DEFAULT)
│
├─ Calculate savings from RIs/SPs?
│  └─> Use on_demand_cost + real_cost
│
├─ Team showback/chargeback?
│  └─> Use discounted_amortized_cost or real_cost
│
├─ Understand RI/SP distribution?
│  └─> Use amortized_cost
│
└─ Capacity planning (not cost)?
   └─> Use usage_amount
```

---

## Important Considerations

### Comparing Cost Types

**Same Resource, Different Cost Types:**
- On-Demand Cost: $100/hour (public pricing)
- Billed Cost: $70/hour (with RI, shown as RI charge + usage)
- Amortized Cost: $70/hour (RI charge distributed to usage)
- Real Cost: $70/hour (consumption focus, excludes support)
- Discounted Amortized Cost: $65/hour (with additional EDP discount)

### When to Mix Cost Types

**DON'T mix cost types in the same analysis** unless explicitly comparing them:
- ❌ Compare Service A's `real_cost` to Service B's `billed_cost`
- ✅ Compare Service A's `real_cost` to Service B's `real_cost`
- ✅ Compare a service's `real_cost` to its `on_demand_cost` for savings analysis

### Default Behavior

If you don't specify `cost_type` in `get_cost_data`, it defaults to `real_cost`.

---

## Advanced Usage

### Calculating Effective Savings Rate

```
on_demand = get_cost_data(cost_type="on_demand_cost")
real = get_cost_data(cost_type="real_cost")

savings_rate = (on_demand - real) / on_demand * 100
```

### Comparing Commitment Impact

```
# Without commitments
amortized = get_cost_data(cost_type="amortized_cost")

# With commitments distributed
discounted_amortized = get_cost_data(cost_type="discounted_amortized_cost")

commitment_benefit = amortized - discounted_amortized
```

---

## See Also

- [CloudZero Tools Reference](${CLAUDE_PLUGIN_ROOT}/references/cloudzero-tools-reference.md)
- [Best Practices](${CLAUDE_PLUGIN_ROOT}/references/best-practices.md)
- [Dimensions Reference](${CLAUDE_PLUGIN_ROOT}/references/dimensions-reference.md)
