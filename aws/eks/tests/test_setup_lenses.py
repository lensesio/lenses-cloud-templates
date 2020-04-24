import yaml
import json
import sys
import os

from setup_lenses import SetupLenes
configure_lenses = SetupLenes()

class TestSetupLenses():

    # def test_create_license(self):
    #     lenses_license = {
    #         "source":"Lenses.io Ltd",
    #         "clientId":"ClinetTest",
    #         "details":"Lenses",
    #         "key":"lenses_key"
    #     }

    #     # This always fails because we do not json.dump the dict
    #     self.create_license, err = configure_lenses.CreateLensesLicense(
    #         secret=lenses_license
    #     )
    #     assert err != 0

    def test_create_manifest(self):
        brokers = "PLAINTEXT://10.164.0.9:51092"
        zookeepers =  "{url:\"10.164.0.9:51181\",jmx:\"10.164.0.9:51585\"}"
        lenses_admin_username = "admin"
        lenses_admin_password = "admin"
        kafka_metrics_opts = ["{id: 1,  url:\"http://10.164.0.9:11001/metrics\"}"]

        lenses_manifest, err = configure_lenses.CreateLensesManifest(
            brokers=brokers,
            zookeepers=zookeepers,
            username=lenses_admin_username,
            password=lenses_admin_password,
            deployment_name="eks_test_deployment",
            lenses_version="eks_lenses_version",
            kafka_metrics_opts=kafka_metrics_opts
        )
        assert err == 0

    def test_manifest_loads(self):
        lenses_deployment_manifest = "/tmp/lenses_deployment.yaml"
        with open(lenses_deployment_manifest) as file:
            manifest = yaml.full_load(file)

        assert type(manifest) is dict
