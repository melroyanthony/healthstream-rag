# AWS Deployment Guide — HealthStream RAG

Deploy the HealthStream RAG API to AWS Lambda + API Gateway in eu-west-1 (Ireland).
The entire demo stack costs roughly **$3 USD** and can be torn down in one command.

---

## Prerequisites

| Tool | Min version | Install |
|------|-------------|---------|
| AWS CLI | 2.x | [docs.aws.amazon.com/cli](https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html) |
| Terraform | 1.7+ | [developer.hashicorp.com/terraform](https://developer.hashicorp.com/terraform/install) |
| uv | 0.6+ | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| Docker | 24+ | [docs.docker.com/get-docker](https://docs.docker.com/get-docker/) |

Configure the AWS CLI before running anything:

```bash
aws configure
# AWS Access Key ID:     <your key>
# AWS Secret Access Key: <your secret>
# Default region name:   eu-west-1
# Default output format: json
```

Verify access:

```bash
aws sts get-caller-identity
```

---

## Step-by-Step Deployment

### 1. Clone and enter the repo

```bash
git clone https://github.com/melroyanthony/healthstream-rag.git
cd healthstream-rag
```

### 2. Initialise Terraform

```bash
cd solution/infra/terraform
terraform init
```

### 3. Review the execution plan

```bash
terraform plan -out=tfplan
```

Check the output carefully. Resources created include:
- VPC with private subnets (networking module)
- KMS key + Cognito User Pool (security module)
- S3 bucket + S3 Vectors bucket + DynamoDB tables (storage module)
- Lambda function + API Gateway HTTP API (compute module)
- CloudWatch log groups + dashboards (monitoring module)

### 4. Apply the infrastructure

```bash
terraform apply tfplan
```

Terraform will print outputs when complete:

```
api_endpoint          = "https://<id>.execute-api.eu-west-1.amazonaws.com"
cognito_user_pool_id  = "eu-west-1_XXXXXXXXX"
s3_vectors_bucket     = "healthstream-demo-vectors-<account>"
```

Save these values; you will need the `api_endpoint` later.

### 5. Package and deploy the Lambda

From the `solution/` directory:

```bash
cd solution
make deploy-lambda
```

This runs `solution/backend/scripts/package_lambda.sh` which:
1. Installs production dependencies into a temp directory via `uv`
2. Copies `app/` into the package
3. Creates `lambda-package.zip`

Then the Makefile uploads the zip to the `healthstream-demo-query` Lambda function
using `aws lambda update-function-code`.

### 6. Ingest sample data

```bash
make ingest-samples
```

This runs `scripts/ingest_samples.py` against the locally configured vector store.
For the AWS environment, set the correct environment variables first:

```bash
cd solution/backend
VECTOR_BACKEND=s3vectors \
S3_VECTORS_BUCKET=<bucket-from-step-4> \
AWS_REGION=eu-west-1 \
MOCK_AUTH=true \
uv run python scripts/ingest_samples.py
```

### 7. Verify the deployment

Check the Lambda is healthy:

```bash
aws lambda invoke \
  --function-name healthstream-demo-query \
  --payload '{"rawPath":"/health","requestContext":{"http":{"method":"GET"}},"headers":{}}' \
  --cli-binary-format raw-in-base64-out \
  response.json && cat response.json
```

Or hit the API Gateway endpoint directly (replace with your endpoint):

```bash
curl -s https://<id>.execute-api.eu-west-1.amazonaws.com/health | python3 -m json.tool
```

Expected response:

```json
{"status": "ok"}
```

---

## Cost Estimate (demo tier, ~30 days)

| Resource | Config | Est. monthly cost |
|----------|--------|-------------------|
| Lambda | 1 024 MB, 30 s timeout, 1 000 invocations/month | < $0.01 |
| API Gateway HTTP API | 1 000 requests/month | < $0.01 |
| S3 Vectors bucket | < 1 GB stored | ~$0.02 |
| S3 documents bucket | < 100 MB | ~$0.01 |
| DynamoDB (on-demand) | < 1 000 read/write units | ~$0.01 |
| CloudWatch logs | < 1 GB ingested | ~$0.50 |
| KMS key | 1 key, minimal API calls | ~$1.00 |
| VPC NAT Gateway | 1 AZ, minimal data | ~$1.50 |
| **Total** | | **~$3.05** |

> NAT Gateway dominates the cost. For a zero-spend demo you can remove VPC config
> from the Lambda and rely on public endpoints, but this requires a security review.

---

## Teardown

```bash
cd solution/infra/terraform
terraform destroy
```

Terraform will list all resources to be destroyed and ask for confirmation.
Type `yes` to proceed.

Note: S3 buckets with objects will fail to destroy unless emptied first:

```bash
aws s3 rm s3://<bucket-name> --recursive
terraform destroy
```

---

## Troubleshooting

### `terraform init` fails with provider error

Ensure you are on Terraform >= 1.7:

```bash
terraform version
```

If behind a proxy, set `HTTP_PROXY` / `HTTPS_PROXY` before running init.

### Lambda deploy fails with "NoCredentialsError"

Run `aws configure` or export credentials:

```bash
export AWS_ACCESS_KEY_ID=...
export AWS_SECRET_ACCESS_KEY=...
export AWS_DEFAULT_REGION=eu-west-1
```

### Lambda returns 502 from API Gateway

Check the CloudWatch log group `/aws/lambda/healthstream-demo-query`:

```bash
aws logs tail /aws/lambda/healthstream-demo-query --follow
```

Common causes:
- Missing environment variable (`VECTOR_BACKEND`, `S3_VECTORS_BUCKET`)
- Lambda cold start exceeded the 30-second timeout — increase `lambda_timeout` in `main.tf`
- VPC misconfiguration — confirm the Lambda's security group allows outbound HTTPS (443)

### S3 Vectors bucket not available

S3 Vectors reached GA in December 2025 and is available in eu-west-1.
If you see `UnknownServiceError`, upgrade the AWS CLI:

```bash
aws --version   # must be >= 2.22
# Install/upgrade AWS CLI v2: https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html
# Do NOT use `pip install awscli` — that installs v1
```

### `make deploy-lambda` zip is too large (> 50 MB)

The Lambda direct-upload limit is 50 MB. Upload via S3 instead:

```bash
aws s3 cp solution/backend/lambda-package.zip s3://<deployment-bucket>/lambda-package.zip
aws lambda update-function-code \
  --function-name healthstream-demo-query \
  --s3-bucket <deployment-bucket> \
  --s3-key lambda-package.zip \
  --region eu-west-1
```

### Ingest script reports 0 documents

Ensure `data/sample_data.json` is present:

```bash
ls solution/backend/data/sample_data.json
```

If missing, regenerate it or copy from the `data/` directory in the repo root.
