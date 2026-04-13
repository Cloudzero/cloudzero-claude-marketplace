# Cost Projection Output Examples

Reference for formatting infrastructure cost projection reports. Used during Phase 7 of the cost-projection skill.

---

## Example 1: Terraform Module — Full Stack

```markdown
## 💰 Infrastructure Cost Projection

**Source**: `terraform/production/`
**Framework**: Terraform
**Analyzed**: 2026-04-10
**Resources**: 12 total (5 existing, 7 new)

### Cost Summary

| Category | Monthly Estimate | Confidence | Notes |
|----------|-----------------|------------|-------|
| Compute | $1,089 | HIGH | 3 EC2 instances, 2 Lambda functions |
| Database | $2,157 | HIGH | 1 RDS cluster (Multi-AZ), 1 ElastiCache |
| Storage | $74 | MEDIUM | 300GB EBS + S3 (depends on data volume) |
| Messaging | $25 | LOW | 1 SQS queue, 1 SNS topic |
| Networking | $82 | HIGH | 1 ALB + 1 NAT Gateway |
| **Total** | **$3,427/mo** | | **$41,124/yr** |

Existing infrastructure (from CloudZero): $2,157/mo
New infrastructure (estimated): $1,270/mo

### Line Items

| # | Resource | Type | Configuration | Monthly Est. | Source | Confidence |
|---|----------|------|---------------|-------------|--------|------------|
| 1 | production-db | RDS PostgreSQL | db.r6g.xlarge, Multi-AZ, 200GB gp3 | $1,719 | CloudZero | HIGH |
| 2 | app-cache | ElastiCache Redis | cache.r6g.large × 2 nodes | $438 | CloudZero | HIGH |
| 3 | api-server (×3) | EC2 Instance | t3.xlarge | $363 | Estimate | HIGH |
| 4 | batch-processor | Lambda | 1024MB, rate(1 hour) | $52 | Estimate | MEDIUM |
| 5 | event-handler | Lambda | 512MB, SQS trigger | $24 | Estimate | LOW |
| 6 | api-lb | ALB | 1 listener, 3 targets | $49 | Estimate | HIGH |
| 7 | vpc-nat | NAT Gateway | Single AZ | $33 | Estimate | HIGH |
| 8 | app-storage (×3) | EBS Volume | 100GB gp3 | $24 | Estimate | HIGH |
| 9 | data-bucket | S3 Bucket | Standard tier | $50 | Estimate | LOW |
| 10 | order-queue | SQS Queue | Standard | $15 | Estimate | LOW |
| 11 | alert-topic | SNS Topic | Standard | $10 | Estimate | LOW |
| 12 | logs | CloudWatch Logs | 3 log groups | $650 | CloudZero | MEDIUM |

### Details

#### Compute — $1,089/mo

**api-server** (EC2 Instance × 3)
- Instance type: `t3.xlarge` (4 vCPU, 16 GB)
- Count: 3 (from `count = var.api_server_count`, default = 3)
- Estimated cost: ~$121/mo × 3 = $363/mo
- Source: Configuration estimate (new resource)
- Confidence: HIGH — fixed instance type, known count

**batch-processor** (Lambda Function)
- Memory: 1024 MB, Timeout: 300s
- Trigger: `rate(1 hour)` = 730 invocations/mo
- Estimated duration: ~60s per invocation (based on timeout/3 heuristic)
- Estimated cost: ~$52/mo (730 inv × 60s × 1024MB)
- Source: Configuration estimate
- Confidence: MEDIUM — invocation count is known, but actual duration varies

**event-handler** (Lambda Function)
- Memory: 512 MB, Timeout: 30s
- Trigger: SQS queue
- Estimated cost: ~$24/mo (assumes moderate message volume)
- Source: Configuration estimate
- Confidence: LOW — cost depends entirely on SQS message volume

#### Database — $2,157/mo

**production-db** (RDS PostgreSQL)
- Instance class: `db.r6g.xlarge` (4 vCPU, 32 GB)
- Multi-AZ: enabled (2× instance cost)
- Storage: 200GB gp3
- Current spend: $1,719/mo (30-day average from CloudZero)
- Source: CloudZero actual spend
- Confidence: HIGH — directly measured

**app-cache** (ElastiCache Redis)
- Node type: `cache.r6g.large`
- Nodes: 2 (replication group with automatic failover)
- Current spend: $438/mo (30-day average from CloudZero)
- Source: CloudZero actual spend
- Confidence: HIGH — directly measured

### Assumptions & Caveats

- EC2 estimates use US East (N. Virginia) on-demand pricing
- Reserved Instances or Savings Plans could reduce compute costs by 30-60%
- S3 cost ($50/mo) assumes ~2TB stored data at Standard tier — actual depends on data growth
- SQS/SNS costs assume moderate traffic (~1M messages/mo) — actual depends on application load
- Data transfer costs not included (typically 5-15% of compute)
- CloudWatch Logs cost may decrease if log retention policies are shortened

### Optimization Opportunities

- **EC2 → Graviton**: `t3.xlarge` → `t4g.xlarge` would save ~20% ($72/mo)
- **RDS Reserved Instance**: 1-year RI on the production database would save ~35% (~$600/mo)
- **NAT Gateway**: Consider VPC endpoints for S3/DynamoDB to reduce NAT data processing costs
```

---

## Example 2: SAM Template — Serverless Application

```markdown
## 💰 Infrastructure Cost Projection

**Source**: `template.yaml`
**Framework**: SAM (Serverless Application Model)
**Analyzed**: 2026-04-10
**Resources**: 8 total (0 existing, 8 new)

### Cost Summary

| Category | Monthly Estimate | Confidence | Notes |
|----------|-----------------|------------|-------|
| Compute | $35–85 | MEDIUM | 3 Lambda functions (traffic-dependent) |
| Database | $25–100 | LOW | 1 DynamoDB table (on-demand) |
| Messaging | $12 | MEDIUM | 1 Kinesis stream (4 shards) |
| Networking | $4–15 | LOW | API Gateway (request-dependent) |
| **Total** | **$76–212/mo** | | **$912–2,544/yr** |

All resources are new — no existing CloudZero spend data.

### Line Items

| # | Resource | Type | Configuration | Monthly Est. | Source | Confidence |
|---|----------|------|---------------|-------------|--------|------------|
| 1 | ProcessOrders | Lambda | 1024MB, API + SQS triggers | $15–40 | Estimate | LOW |
| 2 | GetOrder | Lambda | 256MB, API trigger | $5–15 | Estimate | LOW |
| 3 | AnalyticsIngest | Lambda | 512MB, Kinesis trigger | $15–30 | Estimate | MEDIUM |
| 4 | AnalyticsTable | DynamoDB | PAY_PER_REQUEST | $25–100 | Estimate | LOW |
| 5 | AnalyticsStream | Kinesis | 4 shards, PROVISIONED | $12 | Estimate | HIGH |
| 6 | OrderQueue | SQS | Standard | $1–5 | Estimate | LOW |
| 7 | OrderDLQ | SQS | Standard | <$1 | Estimate | HIGH |
| 8 | ServerlessApi | API Gateway | REST API | $4–15 | Estimate | LOW |

### Details

#### Compute — $35–85/mo

**ProcessOrders** (Lambda)
- Memory: 1024 MB, Timeout: 120s, Provisioned Concurrency: 5
- Triggers: API Gateway POST + SQS queue (batch size 10)
- Provisioned concurrency fixed cost: ~$10/mo (5 × $0.015/GB-hour × 730 hours × 1GB)
- Invocation cost: depends on order volume
- Estimated: $15–40/mo
- Confidence: LOW — provisioned concurrency is fixed, but invocation volume unknown

**AnalyticsIngest** (Lambda)
- Memory: 512 MB, Timeout: 60s
- Trigger: Kinesis stream (batch size 100, parallelization factor not set)
- With 4 Kinesis shards: ~4 concurrent invocations
- Estimated: $15–30/mo
- Confidence: MEDIUM — shard count constrains invocation rate

#### Database — $25–100/mo

**AnalyticsTable** (DynamoDB)
- Billing: PAY_PER_REQUEST (on-demand)
- Key schema: pk (HASH) + sk (RANGE)
- Cost is entirely usage-dependent: $1.25/million writes, $0.25/million reads
- Estimated: $25–100/mo (assumes moderate analytics volume)
- Confidence: LOW — no way to estimate without traffic projections

#### Messaging — $12/mo

**AnalyticsStream** (Kinesis)
- Mode: PROVISIONED, 4 shards
- Fixed cost: 4 × $0.015/shard-hour × 730 = $43.80/mo for shard hours
- PUT costs depend on event volume
- Wait — correcting: $0.015/shard-hour × 4 shards × 730 hours = $43.80/mo
- Confidence: HIGH — shard cost is fixed

### Assumptions & Caveats

- All Lambda estimates assume moderate traffic (10K–100K invocations/day)
- DynamoDB on-demand pricing makes cost highly variable — consider switching to provisioned if traffic is predictable
- API Gateway REST API: $3.50/million requests — estimate assumes 100K–500K requests/mo
- Kinesis PUT payload costs not included (depends on event size and volume)
- This is a new stack with no CloudZero history — all estimates are configuration-based

### Optimization Opportunities

- **DynamoDB**: If traffic patterns are predictable, provisioned capacity mode could save 50%+
- **Lambda memory**: Run Lambda Power Tuning to find optimal memory/cost balance for each function
- **Kinesis**: If event volume is low, consider reducing to 2 shards (saves ~$22/mo)
- **API Gateway**: HTTP API ($1.00/million) vs REST API ($3.50/million) — if no REST-specific features needed, HTTP is 70% cheaper
```

---

## Example 3: CDK Stack — Minimal

```markdown
## 💰 Infrastructure Cost Projection

**Source**: `lib/api-stack.ts`
**Framework**: AWS CDK (TypeScript)
**Analyzed**: 2026-04-10
**Resources**: 3 total (0 existing, 3 new)

### Cost Summary

| Category | Monthly Estimate | Confidence | Notes |
|----------|-----------------|------------|-------|
| Compute | $33 | HIGH | 1 Fargate service (0.5 vCPU, 1GB) |
| Networking | $16 | HIGH | 1 ALB |
| Storage | <$1 | LOW | ECR image storage |
| **Total** | **~$49/mo** | | **~$588/yr** |

### Line Items

| # | Resource | Type | Configuration | Monthly Est. | Source | Confidence |
|---|----------|------|---------------|-------------|--------|------------|
| 1 | ApiService | Fargate Service | 0.5 vCPU, 1GB, desiredCount: 2 | $33 | Estimate | HIGH |
| 2 | ApiLB | ALB | Created by ApplicationLoadBalancedFargateService | $16 | Estimate | HIGH |
| 3 | ApiRepo | ECR Repository | Image storage | <$1 | Estimate | LOW |

### Assumptions & Caveats

- Fargate pricing: $0.04048/vCPU-hour + $0.004445/GB-hour
- 2 tasks × (0.5 vCPU × $0.04048 + 1GB × $0.004445) × 730 hours = $33/mo
- ALB: $0.0225/hour fixed ≈ $16.43/mo (LCU costs depend on traffic)
- Data transfer not included
```
