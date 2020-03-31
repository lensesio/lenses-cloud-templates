from sys import path as syspath
syspath.insert(0, 'modules')

from manifests import (
    lenses_deployment_manifest,
    lenses_service_manifest
)
from sys import exc_info
from exac import exac
import traceback
import yaml

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
                traceback.print_exc()
                return errInfo, 1

            create_secret = exac(
                "kubectl create secret generic 'lenses-license' --from-file=/tmp/license.json -n default",
                secret=True,
                shell=True
            )
            if create_secret['ExitCode'] != 0:
                return "Could not create secret file lenses-license", 1

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
                    'value': "\"%s\"" % username
                }
            )
            manifest['spec']['template']['spec']['containers'][0]['env'].append(
                {
                    'name': 'LENSES_SECURITY_PASSWORD',
                    'value': "\"%s\"" % password
                }
            )

        except (TypeError, KeyError) as e:
            errInfo = exc_info()
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
                create_truststore = exac(
                    "kubectl create secret generic 'kafka-truststore' \
                    --from-file=/tmp/private/ssl/client.truststore.jks -n default",
                    secret=True,
                    shell=True
                )
                if create_truststore['ExitCode'] != 0:
                    return create_truststore['stderr'].strip().decode('utf-8'), 1

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
                traceback.print_exc()
                return errInfo, 1

        try:
            lenses_manifest = yaml.dump(
                manifest,
                default_flow_style=False
            )

            f = open("/tmp/lenses_deployment.yaml", "w")
            f.write(lenses_manifest)
            f.close()

            service_manifest = yaml.safe_load(lenses_service_manifest)
            service_manifest = yaml.dump(
                service_manifest,
                default_flow_style=False
            )

            f = open("/tmp/lenses_service.yaml", "w")
            f.write(service_manifest)
            f.close()
        except:
            errInfo = exc_info()
            traceback.print_exc()
            return errInfo, 1

        return manifest, 0

