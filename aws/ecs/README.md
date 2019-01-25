# Reference Architecture Lenses ECS Fargate

Lenses will be running in Elastic Container Service (ECS) with AWS Fargate compute engine that allows you to run containers without having to manage servers or clusters. This architecture deploys your container into a private subnet.

The Lenses container do not have direct internet access, or a public IP address. Lenses outbound traffic must go out via a NAT gateway, and receipients of requests from Lenses container will just see the request orginating from the IP address of the NAT gateway. However, inbound traffic from the public can still reach Lenses container because there is a public facing load balancer that can proxy traffic from the public to Lenses container in the private subnet.

This template is uses the recommended reference architecture in AWS ECS to keep your data safe and secure and do not expose Lenses directly to the public Internet.

When Lenses started you can use the default credentials `admin/admin`.

<a href="https://console.aws.amazon.com/cloudformation/home?#/stacks/new?stackName=Lenses&templateURL=https://s3.eu-west-2.amazonaws.com/lenses-templates/ecs/fargate.yml" target="_blank">
    <img src="https://s3.amazonaws.com/cloudformation-examples/cloudformation-launch-stack.png"/>
</a>

![](https://s3.eu-west-2.amazonaws.com/lenses-marketplace-diagrams/ecs-reference-architecture/aws-ecs-reference-architecture.png)