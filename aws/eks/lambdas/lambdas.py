from sys import path as syspath
syspath.insert(0, 'modules')

from backend_config import BackendConfig
from setup_lenses import SetupLenes
from eks_config import config_eks_access
from os import path, environ, mkdir
from sys import argv, exc_info, exit
from time import sleep
from exac import exac
import cfnresponse
import traceback
import logging
import random
import string
import json


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
    "LensesPassword": None,
    "NodePort": None
}

proc_log = logging.getLogger()
proc_log = logging.basicConfig(
    level=log_level,
    format='%(levelname)s (%(threadName)-9s) %(message)s',
)


# Simple function that converts all errors to str,
# updates ErrorInfo key of responseData and stops
# the script's execution
def die(err):
    """
        Die function for CF handler.
    """
    print(err)
    responseData['ErrorInfo'] = str(err)
    exit(1)


def main_create(event, context):
    '''
        Function for creating EKS resources and deploying Lenses.

        :param event: Event payload sent from lambda_handler
        :type event: JSON

        :param context: Context sent from lambda_handler
        :type context: JSON
    '''

    print(event)
    deployment_name = "eks-lenses-{d}".format(
        d=event['StackId'].split('/')[-1]
    )

    print("Configuring kubectl")
    (
        region_name,
        cluster_name,
        kafka_cluster_name,
        err
    ) = config_eks_access(
        event=event,
        context=context,
        responseData=responseData
    )
    if err != 0:
        die(region_name)

    # Generate adming credentials
    lenses_admin_username = "admin"
    lenses_admin_password = ''.join(
        random.choice(string.ascii_letters) for i in range(32)
    )
    responseData["LensesPassword"] = lenses_admin_password

    # Get Lenses license
    try:
        lenses_license = event['ResourceProperties']['LensesLicense']
        if type(json.loads(lenses_license)) is not dict:
            die("License is not a valid json")
    except json.JSONDecodeError:
        die(exc_info())

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
        responseData['KubeCheck'] = check_kubectl_access[
            'stderr'
        ].strip().decode('utf-8')

        die(check_kubectl_access['stderr'].strip().decode('utf-8'))

    responseData['KubeCheck'] = "Kubectl configured successfully!"

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
        die(brokers)

    responseData['KafkaBrokers'] = str(brokers)
    responseData['KafkaZookeepers'] = str(zookeepers)

    # Create Lenses license secret in kubernetes
    print("Checking if secret license exits")
    configure_lenses = SetupLenes()
    create_license, err = configure_lenses.CreateLensesLicense(
        secret=lenses_license
    )
    if err != 0:
        die(create_license)

    # Generate lenses deployment manifest
    lenses_manifest, err = configure_lenses.CreateLensesManifest(
        brokers=brokers,
        zookeepers=zookeepers,
        username=lenses_admin_username,
        password=lenses_admin_password,
        deployment_name=deployment_name,
        kafka_metrics_opts=kafka_metrics_opts
    )
    if err != 0:
        die(lenses_manifest)

    responseData['LensesManifest'] = "Manifest created successfully"

    # Create the deployment of Lenses. Die otherwise
    print("Checking if Lenses deployment exits")
    podexists = exac(
        "kubectl get pods -n default | grep -iq %s" % deployment_name,
        shell=True
    )
    if podexists['ExitCode'] != 0:
        print("Creating Lenses deployment")
        deploy_lenses = exac(
            "kubectl apply -f /tmp/lenses_deployment.yaml",
            shell=True
        )
        if deploy_lenses['ExitCode'] != 0:
            die(deploy_lenses['stderr'].strip().decode('utf-8'))

        responseData['LensesDeployment'] = deploy_lenses[
            'stdout'
        ].strip().decode('utf-8')
    else:
        responseData[
            'LensesDeployment'
        ] = "Lenses Deployment already exists in the cluster"

    # Create Lenses Loadbalancer Service. Die otherwise
    print("Checking if Lenses service exits")
    svcexists = exac(
        "kubectl get svc -n default | grep -iq '%s-service'" % deployment_name,
        shell=True
    )
    if svcexists['ExitCode'] != 0:
        print("Creating Lenses service")
        deploy_svc = exac(
            "kubectl apply -f /tmp/lenses_service.yaml",
            shell=True
        )
        if deploy_svc['ExitCode'] != 0:
            die(deploy_svc['stderr'].strip().decode('utf-8'))

        responseData['LensesService'] = deploy_svc[
            'stdout'
        ].strip().decode('utf-8')
    else:
        responseData[
            'LensesService'
        ] = "Lenses Service already exists in the cluster"

    # Check if LB service has been created.
    # The reason for this check is because we need to grap
    # the content of the service exported endpoint and send it back to CF.
    print("Checking for Lenses endpoint")
    for t in range(10):
        serviceInfo = exac(
            "kubectl get service/{sname}-service | tail -n 1 | column -t".format(
                sname=deployment_name
            ),
            shell=True
        )
        if serviceInfo['stderr'].strip().decode('utf-8') != '':
            responseData['LensesServiceInfo'] = "Unable to get service info"
            responseData['LensesEndpoint'] = "Unable to get endpoint"
            die(serviceInfo['stderr'].strip().decode('utf-8'))

        responseData['LensesServiceInfo'] = serviceInfo['stdout'].strip().decode('utf-8')
        print(responseData['LensesServiceInfo'])

        responseData['LensesEndpoint'] = responseData['LensesServiceInfo'].split()[3]
        print(responseData['LensesEndpoint'])

        get_service_endpoint = responseData['LensesServiceInfo'].split()
        get_service_endpoint = get_service_endpoint[4].split(':')[1].split('/')[0]
        responseData['NodePort'] = get_service_endpoint
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

    deployment_name = "eks-lenses-{d}".format(
        d=event['StackId'].split('/')[-1]
    )

    (
        region_name,
        cluster_name,
        kafka_cluster_name,
        err
    ) = config_eks_access(event=event, context=context, responseData=responseData)
    if err != 0:
        die(region_name)

    # Export kube and helm paths to environment path
    old_path = environ["PATH"]
    new_path = "/tmp/helm/:/tmp/kube/:/tmp/awsiam/" + old_path
    environ["PATH"] = new_path

   # Check if Lenses deployment exists. Delete in case it does
    print("Checking if Lenses deployment exists")
    podexists = exac(
        "kubectl get deployment %s -n default | grep -iq lenses" % deployment_name,
        shell=True
    )
    if podexists['ExitCode'] == 0:
        print("Deleting Lenses deployment")
        deploy_lenses = exac(
            "kubectl delete deployment %s" % deployment_name,
            shell=True
        )
        if deploy_lenses['ExitCode'] != 0:
            die(deploy_lenses['stderr'].strip().decode('utf-8'))

    # Delete Lenses LB Service in case it exists
    print("Checking if Lenses service exists")
    svcexists = exac(
        "kubectl get svc %s-service -n default | grep -iq '%s-service'" % (
            deployment_name, deployment_name
        ),
        shell=True
    )
    if svcexists['ExitCode'] == 0:
        print("Deleting Lenses service")
        delete_svc = exac(
            "kubectl delete svc %s-service" % deployment_name,
            shell=True
        )
        if delete_svc['ExitCode'] != 0:
            die(delete_svc['stderr'].strip().decode('utf-8'))

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
            die(delete_lenses_secret['stderr'].strip().decode('utf-8'))

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
            die(delete_truststore['stderr'].strip().decode('utf-8'))

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
            responseData['ErrorInfo'] = "Recieved unsupported event: %s. Exiting..." % (
                    event['RequestType']
            )

            cfnresponse.send(
                event,
                context,
                cfnresponse.FAILED,
                responseData
            )
    except:
        errInfo = exc_info()
        traceback.print_exc()

        responseData['ErrorInfo'] = str(errInfo)
        cfnresponse.send(
            event,
            context,
            cfnresponse.FAILED,
            responseData
        )
