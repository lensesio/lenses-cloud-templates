# Deployment of Lenses in Container Optimized OS

This is a
[Google Cloud Deployment Manager](https://cloud.google.com/deployment-manager/overview)
template that deploys Lenses in a Container Optimized OS VM.

## Deploy the template

Use `config.yaml` to deploy Lenses template. This template uses
Container Optimized OS VM and creates by itslef the necessary Firewall configuration.

When ready, deploy with the following command:

```shell
gcloud deployment-manager deployments create lenses --config config.yaml
```