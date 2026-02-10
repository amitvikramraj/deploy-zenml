# Deploying ZenML Server

Deploying ZenML Server on a local K3s cluster.

> *ref: [Deploy ZenML Server using Helm](https://docs.zenml.io/deploying-zenml/deploying-zenml/deploy-with-helm)* 

1. [Single-node cluster](./docs/local/single-node-cluster.md)
2. [Multi-node cluster](./docs/local/multi-node-cluster.md)
3. [Self-hosting a ZenML OSS Server on an existing EKS cluster](./docs/eks/zenml-oss.md)
4. [Self-hosting ZenML Pro on an existing EKS cluster](./docs/eks/zenml-pro.md)

To follow the guide, make sure you have the environment variables set in as per the [.env.example](.env.example) file.

## Setup

1. Install kubectl, heml

```shell
brew install kubectl, helm
```

2. Install [k3d](https://www.perdian.de/articles/running-kubernetes-locally-on-a-mac-with-k3d/) - a wrapper around [k3s](https://docs.k3s.io/quick-start) that runs a local Kubernetes cluster in docker.

```shell
brew install k3d
```

3. Install `envsubst` for environment variable substitution in the helm values file

```shell
# ref: https://github.com/criteo/kerberos-docker/issues/6
# ref: https://github.com/a8m/envsubst
brew install gettext
brew link --force gettext
```
