"""IoT Core resources for EDEN EC2-to-cloud MQTT bridge."""

import json
import pulumi
import pulumi_aws as aws

TAGS = {"Project": "eden", "Environment": "dev"}

# --- IoT Thing: represents the EC2 MQTT bridge ---
iot_thing = aws.iot.Thing("eden-ec2-bridge",
    name="eden-ec2-bridge",
)

# --- IoT Policy: allow pub/sub on eden/* topics ---
iot_policy = aws.iot.Policy("eden-iot-policy",
    name="eden-ec2-bridge-policy",
    policy=json.dumps({
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "iot:Connect",
                ],
                "Resource": ["*"],
            },
            {
                "Effect": "Allow",
                "Action": [
                    "iot:Publish",
                    "iot:Subscribe",
                    "iot:Receive",
                ],
                "Resource": [
                    "arn:aws:iot:*:*:topic/eden/*",
                    "arn:aws:iot:*:*:topicfilter/eden/*",
                ],
            },
        ],
    }),
)

# --- IoT Certificate ---
iot_cert = aws.iot.Certificate("eden-iot-cert",
    active=True,
)

# --- Attach certificate to thing and policy ---
aws.iot.ThingPrincipalAttachment("eden-cert-thing-attachment",
    thing=iot_thing.name,
    principal=iot_cert.arn,
)

aws.iot.PolicyAttachment("eden-cert-policy-attachment",
    policy=iot_policy.name,
    target=iot_cert.arn,
)

# --- Get IoT endpoint ---
iot_endpoint = aws.iot.get_endpoint(endpoint_type="iot:Data-ATS")
