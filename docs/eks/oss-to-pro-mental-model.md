# Extending ZenML OSS to ZenML Pro: Mental Model

This guide explains the **conceptual model** of extending your existing ZenML OSS deployment on EKS to a full self-hosted ZenML Pro instance. It is written so you can reason about what to do and then follow the official Helm docs and values on your own. No step-by-step commands or copy-paste answers—just the mental map.

---

## 1. OSS vs Pro: What Actually Changes

From your [README](../README.md):

- **OSS** = one server (API + dashboard in one), one metadata DB (MySQL), optional secrets store (e.g. Vault). Single-tenant: everyone shares one logical workspace.
- **Pro** = **Control Plane** (API + Dashboard + its own DB) + **Workspace servers** (one or more). Each workspace is conceptually “OSS plus Pro add-ons”: same kind of workload (pipelines, runs, stacks, secrets) but enrolled with the control plane for users, RBAC, and Pro features.

So extending OSS → Pro is **not** “upgrading the existing server in place.” It is **adding a Control Plane** and then **turning your current OSS server into the first Pro workspace** (or deploying a new workspace and retiring the old one). Two deployments, two Helm charts, two URLs—then wired together.

---

## 2. The Two Pieces of Pro

### 2.1 Control Plane (new)

- **What it is:** The “brain” of Pro. Handles login, organizations, workspaces, users, RBAC, and the Pro dashboard. It does **not** run your pipelines or store pipeline/run metadata; it only knows *which* workspaces exist and *who* can use them.
- **Helm chart:** `zenml-pro` (different from the OSS `zenml` chart). Example: `oci://public.ecr.aws/zenml/zenml-pro`.
- **Where it runs:** New namespace (e.g. `zenml-pro`) on the same EKS cluster.
- **Database:** Its **own** database (PostgreSQL or MySQL). This holds Pro metadata (users, orgs, workspaces, roles). Your existing RDS can host it, but you need a **separate** database (e.g. `zenml_pro`). Not the same DB as your current OSS server.
- **Images:** `zenml-pro-api`, `zenml-pro-dashboard` (from ZenML’s ECR/GAR; see [self-hosted Helm doc](https://docs.zenml.io/pro/deployments/scenarios/self-hosted-deployment/self-hosted-deployment-helm)).
- **URL:** One external URL (e.g. `https://zenml-pro.<your-domain>`). Dashboard and API live under that host (e.g. API at `.../api/v1`). This is the URL users use to **log in** and open the Pro UI.

So in your mental model: **first new thing** = deploy the Control Plane (new chart, new namespace, new DB, new hostname).

### 2.2 Workspace server(s) (your current OSS, reconfigured)

- **What it is:** The server that actually runs pipelines, stores run/artifact metadata, and talks to your stacks (Vault, MySQL, etc.). In Pro, this is still the “OSS-style” server, but with Pro **enrollment**: it trusts the Control Plane for auth and gets org/workspace identity.
- **Helm chart:** Still the **zenml** (OSS) chart. There is no separate “workspace-only” chart. You use the same chart you used for OSS, with different image and a `pro` config block.
- **Image:** Switch from `zenmldocker/zenml-server` to the **workspace** image: `zenml-pro-server` (from ZenML’s ECR/GAR). Same chart, different image + Pro config = workspace server.
- **Database:** Each workspace has its **own** MySQL (PostgreSQL not supported for workspaces). Your **current** OSS MySQL can *be* that first workspace’s DB: same URL, same RDS, possibly same database name or a dedicated one (e.g. `zenml_workspace`). So you don’t necessarily need a second RDS instance—you need a second *database* (control plane DB) and can keep using your existing DB for the workspace.
- **Secrets store:** Unchanged. Your existing Vault (AWS auth, mount point, etc.) stays; the workspace server keeps using it.
- **URL:** The URL where this server is reachable (e.g. `https://zenml-workspace.<your-domain>` or the same host you use today). Clients and the Control Plane talk to this URL for pipeline/run/stack operations.

So in your mental model: **second piece** = your existing OSS deployment, redeployed with the **zenml** chart using `zenml-pro-server` image + Pro enrollment settings (see below). Same cluster, same ingress pattern, same DB and Vault—different image and config.

---

## 3. How They Connect

- **Enrollment:** Before a workspace can act as “Pro,” it must be **enrolled** with the Control Plane. You do that in the Pro dashboard (or via enrollment script): create an organization, create a workspace, get an **enrollment key** plus org/workspace IDs.
- **In the workspace Helm values** you add a `pro` block: control plane API URL, dashboard URL, enrollment key, organization ID/name, workspace ID/name. The workspace server uses these to register and then to validate tokens and permissions with the Control Plane.
- **User flow:** User logs in at the **Control Plane** URL (e.g. `zenml login --pro-api-url https://zenml-pro.../api/v1`). The client gets a token from the Control Plane and then talks to the **workspace** URL for pipeline/run/stack operations. So: one login (Control Plane), two URLs (control plane + workspace) in the picture.

---

## 4. Mapping Your Current Setup to This Model

From your [EKS setup](setup.md) and [values-aws.yaml](../../helm/values-aws.yaml):

- You have: EKS, ingress (e.g. nginx-second), cert-manager, RDS MySQL, HashiCorp Vault (AWS auth), one ZenML OSS deployment (zenml chart, `zenmldocker/zenml-server`, one DB URL, one hostname).

**Control Plane (new):**

- New Helm release: `zenml-pro` in a new namespace (e.g. `zenml-pro`).
- New DB: e.g. a new database on the same RDS instance (or a new instance) for control plane metadata. Values use something like `zenml.database.external` with type `postgres` or `mysql`, host, user, password, database name.
- New hostname: e.g. `zenml-pro.<same-nip-or-domain>` and an Ingress for it (same ingress class, cert-manager if you use it).
- Images: ZenML Pro API and dashboard images (ECR/GAR); if you use a private registry, set `imagePullSecrets` and repository paths in values.

**Workspace (current OSS, reconfigured):**

- Same Helm release name/namespace as today (e.g. `zenml-amit`) **or** a new namespace if you prefer (e.g. `zenml-workspace`). Same **zenml** chart.
- Image: change from `zenmldocker/zenml-server` to `zenml-pro-server` (and repository if using internal registry).
- Database: keep your current `database.url` (MySQL) as the workspace DB. No need to change unless you want a dedicated DB name (e.g. `zenml_workspace`).
- Secrets store: keep your existing `secretsStore` (Vault, AWS auth). No change.
- Ingress: keep or adjust host (e.g. workspace hostname). Same pattern as today.
- Add the **pro** block: `apiURL`, `dashboardURL`, `enabled: true`, `enrollmentKey`, `organizationID`, `organizationName`, `workspaceID`, `workspaceName`. These come from the Control Plane after you create the org and workspace.

So: **reuse** cluster, ingress, cert-manager, RDS (with one extra DB), Vault, and the zenml chart. **Add** one new release (zenml-pro) and **reconfigure** the existing zenml release (image + pro block).

---

## 5. Order of Operations (Conceptually)

1. **Prepare:** Get ZenML Pro images (and charts) as per the self-hosted Helm doc. If you use an internal registry, mirror the control plane images and the workspace server image; keep versions aligned with the charts.
2. **Control Plane first:** Deploy the zenml-pro chart (namespace, DB, ingress, serverURL, image repos). Verify pods and ingress; open the Pro dashboard URL.
3. **Enroll:** In the Pro dashboard, create an organization and a workspace. Obtain enrollment key and IDs. You need these before the workspace server can enroll.
4. **Workspace:** Update your existing zenml values: switch image to `zenml-pro-server`, add the `pro` block with control plane URLs and enrollment data. Optionally set `serverURL` to your workspace URL if different from today. Deploy/upgrade the zenml release.
5. **Clients:** Users point the ZenML client at the Control Plane API URL for login; the client will use the workspace URL for pipeline/run operations (often discovered via the control plane).

So the mental order is: **Control Plane → enroll workspace in UI → configure and (re)deploy workspace server.**

---

## 6. Databases: One RDS, Two Databases

You can keep a single RDS instance and create two databases:

- **Control plane:** e.g. `zenml_pro` (PostgreSQL or MySQL, depending on chart support).
- **Workspace:** your current OSS database or a dedicated one (e.g. `zenml_workspace`). Workspace servers use MySQL only.

So “extend” does not necessarily mean “new RDS”; it means “new DB name + new user or same user with permissions,” and wiring the two Helm releases to the correct DBs.

---

## 7. Optional: Workload Manager (Run Pipelines from UI)

Pro can run pipelines from the UI (snapshots / run templates). That uses a **Workload Manager** that runs jobs (e.g. Kubernetes Jobs) from the workspace server. It is optional and configured on the **workspace** side (environment variables in the zenml chart values), not on the control plane. If you want that later, the self-hosted doc has a section on workload manager: namespace, service account, implementation (Kubernetes vs AWS vs GCP), and optionally a pre-built runner image or a registry for built images. Your current “extend OSS → Pro” mental model does not require this; you can add it after the control plane and first workspace are running.

---

## 8. Summary Table

| Aspect              | Your current OSS              | After extending to Pro                                                                 |
|---------------------|------------------------------|----------------------------------------------------------------------------------------|
| **Control Plane**   | N/A                          | New: zenml-pro chart, new namespace, new DB, new URL (login + Pro dashboard).         |
| **Workspace server**| zenml chart, zenml-server    | Same zenml chart, zenml-pro-server image, same DB/Vault/ingress + `pro` config block. |
| **DBs**             | One MySQL (OSS metadata)     | Same MySQL as workspace DB + one more DB for control plane.                           |
| **URLs**            | One (server + UI)            | Two: Control Plane URL (login, Pro UI) and Workspace URL (pipelines, runs, stacks).  |
| **Secrets (Vault)** | In use                       | Unchanged for workspace server.                                                       |

---

## 9. References

- [ZenML Pro self-hosted deployment (Helm)](https://docs.zenml.io/pro/deployments/scenarios/self-hosted-deployment/self-hosted-deployment-helm) — images, charts, control plane and workspace values, enrollment, optional workload manager.
- [zenml-pro Helm chart values (Artifact Hub)](https://artifacthub.io/packages/helm/zenml-pro/zenml-pro?modal=values) — control plane values reference.
- Your [EKS setup](setup.md) and [values-aws.yaml](../../helm/values-aws.yaml) — what you already have to reuse.

With this mental model, you can go through the official Helm doc and values and decide exactly which namespaces, hostnames, DBs, and value keys to set for your environment.
