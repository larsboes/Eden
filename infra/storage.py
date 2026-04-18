"""S3 bucket for EDEN assets (OpenAPI specs, camera images, etc.)."""

import pulumi
import pulumi_aws as aws

TAGS = {"Project": "eden", "Environment": "dev"}

assets_bucket = aws.s3.Bucket("astrofarm-assets",
    bucket_prefix="astrofarm-assets-",
    tags=TAGS,
)

aws.s3.BucketPublicAccessBlock("astrofarm-assets-public-access-block",
    bucket=assets_bucket.id,
    block_public_acls=True,
    block_public_policy=True,
    ignore_public_acls=True,
    restrict_public_buckets=True,
)
