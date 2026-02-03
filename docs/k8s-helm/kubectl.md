`kubectl` is the command-line interface for managing Kubernetes clusters. Basic `kubectl` commands allow you to **inspect cluster resources, deploy applications, and view logs**.

Inspecting Resources

These commands are used to view the status and details of various resources in your cluster.

- **`kubectl get`**: List one or more resources.
    - `kubectl get pods`: List all pods in the current namespace.
    - `kubectl get services`: List all services.
    - `kubectl get nodes`: List all nodes.
    - `kubectl get all`: List most common resources (pods, services, deployments, etc.) in the current namespace.
    - `kubectl get pods -n kube-system`: List pods in a specific namespace (e.g., `kube-system`).
    - `kubectl get pods -o wide`: Show pods with additional information like node assignment and IP addresses.
- **`kubectl describe`**: Display detailed state and events of a specific resource.
    - `kubectl describe pod <pod-name>`: Show detailed information about a pod.
    - `kubectl describe service <service-name>`: Show detailed information about a service.
- **`kubectl cluster-info`**: Display endpoint information about the control plane and services in the cluster.
- **`kubectl explain`**: Get documentation and structure of a specific resource type.
    - `kubectl explain pod`: View the documentation for the pod resource type.

Deploying and Managing Applications

These commands help you create, update, and manage applications within the cluster.

- **`kubectl apply -f`**: Apply a configuration change to a resource from a file (YAML or JSON). This is the recommended declarative way to manage resources.
    - `kubectl apply -f app.yaml`: Create or update resources defined in `app.yaml`.
- **`kubectl create`**: Create a resource from a file or from the command line.
    - `kubectl create deployment nginx --image=nginx`: Create an NGINX deployment.
    - `kubectl create service nodeport nginx --tcp=80:80`: Create a NodePort service.
- **`kubectl delete`**: Delete resources.
    - `kubectl delete pod <pod-name>`: Delete a specific pod.
    - `kubectl delete -f app.yaml`: Delete resources defined in `app.yaml`.
- **`kubectl scale`**: Change the number of replicas for a scalable resource (Deployment, ReplicaSet, etc.).
    - `kubectl scale deployment nginx --replicas=3`: Scale the `nginx` deployment to 3 replicas.
- **`kubectl edit`**: Edit a live resource definition using your default editor.
    - `kubectl edit service <service-name>`: Open an editor to modify the service definition.

Debugging and Troubleshooting

These commands are crucial for monitoring and debugging issues with your applications.

- **`kubectl logs`**: Print the logs for a container in a pod.
    - `kubectl logs <pod-name>`: View logs for a pod.
    - `kubectl logs -f <pod-name>`: Stream (follow) the logs.
    - `kubectl logs -c <container-name> <pod-name>`: View logs from a specific container within a multi-container pod.
    - `kubectl logs --previous <pod-name>`: View logs from a previous instance of a crashed container.
- **`kubectl exec`**: Execute a command inside a container.
    - `kubectl exec -it <pod-name> -- /bin/bash`: Get an interactive shell session inside a container.
- **`kubectl port-forward`**: Forward one or more local ports to a pod.
    - `kubectl port-forward pod/<pod-name> 8080:80`: Forward local port 8080 to port 80 in the pod.
- **`kubectl top`**: Display resource (CPU/Memory) usage of nodes or pods (requires the Metrics Server to be running in the cluster).
    - `kubectl top pods`: Show pod CPU/memory usage.