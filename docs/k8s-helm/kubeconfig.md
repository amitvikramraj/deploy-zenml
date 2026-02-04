A `kubeconfig` file is a YAML file used to organize information about Kubernetes clusters, users, namespaces, and authentication mechanisms. It is used by `kubectl` and other client tools to know how to communicate with the API server.

The default location is `~/.kube/config` (Linux/macOS) or `%USERPROFILE%\.kube\config` (Windows).

Structure of a Kubeconfig File

The file is organized into four main sections, plus metadata:

1. **Clusters**: API server endpoints and CA certificates.
2. **Users**: Credentials for authentication.
3. **Contexts**: Binds a user and cluster together with an optional namespace.
4. **Current-context**: Specifies which context is currently active.

---

Detailed Field Explanation

1. Top-Level Metadata

- `apiVersion`: Defines the version of the kubeconfig file format (e.g., `v1`).
- `kind`: Always `Config`.
- `current-context`: The name of the context that `kubectl` will use by default.

2. Clusters (`clusters:`)

This section defines the API server endpoint and the CA certificate to verify the server's identity.

- `name`: A unique, user-defined name for this cluster (e.g., `prod-cluster`).
- `cluster.server`: The URL of the Kubernetes API server (e.g., `https://10.0.0.1:6443`).
- `cluster.certificate-authority`: Path to the CA certificate file.
- `cluster.certificate-authority-data`: The Base64-encoded CA certificate data, used to embed the certificate directly instead of referencing a file.
- `cluster.insecure-skip-tls-verify`: (Optional) If set to `true`, ignores SSL certificate validation. Not recommended for production.

3. Users (`users:`)

This section defines the credentials used to authenticate against the cluster.

- `name`: A unique name for this user (e.g., `admin-user`).
- `user.client-certificate` / `client-key`: Paths to the client certificate and private key files for Mutual TLS (mTLS).
- `user.client-certificate-data` / `client-key-data`: Base64-encoded client certificate/key data.
- `user.token`: A bearer token for authentication.
- `user.username` / `password`: Basic authentication credentials.
- `user.exec`: Allows using an external command to fetch credentials (e.g., for AWS IAM, OIDC).

4. Contexts (`contexts:`)

A context defines a binding between a user and a cluster, making it easy to switch between environments (e.g., Dev, Prod).

- `name`: A unique, user-defined name for this context (e.g., `my-context`).
- `context.cluster`: The name of the cluster defined in the `clusters` section.
- `context.user`: The name of the user defined in the `users` section.
- `context.namespace`: (Optional) The default namespace to use when running `kubectl` commands.

---

Useful `kubectl` Commands

- **View current config**: `kubectl config view`
- **Switch context**: `kubectl config use-context <context-name>`
- **List all contexts**: `kubectl config get-contexts`
- **Set current namespace**: `kubectl config set-context --current --namespace=<namespace>`

Precedence Rules

If you have multiple kubeconfig files, or use the `KUBECONFIG` environment variable, `kubectl` merges them based on these rules:

1. `-kubeconfig` flag (highest precedence).
2. `KUBECONFIG` environment variable (list of paths).
3. `~/.kube/config` (default file).