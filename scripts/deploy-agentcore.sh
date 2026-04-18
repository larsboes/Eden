#!/usr/bin/env bash
# Deploy AgentCore Gateway for EDEN — NASA + Mars Transform + Syngenta KB.
#
# Creates the gateway with 3 targets (NASA OpenAPI, Mars Transform Lambda,
# Syngenta MCP KB) and Cedar policies.
#
# Usage:
#   ./scripts/deploy-agentcore.sh                 # deploy with NONE auth
#   ./scripts/deploy-agentcore.sh --auth jwt      # deploy with Cognito JWT
#   ./scripts/deploy-agentcore.sh --dry-run       # print plan only
#   ./scripts/deploy-agentcore.sh --skip-policies  # skip Cedar policies

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

echo "=== AstroFarm AgentCore Gateway Deployment ==="
echo "Region: ${AWS_REGION:-us-west-2}"
echo "Bucket: astrofarm-assets-20260319015916429700000001"
echo ""

# Source AWS creds if available
if [ -f setup-bedrock.sh ]; then
    echo "Sourcing AWS credentials..."
    source setup-bedrock.sh
fi

# Check if boto3/AWS CLI is available
if ! python3 -c "import boto3" 2>/dev/null; then
    echo "ERROR: boto3 not installed. Run: pip install boto3"
    exit 1
fi

# Verify NASA OpenAPI spec exists
if [ ! -f "nasa-openapi-spec.json" ]; then
    echo "ERROR: nasa-openapi-spec.json not found in project root"
    exit 1
fi

# Run the Python deploy script with all forwarded args
exec python3 scripts/deploy_agentcore.py "$@"
