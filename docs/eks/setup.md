# Deploying ZenML Server on an existing EKS cluster

The current state is:
* We already have an EKS cluster with a hashicorp vault, a cert-manager, and a ingress-nginx.
* We already have a RDS MySQL instance.
* We will use this to deploy the ZenML Server.

1. Setting up kubeconfig to locally access the EKS cluster

```shell
# options:
# --alias (string) Alias for the cluster context name. Defaults to match cluster ARN.
# --user-alias (string) Alias for the generated user name. Defaults to match cluster ARN.

aws eks update-kubeconfig \
    --name <cluster-name> \
    --alias eks-zenml \
    --user-alias zenml-amit \
    --profile <aws-profile-name> \
    --region <aws-region>

# Switch to the new context
kubectl config use-context eks-zenml

kubectl config get-contexts
CURRENT   NAME             CLUSTER                                                              AUTHINFO         NAMESPACE
          docker-desktop   docker-desktop                                                       docker-desktop   
*         eks-zenml        arn:aws:eks:<aws-region>:<aws-account-id>:cluster/<cluster-name>     zenml-amit 
```
^^^ This creates a context, `eks-zenml`, in your `~/.kube/config` file witha user `zenml-amit` to authenticate with the EKS cluster.

Example `~/.kube/config` file:
```yaml
apiVersion: v1
clusters:
  - cluster:
      certificate-authority-data: ...
      server: <docker-desktop-server-url>
    name: docker-desktop
  - cluster:
      certificate-authority-data: ...
      server: https://40AD81AC7F685811ECEAD0BD071D69F4.gr7.eu-central-1.eks.amazonaws.com
    name: arn:aws:eks:<aws-region>:<aws-account-id>:cluster/<cluster-name>
contexts:
  - context:
      cluster: docker-desktop
      user: docker-desktop
    name: docker-desktop
  - context:
      cluster: arn:aws:eks:<aws-region>:<aws-account-id>:cluster/<cluster-name>
      user: <user-name>
    name: eks-zenml
current-context: eks-zenml
kind: Config
users:
  - name: docker-desktop
    user:
      client-certificate-data: ...
      client-key-data: ...
  - name: <user-name>
    user:
      exec:
        apiVersion: client.authentication.k8s.io/v1beta1
        args:
          - --region
          - <aws-region>
          - eks
          - get-token
          - --cluster-name
          - <cluster-name>
          - --output
          - json
        command: aws
        env:
          - name: AWS_PROFILE
            value: <aws-profile-name>
```


2. Verify if you can access the EKS cluster

```shell
# get cluster info
kubectl cluster-info

# get all namespaces
kubectl get namespaces

# create a namespace for yourself to work in
kubectl create namespace <namespace-name>
```

3. AWS CLI commands I used to get the cluster info and RDS MySQL info

```shell
# get cluster info
aws eks describe-cluster --name <cluster-name> --region <aws-region> --profile <aws-profile-name> | cat

# get RDS MySQL info
aws rds describe-db-instances --db-instance-identifier <db-instance-identifier> --region <aws-region> --profile <aws-profile-name> | cat
```

4. Inspect the EKS cluster
```shell
kubectl get namespace    
NAME                                         STATUS   AGE
amazon-cloudwatch                            Active   442d
argocd                                       Active   533d
cert-manager                                 Active   645d
default                                      Active   645d
hashicorp-vault                              Active   130d
ingress-nginx                                Active   645d
ingress-nginx-second                         Active   375d
karpenter                                    Active   219d
kube-node-lease                              Active   645d
kube-public                                  Active   645d
kube-system                                  Active   645d
kube-workloads                               Active   442d
zenml-amit                                   Active   23h


# Inspect the Vault
╭─amit@mac ~
╰─$ kubectl -n hashicorp-vault get pod,svc
NAME                                        READY   STATUS    RESTARTS   AGE
pod/vault-0                                 0/1     Running   0          54d
pod/vault-agent-injector-<...>   1/1     Running   0          68d

NAME                               TYPE        CLUSTER-IP      EXTERNAL-IP   PORT(S)             AGE
service/vault                      ClusterIP   <...>           <none>        8200/TCP,8201/TCP   103d
service/vault-agent-injector-svc   ClusterIP   <...>           <none>        443/TCP             103d
service/vault-internal             ClusterIP   None            <none>        8200/TCP,8201/TCP   103d
service/vault-ui                   ClusterIP   <...>           <none>        8200/TCP            103d

# ^^^Vault is running on port 8200 & 8201.


# Get the Vault Info:
╭─amit@mac ~
╰─$ kubectl -n hashicorp-vault exec -it vault-0 -- vault status

Key                Value
---                -----
Seal Type          shamir
Initialized        true
Sealed             true
Total Shares       1
Threshold          1
Unseal Progress    0/1
Unseal Nonce       n/a
Version            1.20.4
Build Date         2025-09-23T13:22:38Z
Storage Type       file
HA Enabled         false
command terminated with exit code 2

# ^^^The vault is sealed, so we may not be able to use it yet.
```

* The cluster is setup with a hashicorp vault, a cert-manager, and a ingress-nginx.
  * We will use the vault for secrets management.
  * We will use the cert-manager for TLS and DNS management.
  * We will use the ingress-nginx for ingress traffic management.

5. Get the SQL credentials for MySQL Instance & Vault info from Secret Manager and put them in a `.env` file.

```shell
export AWS_SQL_USERNAME=<aws-sql-username>
export AWS_SQL_PASSWORD=<aws-sql-password>
export AWS_SQL_HOST=<aws-sql-host>
export AWS_SQL_PORT=<aws-sql-port>
export AWS_SQL_DB_NAME=<aws-sql-db-name>
export TENANT_DEFAULT_ENCRYPTION_KEY=<tenant-encryption-key>

export VAULT_ADDR=<vault-addr>
export VAULT_MOUNT_POINT=<vault-mount-point>
export VAULT_AUTH_METHOD=<vault-auth-method>
export VAULT_AWS_ROLE=<vault-aws-role>
export VAULT_AWS_HEADER_VALUE=<vault-aws-header-value>
```

Explaining the vault config:

* `VAULT_ADDR`: Where the ZenML server pod should reach Vault.

    For in-cluster access, this is usually the Kubernetes Service DNS: `http://vault.hashicorp-vault.svc.cluster.local:8200`
(Your vault ingress exists too, but in-cluster DNS is simplest and avoids hairpinning out to the ELB.)

* `VAULT_MOUNT_POINT`: This is the KV secrets engine mount inside Vault where ZenML will store secrets.

    Example values: `secret` (common default), `kv`, `zenml-secrets`

* `VAULT_AUTH_METHOD`: How ZenML will log into Vault.

    Common options you’ll see in helm charts/apps: `token` (simple but long-lived), `app_role`, `aws`

* `VAULT_AWS_ROLE`: This is a Vault role name configured under Vault’s AWS auth method. 

    This is a Vault role name configured under Vault’s AWS auth method. When ZenML logs in, it asks Vault: “log me in using AWS auth under this role name”.

* `VAULT_AWS_HEADER_VALUE`: This is almost certainly the Vault AWS auth “server ID header” value (used with the header X-Vault-AWS-IAM-Server-ID) to prevent replay attacks / ensure the login request targets the expected Vault. 
  
    In AWS auth flows, clients include this header when calling Vault’s login endpoint.

* Net: you probably do NOT need a Vault token at all if the auth_method is AWS and your pod has AWS credentials (via IRSA).


6. Creating the helm values file for the ZenML Server

   * Since our cluster already has:
      * ingress-nginx with a LoadBalancer service (public ELB hostname)
      * cert-manager (so we can do HTTPS later)

   * We just need to create an Ingress for our namespace + give it a hostname.


   * Getting the Ingress info:
       1. Get the public hostname of your nginx ingress controller LB:
            ```shell
            # Get services
            kubectl -n ingress-nginx get svc

            # Get the public hostname of the nginx ingress controller LB
            kubectl -n ingress-nginx get svc zenml-ingress-nginx-controller

            # You should see something like this: ...elb.eu-central-1.amazonaws.com
            ```
        2. Convert that to an IP (on your laptop):
            ```shell
            dig +short <hostname>
            # You should see a list of IPs, choose any one of them.
            ```
        3. Use the IP to create a hostname for your ingress in the values file:
            ```shell
            <namespace-name>.<ip>.nip.io
            # Example: zenml-amit.1.2.3.4.nip.io
            ```

    * Issuing a Certificate for HTTPS:
        1. We already have cert-manager installed, so we can use it to issue a certificate.
            ```shell
            # find the cluster issuer
            kubectl get clusterissuer

            # ^^^ You should see something like this: letsencrypt, letsencrypt-prod, letsencrypt-staging, etc.
            ```
        2. Update the values file to use the cluster issuer like shown below.

```yaml
zenml:
  database:
    # E.g.: "mysql://admin:password@zenml-mysql:3306/database"
    url: "mysql://${AWS_SQL_USERNAME}:${AWS_SQL_PASSWORD}@${AWS_SQL_HOST}:${AWS_SQL_PORT}/${AWS_SQL_DB_NAME}"

  # Secrets store settings. This is used to store centralized secrets.
  secretsStore:
    enabled: true
    type: hashicorp

    sql:
      encryptionKey: "${TENANT_DEFAULT_ENCRYPTION_KEY}"

    hashicorp:
      authMethod: aws

      authConfig:
        # The url of the HashiCorp Vault server
        vault_addr: "${VAULT_ADDR}"

        # The mount point to use (defaults to "secret" if not set)
        mount_point: "${VAULT_MOUNT_POINT}"

        # Custom mount point to use for the authentication method.
        auth_mount_point:
        aws_role: "${VAULT_AWS_ROLE}"
        aws_header_value: "${VAULT_AWS_HEADER_VALUE}"

  ingress:
    enabled: true
    className: "nginx"
    annotations:
      cert-manager.io/cluster-issuer: "letsencrypt"

    host: zenml-amit.<ip>.nip.io
    path: /
    tls:
      enabled: true
      generateCerts: false
      secretName: zenml-amit-tls-certs
```

7. Deploy the ZenML Server

```shell
./run install:zenml-server-aws
```

To check the status of the certificate:
```shell
# Watch the certificate resources being created
kubectl -n zenml-amit get certificate,order,challenge -w

kubectl -n zenml-amit get certificate
# You should eventually see Status: Ready

kubectl -n zenml-amit describe certificate zenml-amit-tls
kubectl -n zenml-amit get challenge,order

# Describe the challenge
kubectl -n zenml-amit describe challenge <challenge-name>
```

If something fails, check the logs of the pods:
```shell
kubectl -n zenml-amit get pods                                                          
NAME                              READY   STATUS    RESTARTS   AGE
cm-acme-http-solver-dlnm8         1/1     Running   0          166m
zenml-server-6944684fbc-s8j8n     1/1     Running   0          3h37m
zenml-server-db-migration-fwphp   0/1     Error     0          55m

# Check the logs of the pod
kubectl -n zenml-amit logs pod/zenml-server-db-migration-fwphp --follow --all-containers
```

**Errros:**

* The vault is sealed, so I couldn't used it. I need to learn how do people use the vault in production.
```shell
kubectl -n zenml-amit logs pod/zenml-server-db-migration-fwphp --follow --all-containers

RuntimeError: Error initializing hashicorp secrets store: Vault is sealed, on 
post https://vault.staging.cloudinfra.zenml.io/v1/auth/aws/login
```


* The certificates is not working for me as of now. I was getting the following error:
```shell
kubectl -n zenml-amit describe challenge <challenge-name>

Reason: Waiting for HTTP-01 challenge propagation: failed to perform self check GET request 'http://zenml-amit.<ip>.nip.io/.well-known/acme-challenge/1tZl4C40JdxtU_04Se50sOTW5avqf5CxrD6cmC_NaTA': Get "http://zenml-amit.<ip>.nip.io/.well-known/acme-challenge/1tZl4C40JdxtU_04Se50sOTW5avqf5CxrD6cmC_NaTA": dial tcp <ip>:80: connect: connection refused
```

  * So to clean up the certificate resources, I first disable the `tls: enabled: false` in the values file, and used the following commands to clean up the certificate resources.

Cleaning up:
```shell
# Clean up the certificate resources
kubectl -n zenml-amit delete certificate --all
kubectl -n zenml-amit delete order --all
kubectl -n zenml-amit delete challenge --all
kubectl -n zenml-amit delete pod -l acme.cert-manager.io/http01-solver=true
kubectl -n zenml-amit delete secret zenml-amit-tls-certs --ignore-not-found

# Verify if the certificate resources are cleaned up
kubectl -n zenml-amit get certificate,order,challenge,secret | egrep -i 'zenml|acme|tls'
```

* The deployment works without the TLS and you can access the ZenML Server UI via the public URL. Although the browser will shows "Not secure" which is expected.
