# Reference Architecture Lenses Deployment

Lenses will be running in an EC2 instance which should be deployed into a private subnet.

The Lenses EC2 instance will not have direct internet access, or a public IP address. Lenses outbound traffic must go out via a NAT gateway, and recipients of requests from Lenses container will just see the request originating from the IP address of the NAT gateway. However, inbound traffic from the public can still reach Lenses EC2 instance because there is a public facing load balancer that can proxy traffic from the public to Lenses container in the private subnet.

This template is used the recommended reference architecture in AWS with EC2 instance to keep your data safe and secure and do not expose Lenses directly to the public Internet.

When Lenses started you can use the default credentials `admin/admin`.

<a href="https://console.aws.amazon.com/cloudformation/home?#/stacks/new?stackName=Lenses&templateURL=https://s3.eu-west-2.amazonaws.com/lenses-templates/reference/ec2-reference.yaml" target="_blank">
    <img src="https://s3.amazonaws.com/cloudformation-examples/cloudformation-launch-stack.png"/>
</a>

![](https://s3.eu-west-2.amazonaws.com/lenses-marketplace-diagrams/reference-architecture/aws-lenses-reference-architecture.png)