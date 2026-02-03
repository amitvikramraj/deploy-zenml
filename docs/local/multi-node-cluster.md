# Deploying OSS ZenML Server locally on a multi-node cluster

Trying to deploy a local ZenML server on a local K3s cluster with a MySQL Database and a HashiCorp Vault for secrets management.

- We will be using a MySQL Database and a HashiCorp Vault for secrets management.
- ^^^And accordingly we will be setting the helm values for the ZenML Server.

1. Install kubectl, heml, k3d

2. Create a multi-node cluster

```shell
k3d cluster create zenml-multi --servers 1 --agents 2 --api-port 6550
```

```shell
╭─amit@mac ~/repos/zenml/zenml-local ‹main●› 
╰─$ kubectl get nodes -o wide                              
NAME                       STATUS   ROLES                  AGE   VERSION        INTERNAL-IP   EXTERNAL-IP   OS-IMAGE           KERNEL-VERSION     CONTAINER-RUNTIME
k3d-zenml-multi-agent-0    Ready    <none>                 21h   v1.33.6+k3s1   172.18.0.4    <none>        K3s v1.33.6+k3s1   6.12.65-linuxkit   containerd://2.1.5-k3s1.33
k3d-zenml-multi-agent-1    Ready    <none>                 21h   v1.33.6+k3s1   172.18.0.5    <none>        K3s v1.33.6+k3s1   6.12.65-linuxkit   containerd://2.1.5-k3s1.33
k3d-zenml-multi-server-0   Ready    control-plane,master   21h   v1.33.6+k3s1   172.18.0.3    <none>        K3s v1.33.6+k3s1   6.12.65-linuxkit   containerd://2.1.5-k3s1.33
```

3. Install MySQL and HashiCorp Vault

```shell
./run install:mysql

# ref: https://developer.hashicorp.com/vault/docs/deploy/kubernetes/helm/run
./run install:vault

# get the Valult token from the logs
kubectl logs zenml-vault-0 -n zenml-vault | head -n 100

# Should look something like this:
> Root Token: root

# And the Vault address should be: http://host.docker.internal:8200
```

4. Install ZenML Server

```shell
# Install `envsubst` for environment variable substitution in the helm values file

# ref: https://github.com/criteo/kerberos-docker/issues/6
# ref: https://github.com/a8m/envsubst
brew install gettext
brew link --force gettext 

# Install ZenML Server
# Edit the helm/values-local.yaml file to set the correct values for the MySQL and HashiCorp Vault
# - MYSQL_USER
# - MYSQL_PASSWORD
# - MYSQL_DATABASE
# - MYSQL_ENCRYPTION_KEY
# - VAULT_ADDR
# - VAULT_TOKEN

./run install:zenml-server

# port forward the ZenML Server service to the local machine
kubectl --namespace zenml port-forward svc/zenml-server 8080:80

# Go to http://localhost:8080 to access the ZenML Server
```

5. Verify if the pods are running

```shell
╭─amit@mac ~/repos/zenml/zenml-local ‹main●› 
╰─$ kubectl get pods --all-namespaces                              
NAMESPACE     NAME                                          READY   STATUS      RESTARTS   AGE
kube-system   coredns-6d668d687-6qb7w                       1/1     Running     0          21h
kube-system   helm-install-traefik-crd-lcjqx                0/1     Completed   0          21h
kube-system   helm-install-traefik-h2zf8                    0/1     Completed   1          21h
kube-system   local-path-provisioner-869c44bfbd-rcgkf       1/1     Running     0          21h
kube-system   metrics-server-7bfffcd44-tdpjs                1/1     Running     0          21h
kube-system   svclb-traefik-09479c96-844ww                  2/2     Running     0          21h
kube-system   svclb-traefik-09479c96-j9x5h                  2/2     Running     0          21h
kube-system   svclb-traefik-09479c96-rzq66                  2/2     Running     0          21h
kube-system   traefik-865bd56545-xz2nk                      1/1     Running     0          21h
zenml-db      mysql-0                                       1/1     Running     0          18h
zenml-vault   zenml-vault-0                                 1/1     Running     0          21h
zenml-vault   zenml-vault-agent-injector-6d9d799b95-26p9w   1/1     Running     0          21h
zenml         zenml-server-d99cb657b-wcnqb                  1/1     Running     0          18h
zenml         zenml-server-db-migration-zzhf4               0/1     Completed   0          18h
```

6. Login to the ZenML Server

```shell
# install deps
uv sync

# login
uv run zenml login http://localhost:8080

# Run a pipeline
uv run main.py

# Deploy a pipeline
uv run zenml pipeline deploy main.hello_world_pipeline

# trigger the deployment
uv run zenml deployment invoke hello-world

# update the deployment
uv run zenml pipeline deploy main.hello_world_pipeline --update
```

7. Cleanup

```shell
# Uninstall the ZenML Server
helm uninstall zenml-server --namespace zenml

# Uninstall the MySQL
helm uninstall mysql --namespace zenml-db

# Uninstall the HashiCorp Vault
helm uninstall zenml-vault --namespace zenml-vault

# Delete the namespaces
kubectl delete namespace zenml zenml-db zenml-vault

# Delete the k3d cluster
k3d cluster delete zenml-multi
```