import json
import pulumi_aws as aws

TAGS = {"Project": "eden", "Environment": "dev"}

# ============================================================
# EC2 Instance Role (existing — extended with EDEN permissions)
# ============================================================
role = aws.iam.Role("astrofarm-ec2-role",
    assume_role_policy=json.dumps({
        "Version": "2012-10-17",
        "Statement": [{
            "Action": "sts:AssumeRole",
            "Effect": "Allow",
            "Principal": {"Service": "ec2.amazonaws.com"},
        }],
    }),
)

aws.iam.RolePolicy("astrofarm-bedrock",
    role=role.name,
    policy=json.dumps({
        "Version": "2012-10-17",
        "Statement": [{
            "Sid": "AllowModelAndInferenceProfileAccess",
            "Effect": "Allow",
            "Action": [
                "bedrock:InvokeModel",
                "bedrock:InvokeModelWithResponseStream",
                "bedrock:ListInferenceProfiles",
            ],
            "Resource": [
                "arn:aws:bedrock:*:*:inference-profile/*",
                "arn:aws:bedrock:*:*:application-inference-profile/*",
                "arn:aws:bedrock:*:*:foundation-model/*",
            ],
        }],
    }),
)

# EC2 extended permissions for EDEN
aws.iam.RolePolicy("astrofarm-eden-ec2",
    role=role.name,
    policy=json.dumps({
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "DynamoDBFull",
                "Effect": "Allow",
                "Action": "dynamodb:*",
                "Resource": "arn:aws:dynamodb:*:*:table/eden-*",
            },
            {
                "Sid": "S3Full",
                "Effect": "Allow",
                "Action": "s3:*",
                "Resource": [
                    "arn:aws:s3:::astrofarm-assets-*",
                    "arn:aws:s3:::astrofarm-assets-*/*",
                ],
            },
            {
                "Sid": "SSMRead",
                "Effect": "Allow",
                "Action": [
                    "ssm:GetParameter",
                    "ssm:GetParameters",
                    "ssm:GetParametersByPath",
                ],
                "Resource": "arn:aws:ssm:*:*:parameter/eden/*",
            },
            {
                "Sid": "IoTCorePubSub",
                "Effect": "Allow",
                "Action": [
                    "iot:Connect",
                    "iot:Publish",
                    "iot:Subscribe",
                    "iot:Receive",
                    "iot:DescribeEndpoint",
                ],
                "Resource": "*",
            },
            {
                "Sid": "CloudWatchLogs",
                "Effect": "Allow",
                "Action": [
                    "logs:CreateLogStream",
                    "logs:PutLogEvents",
                    "logs:DescribeLogGroups",
                    "logs:DescribeLogStreams",
                ],
                "Resource": "arn:aws:logs:*:*:log-group:/eden/*",
            },
        ],
    }),
)

instance_profile = aws.iam.InstanceProfile("astrofarm-profile",
    role=role.name,
)

# ============================================================
# RuntimeAgentCoreRole — for AgentCore Runtime (Bedrock agent)
# ============================================================
runtime_role = aws.iam.Role("eden-runtime-agentcore-role",
    assume_role_policy=json.dumps({
        "Version": "2012-10-17",
        "Statement": [{
            "Action": "sts:AssumeRole",
            "Effect": "Allow",
            "Principal": {"Service": "bedrock.amazonaws.com"},
        }],
    }),
    tags=TAGS,
)

aws.iam.RolePolicy("eden-runtime-agentcore-policy",
    role=runtime_role.name,
    policy=json.dumps({
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "BedrockInvoke",
                "Effect": "Allow",
                "Action": [
                    "bedrock:InvokeModel",
                    "bedrock:InvokeModelWithResponseStream",
                ],
                "Resource": [
                    "arn:aws:bedrock:*:*:inference-profile/*",
                    "arn:aws:bedrock:*:*:foundation-model/*",
                ],
            },
            {
                "Sid": "ECR",
                "Effect": "Allow",
                "Action": "ecr:*",
                "Resource": "*",
            },
            {
                "Sid": "XRay",
                "Effect": "Allow",
                "Action": "xray:*",
                "Resource": "*",
            },
            {
                "Sid": "CloudWatchLogs",
                "Effect": "Allow",
                "Action": "logs:*",
                "Resource": "arn:aws:logs:*:*:log-group:/eden/*",
            },
            {
                "Sid": "DynamoDB",
                "Effect": "Allow",
                "Action": "dynamodb:*",
                "Resource": "arn:aws:dynamodb:*:*:table/eden-*",
            },
            {
                "Sid": "S3",
                "Effect": "Allow",
                "Action": "s3:*",
                "Resource": [
                    "arn:aws:s3:::astrofarm-assets-*",
                    "arn:aws:s3:::astrofarm-assets-*/*",
                ],
            },
            {
                "Sid": "SSMRead",
                "Effect": "Allow",
                "Action": "ssm:GetParameter",
                "Resource": "arn:aws:ssm:*:*:parameter/eden/*",
            },
        ],
    }),
)

# ============================================================
# GatewayAgentCoreRole — for AgentCore Gateway
# ============================================================
gateway_role = aws.iam.Role("eden-gateway-agentcore-role",
    assume_role_policy=json.dumps({
        "Version": "2012-10-17",
        "Statement": [{
            "Action": "sts:AssumeRole",
            "Effect": "Allow",
            "Principal": {"Service": "bedrock.amazonaws.com"},
        }],
    }),
    tags=TAGS,
)

aws.iam.RolePolicy("eden-gateway-agentcore-policy",
    role=gateway_role.name,
    policy=json.dumps({
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "LambdaInvoke",
                "Effect": "Allow",
                "Action": "lambda:InvokeFunction",
                "Resource": "arn:aws:lambda:*:*:function:eden-*",
            },
            {
                "Sid": "S3Read",
                "Effect": "Allow",
                "Action": "s3:GetObject",
                "Resource": [
                    "arn:aws:s3:::astrofarm-assets-*",
                    "arn:aws:s3:::astrofarm-assets-*/*",
                ],
            },
        ],
    }),
)
