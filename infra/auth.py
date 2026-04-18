"""Cognito user pool and app client for EDEN dashboard auth."""

import pulumi
import pulumi_aws as aws

TAGS = {"Project": "eden", "Environment": "dev"}

# --- User Pool ---
user_pool = aws.cognito.UserPool("eden-users",
    name="eden-users",
    auto_verified_attributes=["email"],
    password_policy=aws.cognito.UserPoolPasswordPolicyArgs(
        minimum_length=8,
        require_lowercase=True,
        require_numbers=True,
        require_symbols=False,
        require_uppercase=True,
    ),
    tags=TAGS,
)

# --- App Client (no secret — SPA implicit grant) ---
app_client = aws.cognito.UserPoolClient("eden-dashboard",
    name="eden-dashboard",
    user_pool_id=user_pool.id,
    generate_secret=False,
    explicit_auth_flows=[
        "ALLOW_USER_PASSWORD_AUTH",
        "ALLOW_REFRESH_TOKEN_AUTH",
        "ALLOW_USER_SRP_AUTH",
    ],
    supported_identity_providers=["COGNITO"],
)

# --- Discovery URL (issuer) ---
region = aws.get_region()
discovery_url = user_pool.id.apply(
    lambda pool_id: f"https://cognito-idp.{region.name}.amazonaws.com/{pool_id}"
)
