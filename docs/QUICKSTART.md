# EDEN Quickstart

Get the Martian greenhouse system running locally or on EC2.

---

## Prerequisites

| Tool | Version | Why |
|------|---------|-----|
| Python | 3.12+ | Runtime |
| uv | latest | Package manager |
| Node.js | 18+ | NASA MCP server (runs via `npx`) |
| AWS credentials | — | Bedrock (Claude), DynamoDB, EC2 |

---

## 1. AWS Credentials

```bash
source setup-bedrock.sh
```

This configures `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_SESSION_TOKEN`, and `AWS_REGION=us-west-2` for your shell session.

**Re-source when credentials expire** — if you see `NoCredentialsError` or `ExpiredTokenException`, just run `source setup-bedrock.sh` again.

---

## 2. Environment Config

```bash
cp .env.example .env
```

Edit `.env` — key variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `MQTT_BROKER_HOST` | `localhost` | Mosquitto broker (EC2 IP for remote) |
| `MQTT_BROKER_PORT` | `1883` | MQTT port |
| `EDEN_SIMULATE` | `true` | `true` = fake sensors, no Pi needed |
| `AWS_REGION` | `us-west-2` | Bedrock region |
| `OLLAMA_HOST` | `http://localhost:11434` | Local LLM fallback |
| `OLLAMA_MODEL` | `llama3.2:3b` | Local model name |
| `RECONCILE_INTERVAL_SECONDS` | `30` | Agent parliament cycle interval |
| `NASA_API_KEY` | `DEMO_KEY` | Get a real key at api.nasa.gov |
| `LOG_LEVEL` | `INFO` | `DEBUG` for verbose output |

---

## 3. Install

```bash
# Install all dependencies (including dev)
uv sync

# Or install as editable package
uv pip install -e ".[dev]"
```

---

## 4. Run Tests

```bash
# Fast — no AWS needed, skips E2E
uv run pytest tests/

# With real AWS (Bedrock, DynamoDB)
source setup-bedrock.sh && uv run pytest tests/ --run-e2e

# Single E2E test with verbose output
uv run pytest tests/e2e/test_parliament_debate.py --run-e2e -v -s
```

---

## 5. Run the System

### Simulated (no Pi, no AWS)
```bash
EDEN_SIMULATE=true python -m eden
```
Starts the reconciler with fake sensors. Agent parliament runs on local Ollama if available, otherwise logs that the model is unavailable and flight rules hold.

### With AWS (Bedrock Claude)
```bash
source setup-bedrock.sh && python -m eden
```
Full system: simulated sensors + Bedrock Claude for the 12-agent parliament + DynamoDB sync.

### API Only (frontend dev)
```bash
uvicorn eden.api:app --host 0.0.0.0 --port 8000 --reload
```
Hot-reloading API server at `http://localhost:8000`. No reconciler — just serves whatever state is in the store.

---

## 6. Deploy Infrastructure

```bash
# Deploy EC2 + networking (Pulumi)
make deploy

# Deploy AgentCore Gateway + Runtime
make deploy-agentcore
```

### SSH to EC2

```bash
# Export SSH key (run once after deploy)
make key

# Connect
make ssh
```

### Other Infra Commands

| Command | Description |
|---------|-------------|
| `make preview` | Preview infra changes |
| `make destroy` | Tear down EC2 |
| `make ip` | Show EC2 public IP |
| `make status` | Check if EC2 bootstrap is done |

---

## Common Issues

### `NoCredentialsError` / `ExpiredTokenException`
AWS session credentials expired. Fix:
```bash
source setup-bedrock.sh
```

### `Connection pool full` / pool warnings
Normal. The agent parliament runs 14 parallel Bedrock calls (12 specialists + FLORA per zone). Connection pool is set to 50 — warnings are informational, not errors.

### `Read timeout` on Bedrock calls
A Bedrock call took >60s. The system auto-retries. This happens under heavy load or when Claude is thinking hard about a complex zone state. No action needed.

### Tests hanging
You're probably running E2E tests without the flag. Default `pytest` skips E2E tests. Use `--run-e2e` to opt in:
```bash
uv run pytest tests/ --run-e2e
```

### MQTT connection refused
Either Mosquitto isn't running or `MQTT_BROKER_HOST` is wrong. For local dev with `EDEN_SIMULATE=true`, the simulated sensors publish directly — MQTT broker failure is logged but non-fatal.
