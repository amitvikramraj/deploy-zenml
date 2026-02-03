Basic Helm commands can be divided into categories for **repository management, release management (installing/upgrading/uninstalling charts), and chart development**.

**Repository Management**

- **`helm repo add [NAME] [URL]`**: Adds a chart repository to your Helm configuration.
    - *Example:* `helm repo add bitnami https://charts.bitnami.com/bitnami`
- **`helm repo list`**: Lists all the chart repositories added to your configuration.
- **`helm repo update`**: Updates the local cache of chart information from all added repositories.
- **`helm search repo [KEYWORD]`**: Searches the locally added repositories for charts matching a keyword.

**Release Management**

- **`helm install [RELEASE_NAME] [CHART]`**: Installs a chart in the Kubernetes cluster, creating a new release.
    - *Example:* `helm install my-release bitnami/nginx`
- **`helm list`** (or `helm ls`): Lists all installed releases in the current namespace.
- **`helm upgrade [RELEASE_NAME] [CHART]`**: Upgrades an existing release to a new version of a chart or with new configuration values.
    - *Example:* `helm upgrade my-release bitnami/nginx --set image.tag=1.21.0`
- **`helm uninstall [RELEASE_NAME]`** (or `helm delete`): Uninstalls a release, deleting all associated Kubernetes resources.
- **`helm rollback [RELEASE_NAME] [REVISION]`**: Rolls back a release to a previous revision number from its history.
- **`helm status [RELEASE_NAME]`**: Displays the status of a specific release, including the resources created and any notes.
- **`helm history [RELEASE_NAME]`**: Views the release history, including revision numbers and statuses.

**Chart Development and Inspection**

- **`helm create [NAME]`**: Creates a new chart directory with a basic, standard structure.
- **`helm lint [CHART_PATH]`**: Examines a chart for possible issues and validates its syntax and configuration.
- **`helm package [CHART_PATH]`**: Packages a chart directory into a compressed `.tgz` archive file for distribution or installation.
- **`helm template [NAME] [CHART]`**: Locally renders the chart's templates into Kubernetes YAML manifests without installing it on a cluster. This is useful for debugging and inspection.
- **`helm show values [CHART]`**: Displays the default `values.yaml` file from a chart, showing which options are configurable.
- **`helm get manifest [RELEASE_NAME]`**: Downloads the manifest (all the generated YAML files) for a named release from the cluster.

For more detailed information and a complete list of commands, refer to the [**official Helm documentation**](https://helm.sh/docs/helm/).