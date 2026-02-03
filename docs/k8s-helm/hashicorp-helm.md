When installing a HashiCorp Helm chart (such as for Vault or Consul), configuration options are primarily managed through the `helm install` or `helm upgrade` commands, using **inline values overrides** with the `--set` flag or by providing a **YAML values file** with the `-f` flag.

**Common Installation Options and Flags**

The `helm install` command accepts numerous standard Helm flags that control the installation process:

- **`[release-name]`**: A custom name for your Helm release (e.g., `vault`).
- **`[repo/chart]`**: The name of the repository and chart (e.g., `hashicorp/vault`).
- **`-namespace` (or `n`)**: Specifies the Kubernetes namespace to install the release into. The `-create-namespace` flag can be used to create the namespace if it doesn't exist.
- **`-version`**: Pins the installation to a specific chart version.
- **`f` (or `-values`)**: Specifies a local YAML file containing configuration overrides.
- **`-set`**: Overrides individual values directly on the command line (e.g., `-set "server.ha.enabled=true"`).
- **`-dry-run`**: Runs the template rendering locally without installing any resources into the Kubernetes cluster, useful for verification.
- **`-wait`**: The Helm client will wait until all the resources are in a ready state before marking the release as successful (default: `true`).
- **`-devel`**: Allows the use of development versions of charts when also using the `-version` flag.
- **`-skip-crds`**: Skips the installation of Custom Resource Definitions (CRDs) if they are already managed separately.

**HashiCorp Chart-Specific Configuration**

HashiCorp Helm charts offer specific configuration options exposed in their respective `values.yaml` files, which can be modified using the options above. You can view all available settings using `helm inspect values <repo/chart>`.

**Vault Helm Chart Options**

Key configuration options for the HashiCorp Vault Helm chart include:

- **Deployment Mode**:
    - `server.dev.enabled=true`: Runs a single Vault server in development mode with in-memory storage (not for production).
    - Default (Standalone): A single server with file storage (not production ready).
    - `server.ha.enabled=true`: Enables High Availability mode, typically using Integrated Storage (Raft) or Consul for a storage backend.
    - `global.externalVaultAddr`: Allows running the agent injector/CSI provider without deploying a Vault server within the cluster.
- **Integrations**:
    - `injector.enabled=true`: Enables the Vault Agent Injector, a mutating admission webhook.
    - `csi.enabled=true`: Enables the Vault Secrets Store CSI provider.
- **Security & Storage**:
    - `server.dataStorage.enabled=true`: Enables Persistent Volume Claims (PVCs) for data storage (recommended).
    - `server.image.tag`: Pins the Docker image to a specific version.
    - `server.extraEnvironmentVars` or `server.extraSecretEnvironmentVars`: Used to pass necessary credentials for features like Auto-unseal with a cloud KMS (AWS KMS, GCP KMS, etc.).
- **UI and Telemetry**:
    - `ui.enabled=true`: Exposes the Vault web interface.
    - `telemetry`: Configures metrics forwarding (e.g., to StatsD).

**Consul Helm Chart Options**

The HashiCorp Consul Helm chart also provides extensive configuration, with common options including:

- `global.name`: The name for the Consul cluster.
- `global.openshift=true`: Enables OpenShift-specific configurations.
- Security settings: By default, security is disabled for ease of use; specific values must be set to enable security features for production.

For detailed, chart-specific options and examples, refer to the official HashiCorp documentation for the [**Vault Helm Chart configuration**](https://developer.hashicorp.com/vault/docs/deploy/kubernetes/helm/configuration) and the [**Consul Helm Chart Reference**](https://developer.hashicorp.com/consul/docs/reference/k8s/helm).