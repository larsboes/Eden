#!/bin/bash
# AstroFarm - Plug & Play Bedrock setup
# Run: source setup-bedrock.sh
# After that: just run `claude` - it uses AWS Bedrock, no API key needed

set -e

export AWS_DEFAULT_REGION="us-west-2"
export AWS_ACCESS_KEY_ID="your_aws_access_key_id"
export AWS_SECRET_ACCESS_KEY="your_aws_secret_access_key"
export AWS_SESSION_TOKEN="your_aws_session_token"

# Write to ~/.aws so Claude Code (AWS SDK) picks them up automatically
mkdir -p ~/.aws

cat > ~/.aws/credentials << EOF
[astrofarm]
aws_access_key_id = ${AWS_ACCESS_KEY_ID}
aws_secret_access_key = ${AWS_SECRET_ACCESS_KEY}
aws_session_token = ${AWS_SESSION_TOKEN}
EOF

cat > ~/.aws/config << EOF
[profile astrofarm]
region = ${AWS_DEFAULT_REGION}
output = json
EOF

echo "✓ AWS credentials written to ~/.aws"

# Also export to current shell (for aws CLI etc.)
export AWS_ACCESS_KEY_ID
export AWS_SECRET_ACCESS_KEY
export AWS_SESSION_TOKEN
export AWS_DEFAULT_REGION
export AWS_PROFILE=astrofarm

echo "✓ AWS env vars exported to current shell"

# Verify
IDENTITY=$(aws sts get-caller-identity --query "Arn" --output text 2>&1)
echo "✓ Authenticated as: $IDENTITY"
echo ""
echo "All done. Run: claude"
echo "Claude Code will use AWS Bedrock (Sonnet 4.6 / Opus 4.6) — no API key needed."
