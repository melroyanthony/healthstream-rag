# HealthStream RAG — Developer & Deployment Makefile
# Region: eu-west-1 | Runtime: Python 3.13 | Package manager: uv
#
# Run from: solution/ directory (where this Makefile lives)
#
# Usage:
#   make dev             Start local dev server (port 8000)
#   make test            Run the test suite with mock auth
#   make lint            Lint app/ and tests/ with ruff
#   make docker-up       Build and start Docker Compose stack
#   make docker-down     Stop Docker Compose stack
#   make deploy          Build + push + update Lambda (one command)
#   make ecr-cleanup     Remove old ECR image tags
#   make ingest-samples  Ingest sample data into the vector store
#   make eval            Run the RAG evaluation script
#   make demo            Run the full AWS demo script

BACKEND_DIR := backend
INFRA_DIR   := infra/terraform
AWS_REGION  := eu-west-1
AWS_ACCOUNT  := $(shell aws sts get-caller-identity --query Account --output text 2>/dev/null)
ECR_REGISTRY := $(if $(AWS_ACCOUNT),$(AWS_ACCOUNT).dkr.ecr.$(AWS_REGION).amazonaws.com,$(error AWS_ACCOUNT is empty — AWS credentials not configured. Run 'aws configure' first))
ECR_REPO     := $(ECR_REGISTRY)/healthstream-rag
LAMBDA_FUNC  := healthstream-demo-query
VERSION     := $(shell date +%Y%m%d-%H%M%S)

.PHONY: dev test lint docker-up docker-down deploy ecr-login ecr-cleanup ingest-samples eval demo terraform-apply

# ---------------------------------------------------------------------------
# Local development
# ---------------------------------------------------------------------------

dev:
	cd $(BACKEND_DIR) && uv run uvicorn app.api.main:app --reload --port 8000

test:
	cd $(BACKEND_DIR) && MOCK_AUTH=true uv run pytest tests/ -v

lint:
	cd $(BACKEND_DIR) && uv run ruff check app/ tests/

# ---------------------------------------------------------------------------
# Docker
# ---------------------------------------------------------------------------

docker-up:
	docker compose up --build -d

docker-down:
	docker compose down

# ---------------------------------------------------------------------------
# AWS Lambda deployment (one command: build → push → deploy)
# ---------------------------------------------------------------------------

ecr-login:
	@aws ecr get-login-password --region $(AWS_REGION) | \
		docker login --username AWS --password-stdin $(ECR_REGISTRY) 2>/dev/null

## Full deploy: build container → push to ECR → update Lambda
deploy: ecr-login
	@echo "==> Building Lambda container ($(VERSION))..."
	docker build --platform linux/arm64 --provenance=false --no-cache \
		--target lambda \
		-t healthstream-rag-lambda:$(VERSION) \
		$(BACKEND_DIR)
	@echo "==> Pushing to ECR..."
	docker tag healthstream-rag-lambda:$(VERSION) $(ECR_REPO):$(VERSION)
	docker tag healthstream-rag-lambda:$(VERSION) $(ECR_REPO):latest
	docker push $(ECR_REPO):$(VERSION)
	docker push $(ECR_REPO):latest
	@echo "==> Updating Lambda function..."
	aws lambda update-function-code \
		--function-name $(LAMBDA_FUNC) \
		--image-uri $(ECR_REPO):$(VERSION) \
		--region $(AWS_REGION) --no-cli-pager | grep -E "CodeSha256|State"
	@echo "==> Waiting for Lambda to be ready..."
	aws lambda wait function-updated --function-name $(LAMBDA_FUNC) --region $(AWS_REGION)
	@echo "==> Deploy complete: $(VERSION)"

## Remove old ECR images (keep latest 3)
ecr-cleanup:
	@echo "==> Cleaning old ECR images (keeping latest 3)..."
	@aws ecr describe-images --repository-name healthstream-rag --region $(AWS_REGION) \
		--query 'sort_by(imageDetails,& imagePushedAt)[:-3].[imageDigest]' --output text 2>/dev/null | \
		while read digest; do \
			if [ -n "$$digest" ]; then \
				aws ecr batch-delete-image --repository-name healthstream-rag \
					--image-ids imageDigest=$$digest --region $(AWS_REGION) --no-cli-pager > /dev/null 2>&1; \
				echo "  Deleted: $$digest"; \
			fi; \
		done
	@echo "==> ECR cleanup done"

## Apply Terraform infrastructure changes
terraform-apply:
	cd $(INFRA_DIR) && terraform init -input=false && \
		terraform plan -var="ecr_image_uri=$(ECR_REPO)" -out=healthstream.plan && \
		terraform apply healthstream.plan

# ---------------------------------------------------------------------------
# Data & evaluation
# ---------------------------------------------------------------------------

ingest-samples:
	cd $(BACKEND_DIR) && MOCK_AUTH=true uv run python scripts/ingest_samples.py

eval:
	cd $(BACKEND_DIR) && MOCK_AUTH=true uv run python scripts/evaluate.py

demo:
	cd $(BACKEND_DIR) && bash scripts/aws_demo.sh
