import pulumi_tls as tls
import pulumi_aws as aws

ssh_key = tls.PrivateKey("astrofarm-key", algorithm="ED25519")

key_pair = aws.ec2.KeyPair("astrofarm-keypair",
    key_name="astrofarm-key",
    public_key=ssh_key.public_key_openssh,
)
