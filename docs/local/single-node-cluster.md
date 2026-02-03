# Deploying ZenML locally on a local K3s cluster

Trying to deploy a local ZenML server on a single-node K3s cluster.

- We will not using an external database or a secrets manager for this example.
- The default SQLite database will be used for the ZenML server.
- All the helm values are set to the default values for the ZenML Server.


1. Create a k3d cluster
```shell
# Create a k3s cluster 
k3d cluster create zenml-local --api-port 6550

# Verify if the cluster is created
╭─amit@mac ~/repos/zenml/zenml-local ‹main●› 
╰─$ k3d cluster list
NAME          SERVERS   AGENTS   LOADBALANCER
zenml-local   1/1       0/0      true

# Verify if the cluster is running
╭─amit@mac ~/repos/zenml/zenml-local ‹main●› 
╰─$ kubectl cluster-info             
Kubernetes control plane is running at https://0.0.0.0:6550
CoreDNS is running at https://0.0.0.0:6550/api/v1/namespaces/kube-system/services/kube-dns:dns/proxy
Metrics-server is running at https://0.0.0.0:6550/api/v1/namespaces/kube-system/services/https:metrics-server:https/proxy

To further debug and diagnose cluster problems, use 'kubectl cluster-info dump'.
```

4. Install ZenML Server with Helm onto the local K3s cluster
```shell
# Pull the ZenML Server chart
mkdir helm
cd helm
helm pull oci://public.ecr.aws/zenml/zenml --untar

# Make a local copy of the values file and edit it to your needs
cp zenml/values.yaml values-local.yaml
# ^^^ We are using all the default values for the ZenML Server

# Create a namespace for the ZenML Server
╭─amit@mac ~/repos/zenml/zenml-local ‹main●› 
╰─$ kubectl create namespace zenml                                                                                                  1 ↵
namespace/zenml created

╭─amit@mac ~/repos/zenml/zenml-local ‹main●› 
╰─$ kubectl get namespace zenml      
NAME    STATUS   AGE
zenml   Active   75s

# Install the ZenML Server
╭─amit@mac ~/repos/zenml/zenml-local/helm ‹main●› 
╰─$ helm install zenml-server ./zenml --namespace zenml --values values-local.yaml
NAME: zenml-server
LAST DEPLOYED: Fri Jan 30 16:36:38 2026
NAMESPACE: zenml
STATUS: deployed
REVISION: 1
DESCRIPTION: Install complete
NOTES:

# Verify if pods are running
╭─amit@mac ~/repos/zenml/zenml-local/helm ‹main●› 
╰─$ kubectl --namespace zenml get pods
NAME                            READY   STATUS    RESTARTS   AGE
zenml-server-79754b84d8-l9w27   1/1     Running   0          164m

╭─amit@mac ~/repos/zenml/zenml-local ‹main●› 
╰─$ kubectl get pods --all-namespaces
NAMESPACE     NAME                                      READY   STATUS      RESTARTS   AGE
kube-system   coredns-6d668d687-l7g4r                   1/1     Running     0          3h29m
kube-system   helm-install-traefik-crd-ckth8            0/1     Completed   0          3h29m
kube-system   helm-install-traefik-zl5rr                0/1     Completed   1          3h29m
kube-system   local-path-provisioner-869c44bfbd-jlcd2   1/1     Running     0          3h29m
kube-system   metrics-server-7bfffcd44-qw9bw            1/1     Running     0          3h29m
kube-system   svclb-traefik-a93cbce9-vzdfl              2/2     Running     0          3h28m
kube-system   traefik-865bd56545-5zx4l                  1/1     Running     0          3h28m
zenml         zenml-server-79754b84d8-l9w27             1/1     Running     0          3h16m
```

5. Port forward the ZenML Server service to the local machine
```shell
╭─amit@mac ~/repos/zenml/zenml-local/helm ‹main●› 
╰─$ kubectl -n zenml get svc

NAME           TYPE        CLUSTER-IP     EXTERNAL-IP   PORT(S)   AGE
zenml-server   ClusterIP   10.43.42.222   <none>        80/TCP    159m

╭─amit@mac ~/repos/zenml/zenml-local/helm ‹main●› 
╰─$ kubectl -n zenml port-forward svc/zenml-server 8080:80  

# Go to http://localhost:8080 to access the ZenML Server
```

6. Login to the ZenML Server
```shell
# Install the dependencies
uv sync

# Login to the ZenML Server
╭─amit@mac ~/repos/zenml/zenml-local ‹main●› 
╰─$ zenml login http://localhost:8080
Initializing the ZenML global configuration version to 0.93.2
Authenticating to ZenML server 'http://localhost:8080' using the web login...

If your browser did not open automatically, please open the following URL into your browser to proceed with the authentication:
http://localhost:8080/devices/verify?device_id=9b7d71ff-bad7-4621-b84b-7e56be1e5af6&user_code=5f0717e5cba8c53742c72d8686547bfd

✔ Successfully logged in to http://localhost:8080.
Setting the global active project to 'default'.
Setting the global active stack to default.
Updated the global store configuration.
```

8. Run the pipeline
   ```shell
   uv run main.py
   ```

9. Cleanup
```shell
# Uninstall the ZenML Server
╭─amit@mac ~/repos/zenml/zenml-local ‹main●› 
╰─$ helm uninstall zenml-server --namespace zenml
release "zenml-server" uninstalled

# Delete the namespace
╭─amit@mac ~/repos/zenml/zenml-local ‹main› 
╰─$ kubectl delete namespace zenml
namespace "zenml" deleted

# Delete the k3d cluster
╭─amit@mac ~/repos/zenml/zenml-local ‹main› 
╰─$ k3d cluster delete zenml-local
INFO[0000] Deleting cluster 'zenml-local'               
INFO[0001] Deleting cluster network 'k3d-zenml-local'   
INFO[0001] Deleting 1 attached volumes...               
INFO[0001] Removing cluster details from default kubeconfig... 
INFO[0001] Removing standalone kubeconfig file (if there is one)... 
INFO[0001] Successfully deleted cluster zenml-local!  
```