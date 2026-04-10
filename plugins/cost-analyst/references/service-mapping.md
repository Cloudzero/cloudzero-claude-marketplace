# Service Mapping: Diff Patterns → CloudZero Dimensions

Reference for translating infrastructure changes detected in diffs to CloudZero MCP queries.

---

## AWS Service Mapping

Maps Terraform resource types, CDK constructs, and CloudFormation types to CloudZero `CZ:Service` dimension values.

### Compute

| IaC Pattern | CZ:Service Value |
|-------------|-----------------|
| `aws_instance`, `aws_ec2_*`, `AWS::EC2::Instance`, `ec2.Instance` | `AmazonEC2` |
| `aws_lambda_function`, `aws_lambda_*`, `AWS::Lambda::Function`, `AWS::Serverless::Function`, `lambda.Function` | `AWS Lambda` |
| `aws_ecs_*`, `aws_ecs_service`, `aws_ecs_task_definition`, `AWS::ECS::*` | `Amazon Elastic Container Service` |
| `aws_eks_*`, `AWS::EKS::*` | `Amazon Elastic Kubernetes Service` |
| `aws_batch_*`, `AWS::Batch::*` | `AWS Batch` |
| `aws_lightsail_*` | `Amazon Lightsail` |

### Database

| IaC Pattern | CZ:Service Value |
|-------------|-----------------|
| `aws_db_instance`, `aws_rds_*`, `aws_db_*`, `AWS::RDS::*`, `rds.DatabaseInstance`, `rds.DatabaseCluster` | `Amazon Relational Database Service` |
| `aws_dynamodb_table`, `aws_dynamodb_*`, `AWS::DynamoDB::*`, `dynamodb.Table` | `Amazon DynamoDB` |
| `aws_elasticache_*`, `AWS::ElastiCache::*` | `Amazon ElastiCache` |
| `aws_redshift_*`, `AWS::Redshift::*` | `Amazon Redshift` |
| `aws_neptune_*`, `AWS::Neptune::*` | `Amazon Neptune` |
| `aws_docdb_*`, `AWS::DocDB::*` | `Amazon DocumentDB (with MongoDB compatibility)` |

### Storage

| IaC Pattern | CZ:Service Value |
|-------------|-----------------|
| `aws_s3_bucket`, `aws_s3_*`, `AWS::S3::*`, `s3.Bucket` | `Amazon Simple Storage Service` |
| `aws_ebs_volume`, `aws_ebs_*` | `AmazonEC2` (EBS is billed under EC2) |
| `aws_efs_*`, `AWS::EFS::*` | `Amazon Elastic File System` |
| `aws_fsx_*` | `Amazon FSx` |

### Messaging & Streaming

| IaC Pattern | CZ:Service Value |
|-------------|-----------------|
| `aws_sqs_queue`, `aws_sqs_*`, `AWS::SQS::*`, `sqs.Queue` | `Amazon Simple Queue Service` |
| `aws_sns_topic`, `aws_sns_*`, `AWS::SNS::*`, `sns.Topic` | `Amazon Simple Notification Service` |
| `aws_kinesis_stream`, `aws_kinesis_*`, `AWS::Kinesis::*` | `Amazon Kinesis` |
| `aws_msk_*`, `AWS::MSK::*` | `Amazon Managed Streaming for Apache Kafka` |

### Networking & CDN

| IaC Pattern | CZ:Service Value |
|-------------|-----------------|
| `aws_lb`, `aws_alb`, `aws_elb`, `aws_lb_*`, `AWS::ElasticLoadBalancingV2::*` | `Elastic Load Balancing` |
| `aws_cloudfront_distribution`, `AWS::CloudFront::*` | `Amazon CloudFront` |
| `aws_nat_gateway`, `AWS::EC2::NatGateway` | `AmazonEC2` (NAT gw billed under EC2/VPC) |
| `aws_vpc_endpoint` | `AmazonEC2` (VPC endpoints billed under EC2) |
| `aws_api_gateway_*`, `AWS::ApiGateway::*`, `AWS::Serverless::Api` | `Amazon API Gateway` |

### Analytics & ML

| IaC Pattern | CZ:Service Value |
|-------------|-----------------|
| `aws_glue_*`, `AWS::Glue::*` | `AWS Glue` |
| `aws_athena_*` | `Amazon Athena` |
| `aws_sagemaker_*`, `AWS::SageMaker::*` | `Amazon SageMaker` |
| `aws_opensearch_*`, `aws_elasticsearch_*` | `Amazon OpenSearch Service` |

### Monitoring & Logging

| IaC Pattern | CZ:Service Value |
|-------------|-----------------|
| `aws_cloudwatch_*`, `AWS::CloudWatch::*` | `AmazonCloudWatch` |
| `aws_cloudwatch_log_group` | `AmazonCloudWatch` (Logs) |

---

## Kubernetes Dimension Mapping

For K8s workload changes, use `CZ:K8s:*` dimensions when available.

| K8s Resource | CloudZero Dimension | How to Match |
|-------------|---------------------|-------------|
| Deployment/StatefulSet | `CZ:K8s:Workload` | Match workload `metadata.name` |
| Namespace | `CZ:K8s:Namespace` | Match `metadata.namespace` |
| Cluster | `CZ:K8s:Cluster` | Match from context/config |
| Pod | `CZ:K8s:Pod` | Usually too granular — use Workload |

---

## Application Code → Service Mapping

When application code introduces new SDK usage, map to the corresponding service.

| Code Pattern | Implied CZ:Service |
|-------------|-------------------|
| `boto3.client('s3')`, `new S3Client()`, `AWS.S3()` | `Amazon Simple Storage Service` |
| `boto3.client('dynamodb')`, `new DynamoDBClient()` | `Amazon DynamoDB` |
| `boto3.client('sqs')`, `new SQSClient()` | `Amazon Simple Queue Service` |
| `boto3.client('sns')`, `new SNSClient()` | `Amazon Simple Notification Service` |
| `boto3.client('kinesis')`, `new KinesisClient()` | `Amazon Kinesis` |
| `boto3.client('lambda')`, `new LambdaClient()` | `AWS Lambda` |
| `boto3.client('ecs')`, `new ECSClient()` | `Amazon Elastic Container Service` |
| `redis.Redis()`, `redis.createClient()` | `Amazon ElastiCache` |
| `boto3.client('logs')`, `new CloudWatchLogsClient()` | `AmazonCloudWatch` |

---

## Dimension Resolution Strategy

When querying CloudZero, follow this sequence:

1. **Exact match first**: Use the `CZ:Service` value from the table above directly in `get_cost_data` filters.

2. **Fuzzy match fallback**: If no data returned, use `get_dimension_values(dimension="CZ:Service", match="<partial_name>")` to find the correct value. Use the `&` prefix for partial matching in filters (e.g., `&EC2`).

3. **Narrow with additional dimensions**: If the diff provides account context (e.g., Terraform backend config, provider alias), add `CZ:Account` filter. If resource tags are present, use `CZ:Tag:<TagName>` filters.

4. **Custom dimensions**: After calling `get_org_context()`, check if the organization has custom dimensions (e.g., `User:Defined:Team`, `User:Defined:Product`) that could narrow the query to the relevant cost allocation.

5. **K8s dimensions**: For Kubernetes changes, prefer `CZ:K8s:Namespace` + `CZ:K8s:Workload` over `CZ:Service` for more granular cost data.
