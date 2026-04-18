"""Lambda function for EDEN Mars Transform."""

import json
import pulumi
import pulumi_aws as aws

TAGS = {"Project": "eden", "Environment": "dev"}

# --- Lambda execution role ---
lambda_role = aws.iam.Role("eden-lambda-role",
    assume_role_policy=json.dumps({
        "Version": "2012-10-17",
        "Statement": [{
            "Action": "sts:AssumeRole",
            "Effect": "Allow",
            "Principal": {"Service": "lambda.amazonaws.com"},
        }],
    }),
    tags=TAGS,
)

aws.iam.RolePolicyAttachment("eden-lambda-basic-execution",
    role=lambda_role.name,
    policy_arn="arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
)

# --- Mars Transform Lambda ---
# Inline handler — same logic as eden/domain/mars_transform.py
mars_transform_fn = aws.lambda_.Function("eden-mars-transform",
    name="eden-mars-transform",
    runtime="python3.12",
    handler="index.handler",
    role=lambda_role.arn,
    memory_size=128,
    timeout=30,
    code=pulumi.AssetArchive({
        "index.py": pulumi.StringAsset("""
import json
import math

def transform_temperature(earth_c: float, sol: int) -> float:
    seasonal = 5.0 * math.sin(2 * math.pi * sol / 668.6)
    return earth_c * 0.85 + seasonal - 10.0

def transform_pressure(earth_hpa: float) -> float:
    return earth_hpa * 0.006  # Mars ~6 hPa

def transform_light(earth_lux: float, dust_opacity: float) -> float:
    mars_factor = 0.43  # Mars gets ~43% of Earth's solar irradiance
    dust_factor = max(0.1, 1.0 - dust_opacity)
    return earth_lux * mars_factor * dust_factor

def handler(event, context):
    body = json.loads(event.get("body", "{}")) if isinstance(event.get("body"), str) else event
    sol = body.get("sol", 1)
    dust_opacity = body.get("dust_opacity", 0.0)
    result = {}
    if "temperature" in body:
        result["temperature"] = transform_temperature(body["temperature"], sol)
    if "pressure" in body:
        result["pressure"] = transform_pressure(body["pressure"])
    if "light" in body:
        result["light"] = transform_light(body["light"], dust_opacity)
    return {
        "statusCode": 200,
        "body": json.dumps(result),
    }
"""),
    }),
    tags=TAGS,
)
