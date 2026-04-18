import pulumi_aws as aws


def create_instance(sg, instance_profile, key_pair, user_data):
    ami = aws.ec2.get_ami(
        most_recent=True,
        filters=[
            aws.ec2.GetAmiFilterArgs(
                name="name",
                values=["ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-amd64-server-*"],
            ),
            aws.ec2.GetAmiFilterArgs(
                name="virtualization-type",
                values=["hvm"],
            ),
        ],
        owners=["099720109477"],  # Canonical
    )

    return aws.ec2.Instance("astrofarm-mc",
        instance_type="t3.xlarge",
        ami=ami.id,
        key_name=key_pair.key_name,
        vpc_security_group_ids=[sg.id],
        iam_instance_profile=instance_profile.name,
        root_block_device=aws.ec2.InstanceRootBlockDeviceArgs(
            volume_size=50,
            volume_type="gp3",
        ),
        user_data=user_data,
        tags={"Name": "AstroFarm-MissionControl"},
    )
