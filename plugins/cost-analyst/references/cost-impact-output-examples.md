# Output Examples

Reference for formatting cost impact analysis reports. Used during Phase 7 of the estimate-cost-impact skill.

---

## Example 1: Cost Increase (Direct IaC Change)

```markdown
## 💰 Infrastructure Cost Impact Analysis

**PR**: #342 — Upgrade production database instance
**Analyzed**: 2026-04-10
**Verdict**: ⬆️ COST INCREASE

### Summary

| Change | Service | Current Spend | Estimated Impact | Confidence |
|--------|---------|---------------|------------------|------------|
| RDS instance type `db.r6g.large` → `db.r6g.2xlarge` | Amazon RDS | $2,847/mo | +$2,847/mo | HIGH |
| New ElastiCache Redis cluster (2 nodes) | Amazon ElastiCache | $0/mo (new) | +$438/mo | MEDIUM |

**Net Estimated Impact**: +$3,285/mo (+$39,420/yr)

### Details

#### 1. RDS Instance Upgrade

**File**: `terraform/modules/database/main.tf:28`
**Change**: `instance_class = "db.r6g.large"` → `"db.r6g.2xlarge"`
**Current baseline**: $2,847/mo (30-day average from CloudZero)
**Estimated new cost**: ~$5,694/mo
**Reasoning**: Moving from 2 vCPU / 16 GB to 8 vCPU / 64 GB — approximately 2x the on-demand price. Current spend suggests this is a Multi-AZ deployment running 24/7.
**Confidence**: HIGH — direct instance class change with clear pricing ratio and solid baseline data

#### 2. New ElastiCache Redis Cluster

**File**: `terraform/modules/cache/main.tf:1-45` (new file)
**Change**: New `aws_elasticache_replication_group` with 2 `cache.r6g.large` nodes
**Current baseline**: $0/mo (new service — no existing spend)
**Estimated new cost**: ~$438/mo
**Reasoning**: 2× cache.r6g.large nodes at ~$219/mo each on-demand in us-east-1. Actual cost may be lower with Reserved Nodes.
**Confidence**: MEDIUM — new resource, estimate based on public pricing rather than observed spend

### Unchanged Files (no cost impact)

- `src/api/handlers.py` — request handler refactor
- `tests/test_database.py` — updated test fixtures
- `docs/runbook.md` — documentation update
```

---

## Example 2: Cost Decrease (Resource Removal)

```markdown
## 💰 Infrastructure Cost Impact Analysis

**Branch**: `cleanup/remove-legacy-search`
**Analyzed**: 2026-04-10
**Verdict**: ⬇️ COST DECREASE

### Summary

| Change | Service | Current Spend | Estimated Impact | Confidence |
|--------|---------|---------------|------------------|------------|
| Remove OpenSearch domain | Amazon OpenSearch Service | $1,523/mo | -$1,523/mo | HIGH |
| Remove 3 Lambda ingest functions | AWS Lambda | $89/mo | -$89/mo | HIGH |

**Net Estimated Impact**: -$1,612/mo (-$19,344/yr savings)

### Details

#### 1. OpenSearch Domain Removal

**File**: `terraform/search/main.tf` (deleted)
**Change**: Entire `aws_opensearch_domain "legacy_search"` resource removed
**Current baseline**: $1,523/mo (30-day average from CloudZero, filtered by resource tag `service=legacy-search`)
**Estimated savings**: $1,523/mo
**Reasoning**: Removing the entire domain eliminates all associated costs (instances, storage, data transfer).
**Confidence**: HIGH — baseline directly measured, full resource deletion

#### 2. Lambda Ingest Functions Removed

**File**: `terraform/search/lambdas.tf` (deleted)
**Change**: 3 Lambda functions (`search-indexer`, `search-reindexer`, `search-cleanup`) removed
**Current baseline**: $89/mo combined (30-day average)
**Estimated savings**: $89/mo
**Confidence**: HIGH — measured baseline, full resource deletion
```

---

## Example 3: No Cost Impact

```markdown
## 💰 Infrastructure Cost Impact Analysis

**PR**: #567 — Fix user profile validation bug
**Analyzed**: 2026-04-10
**Verdict**: ✅ NO COST IMPACT

No infrastructure cost impact detected. Changes are limited to application business logic and tests:

- `src/api/users.py` — validation logic fix
- `src/models/user.py` — field constraint update
- `tests/test_users.py` — new test cases
- `README.md` — usage example update
```

---

## Example 4: Mixed Impact with Indirect Changes

```markdown
## 💰 Infrastructure Cost Impact Analysis

**PR**: #891 — Add real-time analytics pipeline
**Analyzed**: 2026-04-10
**Verdict**: ⬆️ MIXED IMPACT (net increase)

### Summary

| Change | Service | Current Spend | Estimated Impact | Confidence |
|--------|---------|---------------|------------------|------------|
| New Kinesis stream (4 shards) | Amazon Kinesis | $0/mo (new) | +$224/mo | MEDIUM |
| New DynamoDB queries in API handler | Amazon DynamoDB | $342/mo | +$50–150/mo | LOW |
| Batch job schedule daily → hourly | AWS Lambda | $12/mo | +$276/mo | MEDIUM |
| Remove legacy polling cron | AWS Lambda | $34/mo | -$34/mo | HIGH |

**Net Estimated Impact**: +$516–616/mo

### Details

#### 1. New Kinesis Data Stream

**File**: `terraform/analytics/stream.tf:1-32` (new file)
**Change**: New `aws_kinesis_stream` with `shard_count = 4`
**Current baseline**: $0/mo (new service)
**Estimated new cost**: ~$224/mo ($0.015/shard-hour × 4 shards × 730 hrs + PUT payload costs)
**Confidence**: MEDIUM — shard cost is fixed, but PUT payload costs depend on actual event volume

#### 2. New DynamoDB Queries in Hot Path

**File**: `src/api/analytics.py:45-62`
**Change**: Added `dynamodb.query()` call inside `GET /api/analytics/{id}` handler
**Current baseline**: $342/mo for DynamoDB (account-wide)
**Estimated additional cost**: +$50–150/mo
**Reasoning**: This endpoint currently handles ~2M requests/day. Each request will now add 1 DynamoDB read. At on-demand pricing ($0.25/million reads), that's ~$15/mo for reads alone. However, if data size exceeds 4KB, reads may consume multiple RCUs. The range accounts for payload uncertainty.
**Confidence**: LOW — depends on request volume and item sizes. Monitor after deployment.

#### 3. Batch Job Frequency Increase

**File**: `serverless.yml:78`
**Change**: `schedule: rate(1 day)` → `rate(1 hour)`
**Current baseline**: $12/mo (1 invocation/day, ~3 min runtime, 1024 MB)
**Estimated new cost**: ~$288/mo (24× invocations)
**Reasoning**: 24× frequency increase. The function processes analytics aggregations — each invocation costs the same regardless of data volume (fixed window). Lambda cost scales linearly with invocations.
**Confidence**: MEDIUM — invocation count is predictable, but runtime may vary with data growth

#### 4. Legacy Polling Cron Removed

**File**: `serverless.yml:92-98` (block deleted)
**Change**: `analytics-legacy-poller` function and its `rate(5 minutes)` schedule removed
**Current baseline**: $34/mo
**Estimated savings**: -$34/mo
**Confidence**: HIGH — measured baseline, full resource deletion

### Notes

- DynamoDB estimate (item 2) should be validated after 1 week of production traffic
- Kinesis PUT costs will depend on actual event throughput — monitor via CloudZero
- Net impact may be lower if the new streaming pipeline replaces additional legacy batch jobs
```
