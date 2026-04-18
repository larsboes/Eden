# AgentCore Runtime — Research & Implementation Guide

> **Purpose**: Single reference doc for implementing EDEN's AgentCore Runtime deployment.
> **Researcher**: Bryan's agent | **Date**: 2026-03-19
> **Sources**: AWS docs, PyPI, GitHub samples, boto3 API reference, dev.to articles

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [BedrockAgentCoreApp — The SDK Pattern](#2-bedrockagentcoreapp--the-sdk-pattern)
3. [Entrypoint Function Deep Dive](#3-entrypoint-function-deep-dive)
4. [Streaming Support](#4-streaming-support)
5. [Health Check & Async Tasks](#5-health-check--async-tasks)
6. [Docker Requirements](#6-docker-requirements)
7. [Deployment — Two Approaches](#7-deployment--two-approaches)
8. [boto3 create_agent_runtime API Reference](#8-boto3-create_agent_runtime-api-reference)
9. [Invoking the Deployed Agent](#9-invoking-the-deployed-agent)
10. [Session Management](#10-session-management)
11. [Auth Propagation (JWT → Gateway)](#11-auth-propagation-jwt--gateway)
12. [Our EDEN Implementation](#12-our-eden-implementation)
13. [Gotchas & Known Issues](#13-gotchas--known-issues)
14. [Step-by-Step Deploy Runbook](#14-step-by-step-deploy-runbook)

---

## 1. Architecture Overview

AgentCore Runtime is a **serverless, managed container runtime** purpose-built for AI agents.

**Key properties:**
- Each session runs in a **dedicated microVM** with isolated CPU, memory, filesystem
- After session termination, the entire microVM is destroyed and memory sanitized
- Supports **up to 8 hours** of execution time per session
- **15-minute idle timeout** (configurable 60-28800s)
- Port **8080** required (HTTP endpoints `/invocations`, `/ping`, `/ws`)
- **ARM64 containers only** (`linux/arm64`)
- Protocols: HTTP, WebSocket, MCP, A2A, AG-UI

**Lifecycle:**
```
Container Image (ECR)
  → create_agent_runtime() → Version V1 auto-created
    → DEFAULT endpoint auto-created → status: CREATING → READY
      → invoke_agent_runtime() → session spun up in microVM
        → 15min idle → session terminated
```

**Endpoint states:** `CREATING` → `CREATE_FAILED` | `READY` → `UPDATING` → `UPDATE_FAILED` | `READY`

---

## 2. BedrockAgentCoreApp — The SDK Pattern

### Install

```bash
pip install bedrock-agentcore==1.4.7   # Latest as of 2026-03-18
```

Python >=3.10 required (tested on 3.10, 3.11, 3.12, 3.13).

### Import

```python
from bedrock_agentcore.runtime import BedrockAgentCoreApp
# OR (also works):
from bedrock_agentcore import BedrockAgentCoreApp
```

### Minimal Pattern (4 lines to production)

```python
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from strands import Agent

app = BedrockAgentCoreApp()
agent = Agent()

@app.entrypoint
def invoke(payload):
    user_message = payload.get("prompt", "Hello!")
    result = agent(user_message)
    return {"result": result.message}

if __name__ == "__main__":
    app.run()  # Serves on port 8080: /invocations + /ping + /ws
```

### What `app.run()` does:
- Starts HTTP server on **port 8080**
- Registers `/invocations` (POST) — routes to your `@app.entrypoint` function
- Registers `/ping` (GET) — returns `{"status": "Healthy"}` (or custom via `@app.ping`)
- Registers `/ws` (WebSocket) — for bidirectional streaming
- Handles graceful shutdown

---

## 3. Entrypoint Function Deep Dive

### Synchronous (simple)

```python
@app.entrypoint
def invoke(payload):
    prompt = payload.get("prompt", "")
    result = agent(prompt)
    return {"result": result.message}
```

### Async with context

```python
@app.entrypoint
async def invoke(payload, context=None):
    prompt = payload.get("prompt", "")
    session_id = context.session_id          # Auto-populated by Runtime
    headers = context.request_headers or {}  # Dict of incoming HTTP headers
    auth = headers.get("Authorization", "")  # JWT from caller

    result = agent(prompt)
    return {"response": result.message["content"][0]["text"]}
```

### Payload

The `payload` parameter is a **dict** — whatever JSON the caller sends in the request body. Our convention:

```json
{
  "prompt": "Check greenhouse sensors and report status",
  "zone_id": "alpha",
  "session_id": "optional-override"
}
```

### Context object

| Attribute | Type | Description |
|---|---|---|
| `context.session_id` | `str` | Runtime-managed session ID (from `runtimeSessionId` header) |
| `context.request_headers` | `dict[str, str]` | All HTTP headers from the incoming request |

**Important:** `context` may be `None` when testing locally. Always use `getattr(context, "session_id", None)`.

### Return value

Return a **dict** — it gets JSON-serialized and sent back to the caller.

---

## 4. Streaming Support

For streaming responses (SSE), use an **async generator** that `yield`s events:

```python
@app.entrypoint
async def invoke(payload):
    prompt = payload.get("prompt", "")
    stream = agent.stream_async(prompt)
    async for event in stream:
        yield event  # Each yield becomes an SSE event
```

Client-side consumption uses SSE (Server-Sent Events) format — each yielded value is sent as a `data:` line.

---

## 5. Health Check & Async Tasks

### Custom ping handler

```python
from bedrock_agentcore.runtime import BedrockAgentCoreApp, PingStatus

@app.ping
def custom_status():
    if system_busy():
        return PingStatus.HEALTHY_BUSY  # "HealthyBusy"
    return PingStatus.HEALTHY           # "Healthy"
```

Default (no `@app.ping`): returns `{"status": "Healthy"}`.

### Async task management (long-running background work)

```python
# Start tracking
task_id = app.add_async_task("background_processing")

# ... do work in a thread ...

# Mark complete
app.complete_async_task(task_id)
```

While async tasks are running, `/ping` returns `{"status": "HealthyBusy"}`, preventing the 15-min idle timeout from killing the session.

**CRITICAL**: The `@app.entrypoint` handler must NOT block for long periods — it blocks the `/ping` health check thread. Use `threading.Thread` or `asyncio` for long work.

---

## 6. Docker Requirements

### Architecture: ARM64 MANDATORY

AgentCore Runtime runs on Graviton (ARM64). Your Docker image **must** target `linux/arm64`.

### Dockerfile (using uv — recommended)

```dockerfile
FROM --platform=linux/arm64 ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

# Copy dependency files first (layer caching)
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen --no-cache

# Copy application code
COPY eden/ ./eden/

# Expose AgentCore's required port
EXPOSE 8080

# Run the runtime entry point
CMD ["uv", "run", "python", "-m", "eden.runtime_entry"]
```

### Dockerfile (alternative — pip)

```dockerfile
FROM --platform=linux/arm64 python:3.12-slim-bookworm

WORKDIR /app
COPY requirements-runtime.txt .
RUN pip install --no-cache-dir -r requirements-runtime.txt
COPY eden/ ./eden/
EXPOSE 8080
CMD ["python", "-m", "eden.runtime_entry"]
```

### Key constraints:
- **Port 8080** — hardcoded in the Runtime, not configurable
- **ARM64** — `--platform=linux/arm64` in FROM or `docker buildx build --platform linux/arm64`
- Keep image **small** — large images = slow cold start
- AWS credentials are injected via the execution role (no need to bake them in)

---

## 7. Deployment — Two Approaches

### Approach A: Starter Toolkit CLI (recommended for hackathon)

```bash
pip install bedrock-agentcore-starter-toolkit==0.3.3

# Step 1: Configure
agentcore configure -e eden/runtime_entry.py \
  -n eden_greenhouse_agent \
  -r us-west-2 \
  --execution-role arn:aws:iam::658707946640:role/RuntimeAgentCoreRole \
  --idle-timeout 900 \
  --max-lifetime 28800

# Step 2: Deploy (uses CodeBuild — no local Docker needed!)
agentcore deploy

# Step 3: Check status
agentcore status

# Step 4: Test
agentcore invoke '{"prompt": "Check greenhouse sensors"}'

# Cleanup
agentcore destroy
```

**What `agentcore deploy` does under the hood:**
1. Builds Docker image via **AWS CodeBuild** (ARM64 automatically)
2. Pushes to auto-created ECR repository
3. Calls `create_agent_runtime` with container URI
4. Waits for READY status
5. Returns agent ARN

**Deployment modes:**
| Mode | Command | Docker required? | Description |
|---|---|---|---|
| Default | `agentcore deploy` | No | CodeBuild builds in cloud |
| Local | `agentcore deploy --local` | Yes | Build & run locally |
| Hybrid | `agentcore deploy --local-build` | Yes | Build locally, deploy to cloud |

**CLI flags for `agentcore configure`:**
| Flag | Description |
|---|---|
| `-e, --entrypoint` | Python entrypoint file |
| `-n, --name` | Agent name |
| `-r, --region` | AWS region |
| `--execution-role` | IAM role ARN |
| `--ecr` | ECR repo name ("auto" for auto-create) |
| `--deployment-type` | "direct_code_deploy" or "container" |
| `--runtime` | Python version (3.10-3.13) |
| `--requirements-file` | Path to requirements.txt |
| `--disable-memory` | Skip memory provisioning |
| `--idle-timeout` | Session idle timeout (60-28800s, default 900) |
| `--max-lifetime` | Max session lifetime (60-28800s, default 28800) |
| `--vpc` | Enable VPC networking |
| `--non-interactive` | Skip prompts |

### Approach B: Manual Docker + boto3 (full control)

```bash
# 1. Build ARM64 image
docker buildx create --use
docker buildx build --platform linux/arm64 \
  -t 658707946640.dkr.ecr.us-west-2.amazonaws.com/eden-agent:latest \
  --push .

# 2. Login to ECR first
aws ecr get-login-password --region us-west-2 | \
  docker login --username AWS --password-stdin \
  658707946640.dkr.ecr.us-west-2.amazonaws.com
```

Then create runtime via boto3 — see next section.

---

## 8. boto3 create_agent_runtime API Reference

```python
import boto3

client = boto3.client('bedrock-agentcore-control', region_name='us-west-2')

response = client.create_agent_runtime(
    # REQUIRED
    agentRuntimeName='eden_greenhouse_agent',
    agentRuntimeArtifact={
        'containerConfiguration': {
            'containerUri': '658707946640.dkr.ecr.us-west-2.amazonaws.com/eden-agent:latest'
        }
    },
    networkConfiguration={
        'networkMode': 'PUBLIC'
    },
    roleArn='arn:aws:iam::658707946640:role/RuntimeAgentCoreRole',

    # OPTIONAL
    description='EDEN Martian greenhouse AI agent',
    authorizerConfiguration={
        'customJWTAuthorizer': {
            'discoveryUrl': 'https://cognito-idp.us-west-2.amazonaws.com/us-west-2_i3WRiWZeL/.well-known/openid-configuration',
            'allowedClients': ['uq4s0nkf3hsre1jkd001km9n4'],
        }
    },
    protocolConfiguration={
        'serverProtocol': 'HTTP'  # Options: HTTP, MCP, A2A, AGUI
    },
    lifecycleConfiguration={
        'idleRuntimeSessionTimeout': 900,   # 15 min idle timeout
        'maxLifetime': 28800                 # 8 hour max lifetime
    },
    environmentVariables={
        'AGENTCORE_GATEWAY_ENDPOINT': '<gateway-url>',
        'AWS_REGION': 'us-west-2',
    },
    tags={
        'Project': 'eden',
        'Environment': 'dev',
    },
)

print(f"ARN: {response['agentRuntimeArn']}")
print(f"ID: {response['agentRuntimeId']}")
print(f"Status: {response['status']}")  # CREATING → READY
```

### Alternative: Direct Code Deploy (no Docker!)

```python
response = client.create_agent_runtime(
    agentRuntimeName='eden_greenhouse_agent',
    agentRuntimeArtifact={
        'codeConfiguration': {
            'code': {
                's3': {
                    'bucket': 'eden-deployment-bucket',
                    'prefix': 'eden-agent/deployment.zip'
                }
            },
            'runtime': 'PYTHON_3_12',
            'entryPoint': ['python', '-m', 'eden.runtime_entry']
        }
    },
    networkConfiguration={'networkMode': 'PUBLIC'},
    roleArn='arn:aws:iam::658707946640:role/RuntimeAgentCoreRole',
)
```

### Check status (poll until READY)

```python
import time

while True:
    status = client.get_agent_runtime(
        agentRuntimeId=response['agentRuntimeId']
    )
    state = status['status']
    print(f"Status: {state}")
    if state == 'READY':
        break
    if state == 'CREATE_FAILED':
        raise RuntimeError(f"Failed: {status}")
    time.sleep(10)
```

---

## 9. Invoking the Deployed Agent

### Via boto3

```python
import boto3, json, uuid

client = boto3.client('bedrock-agentcore', region_name='us-west-2')

response = client.invoke_agent_runtime(
    agentRuntimeArn='arn:aws:bedrock-agentcore:us-west-2:658707946640:runtime/eden_greenhouse_agent-XXXX',
    runtimeSessionId=str(uuid.uuid4()) + '-extra-chars',  # Must be 33+ chars!
    payload=json.dumps({"prompt": "Check greenhouse sensors"}).encode(),
    qualifier='DEFAULT',  # Or specific endpoint name
)

# Read response
body = response['response'].read()
data = json.loads(body)
print(data)
```

### Via agentcore CLI

```bash
agentcore invoke '{"prompt": "Check greenhouse sensors"}' -a eden_greenhouse_agent
```

### Via HTTP (from frontend)

```python
import requests

url = f"https://bedrock-agentcore.us-west-2.amazonaws.com/runtimes/{escaped_arn}/invocations"
headers = {
    "Authorization": f"Bearer {jwt_token}",
    "Content-Type": "application/json",
    "X-Amzn-Bedrock-AgentCore-Runtime-Session-Id": session_id,
}
response = requests.post(url, headers=headers, json={"prompt": "..."},
                         params={"qualifier": "DEFAULT"}, timeout=100, stream=True)

# SSE streaming
for line in response.iter_lines(chunk_size=1, decode_unicode=True):
    if line and line.startswith("data: "):
        print(line[6:])
```

**runtimeSessionId requirements:**
- Must be **33+ characters**
- Same ID = continue conversation (context preserved)
- New ID = fresh session (new microVM)

---

## 10. Session Management

| Property | Value |
|---|---|
| Idle timeout | 15 min default (configurable 60-28800s) |
| Max lifetime | 8 hours default (configurable 60-28800s) |
| Isolation | Dedicated microVM per session |
| State | Ephemeral — use AgentCore Memory for persistence |
| Session ID | `context.session_id` in entrypoint, `runtimeSessionId` in API |

**Session states:**
- `Active` — processing a request or running background tasks
- `Idle` — waiting for next interaction (context preserved)
- `Terminated` — idle timeout, max lifetime, or unhealthy

**Important:** Same `runtimeSessionId` after termination creates a **new** session (new microVM, no state carry-over).

---

## 11. Auth Propagation (JWT → Gateway)

When the Runtime is configured with a JWT authorizer, the caller's token flows through:

```
Frontend (JWT) → Runtime (validates JWT) → @app.entrypoint(payload, context)
                                            context.request_headers["Authorization"] = "Bearer ..."
                                              → MCPClient(headers={"Authorization": auth_header})
                                                → Gateway (validates same JWT)
                                                  → MCP tools
```

Our `runtime_entry.py` already does this correctly:

```python
auth_header = (context.request_headers or {}).get("Authorization", "")
mcp_client = MCPClient(lambda: streamablehttp_client(
    url=gateway_url,
    headers={"Authorization": auth_header},
))
```

To allow custom headers through, use `requestHeaderConfiguration`:

```python
requestHeaderConfiguration={
    'requestHeaderAllowlist': ['Authorization', 'X-Custom-Header']
}
```

---

## 12. Our EDEN Implementation

### Current state (what we already have)

| File | Status | Notes |
|---|---|---|
| `eden/runtime_entry.py` | **Good** | Full entrypoint with MCP gateway integration |
| `scripts/deploy_agentcore.py` | **Good** | Gateway + Runtime deployment script |
| `infra/runtime.py` | Placeholder | ECR repo created, Runtime is TODO |
| `Dockerfile` | **Missing** | Need to create |
| `requirements-runtime.txt` | **Missing** | Need to create |

### What `runtime_entry.py` does right:
- Lazy imports for fast cold start
- `BedrockAgentCoreApp` + `@app.entrypoint` pattern
- Extracts `context.session_id` with fallback
- Propagates `Authorization` header to MCP gateway
- Local tools (read_sensors, set_actuator, get_nutritional_status)
- System prompt with session ID
- Graceful MCP client cleanup

### What needs fixing in `runtime_entry.py`:
1. Import path: `from bedrock_agentcore.runtime import BedrockAgentCoreApp` ✅ already correct
2. The entrypoint function signature uses `async def` with `context=None` ✅ correct
3. Need to ensure `app.run()` is called at module level for `__main__` ✅ already done
4. Consider switching to sync entrypoint if not streaming (simpler)

### Copy-paste ready `runtime_entry.py`

Our existing `eden/runtime_entry.py` is already well-structured. No major changes needed. The implementer should focus on:

1. Creating the Dockerfile
2. Creating requirements-runtime.txt
3. Running the deploy

### Dockerfile for EDEN

```dockerfile
FROM --platform=linux/arm64 ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install production dependencies only
RUN uv sync --frozen --no-cache --no-dev

# Copy application code
COPY eden/ ./eden/

# AgentCore requires port 8080
EXPOSE 8080

# Set environment defaults
ENV PYTHONUNBUFFERED=1

# Run the runtime entry point
CMD ["uv", "run", "python", "-m", "eden.runtime_entry"]
```

### requirements-runtime.txt (if not using uv)

```
bedrock-agentcore>=1.4.0
strands-agents>=0.1
strands-agents-tools>=0.1
boto3>=1.42
mcp>=1.0
paho-mqtt>=2.0
python-dotenv>=1.0
requests>=2.31
```

### Deploy script (bash — fast for hackathon)

```bash
#!/usr/bin/env bash
set -euo pipefail

ACCOUNT=658707946640
REGION=us-west-2
ECR_REPO=$ACCOUNT.dkr.ecr.$REGION.amazonaws.com/eden-agent
TAG=latest
RUNTIME_ROLE=arn:aws:iam::${ACCOUNT}:role/RuntimeAgentCoreRole
COGNITO_DISCOVERY=https://cognito-idp.$REGION.amazonaws.com/us-west-2_i3WRiWZeL/.well-known/openid-configuration
COGNITO_CLIENT=uq4s0nkf3hsre1jkd001km9n4

echo "=== Step 1: ECR Login ==="
aws ecr get-login-password --region $REGION | \
  docker login --username AWS --password-stdin $ACCOUNT.dkr.ecr.$REGION.amazonaws.com

echo "=== Step 2: Build ARM64 image ==="
docker buildx create --use 2>/dev/null || true
docker buildx build --platform linux/arm64 -t $ECR_REPO:$TAG --push .

echo "=== Step 3: Create AgentCore Runtime ==="
python3 -c "
import boto3, json
client = boto3.client('bedrock-agentcore-control', region_name='$REGION')
try:
    response = client.create_agent_runtime(
        agentRuntimeName='eden_greenhouse_agent',
        agentRuntimeArtifact={
            'containerConfiguration': {
                'containerUri': '$ECR_REPO:$TAG'
            }
        },
        networkConfiguration={'networkMode': 'PUBLIC'},
        roleArn='$RUNTIME_ROLE',
        description='EDEN Martian greenhouse AI agent',
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
        tags={'Project': 'eden'},
    )
    print(f'Runtime ARN: {response[\"agentRuntimeArn\"]}')
    print(f'Runtime ID: {response[\"agentRuntimeId\"]}')
    print(f'Status: {response[\"status\"]}')
except Exception as e:
    print(f'Error: {e}')
"

echo "=== Step 4: Wait for READY ==="
echo "Check status with: agentcore status -a eden_greenhouse_agent"
echo "Or: aws bedrock-agentcore-control get-agent-runtime --agent-runtime-id <ID> --region $REGION"
```

### Alternative: Starter toolkit (even simpler)

```bash
pip install bedrock-agentcore-starter-toolkit

agentcore configure \
  -e eden/runtime_entry.py \
  -n eden_greenhouse_agent \
  -r us-west-2 \
  --execution-role arn:aws:iam::658707946640:role/RuntimeAgentCoreRole \
  --disable-memory \
  --non-interactive

agentcore deploy

agentcore invoke '{"prompt": "Check greenhouse sensors and report status"}'
```

---

## 13. Gotchas & Known Issues

### CRITICAL: CloudWatch Transaction Search must be enabled

> "You need to enable CloudWatch Transaction Search in order for AgentCore Runtime to properly invoke your agent."

This is **mandatory** but not in the tutorials. Without it, you get cryptic invocation errors. Enable it in the AgentCore console before deploying.

### ARM64 only — no x86

AgentCore runs on Graviton. If building locally on an Intel Mac:
```bash
docker buildx create --use
docker buildx build --platform linux/arm64 ...
```
On Apple Silicon Mac, `--platform linux/arm64` works natively.

### Cold start

- First invocation after deploy takes longer (container pull + init)
- Keep image small: use slim base images, multi-stage builds
- Lazy imports in entrypoint (our `runtime_entry.py` already does this)

### Entrypoint must not block

The `@app.entrypoint` handler runs on the same event loop as `/ping`. If it blocks for >15min without background task tracking, the session gets killed. Use `threading.Thread` or `app.add_async_task()` for long work.

### runtimeSessionId must be 33+ characters

Use `str(uuid.uuid4()) + "-eden"` or similar. Short IDs will be rejected.

### Image size matters

Large images = slow cold start. Target <500MB if possible.
- Use `uv sync --no-cache` to avoid cache bloat
- Use slim base images
- Don't include dev dependencies

### Execution role permissions

The IAM role needs at minimum:
- `bedrock:InvokeModel` — to call Claude
- `ecr:GetDownloadUrlForLayer`, `ecr:BatchGetImage` — to pull container
- `logs:CreateLogGroup`, `logs:CreateLogStream`, `logs:PutLogEvents` — CloudWatch
- `xray:PutTraceSegments` — X-Ray tracing
- `bedrock-agentcore:*` — if using Memory features

### Environment variables

Pass via `environmentVariables` in `create_agent_runtime` or via `agentcore deploy --env KEY=VALUE`. AWS credentials are injected automatically via the execution role.

### Port 8080 is hardcoded

Don't try to use a different port. The Runtime expects 8080.

---

## 14. Step-by-Step Deploy Runbook

### Option A: Fastest (starter toolkit, no Docker needed)

```bash
# 1. Install
pip install bedrock-agentcore bedrock-agentcore-starter-toolkit

# 2. Configure
agentcore configure -e eden/runtime_entry.py -n eden_greenhouse_agent -r us-west-2 --disable-memory --non-interactive

# 3. Deploy (CodeBuild handles ARM64 Docker)
agentcore deploy

# 4. Verify
agentcore status -a eden_greenhouse_agent

# 5. Test
agentcore invoke '{"prompt": "Report greenhouse status"}' -a eden_greenhouse_agent

# 6. Get ARN for frontend integration
agentcore status -a eden_greenhouse_agent --verbose
```

### Option B: Manual (full control)

```bash
# 1. ECR login
aws ecr get-login-password --region us-west-2 | \
  docker login --username AWS --password-stdin 658707946640.dkr.ecr.us-west-2.amazonaws.com

# 2. Build & push ARM64 image
docker buildx create --use
docker buildx build --platform linux/arm64 \
  -t 658707946640.dkr.ecr.us-west-2.amazonaws.com/eden-agent:latest \
  --push .

# 3. Create runtime (run deploy_runtime.py — see section 8)
python scripts/deploy_runtime_manual.py

# 4. Wait for READY
aws bedrock-agentcore-control get-agent-runtime \
  --agent-runtime-id <ID> --region us-west-2

# 5. Test invocation
python scripts/invoke_runtime.py
```

### Option C: Our existing deploy script

```bash
# After Gateway is created:
python scripts/deploy_agentcore.py \
  --runtime-role-arn arn:aws:iam::658707946640:role/RuntimeAgentCoreRole \
  --cognito-client-id uq4s0nkf3hsre1jkd001km9n4 \
  --cognito-discovery-url https://cognito-idp.us-west-2.amazonaws.com/us-west-2_i3WRiWZeL/.well-known/openid-configuration
```

### Local testing (before deploy)

```bash
# Install deps
pip install bedrock-agentcore strands-agents

# Run locally
python eden/runtime_entry.py
# → Serves on http://localhost:8080

# Test ping
curl http://localhost:8080/ping
# → {"status": "Healthy"}

# Test invocation
curl -X POST http://localhost:8080/invocations \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Check greenhouse sensors"}'
```

---

## Package Versions (as of 2026-03-19)

| Package | Version | PyPI |
|---|---|---|
| bedrock-agentcore | 1.4.7 | https://pypi.org/project/bedrock-agentcore/ |
| bedrock-agentcore-starter-toolkit | 0.3.3 | https://pypi.org/project/bedrock-agentcore-starter-toolkit/ |
| strands-agents | >=0.1 | (already in our deps) |
| boto3 | >=1.42.3 | (for `bedrock-agentcore-control` client) |

## AWS Account Details

| Resource | Value |
|---|---|
| Account | 658707946640 |
| Region | us-west-2 |
| ECR Repo | 658707946640.dkr.ecr.us-west-2.amazonaws.com/eden-agent |
| IAM Role | RuntimeAgentCoreRole |
| Cognito Pool | us-west-2_i3WRiWZeL |
| Cognito Client | uq4s0nkf3hsre1jkd001km9n4 |
| Cognito Discovery | https://cognito-idp.us-west-2.amazonaws.com/us-west-2_i3WRiWZeL/.well-known/openid-configuration |

---

## Sources

- [AWS Docs: Runtime How It Works](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-how-it-works.html)
- [AWS Docs: Host agent with Runtime](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/agents-tools-runtime.html)
- [AWS Docs: Long-running agents](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-long-run.html)
- [AWS Docs: Response streaming](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/response-streaming.html)
- [AWS Docs: Deploy without toolkit](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/getting-started-custom.html)
- [Starter Toolkit Quickstart](https://aws.github.io/bedrock-agentcore-starter-toolkit/user-guide/runtime/quickstart.html)
- [Starter Toolkit CLI Reference](https://aws.github.io/bedrock-agentcore-starter-toolkit/api-reference/cli.html)
- [Starter Toolkit GitHub](https://github.com/aws/bedrock-agentcore-starter-toolkit)
- [SDK Python GitHub](https://github.com/aws/bedrock-agentcore-sdk-python)
- [PyPI: bedrock-agentcore](https://pypi.org/project/bedrock-agentcore/)
- [PyPI: bedrock-agentcore-starter-toolkit](https://pypi.org/project/bedrock-agentcore-starter-toolkit/)
- [boto3: create_agent_runtime](https://docs.aws.amazon.com/boto3/latest/reference/services/bedrock-agentcore-control/client/create_agent_runtime.html)
- [FreeCodeCamp: Deploy Agent with AgentCore](https://www.freecodecamp.org/news/deploy-an-ai-agent-with-amazon-bedrock/)
- [DEV.to: First Impressions with AgentCore](https://dev.to/aws/first-impressions-with-amazon-bedrock-agentcore-5dje)
- [DEV.to: Custom Agent with Strands SDK](https://dev.to/aws-heroes/amazon-bedrock-agentcore-runtime-part-4-using-custom-agent-with-strands-agents-sdk-201o)
- [AgentCore Samples GitHub](https://github.com/awslabs/amazon-bedrock-agentcore-samples)
