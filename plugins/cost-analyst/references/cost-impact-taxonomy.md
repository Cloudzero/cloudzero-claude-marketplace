# Cost Impact Taxonomy

Reference document for classifying code changes by their infrastructure cost impact. Used during Phase 3 of the estimate-cost-impact skill.

---

## Class 1: Direct Resource Changes

**Confidence: HIGH**

These are explicit infrastructure-as-code changes that directly provision, modify, or remove cloud resources.

### Terraform / OpenTofu

| Signal | Pattern | Impact |
|--------|---------|--------|
| New resource | `+resource "aws_*"`, `+resource "google_*"`, `+resource "azurerm_*"` | New cost line item |
| Deleted resource | `-resource "aws_*"` (entire block removed) | Cost reduction |
| Instance type change | `instance_type`, `node_type`, `instance_class`, `cache_node_type` | Pricing tier change |
| Storage size change | `allocated_storage`, `volume_size`, `disk_size_gb`, `size_in_gb` | Storage cost change |
| IOPS change | `iops`, `throughput`, `provisioned_throughput` | Performance tier cost |
| Engine/version change | `engine_version`, `engine` (e.g., Aurora vs plain RDS) | Pricing model change |
| New module | `+module "..."` | Depends on module contents — investigate |
| Multi-AZ / replication | `multi_az = true`, `replication_configuration` | ~2x cost for HA |
| Backup retention | `backup_retention_period`, `backup_window` | Storage cost for backups |

### CDK / CloudFormation / SAM

| Signal | Pattern | Impact |
|--------|---------|--------|
| New resource (CDK) | `new ec2.Instance`, `new rds.DatabaseCluster`, `new lambda.Function` | New cost line item |
| New resource (CFN) | `Type: AWS::EC2::Instance`, `Type: AWS::RDS::DBInstance` | New cost line item |
| New resource (SAM) | `Type: AWS::Serverless::Function`, `Type: AWS::Serverless::Api` | New cost line item |
| Memory/timeout (Lambda) | `MemorySize:`, `Timeout:`, `memorySize`, `timeout` | Execution cost change |
| Provisioned concurrency | `ProvisionedConcurrencyConfig`, `provisionedConcurrentExecutions` | Always-on Lambda cost |
| DynamoDB capacity | `BillingMode:`, `ProvisionedThroughput`, `ReadCapacityUnits`, `WriteCapacityUnits` | Throughput cost |
| Event source | `Events:` section in SAM, new `SQS`, `Kinesis`, `DynamoDB` triggers | Invocation volume change |

### Pulumi

| Signal | Pattern | Impact |
|--------|---------|--------|
| New resource | `new aws.ec2.Instance`, `new aws.rds.Instance` | New cost line item |
| Property changes | Same property names as Terraform (instanceType, allocatedStorage, etc.) | Same as Terraform |

---

## Class 2: Scaling Changes

**Confidence: HIGH**

Changes to horizontal or vertical scaling configuration that directly affect resource count or capacity.

### Kubernetes

| Signal | Pattern | Impact |
|--------|---------|--------|
| Replica count | `replicas:` in Deployment/StatefulSet | Linear cost scaling |
| HPA min/max | `minReplicas:`, `maxReplicas:` in HorizontalPodAutoscaler | Capacity range change |
| HPA target | `targetCPUUtilizationPercentage`, `targetMemoryUtilizationPercentage` | Scaling sensitivity |
| Resource requests | `resources.requests.cpu`, `resources.requests.memory` | Per-pod cost (scheduler guarantee) |
| Resource limits | `resources.limits.cpu`, `resources.limits.memory` | Per-pod ceiling |
| PVC size | `storage:` in PersistentVolumeClaim | Storage cost |
| Node affinity/tolerations | `nodeSelector`, `tolerations`, `affinity` | May force specific (costlier) node types |

### Auto Scaling Groups (AWS)

| Signal | Pattern | Impact |
|--------|---------|--------|
| Desired/min/max | `desired_capacity`, `min_size`, `max_size` | Instance count range |
| Instance type in launch template | `instance_type` in `aws_launch_template` | Per-instance cost |
| Mixed instances policy | `mixed_instances_policy`, `instances_distribution` | Spot vs on-demand ratio |

### Streaming / Messaging

| Signal | Pattern | Impact |
|--------|---------|--------|
| Kinesis shards | `shard_count`, `ShardCount` | Per-shard hourly cost |
| Kafka partitions | `num_partitions`, `partitions` | Broker resource usage |
| SQS FIFO | `fifo_queue = true`, `FifoQueue` | Higher per-request cost vs standard |

---

## Class 3: Indirect Application Changes

**Confidence: MEDIUM to LOW**

Application code changes that affect cloud resource usage patterns. These require reasoning about runtime behavior.

### Database Operations

| Signal | What to look for | Impact reasoning |
|--------|-----------------|------------------|
| New DynamoDB calls | `dynamodb.get_item`, `dynamodb.query`, `dynamodb.put_item`, `dynamodb.scan`, `Table.get`, `DocumentClient` | Read/write capacity consumption. `scan` is especially expensive. Check if in request handler (per-request) vs. batch job (periodic). |
| New SQL queries | New `.execute()`, `.query()`, `.raw()` calls; new ORM model methods; new SQL files | Database CPU/IO. Large joins or full table scans can trigger RDS scaling. |
| New Redis/cache calls | `redis.get`, `redis.set`, `cache.get`, `cache.put`, `@cached`, `@cache_result` | Adding cache = new ElastiCache cost, but may reduce database cost. Removing cache = increased origin load. |
| Connection pool changes | `pool_size`, `max_connections`, `maxPoolSize` | Larger pools may require larger database instances. |

### Invocation Frequency

| Signal | What to look for | Impact reasoning |
|--------|-----------------|------------------|
| Cron/schedule changes | `rate(1 day)` → `rate(1 hour)`, cron expression changes, `schedule_expression` | Multiplier effect: daily→hourly = 24x invocations. Check what the job does — if it calls AWS services, those costs multiply too. |
| Event source additions | New SNS subscription, new SQS consumer, new Kinesis consumer | New trigger = new invocation path. Volume depends on source throughput. |
| Webhook/callback additions | New HTTP endpoint handlers, new event listeners | Depends on expected call volume. |
| Retry/backoff changes | `max_retries`, `retry_count`, `backoff` | Higher retries = more invocations on failure paths. |

### New Service Dependencies

| Signal | What to look for | Impact reasoning |
|--------|-----------------|------------------|
| New SDK client init | `boto3.client('s3')`, `new S3Client()`, `AWS.SQS()`, `new KinesisClient()` | Implies new AWS service usage even if IaC isn't in this PR. The infra might be provisioned separately. |
| New HTTP client setup | Calls to external APIs, new base URLs, new API key configs | External API costs (data transfer, third-party billing). |
| New pub/sub publishing | `sns.publish`, `sqs.send_message`, `kinesis.put_record`, `kafka.produce` | Message volume → service cost. Check if in hot path. |

### Data Volume

| Signal | What to look for | Impact reasoning |
|--------|-----------------|------------------|
| New S3 operations | `s3.put_object`, `s3.upload_file`, `s3.get_object` in new code paths | Storage growth + request costs + data transfer. |
| New logging | New `logger.info/debug` in hot paths, new log groups, structured logging additions | CloudWatch Logs ingestion cost scales with volume. |
| New metrics emission | `cloudwatch.put_metric_data`, `statsd.increment`, new custom metrics | CloudWatch custom metrics cost per metric per month. |
| Data pipeline changes | New Airflow DAGs, Step Function states, Glue jobs | Execution cost per run × frequency. |

### Resource Intensity

| Signal | What to look for | Impact reasoning |
|--------|-----------------|------------------|
| Batch size changes | `batch_size`, `chunk_size`, `page_size` increases | Larger batches = more memory/CPU per invocation, but fewer invocations. Net effect varies. |
| Concurrency changes | `max_workers`, `num_threads`, `concurrency`, `parallelism` | Higher concurrency may require larger instances or more Lambda concurrent executions. |
| Memory-intensive operations | New large data loading, in-memory aggregation, ML model inference | May trigger OOM → need larger instance/Lambda memory. |

---

## Class 4: Removal / Decommission

**Confidence: HIGH (cost decrease)**

Indicators that infrastructure is being removed or scaled down.

| Signal | Pattern | Impact |
|--------|---------|--------|
| Terraform resource deletion | Entire `resource` block removed | Baseline spend → $0 |
| K8s manifest file deleted | File removed from manifests/ or helm chart | Workload cost eliminated |
| Service teardown | Entire service directory removed | All associated costs eliminated |
| Scale to zero | `replicas: 0`, `desired_capacity = 0`, `min_size = 0` | Near-zero (some fixed costs may remain) |
| Feature flag removal | Removing code behind a feature gate that provisioned resources | Depends on what the gate controlled |
| Module removal | `module` block removed from Terraform | All resources in module eliminated |

---

## Files That Are Never Cost-Relevant

Skip analysis for these file patterns entirely:

- `*.md` (documentation)
- `*.txt` (text files)
- `*test*`, `*spec*`, `*_test.*`, `*.test.*` (test files)
- `*.snap` (snapshots)
- `*.css`, `*.scss`, `*.less` (stylesheets)
- `*.html`, `*.jsx`, `*.tsx` with no backend imports (pure UI)
- `*.svg`, `*.png`, `*.jpg`, `*.gif`, `*.ico` (assets)
- `.eslintrc*`, `.prettierrc*`, `tsconfig.json` (linter/formatter config)
- `LICENSE`, `CHANGELOG*`, `CONTRIBUTING*`
- `.github/CODEOWNERS`, `.github/PULL_REQUEST_TEMPLATE*`
