"""CloudWatch log groups for EDEN system."""

import pulumi_aws as aws

TAGS = {"Project": "eden", "Environment": "dev"}

# --- /eden/agent log group ---
agent_log_group = aws.cloudwatch.LogGroup("eden-agent-logs",
    name="/eden/agent",
    retention_in_days=7,
    tags=TAGS,
)

# --- /eden/telemetry log group ---
telemetry_log_group = aws.cloudwatch.LogGroup("eden-telemetry-logs",
    name="/eden/telemetry",
    retention_in_days=7,
    tags=TAGS,
)
