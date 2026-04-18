"""EventBridge rules for EDEN scheduled tasks."""

import pulumi_aws as aws

TAGS = {"Project": "eden", "Environment": "dev"}


def create_rules(lambda_arn: str):
    """Create EventBridge rules. Call after Lambda is created."""

    # --- eden-reconcile: trigger every 1 minute ---
    reconcile_rule = aws.cloudwatch.EventRule("eden-reconcile",
        name="eden-reconcile",
        schedule_expression="rate(1 minute)",
        description="Trigger EDEN reconciliation cycle every minute",
        tags=TAGS,
    )

    aws.cloudwatch.EventTarget("eden-reconcile-target",
        rule=reconcile_rule.name,
        arn=lambda_arn,
    )

    aws.lambda_.Permission("eden-reconcile-invoke",
        action="lambda:InvokeFunction",
        function=lambda_arn,
        principal="events.amazonaws.com",
        source_arn=reconcile_rule.arn,
    )

    # --- eden-chaos: injectable demo events (disabled by default) ---
    chaos_rule = aws.cloudwatch.EventRule("eden-chaos",
        name="eden-chaos",
        schedule_expression="rate(5 minutes)",
        description="EDEN chaos injection for demo (disabled by default)",
        state="DISABLED",
        tags=TAGS,
    )

    return reconcile_rule, chaos_rule
