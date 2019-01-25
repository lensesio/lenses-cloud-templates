# Deployment Lenses on EC2

Lenses will be running in the EC2 instance from the archive repository and will expose inbound traffic only for the port which you will fill in during the template deployment.

This template creates its own IAM profile and installs the AWS Log agent in EC2 instance. It is used to enable CloudWatch logging in order to be able to check all the available logs for the AWS Stack which has been created for Lenses. More specifically template enables these policies:

Specifcally the template enable theses policies:

- `logs:CreateLogGroup`
- `logs:CreateLogStream`
- `logs:PutLogEvents`

When Lenses started you can use the default credentials `admin/admin`.

<a href="https://console.aws.amazon.com/cloudformation/home?#/stacks/new?stackName=Lenses&templateURL=https://s3.eu-west-2.amazonaws.com/lenses-templates/archive/ec2-archive.yml" target="_blank">
    <img src="https://s3.amazonaws.com/cloudformation-examples/cloudformation-launch-stack.png"/>
</a>

![](https://s3.eu-west-2.amazonaws.com/lenses-marketplace-diagrams/ec2-diagram/aws-ec2-lenses.png)
