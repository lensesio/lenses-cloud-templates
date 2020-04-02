from sys import path as syspath
syspath.insert(0, 'modules')

from sys import exc_info, exit
import boto3
import traceback

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
                exit(1)

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
                errInfo = "Cluster protocol %s is not supported." % (
                    self.cluster_portocol
                )
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
            traceback.print_exc()
            return errInfo, None, None, 1

        return self.brokers, self.zk, self.kafka_metrics_opts, 0
