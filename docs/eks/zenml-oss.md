# Self-hosting a ZenML OSS Server on an existing EKS cluster

References:
* [docs: Deploying ZenML with Helm](https://docs.zenml.io/deploying-zenml/deploying-zenml/deploy-with-helm)
* [ZenML Helm Chart](https://artifacthub.io/packages/helm/zenml/zenml)


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

  <details>
  <summary>Example <code>~/.kube/config</code> file:</summary>

  ```yaml
  apiVersion: v1
  clusters:
    - cluster:
        certificate-authority-data: ...
        server: <docker-desktop-server-url>
      name: docker-desktop
    - cluster:
        certificate-authority-data: ...
        server: <eks-cluster-server-url>
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

  </details>
<br>

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

  <details>
  <summary>Example output:</summary>

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
  </details>
  <br>

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

    <details>
    <summary>Example <code>values.yaml</code> file:</summary>

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
          secretName: zenml-tls-certs
    ```

    </details>
    <br>

7. Deploy the ZenML Server

  ```shell
  ./run install:zenml-oss-server-aws
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

## Errors:

* The vault is sealed, so I couldn't used it. I need to learn how do people use the vault in production.

  ```shell
  kubectl -n zenml-amit logs pod/zenml-server-db-migration-fwphp --follow --all-containers

  RuntimeError: Error initializing hashicorp secrets store: Vault is sealed, on 
  post https://vault.staging.example.com/v1/auth/aws/login

  # Check the vault status
  kubectl -n hashicorp-vault exec -it vault-0 -- vault status                                                                  1 ↵
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
  ```

  See [Using HashiCorp Vault with ZenML OSS](#using-hashicorp-vault-with-zenml-oss) below for steps and the "Vault is sealed" fix.


* The certificates is not working for me as of now. I was getting the following error:

  <details>
  <summary>Example error:</summary>

  ```shell
  kubectl -n zenml-amit describe challenge <challenge-name>

  Reason: Waiting for HTTP-01 challenge propagation: failed to perform self check GET request 'http://zenml-amit.<ip>.nip.io/.well-known/acme-challenge/1tZl4C40JdxtU_04Se50sOTW5avqf5CxrD6cmC_NaTA': Get "http://zenml-amit.<ip>.nip.io/.well-known/acme-challenge/1tZl4C40JdxtU_04Se50sOTW5avqf5CxrD6cmC_NaTA": dial tcp <ip>:80: connect: connection refused


  kubectl -n zenml-amit describe cert

  Name:         zenml-tls-certs
  Namespace:    zenml-amit
  Labels:       app.kubernetes.io/instance=zenml-server
                app.kubernetes.io/managed-by=Helm
                app.kubernetes.io/name=zenml
                app.kubernetes.io/version=0.93.2
                helm.sh/chart=zenml-0.93.2
  Annotations:  <none>
  API Version:  cert-manager.io/v1
  Kind:         Certificate
  Metadata:
    Creation Timestamp:  2026-02-04T12:45:15Z
    Generation:          1
    Owner References:
      API Version:           networking.k8s.io/v1
      Block Owner Deletion:  true
      Controller:            true
      Kind:                  Ingress
      Name:                  zenml-server
      UID:                   d90d9c05-5243-4f26-8ee4-2d012be9df9b
    Resource Version:        253813479
    UID:                     fd4e10d6-7086-4e33-a524-7e7200fea86c
  Spec:
    Dns Names:
      zenml-amit.18.198.138.196.nip.io
    Issuer Ref:
      Group:      cert-manager.io
      Kind:       ClusterIssuer
      Name:       letsencrypt
    Secret Name:  zenml-tls-certs
    Usages:
      digital signature
      key encipherment
  Status:
    Conditions:
      Last Transition Time:        2026-02-04T12:45:15Z
      Message:                     Issuing certificate as Secret does not exist
      Observed Generation:         1
      Reason:                      DoesNotExist
      Status:                      True
      Type:                        Issuing
      Last Transition Time:        2026-02-04T12:45:15Z
      Message:                     Issuing certificate as Secret does not exist
      Observed Generation:         1
      Reason:                      DoesNotExist
      Status:                      False
      Type:                        Ready
    Next Private Key Secret Name:  zenml-tls-certs-h8p9x
  Events:
    Type    Reason     Age    From                                       Message
    ----    ------     ----   ----                                       -------
    Normal  Issuing    2m21s  cert-manager-certificates-trigger          Issuing certificate as Secret does not exist
    Normal  Generated  2m21s  cert-manager-certificates-key-manager      Stored new private key in temporary Secret resource "zenml-tls-certs-h8p9x"
    Normal  Requested  2m21s  cert-manager-certificates-request-manager  Created new CertificateRequest resource "zenml-tls-certs-wzlrr"


  curl -k https://zenml-amit.<ip>.nip.io
  # ^^^This was giving me error
  <html>
  <head><title>308 Permanent Redirect</title></head>
  <body>
  <center><h1>308 Permanent Redirect</h1></center>
  <hr><center>nginx</center>
  </body>
  </html>
  ```

  </details>
  <br>

  * So to clean up the certificate resources, I first disable the `tls: enabled: false` in the values file, redeployed the ZenML Server so that the certificate resources are freed up and then used the following commands to clean up the certificate resources.

  * Cleaning up:
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

---

## Using HashiCorp Vault with ZenML OSS

ZenML OSS uses the **same server configuration** for secrets stores as ZenML Pro. The [ZenML Pro docs for HashiCorp Vault](https://docs.zenml.io/pro/access-management/secrets-stores#hashicorp-vault) describe the same concepts; the difference is how you obtain and manage the server (OSS vs Pro). For a Helm-based OSS deploy, you configure Vault via the same `zenml.secretsStore` values and environment variables.

1. Make sure the Vault is unsealed and reachable.
```shell
kubectl -n hashicorp-vault exec -it vault-0 -- vault status
```

2. **IAM principal not allowed in the Vault AWS role.** While deploying the ZenML Server you may see:
```shell
kubectl -n zenml-amit logs pod/zenml-server-db-migration-<pod-suffix> --follow --all-containers

RuntimeError: Error initializing hashicorp secrets store: IAM Principal 
"arn:aws:sts::<account-id>:assumed-role/<eks-node-role-name>/i-<instance-id>" does not belong to the role "<vault-role-name>", on post https://vault.<staging-domain>.com/v1/auth/aws/login
```

**Why this happens:** ZenML uses Vault’s AWS auth method. The pod authenticates with its IAM identity (often the EKS node group role). Vault has an AWS “role” (e.g. `myapp`) that defines *which* IAM principals are allowed to log in. If the pod’s IAM principal is not in that list, Vault returns “does not belong to the role”.

3. **Fix: add your IAM principal(s) to the Vault AWS role.** Someone with a Vault token that can write to `auth/aws/role/*` must update the role so the ZenML pod’s IAM principal is allowed. You do that by calling Vault’s API to create/update the role with the correct `bound_iam_principal_arn` list.

**Why we run this:** So that when the ZenML pod (using the node group IAM role, or an IRSA role) calls `auth/aws/login`, Vault sees that principal in the role’s allowed list and issues a token with the policy that grants access to the KV mount (e.g. `kv-user-a`).

**What the command does:** It `POST`s a JSON body to `$VAULT_ADDR/v1/auth/aws/role/<vault-role-name>`, which creates or overwrites that AWS auth role. The body says: (1) which IAM principals may assume this role (`bound_iam_principal_arn`), (2) which Vault policy to attach to the issued token (`policies`), and (3) token TTL limits.

Replace placeholders:

- `$VAULT_TOKEN`, `$VAULT_ADDR`
- `<vault-role-name>` – The AWS auth role name ZenML uses (same as `VAULT_AWS_ROLE` in your env, e.g. `myapp`).
- `bound_iam_principal_arn` – List of IAM **role** ARNs allowed to assume this Vault role. Include:
  
  - The EKS node group role ARN if your ZenML pod uses the node’s IAM role (e.g. `arn:aws:iam::<account-id>:role/main-eks-node-group-...`). Get the exact ARN from the error message (`assumed-role/<name>` → IAM role ARN is `arn:aws:iam::<account-id>:role/<name>`).
  
  - Optionally, an IRSA role ARN if you use a dedicated service account role for ZenML.

- `policies` – The Vault policy name that grants access to your KV mount (e.g. `kv-user-a`). That policy should allow `create`, `read`, `update`, `delete`, `list` on `kv-user-a/*` (or your mount path).

**Example:** Add both the node group role and an IRSA role so either can be used:

```shell
curl -sS -X POST \
  -H "X-Vault-Token: $VAULT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "auth_type": "iam",
    "bound_iam_principal_arn": [
      "arn:aws:iam::<account-id>:role/<zenml-irsa-role-name>",
      "arn:aws:iam::<account-id>:role/<eks-node-group-role-name>"
    ],
    "policies": ["$VAULT_MOUNT_POINT"],
    "ttl": "1h",
    "max_ttl": "24h"
  }' \
  "$VAULT_ADDR/v1/auth/aws/role/<vault-role-name>"
```

After this, redeploy ZenML (or retry the failing migration). The pod’s IAM principal will be in the allowed list and Vault will issue a token with the given policy.


### Why "Vault is sealed" and what to do

When Vault starts (or after a restart), it is **sealed**: it holds the data but will not serve requests until it is **unsealed** with the correct number of unseal keys. This is a security feature.

- **Manual unseal:** An operator runs `vault operator unseal` (once or multiple times depending on threshold) with the unseal keys. Common in dev/staging; in production many teams prefer auto-unseal so restarts don’t require an operator.
- **Auto-unseal:** Vault is configured to use a KMS (e.g. AWS KMS) so it can unseal itself on startup. No manual unseal keys needed in the normal flow. See [HashiCorp: Auto-unseal](https://developer.hashicorp.com/vault/docs/configuration/seal#auto-unseal).

---

## Appendix: Understanding the problem from first principles

This section explains the networking and TLS concepts so you can see *why* the nip.io + cert-manager approach caused trouble and why switching to a pre-configured staging domain (e.g. `zenml-amit.staging.example.com`) fixes it.

### 1. How does traffic reach your ZenML server?

High-level path from "user's browser" to "ZenML server pod":

```
User's browser
    → DNS (resolve hostname to IP)
    → That IP is the Load Balancer (ELB) in front of ingress-nginx
    → Load Balancer forwards to ingress-nginx pods (port 80/443)
    → Ingress controller reads the Host header, finds your Ingress rule
    → Forwards to the ZenML Service (ClusterIP)
    → Service forwards to a ZenML pod
```

**Concepts:**

- **Service (ClusterIP)**  
  A stable DNS name and IP inside the cluster (e.g. `zenml-server.zenml-amit.svc.cluster.local`). Other things in the cluster (and the ingress controller) talk to your app via this Service, not directly to the pod IP (which can change).

- **Ingress**  
  An HTTP/HTTPS *routing* rule: "for this hostname and path, send traffic to this Service". It does not expose anything by itself; the **Ingress controller** (e.g. ingress-nginx) is the process that actually receives traffic from the Load Balancer and applies these rules.

- **Load Balancer (e.g. AWS ELB)**  
  The piece that gets a public IP/hostname. All traffic from the internet to your cluster hits this first, then goes to the ingress-nginx pods. So the "entry point" for the cluster is the LB; everything else is internal routing.

So: **hostname → DNS → LB → ingress-nginx → your Ingress rule → ZenML Service → ZenML pod.**

### 2. What is TLS (HTTPS) and what does cert-manager do?

- **TLS** = the "S" in HTTPS. The browser and the server encrypt traffic and the browser checks that the server holds a certificate for the domain you typed (e.g. `zenml-amit.example.com`). That certificate is issued by a **Certificate Authority (CA)**; Let's Encrypt is one such CA.

- **cert-manager** is a Kubernetes component that *obtains* certificates from CAs (like Let's Encrypt) and stores them in Kubernetes Secrets. To get a cert, the CA must verify that you control the domain. The usual method is **HTTP-01 challenge**:

  1. cert-manager asks Let's Encrypt for a cert for `zenml-amit.<ip>.nip.io`.
  2. Let's Encrypt says: "Put this token at `http://zenml-amit.<ip>.nip.io/.well-known/acme-challenge/<token>` and I'll fetch it."
  3. cert-manager creates a temporary pod/service/ingress so that when *someone* requests that URL, the response is that token.
  4. Let's Encrypt does a GET request from the internet to that URL.
  5. If it gets the token back, it issues the certificate.

For step 4 to work, the request path must be:

- **DNS**: `zenml-amit.<ip>.nip.io` must resolve to the IP of your Load Balancer (so Let's Encrypt hits your cluster).
- **Routing**: Port 80 on that IP must reach the ingress controller, and the ingress controller must route `/.well-known/acme-challenge/...` to the ACME solver pod (or the challenge fails).

If *any* of that is wrong (wrong IP, port closed, wrong host routing, firewall), the challenge fails. Your error was:

```text
failed to perform self check GET request 'http://zenml-amit.<ip>.nip.io/.well-known/acme-challenge/...': dial tcp <ip>:80: connect: connection refused
```

So from cert-manager's point of view, **port 80 on that IP was not reachable**. That can be due to:

- A different ingress controller or LB handling that hostname.
- Firewall / security group blocking port 80.
- The LB or ingress not being configured to accept HTTP for that host yet (e.g. TLS redirect or routing misconfiguration).

Debugging this on nip.io often means chasing DNS, LB, and ingress config together, which is why Stefan recommended avoiding nip.io when it doesn't work out of the box.

### 3. Why does a pre-configured staging domain (e.g. `zenml-amit.staging.example.com`) work without cert-manager?

Stefan said:

- *"This domain is already attached to the ingress controller"*  
  So the cluster's ingress (and the LB in front of it) is already set up to accept traffic for `*.staging.example.com` (or whatever staging domain your team uses). DNS for that domain already points to the right Load Balancer, and the ingress controller already has (or shares) a TLS certificate for that wildcard.

- *"You don't need to use the certificate manager anymore, get rid of the annotation"*  
  So you don't need to *request* a new certificate for your hostname. The TLS termination for the staging wildcard is already handled (e.g. a wildcard cert is already on the ingress controller or on a layer in front of it). Your Ingress only needs to say: "for host `zenml-amit.staging.example.com` (or your assigned hostname), route to the ZenML service." No `cert-manager.io/cluster-issuer` and no Certificate resource needed.

- *"You can basically use anything in the form \*.staging.example.com in this cluster"*  
  So you just pick a subdomain (e.g. `zenml-amit`) and use it. No ACME challenge, no nip.io, no cert-manager for your deploy.

**Summary:**

| Approach | DNS | TLS | Complexity |
|----------|-----|-----|------------|
| nip.io + cert-manager | You use `<namespace>.<lb-ip>.nip.io`; nip.io resolves that to the IP. | cert-manager requests a cert via HTTP-01. | High: LB, ingress, and ACME solver must all align; one misconfiguration breaks the challenge. |
| Pre-configured staging host (e.g. zenml-amit.staging.example.com) | Staging domain already points to the cluster's LB. | Wildcard (or existing) cert already on the ingress path. | Low: you only add an Ingress with the right host; no cert-manager. |

### 4. The 308 redirect you saw

You saw:

```html
<html>
<head><title>308 Permanent Redirect</title></head>
...
</html>
```

That means the ingress controller was configured to redirect HTTP → HTTPS (308 Permanent Redirect). So when you (or the ACME solver) hit `http://zenml-amit.<ip>.nip.io`, the server responded with "go to the HTTPS URL instead" instead of serving the HTTP content. Let's Encrypt's HTTP-01 challenge needs to read the token over **HTTP** on port 80; if the server only redirects to HTTPS, the challenge never sees the token and fails. So that redirect is another reason the nip.io + cert-manager path was problematic.

### 5. What to remember

- **Ingress** = routing rules (host + path → Service). **Ingress controller** = the process that does the actual routing behind the Load Balancer.
- **cert-manager** = requests certs from CAs (e.g. Let's Encrypt) via challenges (e.g. HTTP-01). It needs the domain to resolve to your cluster and port 80 to serve the challenge; redirects or wrong routing break it.
- **nip.io** is convenient for quick hostnames, but when something goes wrong, you're debugging DNS + LB + ingress + cert-manager together.
- Using a **pre-configured staging domain** (e.g. `*.staging.example.com`, or whatever your team provides) avoids all of that: DNS and TLS are already set up; you only add an Ingress with the right host and no cert-manager annotation.

### 6. What is `nip.io`?

**nip.io** is a free “magic” DNS service that turns hostnames into IP addresses using the hostname itself.

**How it works**

- Any hostname that **ends with** `.nip.io` is resolved by nip.io’s DNS servers.
- The **last part before** `.nip.io` is treated as an IP address (with dots in the hostname standing for dots in the IP).
- So these all resolve to **18.198.138.196**:
  - `18.198.138.196.nip.io`
  - `zenml-amit.18.198.138.196.nip.io`
  - `anything.you.want.18.198.138.196.nip.io`

**Why people use it**

- You don’t need to buy a domain or configure DNS.
- You get a “real-looking” hostname (e.g. for Ingress) that still points at your IP (e.g. your Load Balancer).
- Handy for dev/staging when you don’t have a proper domain.

**The `*` in `*.nip.io`**

- `*` is a wildcard: “any subdomain.”
- So `*.nip.io` means “any hostname that ends with `.nip.io`” (e.g. `foo.nip.io`, `a.b.c.1.2.3.4.nip.io`). All of those are resolved by nip.io using the same rule above.

**Why it caused trouble in your case**

- You used something like `zenml-amit.<ip>.nip.io` so the hostname contained your LB’s IP. DNS was fine (nip.io resolved it).

- The problem was elsewhere: port 80 not reachable, or HTTP→HTTPS redirect breaking the ACME challenge. So the failure wasn’t nip.io itself, but debugging became harder because you had to think about nip.io, the embedded IP, and the rest of the stack together. That’s why your teammate suggested using the existing staging domain instead.