import pulumi_aws as aws

TAGS = {"Project": "eden", "Environment": "dev"}

sg = aws.ec2.SecurityGroup("astrofarm-sg",
    description="AstroFarm - SSH + EDEN services",
    ingress=[
        # SSH
        aws.ec2.SecurityGroupIngressArgs(
            protocol="tcp",
            from_port=22,
            to_port=22,
            cidr_blocks=["0.0.0.0/0"],
            description="SSH",
        ),
        # MQTT (Mosquitto)
        aws.ec2.SecurityGroupIngressArgs(
            protocol="tcp",
            from_port=1883,
            to_port=1883,
            cidr_blocks=["0.0.0.0/0"],
            description="MQTT - Mosquitto",
        ),
        # API (dashboard backend)
        aws.ec2.SecurityGroupIngressArgs(
            protocol="tcp",
            from_port=8000,
            to_port=8000,
            cidr_blocks=["0.0.0.0/0"],
            description="API - dashboard backend",
        ),
        # Dashboard
        aws.ec2.SecurityGroupIngressArgs(
            protocol="tcp",
            from_port=8080,
            to_port=8080,
            cidr_blocks=["0.0.0.0/0"],
            description="Dashboard",
        ),
        # MQTTS (IoT Core bridge)
        aws.ec2.SecurityGroupIngressArgs(
            protocol="tcp",
            from_port=8883,
            to_port=8883,
            cidr_blocks=["0.0.0.0/0"],
            description="MQTTS - IoT Core bridge",
        ),
    ],
    egress=[aws.ec2.SecurityGroupEgressArgs(
        protocol="-1",
        from_port=0,
        to_port=0,
        cidr_blocks=["0.0.0.0/0"],
    )],
    tags=TAGS,
)
