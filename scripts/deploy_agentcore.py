#!/usr/bin/env python3
"""Deploy AgentCore Gateway for EDEN — NASA + Mars Transform + Syngenta KB.

Creates:
  1. API Key credential provider for NASA API key
  2. Uploads NASA OpenAPI spec to S3
  3. AgentCore Gateway (MCP protocol, Cognito JWT or NONE auth)
  4. 3 Gateway Targets: NASA OpenAPI, Mars Transform Lambda, Syngenta MCP
  5. Cedar policy engine with permit/forbid policies

Usage:
    python scripts/deploy_agentcore.py
    python scripts/deploy_agentcore.py --auth none       # skip Cognito for speed
    python scripts/deploy_agentcore.py --skip-policies   # skip Cedar policies
    python scripts/deploy_agentcore.py --dry-run         # print plan, don't deploy

Environment:
    AWS_REGION (default: us-west-2)
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import subprocess
import sys
import time

import boto3
from botocore.exceptions import ClientError

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────────────────

REGION = "us-west-2"
ACCOUNT = "658707946640"
BUCKET = "astrofarm-assets-20260319015916429700000001"

GATEWAY_NAME = "AstroFarmGateway"
NASA_TARGET_NAME = "NasaMarsAPIs"
LAMBDA_TARGET_NAME = "MarsTransformLayer"
SYNGENTA_TARGET_NAME = "SyngentaCropKB"

NASA_API_KEY = "YOUR_NASA_API_KEY"
LAMBDA_ARN = f"arn:aws:lambda:{REGION}:{ACCOUNT}:function:eden-mars-transform"
SYNGENTA_MCP_URL = "https://kb-start-hack-gateway-buyjtibfpg.gateway.bedrock-agentcore.us-east-2.amazonaws.com/mcp"

COGNITO_POOL_ID = "us-west-2_i3WRiWZeL"
COGNITO_CLIENT_ID = "uq4s0nkf3hsre1jkd001km9n4"
COGNITO_DISCOVERY_URL = f"https://cognito-idp.{REGION}.amazonaws.com/{COGNITO_POOL_ID}/.well-known/openid-configuration"

SPEC_KEY = "nasa-openapi-spec.json"
SPEC_LOCAL_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), SPEC_KEY)

# Mars Transform Lambda tool spec (inline) — must be a list, not JSON string
MARS_TRANSFORM_TOOL_SPEC = [
    {
        "name": "transform_temperature",
        "description": "Convert Earth temperature to Mars-equivalent using seasonal model",
        "inputSchema": {
            "type": "object",
            "properties": {
                "temperature": {"type": "number", "description": "Earth temperature in Celsius"},
                "sol": {"type": "integer", "description": "Current Mars sol (day)"},
            },
            "required": ["temperature", "sol"],
        },
    },
    {
        "name": "transform_pressure",
        "description": "Convert Earth atmospheric pressure to Mars-equivalent (~6 hPa)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "pressure": {"type": "number", "description": "Earth pressure in hPa"},
            },
            "required": ["pressure"],
        },
    },
    {
        "name": "transform_light",
        "description": "Convert Earth light levels to Mars-equivalent accounting for distance and dust",
        "inputSchema": {
            "type": "object",
            "properties": {
                "light": {"type": "number", "description": "Earth light in lux"},
                "dust_opacity": {"type": "number", "description": "Mars dust opacity (0.0-1.0)"},
            },
            "required": ["light"],
        },
    },
]


# ── Pulumi output reader ────────────────────────────────────────────────


def get_pulumi_output(key: str, stack: str = "dev") -> str:
    """Read a single Pulumi stack output."""
    try:
        result = subprocess.run(
            ["uv", "run", "pulumi", "stack", "output", key, "--stack", stack],
            capture_output=True, text=True, check=True, cwd="infra",
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""


def get_gateway_role_arn(stack: str = "dev") -> str:
    """Get gateway role ARN from Pulumi or construct default."""
    arn = get_pulumi_output("gateway_role_arn", stack)
    if arn and arn != "TODO-create-via-cli":
        return arn
    # Fallback: use the expected role name from Pulumi __main__.py
    return f"arn:aws:iam::{ACCOUNT}:role/GatewayAgentCoreRole"


# ── Helpers ──────────────────────────────────────────────────────────────


def wait_for_status(
    check_fn,
    success: str,
    failure: set[str],
    label: str,
    timeout_s: int = 300,
    interval_s: int = 5,
) -> dict:
    """Poll a status-returning function until success, failure, or timeout."""
    for _ in range(timeout_s // interval_s):
        result = check_fn()
        status = result.get("status", "UNKNOWN")
        if status == success:
            log.info("%s is %s", label, success)
            return result
        if status in failure:
            log.error("%s failed: %s", label, status)
            sys.exit(1)
        time.sleep(interval_s)
    log.error("%s did not reach %s within %ds", label, success, timeout_s)
    sys.exit(1)


def find_existing(list_fn, name_field: str, name_value: str, items_key: str = "items") -> dict | None:
    """Search existing resources by name to avoid duplicates."""
    try:
        response = list_fn()
        for item in response.get(items_key, []):
            if item.get(name_field) == name_value or item.get("name") == name_value:
                return item
    except ClientError:
        pass
    return None


# ── Step 1: API Key Credential Provider ──────────────────────────────────


def ensure_credential_provider(client) -> str:
    """Create or find NASA API key credential provider. Returns ARN."""
    # Check existing
    try:
        existing = client.list_api_key_credential_providers()
        for cp in existing.get("credentialProviders", existing.get("items", [])):
            if cp.get("name") == "NasaAPIKey":
                arn = cp["credentialProviderArn"]
                log.info("Credential provider already exists: %s", arn)
                return arn
    except (ClientError, KeyError):
        pass

    log.info("Creating NASA API key credential provider...")
    response = client.create_api_key_credential_provider(
        name="NasaAPIKey",
        apiKey=NASA_API_KEY,
    )
    arn = response["credentialProviderArn"]
    log.info("Credential provider created: %s", arn)
    return arn


# ── Step 2: Upload NASA OpenAPI Spec ─────────────────────────────────────


def upload_openapi_spec() -> str:
    """Upload NASA OpenAPI spec to S3. Returns S3 URI."""
    s3 = boto3.client("s3", region_name=REGION)
    s3_uri = f"s3://{BUCKET}/{SPEC_KEY}"

    if not os.path.exists(SPEC_LOCAL_PATH):
        log.error("NASA OpenAPI spec not found at %s", SPEC_LOCAL_PATH)
        sys.exit(1)

    log.info("Uploading %s to %s ...", SPEC_LOCAL_PATH, s3_uri)
    with open(SPEC_LOCAL_PATH, "rb") as f:
        s3.put_object(
            Bucket=BUCKET,
            Key=SPEC_KEY,
            Body=f,
            ContentType="application/json",
        )
    log.info("Uploaded: %s", s3_uri)
    return s3_uri


# ── Step 3: Create Gateway ───────────────────────────────────────────────


def ensure_gateway(client, role_arn: str, auth_type: str = "CUSTOM_JWT") -> dict:
    """Create or find the AgentCore Gateway. Returns gateway dict."""
    existing = find_existing(client.list_gateways, "name", GATEWAY_NAME)
    if existing:
        gw_id = existing["gatewayId"]
        log.info("Gateway '%s' already exists: %s", GATEWAY_NAME, gw_id)
        gw = client.get_gateway(gatewayIdentifier=gw_id)
        if gw.get("status") not in ("ACTIVE", "READY"):
            log.info("Waiting for existing gateway to become READY...")
            gw = wait_for_status(
                lambda: client.get_gateway(gatewayIdentifier=gw_id),
                "READY", {"FAILED", "DELETE_IN_PROGRESS"}, "Gateway",
            )
        return gw

    log.info("Creating gateway '%s' (auth=%s)...", GATEWAY_NAME, auth_type)

    kwargs = dict(
        name=GATEWAY_NAME,
        roleArn=role_arn,
        protocolType="MCP",
        description="EDEN Martian Greenhouse — NASA + Mars Transform + Syngenta KB",
        exceptionLevel="DEBUG",
    )

    if auth_type == "CUSTOM_JWT":
        kwargs["authorizerType"] = "CUSTOM_JWT"
        kwargs["authorizerConfiguration"] = {
            "customJWTAuthorizer": {
                "allowedClients": [COGNITO_CLIENT_ID],
                "discoveryUrl": COGNITO_DISCOVERY_URL,
            }
        }
    else:
        kwargs["authorizerType"] = "NONE"

    response = client.create_gateway(**kwargs)
    gw_id = response["gatewayId"]
    log.info("Gateway created: %s — waiting for ACTIVE...", gw_id)

    gw = wait_for_status(
        lambda: client.get_gateway(gatewayIdentifier=gw_id),
        "READY", {"FAILED", "DELETE_IN_PROGRESS"}, "Gateway",
    )
    return gw


# ── Step 4: Create Targets ───────────────────────────────────────────────


def _target_exists(client, gateway_id: str, target_name: str) -> dict | None:
    """Check if a target already exists on the gateway."""
    try:
        targets = client.list_gateway_targets(gatewayIdentifier=gateway_id)
        for t in targets.get("items", []):
            if t.get("name") == target_name:
                return t
    except ClientError:
        pass
    return None


def create_nasa_target(client, gateway_id: str, credential_provider_arn: str) -> dict:
    """Create NASA OpenAPI gateway target."""
    existing = _target_exists(client, gateway_id, NASA_TARGET_NAME)
    if existing:
        log.info("NASA target already exists: %s", existing.get("targetId"))
        return existing

    log.info("Creating NASA OpenAPI target '%s'...", NASA_TARGET_NAME)
    response = client.create_gateway_target(
        gatewayIdentifier=gateway_id,
        name=NASA_TARGET_NAME,
        description="NASA InSight weather + DONKI solar events via OpenAPI spec",
        targetConfiguration={
            "mcp": {
                "openApiSchema": {
                    "s3": {
                        "uri": f"s3://{BUCKET}/{SPEC_KEY}",
                        "bucketOwnerAccountId": ACCOUNT,
                    }
                }
            }
        },
        credentialProviderConfigurations=[
            {
                "credentialProviderType": "API_KEY",
                "credentialProvider": {
                    "apiKeyCredentialProvider": {
                        "providerArn": credential_provider_arn,
                        "credentialParameterName": "api_key",
                        "credentialLocation": "QUERY_PARAMETER",
                    }
                },
            }
        ],
    )
    log.info("NASA target created: %s (status=%s)",
             response.get("targetId"), response.get("status"))
    return response


def create_lambda_target(client, gateway_id: str) -> dict:
    """Create Mars Transform Lambda gateway target."""
    existing = _target_exists(client, gateway_id, LAMBDA_TARGET_NAME)
    if existing:
        log.info("Lambda target already exists: %s", existing.get("targetId"))
        return existing

    log.info("Creating Lambda target '%s'...", LAMBDA_TARGET_NAME)
    response = client.create_gateway_target(
        gatewayIdentifier=gateway_id,
        name=LAMBDA_TARGET_NAME,
        description="Mars Transform Lambda — temperature, pressure, light conversion",
        targetConfiguration={
            "mcp": {
                "lambda": {
                    "lambdaArn": LAMBDA_ARN,
                    "toolSchema": {"inlinePayload": MARS_TRANSFORM_TOOL_SPEC},  # list, not JSON string
                }
            }
        },
        credentialProviderConfigurations=[
            {"credentialProviderType": "GATEWAY_IAM_ROLE"}
        ],
    )
    log.info("Lambda target created: %s (status=%s)",
             response.get("targetId"), response.get("status"))
    return response


def create_syngenta_target(client, gateway_id: str) -> dict:
    """Create Syngenta MCP Knowledge Base gateway target."""
    existing = _target_exists(client, gateway_id, SYNGENTA_TARGET_NAME)
    if existing:
        log.info("Syngenta target already exists: %s", existing.get("targetId"))
        return existing

    log.info("Creating Syngenta MCP target '%s'...", SYNGENTA_TARGET_NAME)
    response = client.create_gateway_target(
        gatewayIdentifier=gateway_id,
        name=SYNGENTA_TARGET_NAME,
        description="Syngenta Mars Crop Knowledge Base (organizer-provided MCP server)",
        targetConfiguration={
            "mcp": {
                "mcpServer": {
                    "endpoint": SYNGENTA_MCP_URL,
                }
            }
        },
    )
    log.info("Syngenta target created: %s (status=%s)",
             response.get("targetId"), response.get("status"))
    return response


# ── Step 5: Cedar Policies ───────────────────────────────────────────────


def ensure_policy_engine(client, gateway_id: str, gateway_arn: str) -> str:
    """Create Cedar policy engine + attach to gateway. Returns engine ID."""
    engine_name = "eden_policy_engine"

    # Check existing
    try:
        engines = client.list_policy_engines()
        for e in engines.get("items", []):
            if e.get("name") == engine_name:
                eid = e["policyEngineId"]
                log.info("Policy engine already exists: %s", eid)
                return eid
    except (ClientError, KeyError):
        pass

    log.info("Creating Cedar policy engine '%s'...", engine_name)
    engine = client.create_policy_engine(
        name=engine_name,
        description="EDEN Greenhouse agent access control",
    )
    engine_id = engine["policyEngineId"]
    engine_arn = engine["policyEngineArn"]
    log.info("Policy engine created: %s", engine_id)

    # Permit policy — allow all EDEN tools
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
    resource == AgentCore::Gateway::"{gateway_arn}"
);"""

    log.info("Creating permit policy...")
    client.create_policy(
        policyEngineId=engine_id,
        name="eden_allow_all_tools",
        description="Allow EDEN agent to use all greenhouse management tools",
        definition={"cedar": {"statement": permit_statement}},
    )

    # Forbid policy — block override keywords on transform tools
    forbid_statement = f"""forbid(
    principal,
    action in [
        AgentCore::Action::"MarsTransformLayer___transform_temperature",
        AgentCore::Action::"MarsTransformLayer___transform_pressure"
    ],
    resource == AgentCore::Gateway::"{gateway_arn}"
) when {{
    context.input has keywords &&
    context.input.keywords like "*override*"
}};"""

    log.info("Creating forbid policy (override protection)...")
    client.create_policy(
        policyEngineId=engine_id,
        name="eden_deny_override_keywords",
        description="Deny transform tools when input contains override keywords",
        definition={"cedar": {"statement": forbid_statement}},
    )

    # Attach policy engine to gateway (LOG_ONLY for hackathon safety)
    # update_gateway requires name, roleArn, protocolType, authorizerType
    log.info("Attaching policy engine to gateway (LOG_ONLY mode)...")
    gw = client.get_gateway(gatewayIdentifier=gateway_id)
    client.update_gateway(
        gatewayIdentifier=gateway_id,
        name=gw["name"],
        roleArn=gw["roleArn"],
        protocolType=gw["protocolType"],
        authorizerType=gw["authorizerType"],
        policyEngineConfiguration={
            "arn": engine_arn,
            "mode": "LOG_ONLY",
        },
    )
    log.info("Policy engine attached to gateway")

    return engine_id


# ── Step 6: SSM Parameter Storage ────────────────────────────────────────


def store_params(gateway_id: str, gateway_url: str) -> None:
    """Store gateway params in SSM for runtime discovery."""
    ssm = boto3.client("ssm", region_name=REGION)

    params = {
        "/eden/agentcore/gateway_id": gateway_id,
        "/eden/agentcore/gateway_endpoint": gateway_url,
    }

    for name, value in params.items():
        try:
            ssm.put_parameter(Name=name, Value=value, Type="String", Overwrite=True)
            log.info("SSM: %s = %s", name, value)
        except ClientError as e:
            log.warning("Failed to store SSM param %s: %s", name, e)


# ── Write .env snippet ──────────────────────────────────────────────────


def write_env_snippet(gateway_id: str, gateway_url: str) -> None:
    """Append gateway config to .env if not already present."""
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
    marker = "AGENTCORE_GATEWAY_ENDPOINT"

    existing = ""
    if os.path.exists(env_path):
        with open(env_path) as f:
            existing = f.read()

    if marker in existing:
        log.info(".env already has %s — not overwriting", marker)
        return

    snippet = f"""
# AgentCore Gateway (auto-generated by deploy_agentcore.py)
AGENTCORE_GATEWAY_ID={gateway_id}
AGENTCORE_GATEWAY_ENDPOINT={gateway_url}
"""
    with open(env_path, "a") as f:
        f.write(snippet)
    log.info("Appended gateway config to %s", env_path)


# ── Main ─────────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(description="Deploy AgentCore Gateway for EDEN")
    parser.add_argument("--auth", choices=["jwt", "none"], default="none",
                        help="Auth type: 'jwt' for Cognito, 'none' for hackathon speed (default: none)")
    parser.add_argument("--skip-policies", action="store_true",
                        help="Skip Cedar policy creation")
    parser.add_argument("--skip-syngenta", action="store_true",
                        help="Skip Syngenta MCP target (if already accessible directly)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print plan without deploying")
    parser.add_argument("--gateway-role-arn",
                        help="Override gateway role ARN")
    parser.add_argument("--stack", default="dev",
                        help="Pulumi stack name")
    args = parser.parse_args()

    auth_type = "CUSTOM_JWT" if args.auth == "jwt" else "NONE"

    if args.dry_run:
        log.info("=== DRY RUN — No AWS calls will be made ===")
        log.info("")
        log.info("Plan:")
        log.info("  1. Create API Key credential provider (NASA key)")
        log.info("  2. Upload %s to s3://%s/%s", SPEC_LOCAL_PATH, BUCKET, SPEC_KEY)
        log.info("  3. Create Gateway '%s' (auth=%s)", GATEWAY_NAME, auth_type)
        log.info("  4. Create target: %s (NASA OpenAPI from S3)", NASA_TARGET_NAME)
        log.info("  5. Create target: %s (Lambda %s)", LAMBDA_TARGET_NAME, LAMBDA_ARN)
        if not args.skip_syngenta:
            log.info("  6. Create target: %s (MCP %s)", SYNGENTA_TARGET_NAME, SYNGENTA_MCP_URL)
        if not args.skip_policies:
            log.info("  7. Create Cedar policy engine + permit/forbid policies")
        log.info("  8. Store gateway params in SSM + .env")
        return

    # Resolve role ARN
    role_arn = args.gateway_role_arn or get_gateway_role_arn(args.stack)
    log.info("Using gateway role: %s", role_arn)

    client = boto3.client("bedrock-agentcore-control", region_name=REGION)

    # ── Step 1: Credential Provider ──────────────────────────────────
    log.info("=" * 60)
    log.info("Step 1: NASA API Key Credential Provider")
    log.info("=" * 60)
    cred_arn = ensure_credential_provider(client)

    # ── Step 2: Upload OpenAPI Spec ──────────────────────────────────
    log.info("=" * 60)
    log.info("Step 2: Upload NASA OpenAPI Spec to S3")
    log.info("=" * 60)
    upload_openapi_spec()

    # ── Step 3: Create Gateway ───────────────────────────────────────
    log.info("=" * 60)
    log.info("Step 3: Create AgentCore Gateway")
    log.info("=" * 60)
    gw = ensure_gateway(client, role_arn, auth_type)
    gw_id = gw["gatewayId"]
    gw_url = gw.get("gatewayUrl", "")
    gw_arn = gw.get("gatewayArn", f"arn:aws:bedrock-agentcore:{REGION}:{ACCOUNT}:gateway/{gw_id}")

    # ── Step 4: Create Targets ───────────────────────────────────────
    log.info("=" * 60)
    log.info("Step 4: Create Gateway Targets")
    log.info("=" * 60)
    create_nasa_target(client, gw_id, cred_arn)
    create_lambda_target(client, gw_id)
    if not args.skip_syngenta:
        create_syngenta_target(client, gw_id)

    # ── Step 5: Cedar Policies ───────────────────────────────────────
    if not args.skip_policies:
        log.info("=" * 60)
        log.info("Step 5: Cedar Policies")
        log.info("=" * 60)
        ensure_policy_engine(client, gw_id, gw_arn)

    # ── Step 6: Store Params ─────────────────────────────────────────
    log.info("=" * 60)
    log.info("Step 6: Store Parameters")
    log.info("=" * 60)
    store_params(gw_id, gw_url)
    write_env_snippet(gw_id, gw_url)

    # ── Summary ──────────────────────────────────────────────────────
    log.info("")
    log.info("=" * 60)
    log.info("DEPLOYMENT COMPLETE")
    log.info("=" * 60)
    log.info("Gateway ID:       %s", gw_id)
    log.info("Gateway URL:      %s", gw_url)
    log.info("Gateway Auth:     %s", auth_type)
    log.info("Targets:          %s, %s%s",
             NASA_TARGET_NAME, LAMBDA_TARGET_NAME,
             f", {SYNGENTA_TARGET_NAME}" if not args.skip_syngenta else "")
    log.info("Policies:         %s", "enabled (LOG_ONLY)" if not args.skip_policies else "skipped")
    log.info("")
    log.info("Expected MCP tools:")
    log.info("  - NasaMarsAPIs___getInsightWeather")
    log.info("  - NasaMarsAPIs___getDonkiCME")
    log.info("  - NasaMarsAPIs___getDonkiMPC")
    log.info("  - MarsTransformLayer___transform_temperature")
    log.info("  - MarsTransformLayer___transform_pressure")
    log.info("  - MarsTransformLayer___transform_light")
    if not args.skip_syngenta:
        log.info("  - SyngentaCropKB___<various KB tools>")
    log.info("")
    log.info("To connect from EDEN agent:")
    log.info("  export AGENTCORE_GATEWAY_ENDPOINT=%s", gw_url)
    log.info("  python -m eden")


if __name__ == "__main__":
    main()
