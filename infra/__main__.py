"""AstroFarm EDEN — Full infrastructure provisioned by one `pulumi up`."""

import pulumi

# --- Existing resources (unchanged) ---
from network import sg
from iam import instance_profile, runtime_role, gateway_role
from ssh_key import ssh_key, key_pair
from compute import create_instance

# --- New EDEN resources ---
from database import telemetry_table, state_table, agent_log_table
from storage import assets_bucket
from messaging import iot_thing, iot_cert, iot_endpoint
from compute_functions import mars_transform_fn
from scheduling import create_rules
from auth import user_pool, app_client, discovery_url
from gateway import gateway_id, gateway_endpoint
from runtime import ecr_repo, runtime_id
from monitoring import agent_log_group, telemetry_log_group
from parameters import create_parameters

# --- EC2 Instance (existing) ---
with open("../multiplayer/bootstrap.sh") as f:
    user_data = f.read()

instance = create_instance(sg, instance_profile, key_pair, user_data)

# --- EventBridge rules (need Lambda ARN) ---
reconcile_rule, chaos_rule = create_rules(mars_transform_fn.arn)

# --- SSM Parameters (wire all cross-module references) ---
ssm_params = create_parameters(
    gateway_id=gateway_id,
    lambda_arn=mars_transform_fn.arn,
    cognito_pool_id=user_pool.id,
    cognito_client_id=app_client.id,
    telemetry_table_name=telemetry_table.name,
    state_table_name=state_table.name,
    agent_log_table_name=agent_log_table.name,
    s3_bucket_name=assets_bucket.bucket,
    iot_endpoint=iot_endpoint.endpoint_address,
)

# ============================================================
# Exports
# ============================================================

# EC2 (existing)
pulumi.export("public_ip", instance.public_ip)
pulumi.export("instance_id", instance.id)
pulumi.export("ssh_private_key", ssh_key.private_key_openssh)
pulumi.export("ssh_command", pulumi.Output.concat(
    "ssh -i astrofarm-key.pem ubuntu@", instance.public_ip,
))

# DynamoDB
pulumi.export("dynamo_telemetry_table", telemetry_table.name)
pulumi.export("dynamo_telemetry_arn", telemetry_table.arn)
pulumi.export("dynamo_state_table", state_table.name)
pulumi.export("dynamo_state_arn", state_table.arn)
pulumi.export("dynamo_agent_log_table", agent_log_table.name)
pulumi.export("dynamo_agent_log_arn", agent_log_table.arn)

# S3
pulumi.export("s3_bucket_name", assets_bucket.bucket)
pulumi.export("s3_bucket_arn", assets_bucket.arn)

# IoT Core
pulumi.export("iot_endpoint", iot_endpoint.endpoint_address)
pulumi.export("iot_cert_arn", iot_cert.arn)
pulumi.export("iot_cert_pem", iot_cert.certificate_pem)
pulumi.export("iot_private_key", iot_cert.private_key)

# Lambda
pulumi.export("lambda_mars_transform_arn", mars_transform_fn.arn)

# EventBridge
pulumi.export("eventbridge_reconcile_arn", reconcile_rule.arn)
pulumi.export("eventbridge_chaos_arn", chaos_rule.arn)

# Cognito
pulumi.export("cognito_pool_id", user_pool.id)
pulumi.export("cognito_client_id", app_client.id)
pulumi.export("cognito_discovery_url", discovery_url)

# AgentCore (placeholders)
pulumi.export("agentcore_gateway_id", gateway_id)
pulumi.export("agentcore_gateway_endpoint", gateway_endpoint)
pulumi.export("agentcore_runtime_id", runtime_id)

# ECR
pulumi.export("ecr_repo_url", ecr_repo.repository_url)

# IAM Roles
pulumi.export("runtime_role_arn", runtime_role.arn)
pulumi.export("gateway_role_arn", gateway_role.arn)

# CloudWatch
pulumi.export("cw_agent_log_group_arn", agent_log_group.arn)
pulumi.export("cw_telemetry_log_group_arn", telemetry_log_group.arn)
