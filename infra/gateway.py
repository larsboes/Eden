"""AgentCore Gateway + Cedar policies for EDEN.

NOTE: AgentCore Gateway does not have direct Pulumi support as of March 2026.
This module defines placeholder exports and documents the manual/CLI steps
needed to configure the gateway. The infra is structured so that when
Pulumi support is added, this file can be updated without changing consumers.

Manual steps (via AWS CLI or console):
  1. Create AgentCore Gateway with Cognito JWT auth
  2. Add targets:
     - NASA API (OpenAPI spec from S3 bucket)
     - Mars Transform Lambda (eden-mars-transform)
     - Syngenta MCP server (provided endpoint)
  3. Apply Cedar policies:
     - Allow: read_sensors, set_actuator, get_mars_conditions,
              check_syngenta_documentation, query_telemetry
     - Deny: destructive actions without confirmation
  4. Configure API Key credential provider for NASA API key
"""

import pulumi

# Placeholder exports — replace with real values after manual gateway creation
# or when Pulumi support becomes available.
gateway_id = pulumi.Output.from_input("TODO-create-via-cli")
gateway_endpoint = pulumi.Output.from_input("TODO-create-via-cli")
