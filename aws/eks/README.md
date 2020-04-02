# Deploy Lenses on EKS with MSK

We will describe how to deploy Lenses on EKS that uses MSK as Kafka backend. 
We will go through the infrastracture requirements before deploying Lenses. We will talk 
about VPC, EKS Cluster, EKS Workers, MSK.

## Requirements

Below we list the system requirements for the case of updating the lambdas modules and uploading them to S3, 
and the infrastructure requirements fot the CFT deployment.

### System requerements for creating lambas modules

- make
- zip
- awscli
- pip3

### Infrastructure requirements

The cloudformation template that deploys Lenses in EKS, expects that you have configured 
an EKS cluster, an MKS cluster and the appropriate roles that are required by Lambdas to 
describe MSK and manage EKS.

In this blog, I’ll also go through the steps of:

- EKS Cluster
- EKS Workers
- MSK Cluster
- VPC
- Role

We will explain about these as we move on, but for now note that we need a **VPC** for:

- Connecting MSK with EKS
- Exposing EKS services to Public 

Also, we need a **Role** for:

- Describing MSK
- Managing EKS
- Writing to CloudwatchLogs

## Deploying VPC

Before we deploy EKS and MSK, we need to create a VPC that we will use 
**1)** to allow EKS communicate with MSK via private subnet, **2)** worker nodes communicate 
with EKS via a private subnet, and allow EKS to expose **applications** via **loadbalancers** to the **Public**.

We want MSK and Worker nodes to be protected behind a private subnet and not exposed to the public. 
In this example we will create a new **VPC** that has **2 private subnets** and **2 public subnets**. 
The template that will be used is provided by AWS and will work out of the box.

**Template**: https://amazon-eks.s3-us-west-2.amazonaws.com/cloudformation/2019-11-15/amazon-eks-vpc-private-subnets.yaml

Should you need to edit the network in order to adjust it with your needs then:

- Download the template
- Edit it by adding subnets or changing the network setup
- Save it and import deploy it via Cloudfromation

When the stack’s deployment has finished successfully, you will get the following 3 values in the output tab
    
- SecurityGroups
- SubnetIds
- VpcId

**Note** down the **SecurityGroups** and **VpcId** because we will need those later when we deploy EKS and MSK clusters.

## Creating an EKS cluster

We are now ready to create an EKS cluster. To do that, visit the AWS EKS service and select create a new cluster.

Give a unique Cluster name, select the Kubernetes version and the role.

In the **Networking Section** select the **VpcId** that you noted from the output tab when you deployed the new VPC. 
For the subnets, select all the subnets related with the above VpcId.

    - 2 private subnets (if you did not change the default template)
    - 2 public subnets (if you did not change the default template)

For the **security groups** select the security group of the VPC.

Under API service endpoint access, check (`Enable`) Private access and Public access. Also, in the public access click 
on **Advance Settings** and then add the **Public IP** (`x.x.x.x/32`) of your host by selecting **Add Source**.

If you need to add tags and enable login options, do so now and finally click **Create Cluster**. 
This should take sometime to complete. When EKS cluster is deployed, move to the next part to add worker nodes to EKS 
in order to be able to deploy resources.

## Add worker nodes to EKS Cluster

For deploying the worker nodes, we will use the following template. Go to Cloudformation, select deploy a new template and use the url below.

**Template**: https://amazon-eks.s3-us-west-2.amazonaws.com/cloudformation/2019-02-11/amazon-eks-nodegroup.yaml

Give a name to your stack, then in **EKS Cluster under Parameters**, write the `EKS Cluster name` that you created, 
and for the `ClusterControlPlaneSecurityGroup`, select the security group of the VPC that you created (**See Deploying VPC**).

Under **Worker Node Configuration**, give a name for your `Node Group`, and leave as to default the:

    NodeAutoScalingGroupMinSize: 1
    NodeAutoScalingGroupDesiredCapacity: 3
    NodeAutoScalingGroupMaxSize: 4
    NodeInstanceType: t3.medium

Note: You can change the above values if you want to run a more excotic setup, however if you simply want to deploy Lenses in EKS, 
then the above values are more that enough

Based on your **region**, you have to also select the `NodeImage ID (Image AMI)` that will be used to bootstrap the worker nodes. 
If you do not know where to find these AMIs, please check the following file

**File**: https://github.com/aws-quickstart/quickstart-amazon-eks/blob/9be26456e7daa294b1737b6a5f6d1bb3e3dfdf8d/templates/amazon-eks-nodegroup.template.yaml#L449

Provide an EC2 `keypair` if you have one. You need to provide a keypair only if you need SSH access to the worker nodes.

Next, under the **Worker Network Configuration section**, select the **VpcId** of the VPC that you created earlier, 
and select **only the private subnets of the specific VPC**:

    - 2 private subnets (if you did not change the default template)

Click deploy stack and wait for the deployment to finish. After the deployment has finished, we need to **add the nodegroup to the EKS cluster**. 
To do that, first go to Cloudformation in the output tab of the nodegroup deployment and **note down** the `NodeInstanceRole`.

To add the nodegorup to the EKS Cluster, first open a terminal in your host and **update the kubeconfig**

    aws eks --region ${REGION} update-kubeconfig --name ${EKS_CLUSTER_NAME}

Check that the context has been updated successfully by issuing:

    > kubectl  get pods --all-namespaces 
      NAMESPACE     NAME                      READY   STATUS    RESTARTS   AGE
      kube-system   coredns-9c59b8bbb-9fzzx   0/1     Pending   0          49m
      kube-system   coredns-9c59b8bbb-lxzvp   0/1     Pending   0          49m

Create yhe following **ConfigMap** that will authorize the worker nodes to join the EKS Cluster. 
Replace the `<ROLEARN>` with the value of `NodeInstanceRole` that you noted down when you deployed the nodegroup stack.

    apiVersion: v1
    kind: ConfigMap
    metadata:
    name: aws-auth
    namespace: kube-system
    data:
    mapRoles: |
        - rolearn:  <ROLEARN>
        username: system:node:{{EC2PrivateDNSName}}
        groups:
            - system:bootstrappers
            - system:nodes

To create the **ConfigMap** issue:

    > kubectl create -f auth.yml
      configmap/aws-auth created

The worker nodes should have started joining the cluster. To check that, issue:

    > kubectl  get nodes
      NAME                                             STATUS     ROLES    AGE   VERSION
      ip-192-168-128-74.eu-north-1.compute.internal    NotReady   <none>   1s    v1.14.8-eks-b8860f
      ip-192-168-167-237.eu-north-1.compute.internal   NotReady   <none>   3s    v1.14.8-eks-b8860f
      ip-192-168-195-114.eu-north-1.compute.internal   NotReady   <none>   0s    v1.14.8-eks-b8860f

You can check again to ensure that the status has changed from NotReady to Ready

## Create a Lambda Role for accessing EKS and MSK

We need a role which will allow AWS lambdas:

- Describe MSK Cluster (Get broker endpoints, cluster’s arn, etc)
- Authorize with EKS cluster for Managing Deployments

Go to **AIM**, then **roles** and select `Create role`.

Add the following policies

    AWS managed policy
      AmazonEKSClusterPolicy
      AmazonEKSServicePolicy
      AmazonEKSWorkerNodePolicy
      AmazonMSKReadOnlyAccess

    Inline policy
      logs:CreateLogGroup
      logs:CreateLogStream
      logs:PutLogEvents

NOTE: You can use the `role.yml` Cloudformation template to create the role automatically

After creating the role, you need to map it explicity into the EKS cluster **auth configmap** 
because only the creator of EKS cluster has access by default to the cluster. 
Any other user/role must be added in advance.

First get the `rolearn` and then type in your terminal

    export VISUAL=vim
    export EDITOR="$VISUAL"

    kubectl edit -n kube-system configmap/aws-auth

Under the **mapRoles** key, append the following

    - rolearn: <RoleArn>
      username: aws
      groups:
        - system:masters

Replace the `<RoleArn>` with the `rolearn` id of the role you just created above and then save and exit. 
The final ConfigMap should look like this after adding the above rolearn in the rolemapping section

    # Please edit the object below. Lines beginning with a '#' will be ignored,
    # and an empty file will abort the edit. If an error occurs while saving this file will be
    # reopened with the relevant failures.
    #
    apiVersion: v1
    data:
      mapRoles: |
        - rolearn:  arn:aws:iam::******:role/******
          username: system:node:{{EC2PrivateDNSName}}
          groups:
            - system:bootstrappers
            - system:nodes
        - rolearn: arn:aws:iam::******:role/******
          username: aws
          groups:
            - system:masters
    kind: ConfigMap
    metadata:
      annotations:
        kubectl.kubernetes.io/last-applied-configuration: |
          {"apiVersion":"v1","data":{"mapRoles":"-  ..."namespace":"kube-system"}}
      creationTimestamp: "2020-03-09T01:57:33Z"
      name: aws-auth
      namespace: kube-system
      resourceVersion: "1657"
      selfLink: /api/v1/namespaces/kube-system/configmaps/aws-auth
      uid: ***

## Deploy MSK CLuster

Deploying an MSK cluster should be straightforward. Go to AWS MSK and select Create cluster. 
Give a unique name for your cluster under the General section and select the Kafka version you desire (we recommend you choose **>2.2.x**).

Under the **Networking Section** select the `VpcId` that you created before, the same one you used when you created the EKS Cluster, (**See Deploying VPC**).

Select **availability zones = 2** (In the demo template there are 2 private subnets and 2 publicsubnets, 
1 for each availability zone, with a maximum of 2 availability zones. If you updated the template by adding more subnets, then choose the AZ you desire)

The rest of the options are completely up to you and should not affect the deployment of Lenses, however we suggest that you **enable TLS** for data encryption 
and also **OpenMonitoring** in order for Lenses to be able and **read MSK broker metrics**.

#### Allow EKS & Worker Nodes to communicate with the Brokers

While Both EKS and Worker Nodes belong are sharing a common network, it is not enough for the clients deployed in EKS to communicate with the brokers. 
This is a security setting included by AWS and requires to add the security group of a specific resource in the **inbound tab of MSK’s Security Group** 
in order for the resource to be able and communicate with the brokers.

First go to Cloudformation and select the stack of the nodegroup, then go to the output tab and note down the value of `NodeSecurityGroup`.

Visit the MSK Cluster and select the security group under **Networking section/Security Groups**. 
Click on the **inbound tab** and select Edit, next select **Add Rule**, choose All Traffic as type, paste the security group id of the nodegroup and click save.

That’s it, you are done. Now EKS worker nodes and their resources should be able to communicate with the kafka brokers.

## Deploying Lenses

##### Install lambda modules requirements

To update the local modules required by lambdas, issue:

```
    make inst_deps
```

##### Upload lambdas to s3

Ensure that bucket with name `S3Bucket=vdev-k8` exists
Ensure that directory in bucket `S3BucketPrefix=functions` exists

To zip the updated lambdas directory and push it to s3, issue:

```
    make s3
```
The finaly phase is to deploy Lenses. This should also be straightforward. Go to Cloudformation, import the lenses-eks.yaml template 
and click next. Give a name for the stack, and then provide the following parameters:

    License (JSON)
    EKS Cluster Name
    MSK Cluster Name
    S3 Bucket Name *1
    S3 Bucket Prefix
    Lambda Role *2

The S3 bucket name and S3 bucket prefix, is the bucket and its prefix that will be used to copy the lambdas from our public s3 bucket to your bucket.

The Lambda Role is the role you created and added into the EKS ConfigMap (See Create a Lambda Role for accessing EKS and MSK)

When you provide all the required parameters, click Create stack. Deploying the stack should take around ~5 min to complete. 
When the deployment is finished, go to the output tab, copy the value of LambdaEKSConfigLensesEndpoint, open a new tab, 
paste the content and hit enter.

You should be welcomed with the Lenses Login screen.
