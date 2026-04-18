# AstroFarm — AWS AgentCore Blueprint

> Source: Organizer tip — AgentCore tutorial notebooks from `awslabs/amazon-bedrock-agentcore-samples`
> Labs: 01 (create agent), 03 (gateway), 04 (runtime), 06 (frontend)
> Bonus: OpenAPI-to-MCP tutorial (NASA API → MCP tools via Gateway)

---

## The Organizer Hint

The OpenAPI-to-MCP tutorial **literally builds a Mars Weather agent using NASA APIs through AgentCore Gateway**. This is not a coincidence — this is the intended architecture path.

## Lab Progression → Our Build Order

| Lab | What it teaches | Our equivalent |
|---|---|---|
| Lab 01 | Local agent with `@tool` + Knowledge Base RAG | Local prototype with crop tools + Syngenta KB |
| Lab 03 | AgentCore Gateway + Lambda targets + MCP + Cedar policies | Gateway wrapping NASA APIs + Syngenta MCP + access control |
| Lab 04 | Deploy agent to AgentCore Runtime (4 lines of code) | Deploy our greenhouse agent to managed runtime |
| Lab 06 | Streamlit frontend with Cognito auth + streaming | Our dashboard (React or Streamlit) with streaming agent log |

---

## Key Architecture Pattern: OpenAPI → MCP Gateway → Agent

The NASA tutorial shows exactly how to wrap any REST API as MCP tools:

```
NASA OpenAPI spec (JSON)
    → upload to S3
    → create Gateway Target (type: openApiSchema)
    → attach API key credential provider
    → Agent calls tools via MCP client

Result: Agent can call "get_insight_weather" as a native MCP tool
```

### Gateway Creation

```python
gateway_client = boto3.client('bedrock-agentcore-control')

# Create gateway with Cognito JWT auth
create_response = gateway_client.create_gateway(
    name='AstroFarmGateway',
    roleArn=gateway_role_arn,
    protocolType='MCP',
    authorizerType='CUSTOM_JWT',
    authorizerConfiguration={
        "customJWTAuthorizer": {
            "allowedClients": [client_id],
            "discoveryUrl": cognito_discovery_url
        }
    },
)
```

### API Key Credential Provider (for NASA API key)

```python
acps = boto3.client(service_name="bedrock-agentcore-control")
response = acps.create_api_key_credential_provider(
    name="NasaAPIKey",
    apiKey="YOUR_NASA_API_KEY"
)
```

### OpenAPI Target (NASA APIs as MCP tools)

```python
nasa_openapi_s3_target_config = {
    "mcp": {
        "openApiSchema": {
            "s3": {"uri": "s3://bucket/nasa-openapi-spec.json"}
        }
    }
}
api_key_credential_config = [{
    "credentialProviderType": "API_KEY",
    "credentialProvider": {
        "apiKeyCredentialProvider": {
            "credentialParameterName": "api_key",
            "providerArn": credential_provider_arn,
            "credentialLocation": "QUERY_PARAMETER",
        }
    }
}]
gateway_client.create_gateway_target(
    gatewayIdentifier=gateway_id,
    name='NasaMarsAPIs',
    targetConfiguration=nasa_openapi_s3_target_config,
    credentialProviderConfigurations=api_key_credential_config
)
```

### Lambda Target (for custom tools like Mars Transform)

```python
lambda_target_config = {
    "mcp": {
        "lambda": {
            "lambdaArn": mars_transform_lambda_arn,
            "toolSchema": {"inlinePayload": tool_spec_json},
        }
    }
}
credential_config = [{"credentialProviderType": "GATEWAY_IAM_ROLE"}]
gateway_client.create_gateway_target(
    gatewayIdentifier=gateway_id,
    name='MarsTransformLayer',
    targetConfiguration=lambda_target_config,
    credentialProviderConfigurations=credential_config,
)
```

Lambda handler routes by tool name:
```python
def handler(event, context):
    tool_name = context.client_context.custom["bedrockAgentCoreToolName"]
    resource = tool_name.split("___")[1]  # e.g., "transform_temperature"
    # ... route to appropriate function
```

---

## Agent Code Pattern

### Local Prototype (Lab 01 style)

```python
from strands import Agent
from strands.models import BedrockModel
from strands.tools import tool

@tool
def read_sensors() -> dict:
    """Read current sensor telemetry from all greenhouse nodes."""
    # ... read from DynamoDB

@tool
def set_actuator(device: str, action: str, value: float) -> str:
    """Command a greenhouse actuator (pump, light, fan, heater)."""
    # ... publish to IoT Core MQTT

@tool
def get_nutritional_status() -> dict:
    """Check if crop output meets 4 astronauts' dietary needs for 450 days."""
    # ... calculate from crop profiles

model = BedrockModel(model_id="us.amazon.nova-pro-v1:0", temperature=0.3)
agent = Agent(
    model=model,
    tools=[read_sensors, set_actuator, get_nutritional_status],
    system_prompt=GREENHOUSE_SYSTEM_PROMPT
)
```

### With MCP Gateway (Lab 03 style — local + remote tools)

```python
from mcp.client.streamable_http import streamablehttp_client
from strands.tools.mcp.mcp_client import MCPClient

# Connect to our gateway (NASA APIs + Syngenta KB as MCP tools)
mcp_client = MCPClient(lambda: streamablehttp_client(
    gateway_url,
    headers={"Authorization": f"Bearer {token}"},
))

with mcp_client:
    # Combine local tools + MCP remote tools
    tools = [read_sensors, set_actuator, get_nutritional_status] + mcp_client.list_tools_sync()
    agent = Agent(model=model, tools=tools, system_prompt=SYSTEM_PROMPT)
    agent("Check Mars weather and adjust greenhouse accordingly")
```

### Deploy to Runtime (Lab 04 — 4 lines of code change)

```python
from bedrock_agentcore.runtime import BedrockAgentCoreApp

app = BedrockAgentCoreApp()

@app.entrypoint
async def invoke(payload, context=None):
    user_input = payload.get("prompt", "")
    session_id = context.session_id
    auth_header = (context.request_headers or {}).get('Authorization', '')

    # Setup MCP client with propagated auth
    mcp_client = MCPClient(lambda: streamablehttp_client(
        gateway_url, headers={"Authorization": auth_header}
    ))

    with mcp_client:
        tools = [read_sensors, set_actuator, get_nutritional_status] + mcp_client.list_tools_sync()
        agent = Agent(model=model, tools=tools, system_prompt=SYSTEM_PROMPT)
        response = agent(user_input)
        return response.message["content"][0]["text"]

if __name__ == "__main__":
    app.run()  # Serves on port 8080: /invocations + /ping
```

### Deployment

```python
from bedrock_agentcore_starter_toolkit import Runtime

runtime = Runtime()
runtime.configure(
    entrypoint="agent.py",
    execution_role=role_arn,
    auto_create_ecr=True,
    requirements_file="requirements.txt",
    region="us-east-1",
    agent_name="astrofarm_agent",
    authorizer_configuration={
        "customJWTAuthorizer": {
            "allowedClients": [client_id],
            "discoveryUrl": discovery_url,
        }
    },
)
launch_result = runtime.launch()
```

---

## Frontend Pattern (Lab 06)

### Streaming from AgentCore Runtime

```python
url = f"https://bedrock-agentcore.{region}.amazonaws.com/runtimes/{escaped_arn}/invocations"
headers = {
    "Authorization": f"Bearer {bearer_token}",
    "Content-Type": "application/json",
    "X-Amzn-Bedrock-AgentCore-Runtime-Session-Id": session_id,
}
response = requests.post(url, params={"qualifier": endpoint_name},
                         headers=headers, json=body, timeout=100, stream=True)

# SSE streaming
for line in response.iter_lines(chunk_size=1, decode_unicode=True):
    if line and line.startswith("data: "):
        yield line[6:]
```

Lab 06 uses Streamlit with `streamlit_cognito_auth.CognitoAuthenticator` for login. We can use this directly or adapt the streaming pattern to React.

---

## Cedar Policies (Access Control)

AgentCore supports Cedar-based policies for fine-grained tool access:

```cedar
// Allow agent to use specific tools
permit(
    principal,
    action in [AgentCore::Action::"NasaMarsAPIs___get_insight_weather",
               AgentCore::Action::"MarsTransformLayer___transform_temperature"],
    resource == AgentCore::Gateway::"arn:aws:bedrock-agentcore:us-east-1:ACCOUNT:gateway/GW_ID"
);

// Deny during emergency mode (context-based)
forbid(
    principal,
    action == AgentCore::Action::"MarsTransformLayer___inject_storm",
    resource == AgentCore::Gateway::"..."
) when {
    context.input has keywords && context.input.keywords like "*production*"
};
```

Can also generate policies from natural language:
```python
policy_client.generate_policy(
    policy_engine_id=engine_id,
    name="allow_weather_tools",
    resource={"arn": gateway_arn},
    content={"rawText": "Allow the greenhouse agent to check weather and control actuators"},
    fetch_assets=True,
)
```

---

## Dependencies

```
strands-agents
strands-agents-tools
boto3>=1.42.3
botocore>=1.42.3
bedrock-agentcore==1.1.1
bedrock-agentcore-starter-toolkit==0.2.3
aws-opentelemetry-distro==0.14.0
pyyaml
```

---

## Infrastructure (CloudFormation stack provisions)

- **DynamoDB** — telemetry + crop profiles tables
- **Lambda** — tool handlers (sensor reading, actuator commands, Mars transform)
- **Knowledge Base** — Bedrock KB with Titan embeddings (1024-dim), S3 vector store
- **IAM Roles** — RuntimeAgentCoreRole (Bedrock, ECR, X-Ray, memory) + GatewayAgentCoreRole (Lambda invoke)
- **SSM Parameters** — stores all resource IDs/ARNs for cross-component reference
- **Cognito** — user pool + app client for JWT auth

---

## Our Implementation Path

1. **Hour 0-4**: Run Lab 01 pattern — local agent with `@tool` decorators, connect to Syngenta MCP KB
2. **Hour 4-8**: Run Lab 03 pattern — create Gateway, wrap NASA InSight + DONKI as MCP tools via OpenAPI spec, add Lambda target for Mars Transform
3. **Hour 8-12**: Run Lab 04 pattern — deploy agent to AgentCore Runtime (4 lines)
4. **Hour 12-16**: Run Lab 06 pattern — Streamlit or React frontend with streaming
5. **Hour 16+**: Demo scenarios, polish, pitch prep
