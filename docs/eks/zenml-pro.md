# Deploying ZenML Pro on an existing EKS cluster

The current state is:
* We already have an EKS cluster with a hashicorp vault, a cert-manager, and a ingress-nginx.
* We already have a RDS MySQL instance.
* We will use this to deploy the ZenML Pro and register our existing ZenML OSS server as a workspace.

