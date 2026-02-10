# Self-hosting ZenML Pro on an existing EKS cluster

References:

* [ZenML Pro self-hosted deployment Guide](https://docs.zenml.io/pro/deployments/scenarios/self-hosted-deployment/self-hosted-deployment-helm)
* [zenml-pro helm values](https://artifacthub.io/packages/helm/zenml-pro/zenml-pro)
* [zenml helm values](https://artifacthub.io/packages/helm/zenml/zenml)


The current state is:
* We already have an EKS cluster with a hashicorp vault, a cert-manager, and a ingress-nginx.
* We already have a RDS MySQL instance and a RDS Postgres instance.
* We will use this to deploy the ZenML Pro workspace and register our existing ZenML OSS server as a workspace.

ZenML Pro needs a control plane and a workspace.
* The control plane is a seperate entity which manages the workspaces and users.
* For the workspace, we will use the existing ZenML OSS server.
* The Pro control plane needs a seperate database – it can be either a Postgre or a MySQL database.


My helm values are at [./heml/zenml-pro/](../../helm/zenml-pro/)


1. Use the [`helm/zenml-pro`](https://artifacthub.io/packages/helm/zenml-pro/zenml-pro) values file.
    * We will configure database, authentication and ingress.
    * Make sure the database exists, I had to manually create the database in the RDS instance.
    * I went to AWS RDS console, opened the web terminal and created the database.
        ```shell
        # To list the databases
        \l # or `\list`

        # To create a database
        CREATE DATABASE zenmlpro_amit;
        ```

2. Once the helm values are configured, we can deploy the ZenML Pro control plane.

    ```shell
    ./run install:zenml-pro-control-plane-aws

    # You will get an output like this:

    You may access the ZenML Pro server at: https://zenml-pro.my.domain

    Use the following credentials:
    Username: admin
    Password: fetch the password by running:
    kubectl get secret --namespace zenml-pro zenml-pro -o jsonpath="{.data.ZENML_CLOUD_ADMIN_PASSWORD}" | base64 --decode; echo
    ```

3. Once the control plane is deployed, we need to create a super-user account.

    * You can access the all the Swagger API docs at: https://zenml-pro.my.domain/api/v1/docs

    * Creating a super-user account
    ```shell
    # Fetch a bearer token using admin credentials
    curl -X POST https://zenml-pro.my.domain/api/v1/auth/login \
        -H "Content-Type: application/x-www-form-urlencoded" \
        -d "username=admin&password=<admin-password>"
    ```

    > **NOTE:** The ZenML Pro admin user should only be used for the initial onboarding and emergency administrative operations related to super-user account management: creating the first super-user account and granting super-user privileges to other users when needed. Use a regular user account for all other operations.

    * Creating a regular user account
    ```shell
    # Create a new regular user account
    curl -X 'POST' 'https://zenml-pro.my.domain/api/v1/users?password=<user-password>&username=<username>&is_superuser=false' \
        -H 'accept: application/json' \
        -d ''
    ```

    > **NOTE:** Creating and managing local user accounts is currently only supported through the ZenML Pro OpenAPI interface or programmatically accessing the ZenML Pro API. There is no support for this in the ZenML Pro UI yet.

4. Once the control plane is deployed, we need to configure the helm values for the existing OSS server and register it as a workspace.

    * We first need to first enroll the existing OSS server as a workspace.

    ```shell
    # Create a new super-user account
    curl -X POST "https://zenml-pro.my.domain/api/v1/users?username=superuser&password=password&is_superuser=true" \
        -H "Authorization: Bearer <access-token>"

    # Using the super-user account, enroll the existing OSS server as a workspace.
    curl -X POST "https://zenml-pro.my.domain/api/v1/workspaces?name=<your-oss-server-name>&enroll=true" \
        -H "Authorization: Bearer <access-token>"
    ```

    * The workspace enrollment response will contain all the necessary enrollment credentials for the workspace that you will need to configure the workspace server during deployment: `the workspace ID, the enrollment key, the organization ID, the organization name, and the workspace name`.
    
    * We will use these values to update the helm values for the existing OSS server and register it as a workspace.

        ```yaml
        zenml:
            pro:
                apiURL: https://zenml-pro-amit.18.197.18.197.nip.io/api/v1
                dashboardURL: https://zenml-pro-amit.18.197.18.197.nip.io
                enabled: true
                enrollmentKey: c0q7KRx0sqkeZ_DkcNyVo3z8brLzZSRx2H04G4E3BEJ_ZQxwVV34rnLRgawk-76AOmKRwRU8MNslh0taCK_y9w
                organizationID: 3c300b3c-b062-4109-8cbc-037b3f204850
                organizationName: zenml-amit
                workspaceID: 251ab625-fc96-4ebc-9535-f8cd01da036b
                workspaceName: zenml-pro-amit-workspace
            
            serverURL: https://zenml-amit.18.197.18.197.nip.io
            # ^^^Make sure to add the server URL of the existing OSS server. If it is added the control plane will be able to access the existing OSS server.
        ```

    * We can now deploy the existing OSS server as a workspace.

    ```shell
    ./run install:zenml-pro-workspace-aws
    ```

