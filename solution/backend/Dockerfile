# HealthStream RAG — Multi-stage Dockerfile
#
# Targets:
#   local  — FastAPI dev server with ChromaDB, sentence-transformers, Anthropic
#   lambda — AWS Lambda container with Bedrock, S3 Vectors (no heavy local deps)
#
# Build:
#   docker build --target local  -t healthstream-rag:local .
#   docker build --target lambda -t healthstream-rag:lambda --platform linux/arm64 .

# ============================================================================
# Stage: base — shared tooling and project metadata (uv + pyproject + lockfile)
# ============================================================================
FROM python:3.13-slim AS base

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:0.6.14 /uv /usr/local/bin/uv

COPY pyproject.toml uv.lock ./

# ============================================================================
# Stage: local — full dev environment (ChromaDB + sentence-transformers + Anthropic)
# ============================================================================
FROM base AS local

# Install core + local group deps (chromadb, sentence-transformers, anthropic)
RUN uv sync --no-dev --group local --no-install-project

COPY app/ app/
COPY data/ data/
COPY scripts/ scripts/

EXPOSE 8000

CMD ["uv", "run", "--no-sync", "uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8000"]

# ============================================================================
# Stage: lambda-deps — production deps only (no local group)
# ============================================================================
FROM public.ecr.aws/lambda/python:3.13 AS lambda-deps

COPY --from=ghcr.io/astral-sh/uv:0.6.14 /uv /usr/local/bin/uv

COPY pyproject.toml uv.lock ./

# Export core-only requirements and install to LAMBDA_TASK_ROOT
# This overrides Lambda runtime's bundled boto3 (which lacks s3vectors)
RUN uv export --no-group local --no-group dev --no-hashes > /tmp/requirements.txt && \
    pip install --no-cache-dir --target ${LAMBDA_TASK_ROOT} -r /tmp/requirements.txt && \
    rm /tmp/requirements.txt /usr/local/bin/uv

# ============================================================================
# Stage: lambda — production Lambda container (arm64)
# ============================================================================
FROM lambda-deps AS lambda

COPY app/ ${LAMBDA_TASK_ROOT}/app/

ENV PYTHONPATH=${LAMBDA_TASK_ROOT}

CMD ["app.api.lambda_handler.handler"]
