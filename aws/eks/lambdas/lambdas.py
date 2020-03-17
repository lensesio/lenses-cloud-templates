from sys import path as syspath
syspath.insert(0,'modules')

from manifests import kubeconfig, lenses_deployment_manifest, lenses_service_manifest
from os import getgid, getuid, seteuid, setegid
from os import path, environ, mkdir, getcwd
from sys import argv, exc_info, exit, stdout
from subprocess import call, Popen, PIPE
from ruamel import yaml
from time import sleep
from exac import exac
import cfnresponse
import traceback
import datetime
import logging
import urllib
import boto3
import json
import time


if 'debug' in argv[:]:
    log_level = logging.DEBUG
else:
    log_level = logging.INFO

responseData = {
    "ErrorInfo": None,
    "KubeCheck": None,
    "KubectlBinVersion": None,
    "AWSIAMAuthVersion": None,
    "HelmBinVersion": None,
    "KafkaBrokers": None,
    "KafkaZookeepers": None,
    "LensesManifest": None,
    "LensesDeployment": None,
    "LensesService": None,
    "LensesServiceInfo": None,
    "LensesEndpoint": None,
    "NodePort": None
}

proc_log = logging.getLogger()
proc_log= logging.basicConfig(
    level=log_level,
    format='%(levelname)s (%(threadName)-9s) %(message)s',
)

# Simple function that converts all errors to str,
# updates ErrorInfo key of responseData and stops
# the script's execution
def die(event, context, err):
    """
        Die function for CF handler.
    """

    responseData['ErrorInfo'] = str(err)

    cfnresponse.send(
        event,
        context,
        cfnresponse.SUCCESS,
        responseData
    )
    
    exit(1)

# Convert a bytes to to str
def consume_rawstring(st):
    """
        Consume a raw string by decoding and parsing \n as
        new lines

        :param st: b"string 1\nstring 2\n...string N\n"
        :type st: byte

        :return: ["string 1", "string 2", ..., "string N"]
    """

    return st.strip().decode('utf-8').splitlines()

# Print a queue of messages.
def print_consumed_strings(mqs):
    """
        Print a list of strings. This function calls
        consume_rawstring and then prints the list

        :param st: b"string 1\nstring 2\n...string N\n"
        :type st: byte
    """

    print(2*'\n')
    for msg in consume_rawstring(mqs):
        print(msg)
    else:
        print(2*'\n')

def check_paths(*args):
    """
        Concat paths and append '/' at the end if is missing

        :param args: List of paths
        :type args: List of Strings / String

        :return: path1/path2/.../pathN
    """

    path=''
    for i in args:
        if not i.endswith('/'):
            path=path + i + '/'
        else:
            path=path + i

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
            logging.error(self.errInfo)
            traceback.print_exc()

    def create_kubeconfig(self):
        """
            Method that generates a kubeconfig based on
            the values exported from get_eks_cluster_info method

            :return: kubeconfig, exitCode (0/1)
        """

        self.get_eks_cluster_info()
        if self.err == 0:
            self.kubeconfig = kubeconfig.format(
                endpoint=self.endpoint,
                ca_data=self.ca_data,
                cluster_name=self.cluster_name,
            )
            exitCode = 0
        else:
            logging.error(self.errInfo)
            traceback.print_exc()
            self.kubeconfig = self.errInfo
            exitCode = 1

        return self.kubeconfig, exitCode

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
            logging.error(errInfo)
            traceback.print_exc()
            kc = errInfo
            self.err = 1

        return kc, self.err

class InstallBins():
    """
        Class for downloading binary files
    """

    def GetBinary(self, url, pkgName, pkgPath):
        """
            Download a specific binary from a url. This fuction
            invokes self.BinDL(...) method to actually download
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
            filePath, err = self.BinDL(
                pkgRequest=pkgRequest,
                pkgName=pkgName,
                pkgPath=pkgPath
            )
        except:
            errInfo = exc_info()
            logging.error(errInfo)
            traceback.print_exc()
            filePath = errInfo
            err = 1

        return filePath, err

    def BinDL(self, pkgRequest, pkgName, pkgPath, blockSize=8192):
        """
            Method for downloading resources from a url. This method
            is invoked from InstallBins.GetBinary() method.

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
            logging.error(errInfo)
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

class BackendConfig():
    """
        Class for exporting MSK Connection information
        - Brokers
        - Zookeepers
        - Connection Protocol
        - Trustostore
    """
    def __init__(self, cluster_name, region_name):
        """
            :param region_name": Region Name for the AWS MSK Cluster
            :type region_name": string

            :param cluster_name: AWS MSK Cluster Name
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

    def GetKafkaClustersInfo(self):
        """
            Method that creates a MSK boto3 session.
            Then proceeds and extracts:
            - MSK CLuster ARN
            - MSK Cluster Protocol
            - MSK Cluster Info
            - MSK Cluster Brokers

            :return: None
        """
        self.err = 0
        errInfo = None
        try:
            client = boto3.Session(region_name=self.region_name)
            self.msk_client = client.client('kafka')
            aws_kafka_clusters = self.msk_client.list_clusters()

            for c in aws_kafka_clusters['ClusterInfoList']:
                if c['ClusterName'] == self.cluster_name:
                    self.cluster_arn = c['ClusterArn']

                    self.cluster_portocol = c['EncryptionInfo'][
                        'EncryptionInTransit'
                        ]['ClientBroker']

                    self.kafka_cluster_info = self.msk_client.describe_cluster(
                        ClusterArn=self.cluster_arn
                    )

                    self.kafka_cluster_brokers = self.msk_client.get_bootstrap_brokers(
                        ClusterArn=self.cluster_arn
                    )

                    self.kafka_nodes_list = self.msk_client.list_nodes(
                        ClusterArn=self.cluster_arn
                    )
                    break
            else:
                errInfo = "No cluster with name %s found." % self.cluster_name
                self.err = 1
        except:
            errInfo = exc_info()
            logging.error(errInfo)
            traceback.print_exc()
            self.err = 1
        
        return errInfo, self.err

    def GetBackendInfo(self):
        """
            Method that generates the broker and zookeeper endpoints,
            for Lenses.

            The methods calls self.GetKafkaClustersInfo() method
            then generates the brokers and zookeepers in hocoon
            format.

            :returns: 'PROTOCOL://broker1,...,PROTOCOL://broker2',
                '{url:"zookeeper1"}, ..., {url:"zookeeperN"}',
                errorCode 
        """

        errInfo, err = self.GetKafkaClustersInfo()
        if err != 0:
            return errInfo, None, None, 1

        try:
            if self.cluster_portocol in ['PLAINTEXT', 'TLS_PLAINTEXT']:
                self.brokers = self.kafka_cluster_brokers[
                    'BootstrapBrokerString'
                ]

                self.brokers = [
                    'PLAINTEXT://' + x for x in self.brokers.split(',')
                ]
            elif self.cluster_portocol in ['TLS']:
                self.brokers = self.kafka_cluster_brokers[
                    'BootstrapBrokerStringTls'
                ]

                self.brokers = [
                    'SSL://' + x for x in self.brokers.split(',')
                ]
            else:
                errInfo = "Cluster protocol %s is not supported." % self.cluster_portocol
                return errInfo, None, None, 1

            self.zookeepers = self.kafka_cluster_info[
                'ClusterInfo'
            ]['ZookeeperConnectString']

            self.zk = ["{url:\"%s\"}" % x for x in self.zookeepers.split(',')]
            self.zk = ', '.join(self.zk)

            self.brokers = ','.join(self.brokers)

            self.jmx_enabled = self.kafka_cluster_info[
                'ClusterInfo'
            ]['OpenMonitoring']['Prometheus'][
                'JmxExporter'
            ]['EnabledInBroker']

            self.kafka_metrics_opts = []
            
            if self.jmx_enabled:
                for node in self.kafka_nodes_list['NodeInfoList']:
                    self.kafka_metrics_opts.append(
                        "{id: %s,  url:\"http://%s:11001/metrics\"}" % (
                            node['BrokerNodeInfo']['BrokerId'],
                            node['BrokerNodeInfo']['Endpoints'][0]
                        )
                    )

        except:
            errInfo = exc_info()
            logging.error(errInfo)
            traceback.print_exc()
            return errInfo, None, None, 1

        return self.brokers, self.zk, self.kafka_metrics_opts, 0

class SetupLenes():
    """
        Class for creating k8 screts & deployment manifests for Lenses.
    """
    def CreateLensesLicense(self, secret):
        """
            Method for creating lenses-license secret in kubernetes

            :param secret: Lenses License (JSON)
            :type secret: string

            :return: info, errorCode
        """

        check_if_license_exists = exac(
            "kubectl get secrets -n default | grep -iq lenses-license",
            shell=True
        )
        if check_if_license_exists['ExitCode'] != 0:
            try:
                f = open("/tmp/license.json", "w")
                f.write(secret)
                f.close()
            except:
                errInfo = exc_info()
                logging.error(errInfo)
                traceback.print_exc()
                return errInfo, 1

            create_secret = exac(
                "kubectl create secret generic 'lenses-license' --from-file=/tmp/license.json -n default",
                secret=True,
                shell=True
            )
            if create_secret['ExitCode'] != 0:
                return "Could not create secret file lenses-license", 1

            print_consumed_strings(
                create_secret['stdout']
            )
        
            return "Lenses license secret added successfuly to kubernetes", 0
        else:
            return "Lenses license secret already exists in kubernetes", 0

    def CreateLensesManifest(
        self,
        brokers,
        zookeepers,
        username,
        password,
        kafka_metrics_opts=None,
        registry=None,
        connect=None
    ):
        """
            Method that creates the Lenses Kubernetes Manifest.
            It reads a basic manifest: lenses_deployment_manifest
            and updates it with additional values:
            - Brokers Endpoints
            - Zookeepers Endpoints
            - Connect Endpoints
            - Registry Endpoints

            - License Volumes
            - Truststore Volumes

            :param brokers: Brokers endpoints
            :type brokers: string

            :param zookeepers: Zookeepers endpoints
            :type zookeepers: string

            :param username: Admin username
            :type username: string

            :param password: Admin password
            :type password: string

            :param registry: Registry endpoints
            :type registry: string

            :param connect: Connect endpoints
            :type connect: string

            :return: deployment_manifest, errorCode 
        """

        try:
            manifest = yaml.safe_load(lenses_deployment_manifest)
            manifest['spec']['template']['spec']['containers'][0]['env'].append(
                {
                    'name': 'LENSES_KAFKA_BROKERS',
                    'value': brokers
                }
            ) 
            manifest['spec']['template']['spec']['containers'][0]['env'].append(
                {
                    'name': 'LENSES_ZOOKEEPER_HOSTS',
                    'value': "[%s]" % zookeepers
                }
            )
            if kafka_metrics_opts is not None:
                manifest['spec']['template']['spec']['containers'][0]['env'].append(
                    {
                        'name': 'LENSES_KAFKA_METRICS',
                        'value': "{type: \"AWS\", port: [%s]}" % (
                            ', '.join(kafka_metrics_opts)
                        )
                    }
                )
            manifest['spec']['template']['spec']['containers'][0]['env'].append(
                {
                    'name': 'LENSES_SECURITY_USER',
                    'value': username
                }
            )
            manifest['spec']['template']['spec']['containers'][0]['env'].append(
                {
                    'name': 'LENSES_SECURITY_PASSWORD',
                    'value': password
                }
            )

        except (TypeError, KeyError) as e:
            errInfo = exc_info()
            logging.error(errInfo)
            traceback.print_exc()
            return errInfo, 1

        print("Checking if MSK Cluster SSL is enabled")
        if "SSL" in brokers:
            print("MSK SSL: Enabled")
            action = exac("mkdir -vp /tmp/private/ssl", shell=True)
            if action['ExitCode'] != 0:
                return action['stderr'].strip().decode('utf-8'), 1

            print("Checking if secret truststore exists")
            action = exac("[ ! -e /var/private/ssl/client.truststore.jks ] && exit 1", shell=True)
            if action['ExitCode'] != 0:
                action = exac("cp /etc/pki/java/cacerts /tmp/private/ssl/client.truststore.jks", shell=True)
                if action['ExitCode'] != 0:
                    return action['stderr'].strip().decode('utf-8'), 1

            check_if_truststore_exists = exac(
                "kubectl get secrets -n default | grep -iq kafka-truststore",
                shell=True
            )
            if check_if_truststore_exists['ExitCode'] != 0:
                create_truststore=exac(
                    "kubectl create secret generic 'kafka-truststore' \
                    --from-file=/tmp/private/ssl/client.truststore.jks -n default",
                    secret=True,
                    shell=True
                )
                if create_truststore['ExitCode'] != 0:
                    return create_truststore['stderr'].strip().decode('utf-8'), 1

                print_consumed_strings(
                    create_truststore['stdout']
                )

            try:
                manifest['spec']['template']['spec']['containers'][0]['env'].append(
                    {
                        'name': 'LENSES_KAFKA_SETTINGS_CONSUMER_SECURITY_PROTOCOL',
                        'value': "SSL"
                    }
                )
                manifest['spec']['template']['spec']['containers'][0]['env'].append(
                    {
                        'name': 'LENSES_KAFKA_SETTINGS_CONSUMER_SSL_TRUSTSTORE_LOCATION',
                        'value': "/var/private/ssl/client.truststore.jks"
                    }
                )
                manifest['spec']['template']['spec']['containers'][0]['env'].append(
                    {
                        'name': 'LENSES_KAFKA_SETTINGS_PRODUCER_SECURITY_PROTOCOL',
                        'value': "SSL"
                    }
                )
                manifest['spec']['template']['spec']['containers'][0]['env'].append(
                    {
                        'name': 'LENSES_KAFKA_SETTINGS_PRODUCER_SSL_TRUSTSTORE_LOCATION',
                        'value': "/var/private/ssl/client.truststore.jks"
                    }
                )
                manifest['spec']['template']['spec']['volumes'].append(
                    {
                        'name': 'kafka-certs',
                        'secret': {
                            'secretName': 'kafka-truststore'
                        }
                    }
                )
                manifest['spec']['template']['spec']['containers'][0]['volumeMounts'].append(
                    {
                        'name': 'kafka-certs',
                        'mountPath': '/var/private/ssl'
                    }
                )
            except (TypeError, KeyError) as e:
                errInfo = exc_info()
                logging.error(errInfo)
                traceback.print_exc()
                return errInfo, 1

        try:
            lenses_manifest=yaml.dump(manifest, default_flow_style=False)
            f = open("/tmp/lenses_deployment.yaml", "w")
            f.write(lenses_manifest)
            f.close()

            service_manifest = yaml.safe_load(lenses_service_manifest)
            service_manifest = yaml.dump(service_manifest, default_flow_style=False)
            f = open("/tmp/lenses_service.yaml", "w")
            f.write(service_manifest)
            f.close()
        except:
            errInfo = exc_info()
            logging.error(errInfo)
            traceback.print_exc()
            return errInfo, 1
        
        return manifest, 0

def config_eks_access(event, context):
    logging.info(event)
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
        logging.error(err)
        traceback.print_exc()
        die(event,context, err)
        exit(1)

    # Generate kubeconfig manifest
    print("Setting up kubeconfig")
    kube_config, err = setup_kubeconfig.create_kubeconfig()
    if err != 0:
        die(
            event,
            context,
            kube_config
        )
    
    # Create kubeconfig file
    print("Creating kubeconfig file")
    kubeconfig_path = "/tmp/.kube/"
    kubeconfig_file, err = setup_kubeconfig.create_kubeconfig_file(
        kubeconfig_path,
        kube_config
    )
    if err != 0:
        die(
            event,
            context,
            kubeconfig_file
        )

    # Add KUBECONFIG path to environment
    environ["KUBECONFIG"] = kubeconfig_file

    # Cleanup no longer used objects
    del setup_kubeconfig, kubeconfig_path, err

    ### Install kubectl & helm
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
        die(
            event,
            context,
            kubectl_bin_version['stderr'].strip().decode('utf-8')
        )

    kubectl_bin_version = kubectl_bin_version['stdout'].strip().decode('utf-8')
    responseData['KubectlBinVersion'] = str(kubectl_bin_version)

    # Create kubectl download url
    kubectl_dl_url = "https://storage.googleapis.com/kubernetes-release/release/"
    kubectl_dl_url =  kubectl_dl_url + kubectl_bin_version + "/bin/linux/amd64/kubectl"

    # Start downloading kubectl binary
    kubectl_bin, err = install_bins.GetBinary(
        url=kubectl_dl_url,
        pkgName="kubectl",
        pkgPath="/tmp/kube/"
    )
    if err != 0:
        die(
            event,
            context,
            kubectl_bin
        )

    # Start downloading aws-iam-authenticator binary
    print("Downloading aws-iam-authenticator binary")
    aws_iam_url = "https://amazon-eks.s3-us-west-2.amazonaws.com/"
    aws_iam_url = aws_iam_url + "1.14.6/2019-08-22/bin/linux/amd64/"
    aws_iam_url = aws_iam_url + "aws-iam-authenticator"
    aws_iam_bin, err = install_bins.GetBinary(
        url=aws_iam_url,
        pkgName="aws-iam-authenticator",
        pkgPath="/tmp/awsiam/"
    )
    if err != 0:
        die(
            event,
            context,
            aws_iam_bin
        )

    responseData['AWSIAMAuthVersion'] = str("1.14.6")

    # Get helm latest stable version
    print("Downloading helm tarball")
    get_helm_ver_cmd = "curl -sSL https://github.com/kubernetes/helm/releases"
    get_helm_ver_cmd = get_helm_ver_cmd +  "| sed -n '/Latest release<\/a>/,$p'"
    get_helm_ver_cmd = get_helm_ver_cmd + "| grep -oE 'v[0-9]+\.[0-9]+\.[0-9]+' | head -1"

    helm_bin_version = exac(
        get_helm_ver_cmd,
        shell=True
    )
    if helm_bin_version['ExitCode'] != 0:
        die(
            event,
            context,
            helm_bin_version['stderr'].strip().decode('utf-8')
        )

    helm_dl_url = "https://get.helm.sh/helm-{v}-linux-amd64.tar.gz".format(
        v=helm_bin_version['stdout'].strip().decode('utf-8')
    )

    # Start downloading helm tarball
    helm_bin, err = install_bins.GetBinary(
        url=helm_dl_url,
        pkgName="helm-{v}-linux-amd64.tar.gz".format(
            v=helm_bin_version['stdout'].strip().decode('utf-8')
        ),
        pkgPath="/tmp/helm/"
    )
    if err != 0:
        die(
            event,
            context,
            helm_bin
        )

    responseData['HelmBinVersion'] = str(
        helm_bin_version['stdout'].strip().decode('utf-8')
    )

    # Install helm tarball to /tmp/helm
    print("Installing helm binary")
    action_list = [
        "cd /tmp/helm && tar xf helm-{v}-linux-amd64.tar.gz; cd -".format(
            v=helm_bin_version['stdout'].strip().decode('utf-8')
        ),
        "mv /tmp/helm/linux-amd64/helm /tmp/helm/helm",
        "rm -rf /tmp/helm/linux-amd64",
        "chmod +x /tmp/helm/helm /tmp/kube/kubectl /tmp/awsiam/aws-iam-authenticator"
    ]

    for action in action_list:
        logging.info("Executing: %s" % action)
        inst_action = exac(
            action,
            shell=True
        )
        if inst_action['ExitCode'] != 0:
            die(
                event,
                context,
                inst_action['stderr'].strip().decode('utf-8')
            )

    # Clear no longer used objects
    del (
        err, helm_bin_version, helm_dl_url, aws_iam_url,
        kubectl_bin_version, kubectl_dl_url, install_bins,
        helm_bin, action_list, action, inst_action,
        get_helm_ver_cmd, kubectl_bin, aws_iam_bin
    )

    return region_name, cluster_name, kafka_cluster_name

def check_credentials(secret, stype):
    print("Checking %s" % stype)
    if secret in ['', ' ', None]:
        err = "Error: Invalid %s value: %s - type: %s" % (
            stype,
            secret,
            type(secret)
        )
        print(err)
        return err, 1
    if stype == 'username' and len(secret) < 4:
        err = "Error: Invalid %s length: %s. Username must be >= 4 characters" % (
            stype,
            len(secret),
        )
        print(err)
        return err, 1
    elif stype == 'password' and len(secret) < 8:
        err = "Error: Invalid %s length: %s. Password must be >= 8 characters" % (
            stype,
            len(secret),
        )
        print(err)
        return err, 1
    elif stype == 'license':
        key_list = [
            "source",
            "clientId",
            "details",
            "key"
        ]
        try:
            for c in key_list:
                if c not in json.loads(secret).keys():
                    err = "Error: Invalid license"
                    print(err)
                    return err, 1
        except:
            errInfo = exc_info()
            logging.error(errInfo)
            traceback.print_exc()

            return errInfo, 1

    print("Smoke tests passed for: %s" % stype)
    return '', 0

def main_create(event, context):
    '''
        Function for creating EKS resources and deploying Lenses.

        :param event: Event payload sent from lambda_handler
        :type event: JSON

        :param context: Context sent from lambda_handler
        :type context: JSON
    '''
    print("Configuring kubectl")
    (
        region_name,
        cluster_name,
        kafka_cluster_name
    ) = config_eks_access(event=event, context=context)

    # Export Lenses Admin and Password
    lenses_admin_username = event['ResourceProperties']['LensesAdminUsername']
    lenses_admin_password = event['ResourceProperties']['LensesAdminPassword']
    lenses_license = event['ResourceProperties']['LensesLicense']

    # Check that admin and password are valid strings with some lenght restrictions
    check_username, err = check_credentials(
        secret=lenses_admin_username,
        stype="username"
    )
    if err != 0:
        die(
            event,
            context,
            check_username
        )
    check_password, err = check_credentials(
        secret=lenses_admin_password,
        stype="password"
    )
    if err != 0:
        die(
            event,
            context,
            check_password
        )

    check_license, err = check_credentials(
        secret=lenses_license,
        stype="license"
    )
    if err != 0:
        die(
            event,
            context,
            check_license
        )

    # Export kube and helm paths to environment path
    old_path = environ["PATH"]
    new_path = "/tmp/helm/:/tmp/kube/:/tmp/awsiam/" + old_path
    environ["PATH"] = new_path

    # Check if kubectl can access EKS cluster
    print("Checking if kubectl can access EKS cluster")
    check_kubectl_access = exac(
        "export KUBECONFIG=/tmp/.kube/config; kubectl get pods --all-namespaces",
        shell=True
    )
    if check_kubectl_access['ExitCode'] != 0:
        responseData['KubeCheck'] = check_kubectl_access['stderr'].strip().decode('utf-8')
        die(
            event,
            context,
            check_kubectl_access['stderr'].strip().decode('utf-8')
        )

    responseData['KubeCheck'] = "Kubectl configured successfully!"

    # Get all pods, and print the result
    print_consumed_strings(
        exac(
            "export KUBECONFIG=/tmp/.kube/config; kubectl get pods --all-namespaces",
            shell=True
        )['stdout']
    )

    # Configure Kafka Backend endpoints
    print("Getting kafka endpoints")
    kafka_endpoints = BackendConfig(
        cluster_name=kafka_cluster_name,
        region_name=region_name
    )

    (
        brokers,
        zookeepers,
        kafka_metrics_opts,
        err
    ) = kafka_endpoints.GetBackendInfo()
    if err != 0:
        die(
            event,
            context,
            brokers
        )

    responseData['KafkaBrokers'] = str(brokers)
    responseData['KafkaZookeepers'] = str(zookeepers)

    # Create Lenses license secret in kubernetes
    print("Checking if secret license exits")
    configure_lenses = SetupLenes()
    create_license, err = configure_lenses.CreateLensesLicense(
        secret=lenses_license
    )
    if err != 0:
        die(
            event,
            context,
            create_license
        )

    # Generate lenses deployment manifest
    lenses_manifest, err = configure_lenses.CreateLensesManifest(
        brokers=brokers,
        zookeepers=zookeepers,
        username=lenses_admin_username,
        password=lenses_admin_password,
        kafka_metrics_opts=kafka_metrics_opts
    )
    if err != 0:
        die(
            event,
            context,
            lenses_manifest
        )

    responseData['LensesManifest'] = "Manifest created successfully"

    # Create the deployment of Lenses. Die otherwise
    print("Checking if Lenses deployment exits")
    podexists = exac(
        "kubectl get pods -n default | grep -iq lenses",
        shell=True
    )
    if podexists['ExitCode'] != 0:
        print("Creating Lenses deployment")
        deploy_lenses = exac(
            "kubectl apply -f /tmp/lenses_deployment.yaml",
            shell=True
        )
        if deploy_lenses['ExitCode'] != 0:
            die(
                event,
                context,
                deploy_lenses['stderr'].strip().decode('utf-8')
            )

        responseData['LensesDeployment'] = deploy_lenses['stdout'].strip().decode('utf-8')
    else:
        responseData['LensesDeployment'] = "Lenses Deployment already exists in the cluster"

    # Create Lenses Loadbalancer Service. Die otherwise
    print("Checking if Lenses service exits")
    svcexists = exac(
        "kubectl get svc -n default | grep -iq 'lenses-service'",
        shell=True
    )
    if svcexists['ExitCode'] != 0:
        print("Creating Lenses service")
        deploy_svc = exac(
            "kubectl apply -f /tmp/lenses_service.yaml",
            shell=True
        )
        if deploy_svc['ExitCode'] != 0:
            die(
                event,
                context,
                deploy_svc['stderr'].strip().decode('utf-8')
            )

        responseData['LensesService'] = deploy_svc['stdout'].strip().decode('utf-8')
    else:
        responseData['LensesService'] = "Lenses Service already exists in the cluster"

    # Check if LB service has been created. The reason for this check is because we need to grap
    # the content of the service exported endpoint and send it back to CF.
    logging.info("Checking for Lenses endpoint")
    print("Checking for Lenses endpoint")
    for t in range(10):
        serviceInfo = exac(
            "kubectl get service/lenses-service | tail -n 1 | column -t",
            shell=True
        )
        if serviceInfo['stderr'].strip().decode('utf-8') != '':
            responseData['LensesServiceInfo'] = "Unable to get service info"
            responseData['LensesEndpoint'] = "Unable to get endpoint"
            die(
                event,
                context,
                serviceInfo['stderr'].strip().decode('utf-8')
            )

        responseData['LensesServiceInfo'] = serviceInfo['stdout'].strip().decode('utf-8')
        print(responseData['LensesServiceInfo'])
        logging.info(responseData['LensesServiceInfo'])

        responseData['LensesEndpoint'] = responseData['LensesServiceInfo'].split()[3]
        logging.info(responseData['LensesEndpoint'])
        print(responseData['LensesEndpoint'])

        get_service_endpoint = responseData['LensesServiceInfo'].split()
        get_service_endpoint = get_service_endpoint[4].split(':')[1].split('/')[0]
        responseData['NodePort'] = get_service_endpoint
        logging.info(responseData['NodePort'])
        print(responseData['NodePort'])

        if responseData['LensesEndpoint'] != '<pending>':
            break

        sleep(5)

    # Finally responde back to Cloudformation
    cfnresponse.send(
        event,
        context,
        cfnresponse.SUCCESS,
        responseData
    )

def main_del(event, context):
    '''
        Funcction for handling delete CF events.
        The function is required since CF does not have direct access to EKS,
        therefore on CF deletion we ant to ensure tha all resources created
        should be deleted successfully.

        :param event: Event payload sent from lambda_handler
        :type event: JSON

        :param context: Context sent from lambda_handler
        :type context: JSON
    '''
    (
        region_name,
        cluster_name,
        kafka_cluster_name
    ) = config_eks_access(event=event, context=context)

    # Export kube and helm paths to environment path
    old_path = environ["PATH"]
    new_path = "/tmp/helm/:/tmp/kube/:/tmp/awsiam/" + old_path
    environ["PATH"] = new_path

   # Check if Lenses deployment exists. Delete in case it does
    print("Checking if Lenses deployment exists")
    podexists = exac(
        "kubectl get deployment lenses -n default | grep -iq lenses",
        shell=True
    )
    if podexists['ExitCode'] == 0:
        print("Deleting Lenses deployment")
        deploy_lenses = exac(
            "kubectl delete deployment lenses",
            shell=True
        )
        if deploy_lenses['ExitCode'] != 0:
            die(
                event,
                context,
                deploy_lenses['stderr'].strip().decode('utf-8')
            )

    # Delete Lenses LB Service in case it exists
    print("Checking if Lenses service exists")
    svcexists = exac(
        "kubectl get svc lenses-service -n default | grep -iq 'lenses-service'",
        shell=True
    )
    if svcexists['ExitCode'] == 0:
        print("Deleting Lenses service")
        delete_svc = exac(
            "kubectl delete svc lenses-service",
            shell=True
        )
        if delete_svc['ExitCode'] != 0:
            die(
                event,
                context,
                delete_svc['stderr'].strip().decode('utf-8')
            )

    # Check if license secret exists. In case it does exists, delete
    print("Checking if secret license exists")
    check_if_license_exists = exac(
        "kubectl get secrets -n default | grep -iq lenses-license",
        shell=True
    )
    if check_if_license_exists['ExitCode'] == 0:
        print("Deleting secret license")
        delete_lenses_secret = exac(
            "kubectl delete secret 'lenses-license'",
            secret=True,
            shell=True
        )
        if delete_lenses_secret['ExitCode'] != 0:
            die(
                event,
                context,
                delete_lenses_secret['stderr'].strip().decode('utf-8')
            )

    # Same check and action if true as the secret license from above,
    # but for turststore.
    print("Checking if secret truststore exists")
    check_if_truststore_exists = exac(
        "kubectl get secrets -n default | grep -iq kafka-truststore",
        shell=True
    )
    if check_if_truststore_exists['ExitCode'] == 0:
        print("Deleting secret truststore")
        delete_truststore=exac(
            "kubectl delete secret 'kafka-truststore'",
            secret=True,
            shell=True
        )
        if delete_truststore['ExitCode'] != 0:
            die(
                event,
                context,
                delete_truststore['stderr'].strip().decode('utf-8')
            )

    # Finally send back to CF that the deletion has been completed successfully.
    cfnresponse.send(
        event,
        context,
        cfnresponse.SUCCESS,
        responseData
    )

def lambda_handler(event, context):
    '''
        Main lambda handler function.
        Check event type with accept values [Create/Delete],
        and invoke the appropriate function or die.

        :param event: Event payload sent from CF.
        :type event: JSON

        :param context: Context sent from CF.
        :type context: JSON
    '''
    try:
        if event['RequestType'] == 'Create':
            main_create(
                event=event,
                context=context
            )
        elif event['RequestType'] == 'Delete':
            main_del(
                event=event,
                context=context
            )
        else:
            die(
                event,
                context,
                "Recieved unsupported event: %s. Exiting..." % (
                    event['RequestType']
                )
            )
    except SystemExit:
        pass
    except:
        errInfo = exc_info()
        logging.error(errInfo)
        traceback.print_exc()

        die(
            event,
            context,
            errInfo
        )
