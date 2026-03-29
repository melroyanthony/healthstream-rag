# HealthStream RAG — Developer & Deployment Makefile
# Region: eu-west-1 | Runtime: Python 3.13 | Package manager: uv
#
# Run from: solution/ directory (where this Makefile lives)
#
# Usage:
#   make dev            Start local dev server (port 8000)
#   make test           Run the test suite with mock auth
#   make lint           Lint app/ and tests/ with ruff
#   make docker-up      Build and start Docker Compose stack
#   make docker-down    Stop Docker Compose stack
#   make deploy-lambda  Package and upload Lambda to AWS
#   make ingest-samples Ingest sample data into the vector store
#   make eval           Run the RAG evaluation script

BACKEND_DIR := backend
INFRA_DIR   := infra/terraform
AWS_REGION  := eu-west-1
LAMBDA_FUNC := healthstream-demo-query

.PHONY: dev test lint docker-up docker-down deploy-lambda ingest-samples eval

# ---------------------------------------------------------------------------
# Local development
# ---------------------------------------------------------------------------

## Start the FastAPI dev server with live reload on port 8000
dev:
	cd $(BACKEND_DIR) && uv run uvicorn app.api.main:app --reload --port 8000

## Run pytest with mock authentication enabled
test:
	cd $(BACKEND_DIR) && MOCK_AUTH=true uv run pytest tests/ -v

## Check code style and imports with ruff (no auto-fix)
lint:
	cd $(BACKEND_DIR) && uv run ruff check app/ tests/

# ---------------------------------------------------------------------------
# Docker
# ---------------------------------------------------------------------------

## Build images and start all services in detached mode
docker-up:
	docker compose up --build -d

## Stop and remove all Docker Compose containers
docker-down:
	docker compose down

# ---------------------------------------------------------------------------
# AWS deployment
# ---------------------------------------------------------------------------

## Package the Lambda zip then upload it to the deployed function
deploy-lambda:
	cd $(BACKEND_DIR) && bash scripts/package_lambda.sh
	aws lambda update-function-code \
		--function-name $(LAMBDA_FUNC) \
		--zip-file fileb://$(BACKEND_DIR)/lambda-package.zip \
		--region $(AWS_REGION)

## Ingest sample health documents into the vector store (mock auth)
ingest-samples:
	cd $(BACKEND_DIR) && MOCK_AUTH=true uv run python scripts/ingest_samples.py

## Run the offline RAG evaluation script (mock auth)
eval:
	cd $(BACKEND_DIR) && MOCK_AUTH=true uv run python scripts/evaluate.py
