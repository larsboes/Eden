"""ECR repository + AgentCore Runtime placeholder for EDEN."""

import pulumi
import pulumi_aws as aws

TAGS = {"Project": "eden", "Environment": "dev"}

# --- ECR Repository ---
ecr_repo = aws.ecr.Repository("eden-agent",
    name="eden-agent",
    image_tag_mutability="MUTABLE",
    image_scanning_configuration=aws.ecr.RepositoryImageScanningConfigurationArgs(
        scan_on_push=True,
    ),
    tags=TAGS,
)

# Lifecycle policy: keep last 5 images
aws.ecr.LifecyclePolicy("eden-agent-lifecycle",
    repository=ecr_repo.name,
    policy="""{
        "rules": [{
            "rulePriority": 1,
            "description": "Keep last 5 images",
            "selection": {
                "tagStatus": "any",
                "countType": "imageCountMoreThan",
                "countNumber": 5
            },
            "action": {
                "type": "expire"
            }
        }]
    }""",
)

# --- AgentCore Runtime ---
# NOTE: AgentCore Runtime does not have direct Pulumi support as of March 2026.
# Deploy via: bedrock-agentcore-starter-toolkit CLI after `pulumi up`
# Steps:
#   1. Build & push Docker image to ECR repo above
#   2. Create AgentCore Runtime via CLI/SDK
#   3. Configure runtime endpoint
runtime_id = pulumi.Output.from_input("TODO-deploy-via-agentcore-cli")
