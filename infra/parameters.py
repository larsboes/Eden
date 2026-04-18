"""SSM Parameter Store for EDEN cross-component configuration."""

import pulumi
import pulumi_aws as aws

TAGS = {"Project": "eden", "Environment": "dev"}


def create_parameters(
    gateway_id,
    lambda_arn,
    cognito_pool_id,
    cognito_client_id,
    telemetry_table_name,
    state_table_name,
    agent_log_table_name,
    s3_bucket_name,
    iot_endpoint,
):
    """Create SSM parameters from all module outputs."""
    params = {}

    param_defs = {
        "/eden/gateway-id": gateway_id,
        "/eden/lambda-arn": lambda_arn,
        "/eden/cognito-pool-id": cognito_pool_id,
        "/eden/cognito-client-id": cognito_client_id,
        "/eden/dynamo-telemetry-table": telemetry_table_name,
        "/eden/dynamo-state-table": state_table_name,
        "/eden/dynamo-agent-log-table": agent_log_table_name,
        "/eden/s3-bucket-name": s3_bucket_name,
        "/eden/iot-endpoint": iot_endpoint,
    }

    for name, value in param_defs.items():
        # Create a Pulumi-safe resource name from the parameter path
        resource_name = "eden-param" + name.replace("/eden/", "-")
        params[name] = aws.ssm.Parameter(resource_name,
            name=name,
            type="String",
            value=value,
            tags=TAGS,
        )

    return params
