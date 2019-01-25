# Deployment Lenses on EC2 with Docker

Lenses will be running in the EC2 instance as a docker container and will expose inbound traffic only for the port 80 which is exposed for the port which Lenses uses internally to run.

This template creates its own IAM profile which is attached in EC2 instance. It is used to enable CloudWatch logging in order to be be able to check all the available logs for the AWS Stack which has been created for Lenses. Apart from CloudWatch logging policies, it enables one more extra policy which is used to autodiscover Apache Kafka Brokers, Zookeeper and Workers based on AWS tagging.

Specifcally the template enable theses policies:

- `logs:CreateLogGroup`
- `logs:CreateLogStream`
- `logs:PutLogEvents`
- `ec2:DescribeInstances`

When Lenses started you can use the default credentials `admin/admin`.

<a href="https://console.aws.amazon.com/cloudformation/home?#/stacks/new?stackName=lenses&templateURL=https://s3.eu-west-2.amazonaws.com/lenses-templates/docker/ec2-docker.yml" target="_blank">
    <img src="https://s3.amazonaws.com/cloudformation-examples/cloudformation-launch-stack.png"/>
</a>

![](https://s3.eu-west-2.amazonaws.com/lenses-marketplace-diagrams/ec2-diagram/aws-ec2-lenses.png)