# AgentCore Gateway — Deep Research for EDEN Implementation

> Researched 2026-03-19 from AWS docs, boto3 API reference, and awslabs tutorial notebooks.
> This is the ONLY reference the implementer needs.

---

## TL;DR — What We're Building

```
NASA InSight API ──┐
NASA DONKI API ────┤── OpenAPI spec → S3 → Gateway Target (API_KEY auth)
                   │
Mars Transform λ ──┤── Lambda Target (GATEWAY_IAM_ROLE auth)
                   │
Syngenta MCP KB ───┘── MCP Server Target (no auth, public endpoint)
                   │
                   ▼
         AgentCore Gateway (MCP protocol, Cognito JWT inbound auth)
              │
              ▼  gatewayUrl = https://<id>.gateway.bedrock-agentcore.us-west-2.amazonaws.com/mcp
              │
         EDEN Agent (Strands SDK + MCPClient)
```

---

## 1. Account & Resource Inventory

| Resource | Value |
|---|---|
| AWS Account | `658707946640` |
| Region | `us-west-2` |
| Cognito Pool ID | `us-west-2_i3WRiWZeL` |
| Cognito Client ID | `uq4s0nkf3hsre1jkd001km9n4` |
| Cognito Discovery URL | `https://cognito-idp.us-west-2.amazonaws.com/us-west-2_i3WRiWZeL/.well-known/openid-configuration` |
| S3 Bucket | `astrofarm-assets-20260319015916429700000001` |
| Lambda (Mars Transform) | `arn:aws:lambda:us-west-2:658707946640:function:eden-mars-transform` |
| ECR Repo | `658707946640.dkr.ecr.us-west-2.amazonaws.com/eden-agent` |
| NASA API Key | `YOUR_NASA_API_KEY` |
| Syngenta MCP KB | `https://kb-start-hack-gateway-buyjtibfpg.gateway.bedrock-agentcore.us-east-2.amazonaws.com/mcp` |

---

## 2. IAM — Gateway Execution Role

### 2a. Trust Policy

The role MUST trust `bedrock-agentcore.amazonaws.com`:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowBedrockAgentCoreAssumeRole",
      "Effect": "Allow",
      "Principal": {
        "Service": "bedrock-agentcore.amazonaws.com"
      },
      "Action": "sts:AssumeRole",
      "Condition": {
        "StringEquals": {
          "aws:SourceAccount": "658707946640"
        },
        "ArnLike": {
          "aws:SourceArn": "arn:aws:bedrock-agentcore:us-west-2:658707946640:*"
        }
      }
    }
  ]
}
```

### 2b. Permission Policy

The Gateway role needs these permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "LambdaInvoke",
      "Effect": "Allow",
      "Action": "lambda:InvokeFunction",
      "Resource": "arn:aws:lambda:us-west-2:658707946640:function:eden-mars-transform"
    },
    {
      "Sid": "S3ReadOpenAPISpec",
      "Effect": "Allow",
      "Action": ["s3:GetObject"],
      "Resource": "arn:aws:s3:::astrofarm-assets-20260319015916429700000001/nasa-openapi-spec.json"
    },
    {
      "Sid": "SecretsManagerReadAPIKey",
      "Effect": "Allow",
      "Action": ["secretsmanager:GetSecretValue"],
      "Resource": "arn:aws:secretsmanager:us-west-2:658707946640:secret:*"
    },
    {
      "Sid": "PolicyEngineOps",
      "Effect": "Allow",
      "Action": [
        "bedrock-agentcore:GetPolicyEngine",
        "bedrock-agentcore:AuthorizeAction",
        "bedrock-agentcore:PartiallyAuthorizeActions"
      ],
      "Resource": [
        "arn:aws:bedrock-agentcore:us-west-2:658707946640:policy-engine/*",
        "arn:aws:bedrock-agentcore:us-west-2:658707946640:gateway/*"
      ]
    }
  ]
}
```

### 2c. User/Admin Permissions (for deployment script)

The user running `deploy_agentcore.py` needs:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "GatewayManagement",
      "Effect": "Allow",
      "Action": [
        "bedrock-agentcore:CreateGateway",
        "bedrock-agentcore:UpdateGateway",
        "bedrock-agentcore:GetGateway",
        "bedrock-agentcore:DeleteGateway",
        "bedrock-agentcore:ListGateways",
        "bedrock-agentcore:CreateGatewayTarget",
        "bedrock-agentcore:UpdateGatewayTarget",
        "bedrock-agentcore:GetGatewayTarget",
        "bedrock-agentcore:DeleteGatewayTarget",
        "bedrock-agentcore:ListGatewayTargets"
      ],
      "Resource": "arn:aws:bedrock-agentcore:us-west-2:658707946640:gateway/*"
    },
    {
      "Sid": "CredentialProviders",
      "Effect": "Allow",
      "Action": [
        "bedrock-agentcore:CreateApiKeyCredentialProvider",
        "bedrock-agentcore:GetApiKeyCredentialProvider",
        "bedrock-agentcore:DeleteApiKeyCredentialProvider",
        "bedrock-agentcore:ListApiKeyCredentialProviders"
      ],
      "Resource": "*"
    },
    {
      "Sid": "PolicyEngineManagement",
      "Effect": "Allow",
      "Action": [
        "bedrock-agentcore:CreatePolicyEngine",
        "bedrock-agentcore:GetPolicyEngine",
        "bedrock-agentcore:DeletePolicyEngine",
        "bedrock-agentcore:ListPolicyEngines",
        "bedrock-agentcore:CreatePolicy",
        "bedrock-agentcore:GetPolicy",
        "bedrock-agentcore:DeletePolicy",
        "bedrock-agentcore:ListPolicies"
      ],
      "Resource": "arn:aws:bedrock-agentcore:us-west-2:658707946640:policy-engine/*"
    },
    {
      "Sid": "PassRole",
      "Effect": "Allow",
      "Action": "iam:PassRole",
      "Resource": "arn:aws:iam::658707946640:role/*",
      "Condition": {
        "StringEquals": {
          "iam:PassedToService": "bedrock-agentcore.amazonaws.com"
        }
      }
    }
  ]
}
```

---

## 3. Step-by-Step Deployment

### Step 1: Create API Key Credential Provider (NASA API key)

```python
import boto3

client = boto3.client('bedrock-agentcore-control', region_name='us-west-2')

response = client.create_api_key_credential_provider(
    name='NasaAPIKey',
    apiKey='YOUR_NASA_API_KEY',
    tags={'Project': 'EDEN', 'Purpose': 'NASA-InSight-DONKI'}
)

credential_provider_arn = response['credentialProviderArn']
secret_arn = response['apiKeySecretArn']['secretArn']
print(f"Credential Provider ARN: {credential_provider_arn}")
print(f"Secret ARN: {secret_arn}")
```

**Response shape:**
```python
{
    'apiKeySecretArn': {'secretArn': 'string'},
    'name': 'string',
    'credentialProviderArn': 'string'  # ← save this for target creation
}
```

### Step 2: Upload NASA OpenAPI Spec to S3

```python
import json
import boto3

s3 = boto3.client('s3', region_name='us-west-2')
BUCKET = 'astrofarm-assets-20260319015916429700000001'
SPEC_KEY = 'nasa-openapi-spec.json'

# The spec (see Section 5 below for full content)
with open('nasa-openapi-spec.json', 'rb') as f:
    s3.put_object(Bucket=BUCKET, Key=SPEC_KEY, Body=f)

openapi_s3_uri = f's3://{BUCKET}/{SPEC_KEY}'
print(f"Uploaded: {openapi_s3_uri}")
```

### Step 3: Create the Gateway

```python
import boto3

client = boto3.client('bedrock-agentcore-control', region_name='us-west-2')

COGNITO_DISCOVERY_URL = 'https://cognito-idp.us-west-2.amazonaws.com/us-west-2_i3WRiWZeL/.well-known/openid-configuration'
COGNITO_CLIENT_ID = 'uq4s0nkf3hsre1jkd001km9n4'
GATEWAY_ROLE_ARN = 'arn:aws:iam::658707946640:role/GatewayAgentCoreRole'  # from Pulumi

create_response = client.create_gateway(
    name='AstroFarmGateway',
    roleArn=GATEWAY_ROLE_ARN,
    protocolType='MCP',
    authorizerType='CUSTOM_JWT',
    authorizerConfiguration={
        'customJWTAuthorizer': {
            'allowedClients': [COGNITO_CLIENT_ID],
            'discoveryUrl': COGNITO_DISCOVERY_URL,
        }
    },
    description='EDEN Martian Greenhouse — NASA + Mars Transform + Syngenta KB',
    exceptionLevel='DEBUG',  # Enable debug logs during hackathon
)

gateway_id = create_response['gatewayId']
gateway_url = create_response['gatewayUrl']
gateway_arn = create_response.get('gatewayArn', '')
print(f"Gateway ID:  {gateway_id}")
print(f"Gateway URL: {gateway_url}")
print(f"Gateway ARN: {gateway_arn}")
```

**Response shape:**
```python
{
    'gatewayUrl': 'https://<id>.gateway.bedrock-agentcore.us-west-2.amazonaws.com/mcp',
    'gatewayId': 'string',
    'gatewayArn': 'arn:aws:bedrock-agentcore:us-west-2:658707946640:gateway/<id>',
    'name': 'AstroFarmGateway',
    'status': 'CREATING',   # → ACTIVE after ~30-60s
    'createdAt': datetime,
    'updatedAt': datetime,
}
```

**Wait for ACTIVE status:**
```python
import time

for _ in range(60):
    gw = client.get_gateway(gatewayIdentifier=gateway_id)
    status = gw.get('status', 'UNKNOWN')
    if status == 'ACTIVE':
        print(f"Gateway ACTIVE. URL: {gw['gatewayUrl']}")
        break
    if status in ('FAILED', 'DELETE_IN_PROGRESS'):
        raise RuntimeError(f"Gateway failed: {status}")
    time.sleep(5)
else:
    raise TimeoutError("Gateway did not become ACTIVE in 5 minutes")
```

### Step 4: Create NASA OpenAPI Target

```python
nasa_target = client.create_gateway_target(
    gatewayIdentifier=gateway_id,
    name='NasaMarsAPIs',
    description='NASA InSight weather + DONKI solar events via OpenAPI spec',
    targetConfiguration={
        'mcp': {
            'openApiSchema': {
                's3': {
                    'uri': f's3://{BUCKET}/{SPEC_KEY}',
                    'bucketOwnerAccountId': '658707946640',
                }
            }
        }
    },
    credentialProviderConfigurations=[
        {
            'credentialProviderType': 'API_KEY',
            'credentialProvider': {
                'apiKeyCredentialProvider': {
                    'providerArn': credential_provider_arn,
                    'credentialParameterName': 'api_key',
                    'credentialLocation': 'QUERY_PARAMETER',
                }
            }
        }
    ],
)

print(f"NASA target ID: {nasa_target['targetId']}")
print(f"NASA target status: {nasa_target['status']}")
```

**Key detail:** `credentialParameterName` = `'api_key'` because NASA APIs use `?api_key=KEY` query param.

**`credentialLocation` options:** `'QUERY_PARAMETER'` or `'HEADER'`.

### Step 5: Create Mars Transform Lambda Target

```python
import json

MARS_TRANSFORM_TOOL_SPEC = [
    {
        'name': 'transform_temperature',
        'description': 'Convert Earth temperature to Mars-equivalent using seasonal model',
        'inputSchema': {
            'type': 'object',
            'properties': {
                'temperature': {'type': 'number', 'description': 'Earth temperature in Celsius'},
                'sol': {'type': 'integer', 'description': 'Current Mars sol (day)'},
            },
            'required': ['temperature', 'sol'],
        },
        'outputSchema': {
            'type': 'object',
            'properties': {
                'mars_temperature': {'type': 'number'},
                'adjustment_factor': {'type': 'number'},
            },
        },
    },
    {
        'name': 'transform_pressure',
        'description': 'Convert Earth atmospheric pressure to Mars-equivalent (~6 hPa)',
        'inputSchema': {
            'type': 'object',
            'properties': {
                'pressure': {'type': 'number', 'description': 'Earth pressure in hPa'},
            },
            'required': ['pressure'],
        },
        'outputSchema': {
            'type': 'object',
            'properties': {
                'mars_pressure': {'type': 'number'},
            },
        },
    },
    {
        'name': 'transform_light',
        'description': 'Convert Earth light levels to Mars-equivalent accounting for distance and dust',
        'inputSchema': {
            'type': 'object',
            'properties': {
                'light': {'type': 'number', 'description': 'Earth light in lux'},
                'dust_opacity': {'type': 'number', 'description': 'Mars dust opacity (0.0-1.0)'},
            },
            'required': ['light'],
        },
        'outputSchema': {
            'type': 'object',
            'properties': {
                'mars_light': {'type': 'number'},
            },
        },
    },
]

lambda_target = client.create_gateway_target(
    gatewayIdentifier=gateway_id,
    name='MarsTransformLayer',
    description='Mars Transform Lambda — temperature, pressure, light conversion',
    targetConfiguration={
        'mcp': {
            'lambda': {
                'lambdaArn': 'arn:aws:lambda:us-west-2:658707946640:function:eden-mars-transform',
                'toolSchema': {
                    'inlinePayload': MARS_TRANSFORM_TOOL_SPEC,
                },
            }
        }
    },
    credentialProviderConfigurations=[
        {'credentialProviderType': 'GATEWAY_IAM_ROLE'}
    ],
)

print(f"Lambda target ID: {lambda_target['targetId']}")
print(f"Lambda target status: {lambda_target['status']}")
```

**Lambda handler routing pattern:**
```python
def handler(event, context):
    tool_name = context.client_context.custom["bedrockAgentCoreToolName"]
    resource = tool_name.split("___")[1]  # e.g., "transform_temperature"
    # Route to appropriate function based on resource name
```

### Step 6: Create Syngenta MCP Server Target

```python
syngenta_target = client.create_gateway_target(
    gatewayIdentifier=gateway_id,
    name='SyngentaCropKB',
    description='Syngenta Mars Crop Knowledge Base (organizer-provided MCP server)',
    targetConfiguration={
        'mcp': {
            'mcpServer': {
                'endpoint': 'https://kb-start-hack-gateway-buyjtibfpg.gateway.bedrock-agentcore.us-east-2.amazonaws.com/mcp'
            }
        }
    },
    # No credentials needed — public endpoint
)

print(f"Syngenta target ID: {syngenta_target['targetId']}")
```

**Note:** The Syngenta KB is in `us-east-2`. This is a cross-region call from our `us-west-2` gateway. This should work since it's just an HTTP endpoint — the gateway makes outbound HTTP requests to it.

### Step 7: Connect Agent to Gateway

```python
from strands import Agent
from strands.models import BedrockModel
from strands.tools.mcp.mcp_client import MCPClient
from mcp.client.streamable_http import streamablehttp_client

# Get Cognito access token (see Section 7 for auth details)
access_token = get_cognito_token()  # your auth function

# Create MCP client pointing at gateway
mcp_client = MCPClient(lambda: streamablehttp_client(
    gateway_url,  # https://<id>.gateway.bedrock-agentcore.us-west-2.amazonaws.com/mcp
    headers={'Authorization': f'Bearer {access_token}'},
))

model = BedrockModel(model_id='us.amazon.nova-pro-v1:0', temperature=0.3)

with mcp_client:
    # Discover all tools from all targets
    tools = mcp_client.list_tools_sync()
    print(f"Available tools: {[t.tool_name for t in tools]}")
    # Expected tools:
    #   NasaMarsAPIs___getInsightWeather
    #   NasaMarsAPIs___getDonkiCME
    #   NasaMarsAPIs___getDonkiMPC
    #   MarsTransformLayer___transform_temperature
    #   MarsTransformLayer___transform_pressure
    #   MarsTransformLayer___transform_light
    #   SyngentaCropKB___<various KB tools>

    # Combine with local tools
    local_tools = [read_sensors, set_actuator, get_nutritional_status]
    all_tools = local_tools + tools

    agent = Agent(model=model, tools=all_tools, system_prompt=SYSTEM_PROMPT)
    agent("Check Mars weather and adjust greenhouse accordingly")
```

**Tool naming convention:** `{targetName}___{operationId}`
(That's THREE underscores)

**Pagination for large tool lists:**
```python
def get_all_tools(mcp_client):
    tools = []
    pagination_token = None
    while True:
        tmp = mcp_client.list_tools_sync(pagination_token=pagination_token)
        tools.extend(tmp)
        if tmp.pagination_token is None:
            break
        pagination_token = tmp.pagination_token
    return tools
```

---

## 4. Cedar Policies (Access Control)

### 4a. Create Policy Engine

```python
client = boto3.client('bedrock-agentcore-control', region_name='us-west-2')

engine = client.create_policy_engine(
    name='eden_policy_engine',
    description='EDEN Greenhouse agent access control'
)

engine_id = engine['policyEngineId']
engine_arn = engine['policyEngineArn']
print(f"Policy Engine ID: {engine_id}")
print(f"Policy Engine ARN: {engine_arn}")
```

### 4b. Add Permit Policy

```python
GATEWAY_ARN = f'arn:aws:bedrock-agentcore:us-west-2:658707946640:gateway/{gateway_id}'

permit_statement = f"""permit(
    principal,
    action in [
        AgentCore::Action::"NasaMarsAPIs___getInsightWeather",
        AgentCore::Action::"NasaMarsAPIs___getDonkiCME",
        AgentCore::Action::"NasaMarsAPIs___getDonkiMPC",
        AgentCore::Action::"MarsTransformLayer___transform_temperature",
        AgentCore::Action::"MarsTransformLayer___transform_pressure",
        AgentCore::Action::"MarsTransformLayer___transform_light",
        AgentCore::Action::"SyngentaCropKB___query_knowledge_base"
    ],
    resource == AgentCore::Gateway::"{GATEWAY_ARN}"
);"""

client.create_policy(
    policyEngineId=engine_id,
    name='eden_allow_all_tools',
    description='Allow EDEN agent to use all greenhouse management tools',
    validationMode='FAIL_ON_ANY_FINDINGS',
    definition={
        'cedar': {
            'statement': permit_statement
        }
    }
)
```

### 4c. Add Forbid Policy (Emergency Mode)

```python
forbid_statement = f"""forbid(
    principal,
    action in [
        AgentCore::Action::"MarsTransformLayer___transform_temperature",
        AgentCore::Action::"MarsTransformLayer___transform_pressure"
    ],
    resource == AgentCore::Gateway::"{GATEWAY_ARN}"
) when {{
    context.input has keywords &&
    context.input.keywords like "*override*"
}};"""

client.create_policy(
    policyEngineId=engine_id,
    name='eden_deny_override_keywords',
    description='Deny transform tools when input contains override keywords',
    validationMode='FAIL_ON_ANY_FINDINGS',
    definition={
        'cedar': {
            'statement': forbid_statement
        }
    }
)
```

### 4d. Attach Policy Engine to Gateway

**Option A: At gateway creation time** (add to create_gateway call):
```python
policyEngineConfiguration={
    'arn': engine_arn,
    'mode': 'LOG_ONLY'  # Use LOG_ONLY for testing, ENFORCE for production
}
```

**Option B: Update existing gateway:**
```python
client.update_gateway(
    gatewayIdentifier=gateway_id,
    policyEngineConfiguration={
        'arn': engine_arn,
        'mode': 'ENFORCE'
    }
)
```

### Cedar Policy Semantics

| Rule | Behavior |
|---|---|
| Default | **DENY** — all actions denied unless explicitly permitted |
| `permit` | Allows action if conditions match |
| `forbid` | Denies action, **overrides** any matching `permit` (forbid-wins) |
| No match | DENY (default deny) |

### Entity Types

| Cedar Entity | Maps To |
|---|---|
| `principal` | OAuth user/agent identity (from JWT) |
| `AgentCore::Action::"TargetName___toolName"` | Tool invocation |
| `AgentCore::Gateway::"arn:..."` | The gateway resource |
| `AgentCore::OAuthUser` | Principal type for JWT-authenticated callers |

### Condition Attributes

- `principal.hasTag("username")` — check JWT claims
- `principal.getTag("username")` — read JWT claim value
- `context.input.<param>` — tool input parameters
- `context.input has keywords` — check if input has keywords field

---

## 5. NASA OpenAPI Specification (Complete)

Save as `nasa-openapi-spec.json` and upload to S3:

```json
{
  "openapi": "3.0.3",
  "info": {
    "title": "NASA Mars APIs for EDEN Greenhouse",
    "description": "InSight weather + DONKI solar events for Mars greenhouse management",
    "version": "1.0.0"
  },
  "servers": [
    { "url": "https://api.nasa.gov" }
  ],
  "paths": {
    "/insight_weather/": {
      "get": {
        "summary": "Get Mars surface weather from InSight lander (Sol 675-681, Oct 2020 — frozen data)",
        "operationId": "getInsightWeather",
        "parameters": [
          {
            "name": "feedtype",
            "in": "query",
            "required": true,
            "description": "Response format (only 'json' supported)",
            "schema": { "type": "string", "enum": ["json"] }
          },
          {
            "name": "ver",
            "in": "query",
            "required": true,
            "description": "API version (only '1.0' supported)",
            "schema": { "type": "string", "enum": ["1.0"] }
          }
        ],
        "responses": {
          "200": {
            "description": "Per-sol weather: temperature (AT), pressure (PRE), wind speed (HWS), wind direction (WD), season",
            "content": {
              "application/json": {
                "schema": { "$ref": "#/components/schemas/InsightWeatherResponse" }
              }
            }
          }
        }
      }
    },
    "/DONKI/CME": {
      "get": {
        "summary": "Get Coronal Mass Ejection events that could affect Mars solar exposure",
        "operationId": "getDonkiCME",
        "parameters": [
          {
            "name": "startDate",
            "in": "query",
            "required": false,
            "description": "Start date (YYYY-MM-DD). Default: 30 days ago",
            "schema": { "type": "string", "format": "date" }
          },
          {
            "name": "endDate",
            "in": "query",
            "required": false,
            "description": "End date (YYYY-MM-DD). Default: today",
            "schema": { "type": "string", "format": "date" }
          }
        ],
        "responses": {
          "200": {
            "description": "Array of CME events with time, source location, speed, and analysis",
            "content": {
              "application/json": {
                "schema": {
                  "type": "array",
                  "items": { "$ref": "#/components/schemas/CMEEvent" }
                }
              }
            }
          }
        }
      }
    },
    "/DONKI/MPC": {
      "get": {
        "summary": "Get Mars Magnetopause Crossing events — indicates solar wind pressure changes",
        "operationId": "getDonkiMPC",
        "parameters": [
          {
            "name": "startDate",
            "in": "query",
            "required": false,
            "description": "Start date (YYYY-MM-DD). Default: 30 days ago",
            "schema": { "type": "string", "format": "date" }
          },
          {
            "name": "endDate",
            "in": "query",
            "required": false,
            "description": "End date (YYYY-MM-DD). Default: today",
            "schema": { "type": "string", "format": "date" }
          }
        ],
        "responses": {
          "200": {
            "description": "Array of magnetopause crossing events with linked CME activity",
            "content": {
              "application/json": {
                "schema": {
                  "type": "array",
                  "items": { "$ref": "#/components/schemas/MPCEvent" }
                }
              }
            }
          }
        }
      }
    }
  },
  "components": {
    "schemas": {
      "InsightWeatherResponse": {
        "type": "object",
        "description": "Weather data keyed by sol number, plus metadata",
        "properties": {
          "sol_keys": {
            "type": "array",
            "description": "List of sol numbers in this payload",
            "items": { "type": "string" }
          },
          "validity_checks": {
            "type": "object",
            "description": "Data quality per sol and sensor",
            "additionalProperties": {
              "type": "object",
              "properties": {
                "AT": { "$ref": "#/components/schemas/SensorValidity" },
                "HWS": { "$ref": "#/components/schemas/SensorValidity" },
                "PRE": { "$ref": "#/components/schemas/SensorValidity" },
                "WD": { "$ref": "#/components/schemas/SensorValidity" }
              }
            }
          }
        },
        "additionalProperties": {
          "oneOf": [{ "$ref": "#/components/schemas/SolWeather" }]
        }
      },
      "SolWeather": {
        "type": "object",
        "properties": {
          "AT": { "$ref": "#/components/schemas/SensorData" },
          "HWS": { "$ref": "#/components/schemas/SensorData" },
          "PRE": { "$ref": "#/components/schemas/SensorData" },
          "WD": {
            "type": "object",
            "properties": {
              "most_common": { "$ref": "#/components/schemas/WindCompassPoint" }
            },
            "additionalProperties": { "$ref": "#/components/schemas/WindCompassPoint" }
          },
          "Season": { "type": "string", "enum": ["winter", "spring", "summer", "fall"] },
          "First_UTC": { "type": "string", "format": "date-time" },
          "Last_UTC": { "type": "string", "format": "date-time" }
        }
      },
      "SensorData": {
        "type": "object",
        "properties": {
          "av": { "type": "number", "description": "Average" },
          "ct": { "type": "number", "description": "Sample count" },
          "mn": { "type": "number", "description": "Minimum" },
          "mx": { "type": "number", "description": "Maximum" }
        }
      },
      "WindCompassPoint": {
        "type": "object",
        "properties": {
          "compass_degrees": { "type": "number" },
          "compass_point": { "type": "string" },
          "compass_right": { "type": "number" },
          "compass_up": { "type": "number" },
          "ct": { "type": "number" }
        }
      },
      "SensorValidity": {
        "type": "object",
        "properties": {
          "sol_hours_with_data": {
            "type": "array",
            "items": { "type": "integer", "minimum": 0, "maximum": 23 }
          },
          "valid": { "type": "boolean" }
        }
      },
      "CMEEvent": {
        "type": "object",
        "properties": {
          "activityID": { "type": "string" },
          "startTime": { "type": "string", "format": "date-time" },
          "sourceLocation": { "type": "string", "description": "Solar coordinates (e.g., S15W25)" },
          "note": { "type": "string" },
          "cmeAnalyses": {
            "type": "array",
            "items": {
              "type": "object",
              "properties": {
                "speed": { "type": "number", "description": "CME speed in km/s" },
                "halfAngle": { "type": "number", "description": "Half-angle in degrees" },
                "type": { "type": "string", "description": "S (slow), C (common), O (other)" },
                "isMostAccurate": { "type": "boolean" }
              }
            }
          }
        }
      },
      "MPCEvent": {
        "type": "object",
        "properties": {
          "eventTime": { "type": "string", "format": "date-time" },
          "instruments": {
            "type": "array",
            "items": {
              "type": "object",
              "properties": {
                "displayName": { "type": "string" }
              }
            }
          },
          "linkedEvents": {
            "type": "array",
            "items": {
              "type": "object",
              "properties": {
                "activityID": { "type": "string" }
              }
            }
          }
        }
      }
    }
  }
}
```

---

## 6. Gateway URL Format

After `create_gateway()`, the response contains `gatewayUrl`:

```
https://<gateway-id>.gateway.bedrock-agentcore.<region>.amazonaws.com/mcp
```

For us:
```
https://<id>.gateway.bedrock-agentcore.us-west-2.amazonaws.com/mcp
```

This is a standard MCP Streamable HTTP endpoint. Agents connect using:
```python
from mcp.client.streamable_http import streamablehttp_client

streamablehttp_client(gateway_url, headers={"Authorization": f"Bearer {token}"})
```

---

## 7. Cognito Authentication

### Getting an Access Token (M2M / Client Credentials)

```python
import boto3
import requests

cognito = boto3.client('cognito-idp', region_name='us-west-2')

# For M2M (machine-to-machine) — needs client secret
# Our Cognito app client must have client credentials flow enabled
COGNITO_DOMAIN = 'your-domain.auth.us-west-2.amazoncognito.com'  # set in Cognito
CLIENT_ID = 'uq4s0nkf3hsre1jkd001km9n4'
CLIENT_SECRET = '<from Cognito console>'  # if app client has a secret

token_url = f'https://{COGNITO_DOMAIN}/oauth2/token'
response = requests.post(token_url, data={
    'grant_type': 'client_credentials',
    'client_id': CLIENT_ID,
    'client_secret': CLIENT_SECRET,
    'scope': 'your-scopes',
}, headers={'Content-Type': 'application/x-www-form-urlencoded'})

access_token = response.json()['access_token']
```

### Using Starter Toolkit (easier)

```python
from bedrock_agentcore_starter_toolkit.operations.gateway.client import GatewayClient

gw_client = GatewayClient(region_name='us-west-2')

# If the toolkit created the Cognito pool:
client_info = {...}  # from gateway_config.json
access_token = gw_client.get_access_token_for_cognito(client_info)
```

### Using NONE Auth (simpler, for hackathon)

If auth complexity is blocking, use `authorizerType='NONE'`:
```python
client.create_gateway(
    name='AstroFarmGateway',
    roleArn=GATEWAY_ROLE_ARN,
    protocolType='MCP',
    authorizerType='NONE',  # No auth required — OK for hackathon demo
)
```
Then no `Authorization` header needed in MCP client.

---

## 8. Gotchas & Known Issues

### Critical

1. **IAM propagation delay**: Wait 10-30 seconds after creating/modifying IAM roles before using them. The `fix_iam_permissions()` in starter toolkit waits 30s.

2. **DNS propagation**: Gateway URL may take 30-60s to resolve after creation. The `get_gateway()` polling loop handles this.

3. **Pydantic version conflict**: If you get `TypeError: model_schema() got unexpected keyword argument 'generic_origin'`, pin `pydantic==2.7.2` and `pydantic-core==2.27.2`.

4. **Tool naming**: Tools are named `{targetName}___{operationId}` (THREE underscores). The `operationId` comes from the OpenAPI spec or the `name` field in Lambda toolSchema.

5. **Credential array limit**: `credentialProviderConfigurations` has a **fixed size of 1 item** per target. You cannot attach multiple credential providers to one target.

### Region Considerations

6. **Cross-region targets**: Our gateway is in `us-west-2`, Syngenta KB is in `us-east-2`. This works because the gateway makes outbound HTTP requests. The MCP server target just needs a reachable URL.

7. **AgentCore availability**: AgentCore Gateway is available in `us-west-2` (confirmed in docs). The default region in the starter toolkit is `us-west-2`.

### Operational

8. **Token expiration**: Cognito tokens expire after 1 hour. The agent must refresh tokens for long-running sessions.

9. **Frozen InSight data**: The InSight API is live but returns data frozen at Sol 675-681 (Oct 2020). This is fine for our demo — it's real Mars data.

10. **Lambda tool routing**: The Lambda handler gets the tool name via `context.client_context.custom["bedrockAgentCoreToolName"]`. Split on `___` to get the resource name.

11. **Gateway status polling**: After `create_gateway()`, status goes `CREATING → ACTIVE`. After `create_gateway_target()`, status goes `CREATING → READY`. Both need polling.

12. **No Pulumi support**: As of March 2026, there is no Pulumi provider for AgentCore. Use boto3 directly (our `deploy_agentcore.py` script).

### Policy

13. **Default deny**: Cedar policies use default-deny. If you attach a policy engine without any `permit` policies, ALL tool calls are denied.

14. **forbid wins**: A single matching `forbid` overrides all `permit` policies. Be careful with broad forbid rules.

15. **LOG_ONLY mode**: Start with `mode='LOG_ONLY'` to test policies without blocking. Check CloudWatch logs. Switch to `ENFORCE` when ready.

---

## 9. Complete Deployment Script Outline

```python
#!/usr/bin/env python3
"""Deploy AgentCore Gateway for EDEN — run after `pulumi up`."""

import boto3, json, time

REGION = 'us-west-2'
ACCOUNT = '658707946640'
BUCKET = 'astrofarm-assets-20260319015916429700000001'

client = boto3.client('bedrock-agentcore-control', region_name=REGION)

# 1. API Key Credential Provider
cred = client.create_api_key_credential_provider(
    name='NasaAPIKey',
    apiKey='YOUR_NASA_API_KEY',
)
cred_arn = cred['credentialProviderArn']

# 2. Upload OpenAPI spec to S3
s3 = boto3.client('s3', region_name=REGION)
with open('nasa-openapi-spec.json', 'rb') as f:
    s3.put_object(Bucket=BUCKET, Key='nasa-openapi-spec.json', Body=f)

# 3. Create Gateway
gw = client.create_gateway(
    name='AstroFarmGateway',
    roleArn=f'arn:aws:iam::{ACCOUNT}:role/GatewayAgentCoreRole',
    protocolType='MCP',
    authorizerType='CUSTOM_JWT',
    authorizerConfiguration={
        'customJWTAuthorizer': {
            'allowedClients': ['uq4s0nkf3hsre1jkd001km9n4'],
            'discoveryUrl': f'https://cognito-idp.{REGION}.amazonaws.com/us-west-2_i3WRiWZeL/.well-known/openid-configuration',
        }
    },
    exceptionLevel='DEBUG',
)
gw_id = gw['gatewayId']
gw_url = gw['gatewayUrl']

# Wait for ACTIVE
for _ in range(60):
    status = client.get_gateway(gatewayIdentifier=gw_id)['status']
    if status == 'ACTIVE': break
    time.sleep(5)

# 4. NASA OpenAPI target
client.create_gateway_target(
    gatewayIdentifier=gw_id,
    name='NasaMarsAPIs',
    targetConfiguration={'mcp': {'openApiSchema': {'s3': {'uri': f's3://{BUCKET}/nasa-openapi-spec.json'}}}},
    credentialProviderConfigurations=[{
        'credentialProviderType': 'API_KEY',
        'credentialProvider': {'apiKeyCredentialProvider': {
            'providerArn': cred_arn,
            'credentialParameterName': 'api_key',
            'credentialLocation': 'QUERY_PARAMETER',
        }}
    }],
)

# 5. Lambda target
client.create_gateway_target(
    gatewayIdentifier=gw_id,
    name='MarsTransformLayer',
    targetConfiguration={'mcp': {'lambda': {
        'lambdaArn': f'arn:aws:lambda:{REGION}:{ACCOUNT}:function:eden-mars-transform',
        'toolSchema': {'inlinePayload': MARS_TRANSFORM_TOOL_SPEC},  # from Section 3 Step 5
    }}},
    credentialProviderConfigurations=[{'credentialProviderType': 'GATEWAY_IAM_ROLE'}],
)

# 6. Syngenta MCP target
client.create_gateway_target(
    gatewayIdentifier=gw_id,
    name='SyngentaCropKB',
    targetConfiguration={'mcp': {'mcpServer': {
        'endpoint': 'https://kb-start-hack-gateway-buyjtibfpg.gateway.bedrock-agentcore.us-east-2.amazonaws.com/mcp'
    }}},
)

print(f"GATEWAY URL: {gw_url}")
print(f"GATEWAY ID:  {gw_id}")
```

---

## 10. Target Configuration Reference (All Variants)

### OpenAPI from S3
```python
{'mcp': {'openApiSchema': {'s3': {'uri': 's3://bucket/spec.json', 'bucketOwnerAccountId': '123456789012'}}}}
```

### OpenAPI inline
```python
{'mcp': {'openApiSchema': {'inlinePayload': '{"openapi":"3.0.3",...}'}}}
```

### Lambda with inline tool spec
```python
{'mcp': {'lambda': {'lambdaArn': 'arn:...', 'toolSchema': {'inlinePayload': [...]}}}}
```

### Lambda with S3 tool spec
```python
{'mcp': {'lambda': {'lambdaArn': 'arn:...', 'toolSchema': {'s3': {'uri': 's3://bucket/tools.json'}}}}}
```

### MCP Server (remote)
```python
{'mcp': {'mcpServer': {'endpoint': 'https://...'}}}
```

### API Gateway
```python
{'mcp': {'apiGateway': {'restApiId': 'abc123', 'stage': 'prod', 'apiGatewayToolConfiguration': {
    'toolFilters': [{'filterPath': '/pets', 'methods': ['GET']}],
    'toolOverrides': [{'name': 'get_pet', 'description': '...', 'path': '/pets/{id}', 'method': 'GET'}]
}}}}
```

### Smithy Model
```python
{'mcp': {'smithyModel': {'inlinePayload': '...'}}}
# or
{'mcp': {'smithyModel': {'s3': {'uri': 's3://bucket/model.smithy'}}}}
```

---

## 11. Credential Provider Types

| Type | Use Case | Configuration |
|---|---|---|
| `GATEWAY_IAM_ROLE` | Lambda, AWS services | `[{'credentialProviderType': 'GATEWAY_IAM_ROLE'}]` |
| `API_KEY` | REST APIs with API keys | See NASA target example above |
| `OAUTH` | APIs with OAuth2 | `{'oauthCredentialProvider': {'providerArn': '...', 'scopes': [...], 'grantType': 'CLIENT_CREDENTIALS'}}` |

---

## 12. Starter Toolkit Alternative

If manual boto3 is too verbose, the `bedrock-agentcore-starter-toolkit` provides a simpler CLI:

```bash
pip install bedrock-agentcore-starter-toolkit

# Create gateway with auto-configured Cognito
agentcore create_mcp_gateway --region us-west-2 --name AstroFarmGateway

# Or via Python
from bedrock_agentcore_starter_toolkit.operations.gateway.client import GatewayClient
client = GatewayClient(region_name='us-west-2')
gateway = client.create_mcp_gateway(name='AstroFarmGateway', enable_semantic_search=True)
```

The toolkit auto-creates Cognito pool, IAM role, and configures everything. But we have Cognito already via Pulumi, so direct boto3 gives more control.

---

## 13. Dependencies

```
boto3>=1.42.3
botocore>=1.42.3
bedrock-agentcore==1.1.1
bedrock-agentcore-starter-toolkit==0.2.3
strands-agents
strands-agents-tools
mcp
pydantic==2.7.2
```

---

## Sources

- [AWS AgentCore Gateway Docs](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway.html)
- [CreateGateway API](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway-create-api.html)
- [CreateGatewayTarget API](https://docs.aws.amazon.com/bedrock-agentcore-control/latest/APIReference/API_CreateGatewayTarget.html)
- [create_api_key_credential_provider boto3](https://docs.aws.amazon.com/boto3/latest/reference/services/bedrock-agentcore-control/client/create_api_key_credential_provider.html)
- [create_gateway_target boto3](https://docs.aws.amazon.com/boto3/latest/reference/services/bedrock-agentcore-control/client/create_gateway_target.html)
- [Cedar Policy Docs](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/policy-understanding-cedar.html)
- [IAM Permissions](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/policy-permissions.html)
- [Gateway Quick Start](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway-quick-start.html)
- [OpenAPI→MCP Tutorial (NASA)](https://github.com/awslabs/amazon-bedrock-agentcore-samples/blob/main/01-tutorials/02-AgentCore-gateway/02-transform-apis-into-mcp-tools/01-transform-openapi-into-mcp-tools/01-openapis-into-mcp-api-key.ipynb)
- [Lab 03 E2E Tutorial](https://github.com/awslabs/amazon-bedrock-agentcore-samples/blob/main/01-tutorials/09-AgentCore-E2E/strands-agents/lab-03-agentcore-gateway.ipynb)
- [Policy Engine Creation](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/policy-create-engine.html)
- [Add Policies to Engine](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/add-policies-to-engine.html)
- [Create Gateway with Policy](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/create-gateway-with-policy.html)
