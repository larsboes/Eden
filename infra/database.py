"""DynamoDB tables for EDEN greenhouse system."""

import pulumi_aws as aws

TAGS = {"Project": "eden", "Environment": "dev"}

# --- eden-telemetry: time-series sensor data ---
telemetry_table = aws.dynamodb.Table("eden-telemetry",
    name="eden-telemetry",
    billing_mode="PAY_PER_REQUEST",
    hash_key="zone_id",
    range_key="timestamp",
    attributes=[
        aws.dynamodb.TableAttributeArgs(name="zone_id", type="S"),
        aws.dynamodb.TableAttributeArgs(name="timestamp", type="N"),
    ],
    tags=TAGS,
)

# --- eden-state: key-value state store ---
state_table = aws.dynamodb.Table("eden-state",
    name="eden-state",
    billing_mode="PAY_PER_REQUEST",
    hash_key="key",
    attributes=[
        aws.dynamodb.TableAttributeArgs(name="key", type="S"),
    ],
    tags=TAGS,
)

# --- eden-agent-log: agent decision log ---
agent_log_table = aws.dynamodb.Table("eden-agent-log",
    name="eden-agent-log",
    billing_mode="PAY_PER_REQUEST",
    hash_key="partition",
    range_key="timestamp",
    attributes=[
        aws.dynamodb.TableAttributeArgs(name="partition", type="S"),
        aws.dynamodb.TableAttributeArgs(name="timestamp", type="N"),
    ],
    tags=TAGS,
)
