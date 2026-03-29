#!/usr/bin/env bash
# package_lambda.sh — Build a deployable Lambda zip for HealthStream RAG
#
# What it does:
#   1. Creates a fresh temp directory
#   2. Installs production dependencies into it via uv (no dev extras)
#   3. Copies app/ into the package root
#   4. Zips everything into lambda-package.zip at the repo backend root
#
# Usage (from solution/backend/):
#   bash scripts/package_lambda.sh
#
# Output:
#   solution/backend/lambda-package.zip

set -euo pipefail

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
OUTPUT_ZIP="${BACKEND_DIR}/lambda-package.zip"
BUILD_DIR="$(mktemp -d)"

# Cleanup on exit (even on failure)
cleanup() { rm -rf "${BUILD_DIR}"; }
trap cleanup EXIT

echo "==> HealthStream RAG — Lambda packager"
echo "    backend : ${BACKEND_DIR}"
echo "    build   : ${BUILD_DIR}"
echo "    output  : ${OUTPUT_ZIP}"
echo ""

# ---------------------------------------------------------------------------
# Step 1: Install production dependencies into build dir
# ---------------------------------------------------------------------------
echo "==> Installing production dependencies with uv..."

cd "${BACKEND_DIR}" && uv export --no-dev --no-hashes --frozen -o "${BUILD_DIR}/requirements.txt" 2>/dev/null \
  || uv pip compile "${BACKEND_DIR}/pyproject.toml" --no-deps -o "${BUILD_DIR}/requirements.txt"
uv pip install \
  --python python3.13 \
  --target "${BUILD_DIR}" \
  -r "${BUILD_DIR}/requirements.txt"
rm -f "${BUILD_DIR}/requirements.txt"

echo "    Done."

# ---------------------------------------------------------------------------
# Step 2: Copy application source
# ---------------------------------------------------------------------------
echo "==> Copying app/ into package..."
cp -r "${BACKEND_DIR}/app" "${BUILD_DIR}/app"
echo "    Done."

# ---------------------------------------------------------------------------
# Step 3: Remove unnecessary files to keep the zip small
# ---------------------------------------------------------------------------
echo "==> Cleaning up cache and dist-info files..."
find "${BUILD_DIR}" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find "${BUILD_DIR}" -type d -name "*.dist-info" -exec rm -rf {} + 2>/dev/null || true
find "${BUILD_DIR}" -type d -name "*.egg-info"  -exec rm -rf {} + 2>/dev/null || true
find "${BUILD_DIR}" -name "*.pyc" -delete 2>/dev/null || true
echo "    Done."

# ---------------------------------------------------------------------------
# Step 4: Create the zip
# ---------------------------------------------------------------------------
echo "==> Creating ${OUTPUT_ZIP}..."
rm -f "${OUTPUT_ZIP}"

# Change into build dir so zip paths are relative (Lambda requires this)
(cd "${BUILD_DIR}" && zip -r -q "${OUTPUT_ZIP}" .)

ZIP_SIZE_MB=$(du -sm "${OUTPUT_ZIP}" | cut -f1)
echo "    Package size: ${ZIP_SIZE_MB} MB"

# Cleanup handled by EXIT trap
echo ""
echo "==> lambda-package.zip is ready at: ${OUTPUT_ZIP}"
echo "    Deploy with:"
echo "      make deploy-lambda"
echo "    or manually:"
echo "      aws lambda update-function-code \\"
echo "        --function-name healthstream-demo-query \\"
echo "        --zip-file fileb://${OUTPUT_ZIP} \\"
echo "        --region eu-west-1"
