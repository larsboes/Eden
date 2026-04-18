#!/usr/bin/env bash
# Deploy EDEN agent to AgentCore Runtime.
#
# Two modes:
#   1. Starter toolkit (default) — no local Docker needed, CodeBuild handles ARM64
#   2. Manual Docker + boto3   — use --manual flag
#
# Usage:
#   ./scripts/deploy-runtime.sh                  # starter toolkit (recommended)
#   ./scripts/deploy-runtime.sh --manual         # Docker build + boto3
#   ./scripts/deploy-runtime.sh --local-test     # run locally on :8080
#   ./scripts/deploy-runtime.sh --status         # check runtime status
#   ./scripts/deploy-runtime.sh --invoke "msg"   # send a test invocation

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

# ── Config ────────────────────────────────────────────────────────────
ACCOUNT=658707946640
REGION=${AWS_REGION:-us-west-2}
ECR_REPO="$ACCOUNT.dkr.ecr.$REGION.amazonaws.com/eden-agent"
TAG="latest"
AGENT_NAME="eden_greenhouse_agent"
RUNTIME_ROLE="${RUNTIME_ROLE_ARN:-arn:aws:iam::${ACCOUNT}:role/eden-runtime-agentcore-role-48c23c3}"
COGNITO_POOL="us-west-2_i3WRiWZeL"
COGNITO_DISCOVERY="https://cognito-idp.$REGION.amazonaws.com/$COGNITO_POOL/.well-known/openid-configuration"
COGNITO_CLIENT="uq4s0nkf3hsre1jkd001km9n4"

# ── Source creds ──────────────────────────────────────────────────────
if [ -f "$PROJECT_DIR/setup-bedrock.sh" ]; then
    echo "Sourcing AWS credentials..."
    # shellcheck disable=SC1091
    source "$PROJECT_DIR/setup-bedrock.sh"
fi

# ── Helpers ───────────────────────────────────────────────────────────
check_aws() {
    if ! aws sts get-caller-identity &>/dev/null; then
        echo "ERROR: AWS credentials not configured or expired."
        echo "  Run: source setup-bedrock.sh"
        exit 1
    fi
    echo "AWS identity: $(aws sts get-caller-identity --query 'Arn' --output text)"
}

# ── Mode: Local test ─────────────────────────────────────────────────
local_test() {
    echo "=== Local test mode: running on http://localhost:8080 ==="
    echo "  POST /invocations  — agent invocation"
    echo "  GET  /ping         — health check"
    echo ""
    uv run python -m eden.runtime_entry
}

# ── Mode: Status check ──────────────────────────────────────────────
check_status() {
    echo "=== Checking AgentCore Runtime status ==="
    if command -v agentcore &>/dev/null; then
        agentcore status -a "$AGENT_NAME" 2>/dev/null || true
    fi

    # Also try boto3 directly
    python3 -c "
import boto3, json
client = boto3.client('bedrock-agentcore-control', region_name='$REGION')
try:
    runtimes = client.list_agent_runtimes()
    for rt in runtimes.get('agentRuntimeSummaries', []):
        if '$AGENT_NAME' in rt.get('agentRuntimeName', ''):
            print(json.dumps(rt, indent=2, default=str))
except Exception as e:
    print(f'Could not list runtimes: {e}')
"
}

# ── Mode: Invoke ─────────────────────────────────────────────────────
invoke_test() {
    local prompt="${1:-Check greenhouse sensors and report status}"
    echo "=== Invoking EDEN agent ==="
    echo "Prompt: $prompt"
    echo ""

    if command -v agentcore &>/dev/null; then
        agentcore invoke "{\"prompt\": \"$prompt\"}" -a "$AGENT_NAME"
    else
        echo "Install starter toolkit: pip install bedrock-agentcore-starter-toolkit"
        exit 1
    fi
}

# ── Mode: Starter Toolkit Deploy (default) ───────────────────────────
deploy_toolkit() {
    echo "=== AgentCore Runtime Deploy (Starter Toolkit) ==="
    check_aws

    # Ensure toolkit is installed
    if ! command -v agentcore &>/dev/null; then
        echo "Installing bedrock-agentcore-starter-toolkit..."
        uv pip install bedrock-agentcore-starter-toolkit
    fi

    echo ""
    echo "Step 1/3: Configure"
    agentcore configure \
        -e eden/runtime_entry.py \
        -n "$AGENT_NAME" \
        -r "$REGION" \
        --execution-role "$RUNTIME_ROLE" \
        --idle-timeout 900 \
        --max-lifetime 28800 \
        --disable-memory \
        --non-interactive

    echo ""
    echo "Step 2/3: Deploy (CodeBuild — ARM64 automatic)"
    agentcore deploy

    echo ""
    echo "Step 3/3: Verify"
    agentcore status -a "$AGENT_NAME"

    echo ""
    echo "=== DEPLOY COMPLETE ==="
    echo "Test with:"
    echo "  ./scripts/deploy-runtime.sh --invoke 'Check greenhouse sensors'"
    echo "  agentcore invoke '{\"prompt\": \"Report greenhouse status\"}' -a $AGENT_NAME"
}

# ── Mode: Manual Docker + boto3 ─────────────────────────────────────
deploy_manual() {
    echo "=== AgentCore Runtime Deploy (Manual Docker + boto3) ==="
    check_aws

    echo ""
    echo "Step 1/4: ECR Login"
    aws ecr get-login-password --region "$REGION" | \
        docker login --username AWS --password-stdin \
        "$ACCOUNT.dkr.ecr.$REGION.amazonaws.com"

    echo ""
    echo "Step 2/4: Build ARM64 image & push to ECR"
    docker buildx create --use 2>/dev/null || true
    docker buildx build --platform linux/arm64 \
        -t "$ECR_REPO:$TAG" \
        --push .

    echo ""
    echo "Step 3/4: Create AgentCore Runtime"
    python3 -c "
import boto3, json, time

client = boto3.client('bedrock-agentcore-control', region_name='$REGION')

# Check if runtime already exists
try:
    runtimes = client.list_agent_runtimes()
    for rt in runtimes.get('agentRuntimeSummaries', []):
        if rt.get('agentRuntimeName') == '$AGENT_NAME':
            rt_id = rt['agentRuntimeId']
            print(f'Runtime already exists: {rt_id} (status: {rt.get(\"status\", \"unknown\")})')
            print(f'To update, delete first or use a new name.')
            exit(0)
except Exception:
    pass

response = client.create_agent_runtime(
    agentRuntimeName='$AGENT_NAME',
    agentRuntimeArtifact={
        'containerConfiguration': {
            'containerUri': '$ECR_REPO:$TAG'
        }
    },
    networkConfiguration={'networkMode': 'PUBLIC'},
    roleArn='$RUNTIME_ROLE',
    description='EDEN Martian greenhouse AI agent — autonomous greenhouse management for 4-astronaut Mars mission',
    authorizerConfiguration={
        'customJWTAuthorizer': {
            'discoveryUrl': '$COGNITO_DISCOVERY',
            'allowedClients': ['$COGNITO_CLIENT'],
        }
    },
    protocolConfiguration={'serverProtocol': 'HTTP'},
    lifecycleConfiguration={
        'idleRuntimeSessionTimeout': 900,
        'maxLifetime': 28800,
    },
    tags={'Project': 'eden', 'Environment': 'dev'},
)

rt_id = response['agentRuntimeId']
rt_arn = response['agentRuntimeArn']
print(f'Runtime created!')
print(f'  ID:     {rt_id}')
print(f'  ARN:    {rt_arn}')
print(f'  Status: {response[\"status\"]}')

# Poll for READY
print()
print('Waiting for READY status...')
for i in range(60):
    status = client.get_agent_runtime(agentRuntimeId=rt_id)
    state = status['status']
    print(f'  [{i*10}s] Status: {state}')
    if state == 'READY':
        print(f'Runtime is READY!')
        print(f'  Endpoint: {status.get(\"agentRuntimeEndpoint\", \"N/A\")}')
        break
    if state == 'CREATE_FAILED':
        print(f'FAILED: {status.get(\"statusReasons\", \"unknown\")}')
        exit(1)
    time.sleep(10)
else:
    print('Timeout waiting for READY — check console.')
"

    echo ""
    echo "Step 4/4: Store runtime info in SSM"
    echo "(Check status with: ./scripts/deploy-runtime.sh --status)"

    echo ""
    echo "=== MANUAL DEPLOY COMPLETE ==="
}

# ── Parse args ───────────────────────────────────────────────────────
case "${1:-}" in
    --manual)
        deploy_manual
        ;;
    --local-test|--local)
        local_test
        ;;
    --status)
        check_aws
        check_status
        ;;
    --invoke)
        check_aws
        invoke_test "${2:-}"
        ;;
    --help|-h)
        echo "Usage: $0 [--manual|--local-test|--status|--invoke \"prompt\"|--help]"
        echo ""
        echo "  (default)       Deploy via starter toolkit (recommended, no Docker needed)"
        echo "  --manual        Deploy via Docker build + boto3 API"
        echo "  --local-test    Run runtime locally on :8080 for testing"
        echo "  --status        Check deployed runtime status"
        echo "  --invoke \"msg\"  Send test invocation to deployed agent"
        echo "  --help          Show this help"
        ;;
    *)
        deploy_toolkit
        ;;
esac
