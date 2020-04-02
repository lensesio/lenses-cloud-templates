from sys import path as syspath
syspath.insert(0, 'modules')

from os import path, environ, mkdir
from manifests import kubeconfig
from sys import exc_info, exit
from exac import exac
import traceback
import urllib
import boto3
import json


def check_paths(*args):
    """
        Concat paths and append '/' at the end if is missing

        :param args: List of paths
        :type args: List of Strings / String

        :return: path1/path2/.../pathN
    """

    path = ''
    for i in args:
        if not i.endswith('/'):
            path = path + i + '/'
            continue

        path = path + i

    return path


class SetupKubeConfig():

    """
        Class for setting up generating and writing to file
        kubecofig.
    """

    def __init__(self, region_name, cluster_name):
        """
            :param region_name": Region Name for the AWS EKS Cluster
            :type region_name": string

            :param cluster_name: AWS EKS Cluster Name
            :type cluster_name: string
        """

        for p in [region_name, cluster_name]:
            if p is None or p == '' or p == ' ':
                self.die(
                    "Error: Empty parameters",
                    "region_name value: %s - type: %s" % (
                        region_name,
                        type(region_name)
                    ),
                    "cluster_name value: %s - type: %s" % (
                        cluster_name,
                        type(cluster_name)
                    ),
                )
        else:
            self.region_name = region_name
            self.cluster_name = cluster_name
            self.err = 0

    def die(self, *err):
        for m in err:
            print(m)

        exit(1)

    def get_eks_cluster_info(self):
        """
            Method invoked from create_kubeconfig method.
            Creates an eks session with boto3 and exports:
            - EKS Cluster Endpoint
            - EKS Cluster ARN
            - EKS Cluster CA
        """

        try:
            # Setting up aws eks client
            client = boto3.Session(region_name=self.region_name)
            eks_client = client.client('eks')

            # Getting eks endpoint, cluster_arn, ca_data
            self.endpoint = eks_client.describe_cluster(
                name=self.cluster_name
            )['cluster']['endpoint']

            self.cluster_arn = eks_client.describe_cluster(
                name=self.cluster_name
            )['cluster']['arn']

            self.ca_data = eks_client.describe_cluster(
                name=self.cluster_name
            )['cluster']['certificateAuthority']['data']
        except:
            self.err = 1
            self.errInfo = exc_info()
            traceback.print_exc()

    def create_kubeconfig(self):
        """
            Method that generates a kubeconfig based on
            the values exported from get_eks_cluster_info method

            :return: kubeconfig, exitCode (0/1)
        """

        self.get_eks_cluster_info()
        if self.err != 0:
            traceback.print_exc()
            self.kubeconfig = self.errInfo
            return self.kubeconfig, 1

        self.kubeconfig = kubeconfig.format(
            endpoint=self.endpoint,
            ca_data=self.ca_data,
            cluster_name=self.cluster_name,
        )
        return self.kubeconfig, 0

    def create_kubeconfig_file(self, kubepath, kubeconfig):
        '''
            Write kube_config file locally

            :param kubepath: Under which path to write the config
            :type kubepath: string
            :example kubepath: "/tmp/.kube"

            :param kubeconfig: The kube config returned from
                            create_kubeconfig() function.
            :type kubeconfig: string/json
            :example kubeconfig: SetupKubeConfig.create_kubeconfig()[0]

            :return: /absolute/path/to/kubeconfig/config
        '''

        self.kubepath = check_paths(kubepath)
        if not path.isdir(self.kubepath):
            mkdir(self.kubepath)

        try:
            create_config = open(self.kubepath + "config", "w")
            create_config.write(kubeconfig)
            create_config.close()

            self.err = 0
            kc = self.kubepath + "config"
        except:
            errInfo = exc_info()
            traceback.print_exc()
            kc = errInfo
            self.err = 1

        return kc, self.err


class InstallBins():
    """
        Class for downloading binary files
    """

    def get_binary(self, url, pkgName, pkgPath):
        """
            Download a specific binary from a url. This fuction
            invokes self.bin_download(...) method to actually download
            the resource.

            :param url: URL of the resource to be downloaded
            :typr url: string

            :param pkgName: How the resource should be named
            :type pkgName: string

            :param pkgPath: Where the resource should be saved
            :type pkgPath: string

            :return: /path/to/pkgName, err (0/1)
        """
        try:
            pkgRequest = urllib.request.urlopen(url)
            filePath, err = self.bin_download(
                pkgRequest=pkgRequest,
                pkgName=pkgName,
                pkgPath=pkgPath
            )
        except:
            errInfo = exc_info()
            traceback.print_exc()
            filePath = errInfo
            err = 1

        return filePath, err

    def bin_download(self, pkgRequest, pkgName, pkgPath, blockSize=8192):
        """
            Method for downloading resources from a url. This method
            is invoked from InstallBins.get_binary() method.

            :param pkgRequest: urllib request object
            :type pkgRequest: type(urllib.request.urlopen(url))

            :param pkgName: How the resource should be named
            :type pkgName: string

            :param pkgPath: Where the resource should be saved
            :type pkgPath: string

            :param blockSize: blockSize for pkgRequest.read()
            :type blockSize: Int

            :return: /path/to/pkgName, exitCode (0/1)
        """

        pkgPath = check_paths(pkgPath)
        filePath = pkgPath + pkgName
        pkgSize = int(pkgRequest.length)
        currentBytes = 0

        if not path.isdir(pkgPath):
            mkdir(pkgPath)

        try:
            WFile = open(filePath, 'wb')

            while True:
                byteBlock = pkgRequest.read(blockSize)

                if not byteBlock:
                    break

                WFile.write(byteBlock)
                currentBytes += len(byteBlock)
        except:
            errInfo = exc_info()
            traceback.print_exc()
            WFile.close()
            return errInfo, 1

        print(
            "Downloaded %s: [%s%%]" % (
                pkgName,
                round(
                    (float(currentBytes) / pkgSize) * 100,
                    2
                )
            )
        )
        WFile.close()
        return filePath, 0


def config_eks_access(event, context, responseData):
    responseData['ErrorInfo'] = 'None'

    # Create kubeconfig
    try:
        print("Exporting: region_name, eks name, msk name")
        region_name = environ['AWS_DEFAULT_REGION']
        cluster_name = event['ResourceProperties']['ClusterName']
        kafka_cluster_name = event['ResourceProperties']['KafkaClusterName']

        setup_kubeconfig = SetupKubeConfig(
            region_name=region_name,
            cluster_name=cluster_name
        )
    except:
        err = exc_info()
        traceback.print_exc()
        return err, None, None, 1

    # Generate kubeconfig manifest
    print("Setting up kubeconfig")
    kube_config, err = setup_kubeconfig.create_kubeconfig()
    if err != 0:
        return kube_config, None, None, 1

    # Create kubeconfig file
    print("Creating kubeconfig file")
    kubeconfig_path = "/tmp/.kube/"
    kubeconfig_file, err = setup_kubeconfig.create_kubeconfig_file(
        kubeconfig_path,
        kube_config
    )
    if err != 0:
        return kubeconfig_file, None, None, 1

    # Add KUBECONFIG path to environment
    environ["KUBECONFIG"] = kubeconfig_file

    # Cleanup no longer used objects
    del setup_kubeconfig, kubeconfig_path, err

    # Install kubectl & helm
    install_bins = InstallBins()

    # Get kubectl latest stable version
    print("Downloading kubectl binary")
    kubectl_bin_version = exac(
        [
            'curl',
            '-s',
            'https://storage.googleapis.com/kubernetes-release/release/stable.txt'
        ]
    )
    if kubectl_bin_version['ExitCode'] != 0:
        return kubectl_bin_version['stderr'].strip().decode('utf-8'), None, None, 1

    kubectl_bin_version = kubectl_bin_version['stdout'].strip().decode('utf-8')
    responseData['KubectlBinVersion'] = str(kubectl_bin_version)

    # Create kubectl download url
    kubectl_dl_url = "https://storage.googleapis.com/kubernetes-release/release/"
    kubectl_dl_url = kubectl_dl_url + kubectl_bin_version + "/bin/linux/amd64/kubectl"

    # Start downloading kubectl binary
    kubectl_bin, err = install_bins.get_binary(
        url=kubectl_dl_url,
        pkgName="kubectl",
        pkgPath="/tmp/kube/"
    )
    if err != 0:
        return kubectl_bin, None, None, 1

    # Start downloading aws-iam-authenticator binary
    print("Downloading aws-iam-authenticator binary")
    aws_iam_url = "https://amazon-eks.s3-us-west-2.amazonaws.com/"
    aws_iam_url = aws_iam_url + "1.14.6/2019-08-22/bin/linux/amd64/"
    aws_iam_url = aws_iam_url + "aws-iam-authenticator"
    aws_iam_bin, err = install_bins.get_binary(
        url=aws_iam_url,
        pkgName="aws-iam-authenticator",
        pkgPath="/tmp/awsiam/"
    )
    if err != 0:
        return aws_iam_bin, None, None, 1

    responseData['AWSIAMAuthVersion'] = str("1.14.6")

    inst_action = exac(
        "chmod +x /tmp/kube/kubectl /tmp/awsiam/aws-iam-authenticator",
        shell=True
    )
    if inst_action['ExitCode'] != 0:
        return inst_action['stderr'].strip().decode('utf-8'), None, None, 1

    return region_name, cluster_name, kafka_cluster_name, 0
