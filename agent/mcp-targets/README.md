# EDEN MCP Gateway Targets

AgentCore Gateway exposes external APIs and custom Lambda functions as MCP tools the EDEN agent can call natively.

## Architecture

```
EDEN Agent (Strands SDK)
  |
  +-- MCP Client
        |
        +-- AgentCore Gateway (MCP protocol, JWT auth, Cedar policies)
              |
              +-- Target 1: Syngenta KB      (provided, already live)
              +-- Target 2: NASA DONKI       (OpenAPI spec -> S3 -> gateway target)
              +-- Target 3: Eden Lambda      (Lambda + toolSchema -> gateway target)
```

## Targets

### 1. Syngenta Knowledge Base (provided)

- **Endpoint:** `https://kb-start-hack-gateway-buyjtibfpg.gateway.bedrock-agentcore.us-east-2.amazonaws.com/mcp`
- **Tools:** `kb-start-hack-target___knowledge_base_retrieve`
- **Status:** Already deployed by organizers. We connect to it directly.

### 2. NASA DONKI (donki-cme-openapi.json)

- **Type:** OpenAPI schema target
- **Tools produced:**
  - `NasaDONKI___get_cme_events` - Coronal mass ejection data
  - `NasaDONKI___get_mars_magnetopause_crossings` - Mars magnetopause crossings
- **Auth:** API key credential provider (query parameter `api_key`)

### 3. Eden Lambda (eden-lambda-tools.json)

- **Type:** Lambda target with inline tool schema
- **Tools produced:**
  - `eden___read_sensors` - Greenhouse zone telemetry
  - `eden___run_simulation` - Virtual Farming Lab Monte Carlo simulations
  - `eden___calculate_triage` - Crisis salvageability scoring with human-cost awareness
  - `eden___mars_transform` - Earth-to-Mars parameter transformation
- **Auth:** Gateway IAM role (Lambda invoke)

## Deployment

### Step 1: Upload OpenAPI spec to S3

```bash
aws s3 cp agent/mcp-targets/donki-cme-openapi.json s3://astrofarm-assets/mcp-targets/donki-cme-openapi.json
```

### Step 2: Create API key credential provider

```python
acps = boto3.client("bedrock-agentcore-control")
cred_resp = acps.create_api_key_credential_provider(
    name="NasaDONKI_APIKey",
    apiKey="YOUR_NASA_API_KEY"
)
cred_arn = cred_resp["arn"]
```

### Step 3: Create DONKI gateway target

```python
gw = boto3.client("bedrock-agentcore-control")
gw.create_gateway_target(
    gatewayIdentifier=gateway_id,
    name="NasaDONKI",
    targetConfiguration={
        "mcp": {
            "openApiSchema": {
                "s3": {"uri": "s3://astrofarm-assets/mcp-targets/donki-cme-openapi.json"}
            }
        }
    },
    credentialProviderConfigurations=[{
        "credentialProviderType": "API_KEY",
        "credentialProvider": {
            "apiKeyCredentialProvider": {
                "credentialParameterName": "api_key",
                "providerArn": cred_arn,
                "credentialLocation": "QUERY_PARAMETER"
            }
        }
    }]
)
```

### Step 4: Create Eden Lambda gateway target

```python
import json

with open("agent/mcp-targets/eden-lambda-tools.json") as f:
    tool_spec = f.read()

gw.create_gateway_target(
    gatewayIdentifier=gateway_id,
    name="EdenLambdaTools",
    targetConfiguration={
        "mcp": {
            "lambda": {
                "lambdaArn": eden_lambda_arn,
                "toolSchema": {"inlinePayload": tool_spec}
            }
        }
    },
    credentialProviderConfigurations=[{
        "credentialProviderType": "GATEWAY_IAM_ROLE"
    }]
)
```

### Step 5: Agent connects to all tools via gateway

```python
from mcp.client.streamable_http import streamablehttp_client
from strands.tools.mcp.mcp_client import MCPClient

mcp_client = MCPClient(lambda: streamablehttp_client(
    gateway_url,
    headers={"Authorization": f"Bearer {token}"}
))

with mcp_client:
    tools = mcp_client.list_tools_sync()
    # tools now includes all 7 tools from all 3 targets
```

## Tool Summary

| Target | Tool Name | Purpose |
|--------|-----------|---------|
| Syngenta KB | `kb-start-hack-target___knowledge_base_retrieve` | Crop science knowledge retrieval |
| NASA DONKI | `NasaDONKI___get_cme_events` | Solar storm detection |
| NASA DONKI | `NasaDONKI___get_mars_magnetopause_crossings` | Mars radiation events |
| Eden Lambda | `eden___read_sensors` | Greenhouse telemetry |
| Eden Lambda | `eden___run_simulation` | Monte Carlo growth simulation |
| Eden Lambda | `eden___calculate_triage` | Crisis crop triage |
| Eden Lambda | `eden___mars_transform` | Earth-to-Mars value adjustment |
