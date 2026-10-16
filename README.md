# ClinicFlow — clinic appointment booking, from laptop to monitored EKS

[![ClinicFlow CI/CD](https://github.com/ankit14-dev/clinicflow/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/ankit14-dev/clinicflow/actions/workflows/ci-cd.yml)

**Author:** Ankit Kumar · DevOps Heroes — Session 21 Final Capstone

ClinicFlow is the front-desk system of a small multi-specialty clinic. Receptionists register patients,
book them with a doctor, check them in when they arrive and close the visit when the consultation is done.
The dashboard shows today's schedule, who is in the waiting room, upcoming bookings and load per specialty.

The DevOps layer takes this application from source code to a monitored, autoscaling Kubernetes
deployment on AWS: tests → container images → security scan → registry → Terraform-built EKS → Helm →
Ingress → HPA → Prometheus/Grafana → troubleshooting.

| | |
|---|---|
| **Business rules the API enforces** | no double booking of a doctor (overlap check, `409`), appointments only in the future, doctors marked off duty cannot be booked, status workflow `SCHEDULED → CHECKED_IN → COMPLETED` (or `CANCELLED` / `NO_SHOW`), patients/doctors with history cannot be deleted |
| **Clinic timezone** | "today" on the dashboard is computed in `Asia/Kolkata`, not UTC |
| **Business metrics** | `clinicflow_appointments_booked_total{specialty}`, `clinicflow_appointment_status_changes_total{status}`, `clinicflow_booking_conflicts_total` on `/metrics`, graphed in Grafana |

---

## 1. Architecture

```mermaid
flowchart TB
  dev([Developer]) -->|git push| gh[GitHub repo]
  gh --> ci

  subgraph ci [GitHub Actions]
    direction LR
    t[pytest on PostgreSQL<br/>ruff · alembic check] --> b[docker build<br/>backend + frontend]
    fe[frontend build<br/>npm audit] --> b
    iac[helm lint<br/>terraform validate] --> b
    b --> s[Trivy scan<br/>HIGH/CRITICAL gate] --> p[push to GHCR<br/>tag = commit SHA]
    p --> k[kind cluster<br/>helm install + helm test] --> g[commit image tag<br/>values-gitops.yaml]
  end

  g -->|git push| gh
  gh -.->|polls every 60 s| argo

  p -.-> ghcr[(GHCR images)]
  tf[Terraform] --> aws

  subgraph aws [AWS ap-south-1 — VPC 10.40.0.0/16, 2 AZs]
    edge[edge node · t3.small<br/>public subnet, ports 80/443]
    subgraph eks [EKS cluster · 3 × t3.medium in private subnets + 1 edge node]
      argo[Argo CD<br/>auto-sync · prune · self-heal] -->|renders helm/clinicflow| be
      ing[ingress-nginx] -->|/| fe2[frontend ×2<br/>React on nginx]
      ing -->|/api| be[backend ×2–8<br/>FastAPI · HPA]
      fe2 -->|/api| be
      be --> pg[(PostgreSQL<br/>StatefulSet + EBS gp3)]
      prom[Prometheus] -->|ServiceMonitor /metrics| be
      graf[Grafana] --> prom
    end
    edge --> ing
  end

  ghcr -.->|image pull| eks
  user([Clinic staff]) -->|http://public-ip| edge
```

| Layer | Technology |
|---|---|
| Frontend | React 19 + Vite 8, responsive CSS, served by `nginx-unprivileged` (non-root, port 8080) |
| Backend | FastAPI, SQLAlchemy 2, Pydantic 2, Alembic, prometheus-fastapi-instrumentator |
| Database | PostgreSQL 17 |
| Tests | pytest + coverage (25 tests, 99 %), ruff |
| Containers | Docker multi-stage builds, Docker Compose |
| CI/CD | GitHub Actions, GHCR, Trivy, kind |
| Infrastructure | Terraform (terraform-aws-modules VPC 6.x / EKS 21.x), AWS VPC + EKS 1.36 |
| Kubernetes | Helm 4 chart, ingress-nginx, HPA (metrics-server), PDBs, EBS CSI |
| GitOps | Argo CD 3.5 (automated sync, prune, self-heal) |
| Observability | kube-prometheus-stack: Prometheus Operator, Prometheus, Grafana, Alertmanager |

## 2. Repository layout

```text
clinicflow/
├── backend/                 FastAPI app (app/), Alembic migrations, pytest suite, Dockerfile
├── frontend/                React app (src/), nginx config template, multi-stage Dockerfile
├── docker-compose.yml       full local stack: postgres + backend + frontend
├── .github/workflows/       ci-cd.yml — test → build → scan → push → smoke-deploy → GitOps promote → verify
├── terraform/               AWS VPC + EKS + IAM (OIDC deploy role, EBS CSI role)
├── k8s/                     namespace (Pod Security "restricted"), LimitRange, gp3 StorageClass
├── helm/clinicflow/         Helm chart + values-dev.yaml (minikube) / values-eks.yaml (AWS)
├── monitoring/              kube-prometheus-stack and ingress-nginx values
├── troubleshooting/         4 break/fix labs + lab.sh driver
├── argocd/                  Argo CD install values + the ClinicFlow Application (GitOps)
├── scripts/                 demo data, traffic generator, HPA load test, eks-up / argocd-up / eks-down
├── docs/                    EKS demo-day runbook, IAM policy, screenshots/
└── demo/                    presentation video (MP4) + slide deck (PPTX/PDF)
```

---

## 3. Run it locally

### Docker Compose (one command)

```bash
docker compose up --build
./scripts/seed-demo.sh            # optional: 6 patients + 8 appointments
```

* App: <http://localhost:3000>
* API docs (Swagger): <http://localhost:8000/docs>
* Health / readiness / metrics: <http://localhost:8000/health>, `/ready`, `/metrics`
* Database: `docker compose exec postgres psql -U clinicflow -c 'select * from appointments;'`

`docker compose down` stops it; `docker compose down -v` also deletes the database volume.

### Backend without Docker

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
export DATABASE_URL='postgresql+psycopg://clinicflow:clinicflow@localhost:5432/clinicflow'
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

Frontend dev server with hot reload: `cd frontend && npm ci && npm run dev` (proxies `/api` to `:8000`).

## 4. REST API

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | liveness — process is up (no DB call) |
| GET | `/ready` | readiness — `503` if the database is unreachable |
| GET | `/metrics` | Prometheus metrics |
| GET | `/api/info` | running version (commit SHA) and environment |
| GET | `/api/stats` | dashboard KPIs: today, upcoming, completed, no-shows, by status, by specialty |
| GET / POST | `/api/doctors` | list (`?active=true`) / add a doctor |
| GET / PUT / DELETE | `/api/doctors/{id}` | read / update (e.g. off duty) / delete (`409` if it has appointments) |
| GET / POST | `/api/patients` | list (`?q=` search by name, phone, email) / register |
| GET / PUT / DELETE | `/api/patients/{id}` | read / update / delete (`409` with history) |
| GET | `/api/patients/{id}/appointments` | visit history |
| GET / POST | `/api/appointments` | list (`?status=&doctor_id=&patient_id=&on=YYYY-MM-DD`) / book (`409` on double booking) |
| GET / PUT / DELETE | `/api/appointments/{id}` | read / reschedule or change status (validated transitions) / delete |

Schema changes go through Alembic (`backend/alembic/versions/`): `0001` creates `doctors`, `patients`,
`appointments` with check constraints and indexes, `0002` seeds five demo doctors.

## 5. Tests — the first quality gate

```bash
cd backend && pytest -v                       # SQLite, no setup needed
TEST_DATABASE_URL=postgresql+psycopg://... pytest -v   # what CI does, against a throwaway PostgreSQL
```

25 tests cover all four resources: CRUD, validation (`422`), not-found (`404`), double booking and
back-to-back slots, rescheduling conflicts, the status state machine, filters, stats and `/metrics`.
Tests never touch a real database: [`tests/conftest.py`](backend/tests/conftest.py) points the app at
`TEST_DATABASE_URL` (CI service container) or a local SQLite file, and recreates the schema per test.
CI fails below 90 % coverage. A broken test stops the pipeline before any image is built.

## 6. Docker

| Image | Build | Runtime user | Notes |
|---|---|---|---|
| `clinicflow-backend` | 2 stages: venv built in `python:3.14-slim`, copied into a clean `python:3.14-slim` | `appuser` uid 10001 | runs `alembic upgrade head`, then `exec uvicorn`; pip removed from the runtime image |
| `clinicflow-frontend` | 2 stages: `node:24-alpine` builds `dist/`, `nginx-unprivileged:1.30-alpine` serves it | `nginx` uid 101 | `/api` proxied to `$BACKEND_URL`; security headers; hashed assets cached 1 year |

In Kubernetes every container also runs with a read-only root filesystem, no Linux capabilities and
`allowPrivilegeEscalation: false` — the namespace enforces Pod Security **restricted**.

---

## 7. CI/CD — [`.github/workflows/ci-cd.yml`](.github/workflows/ci-cd.yml)

Runs on every push and pull request to `main`.

| Job | What it proves |
|---|---|
| **Backend tests** | ruff lint/format, `alembic upgrade → check → downgrade` on PostgreSQL, pytest with coverage ≥ 90 % |
| **Frontend build** | `npm ci`, `npm audit --audit-level=high`, `vite build` |
| **Helm + Terraform validation** | `helm lint` for every values file, `terraform fmt -check` + `validate` |
| **Build, scan & push** (matrix: backend, frontend) | image built and loaded locally → Trivy SARIF report to the Security tab → **Trivy gate** fails the job on fixable HIGH/CRITICAL CVEs or leaked secrets → only then pushed to GHCR as `ghcr.io/ankit14-dev/clinicflow-<component>:<commit-sha>` (PRs never push) |
| **Helm deploy smoke test** | spins up a kind cluster, loads the *scanned* images, `helm upgrade --install`, `helm test` |
| **GitOps promote** | only on `main`: writes the scanned image SHA into [`helm/clinicflow/values-gitops.yaml`](helm/clinicflow/values-gitops.yaml) and commits it as `github-actions[bot]` (`[skip ci]`) — git is now the record of what runs in production |
| **Verify Argo CD rollout on EKS** | only while repository variable `EKS_DEPLOY=true`: OIDC → AWS role (read-only use) → waits until Argo CD has synced the new tag and both Deployments finished rolling out, then smoke-tests `/api/info` + `/api/stats` through the Ingress |

The image tag is the full commit SHA: `commit A → image A → pods running A`. The UI footer shows the
running SHA (`/api/info`), so a deploy is visible in the browser.

All third-party actions are pinned to commit SHAs (a moved tag cannot inject code into the pipeline),
and Dependabot keeps the pins, Python/npm packages and base images up to date.

**GitHub settings used by the verify job** (Settings → Secrets and variables → Actions → *Variables*):

| Variable | Value |
|---|---|
| `EKS_DEPLOY` | `true` while the cluster exists, otherwise unset/`false` (job is skipped, pipeline stays green) |
| `AWS_DEPLOY_ROLE_ARN` | `terraform output -raw github_deploy_role_arn` |
| `AWS_REGION` | `ap-south-1` |
| `EKS_CLUSTER_NAME` | `clinicflow-eks` |

No AWS access keys are stored in GitHub. The verify job also uses a GitHub *environment* named
`production`, which is part of the OIDC trust condition. CI never runs `kubectl apply` or `helm upgrade`
against EKS — it only changes git; Argo CD applies.

### GitOps with Argo CD — [`argocd/`](argocd/)

```text
git push ─▶ CI: test → build → Trivy → GHCR → kind smoke test ─▶ CI commits new tag to values-gitops.yaml
                                                                          │
EKS ◀── Argo CD syncs (auto, prune, self-heal) ◀── Argo CD sees new commit on main (polls every 60 s)
```

* [`argocd/clinicflow-application.yaml`](argocd/clinicflow-application.yaml) — the Application: source
  `helm/clinicflow` on `main` with `values-eks.yaml` + `values-gitops.yaml`, destination namespace `clinicflow`,
  automated sync with **prune** (removed from git → removed from cluster) and **self-heal** (manual `kubectl`
  edits are reverted). HPA-owned `replicas` is ignored in the diff.
* [`argocd/argocd-values.yaml`](argocd/argocd-values.yaml) — Argo CD install (60 s git polling,
  annotation-based resource tracking, no Dex/notifications).
* [`scripts/argocd-up.sh`](scripts/argocd-up.sh) — installs Argo CD, creates the DB Secret, and **adopts** a
  release previously installed with `helm upgrade` in place (no pod or database restart: tested on EKS).
* **Rollback** = `git revert` of the bot's tag commit; Argo CD rolls back to the previous image.

```bash
kubectl get applications -n argocd                       # SYNC STATUS / HEALTH
kubectl port-forward -n argocd svc/argocd-server 8080:80  # UI → http://localhost:8080, user admin
kubectl get secret -n argocd argocd-initial-admin-secret -o jsonpath='{.data.password}' | base64 -d; echo
```

## 8. DevSecOps — Trivy

Trivy scans both final images for OS-package and language-library CVEs and for secrets baked into layers.
The gate uses `--severity HIGH,CRITICAL --ignore-unfixed --exit-code 1`: a vulnerability that already has a
fix fails the build, so it cannot reach the registry; unfixed ones are reported (SARIF → GitHub Security tab)
but do not block. The full report of all severities goes to the Security tab.

**What the first scan found and how it was fixed:** the backend image had 4 HIGH findings —
CVE-2026-97687 / CVE-2026-97689 in `urllib3` and GHSA-6v7p-g79w-8964 in `msgpack` — all inside **pip's own
vendored copies**, which the application never uses at runtime. Removing pip from the runtime image
(one line in the Dockerfile) cleared them. The frontend's older nginx base had 43 HIGH Alpine package CVEs
(curl, c-ares, …); moving to the `nginx-unprivileged:1.30-alpine` stable base cleared all of them.
Both images now pass the gate with zero fixable HIGH/CRITICAL findings.

Security layers in this project:

| Layer | Where |
|---|---|
| Dependency scanning | `npm audit`, Trivy (python-pkg / npm in images), Dependabot |
| Container scanning | Trivy gate before push |
| Secret scanning | Trivy `secret` scanner on images; `.gitignore` for `.env`, `*.tfvars`, state |
| Supply chain | actions pinned to SHAs; images tagged by immutable commit SHA |
| Runtime hardening | non-root, read-only root fs, dropped capabilities, seccomp, Pod Security *restricted* |
| Cloud access | GitHub OIDC → short-lived AWS credentials; nodes in private subnets |

## 9. Terraform — AWS VPC + EKS

Details, cost table and design decisions: [`terraform/README.md`](terraform/README.md).

```bash
cd terraform && terraform init && terraform plan -out clinicflow.tfplan   # 59 resources
terraform apply clinicflow.tfplan                                         # ~15 min
cd .. && ./scripts/eks-up.sh        # kubeconfig, gp3 StorageClass, kube-prometheus-stack, ingress-nginx
...
./scripts/eks-down.sh               # deletes NLB + EBS volumes first, then terraform destroy
```

Step-by-step demo day with every screenshot to take: [`docs/eks-demo-runbook.md`](docs/eks-demo-runbook.md).

## 10. Kubernetes + Helm

On EKS the chart is deployed by **Argo CD** (section 7). Installed directly with Helm — as on minikube,
in the CI kind cluster, or before GitOps is set up:

```bash
kubectl apply -f k8s/namespace.yaml -f k8s/limitrange.yaml
helm upgrade --install clinicflow helm/clinicflow -n clinicflow -f helm/clinicflow/values-eks.yaml \
  --set backend.image.tag=<sha> --set frontend.image.tag=<sha> --wait
helm test clinicflow -n clinicflow
helm list -n clinicflow
helm history clinicflow -n clinicflow
kubectl get pods,svc,ingress,hpa,pdb -n clinicflow
```

Platform components on EKS are Helm releases too: `helm list -A` shows `argocd`, `ingress-nginx` and
`kube-prometheus-stack`.

What the chart deploys:

* **Deployments** — backend (2–8 pods, HPA) and frontend (2 pods); rolling updates with `maxUnavailable: 0`;
  pods spread across nodes; PodDisruptionBudgets keep one pod during node drains.
* **Probes** — `startupProbe` gives Alembic time to migrate; `readinessProbe` → `/ready` (needs the DB);
  `livenessProbe` → `/health` (a DB outage must not restart every pod).
* **Services** — ClusterIP for backend (8000), frontend (80), headless for PostgreSQL.
* **PostgreSQL** — StatefulSet with a PersistentVolumeClaim (EBS gp3 on EKS); password generated once into a
  Secret and kept across upgrades (`lookup` + `helm.sh/resource-policy: keep`).
* **Ingress** — `/api` → backend, `/` → frontend. The Ingress is only configuration; the **ingress-nginx
  controller** implements it. This AWS account is not allowed to create load balancers
  (`OperationNotPermitted`), so the controller runs on a dedicated **edge node** in a public subnet
  (`hostNetwork`, ports 80/443) and the app is reached at `http://<edge-node-public-ip>/`. With load balancers
  available, set `public_ingress_node = false` in Terraform and `eks-up.sh` installs the NLB variant instead.
* **HPA** — CPU target 60 % of the 100m request; faster scale-down window so the demo is visible.
* **Monitoring objects** — ServiceMonitor, PrometheusRule (backend down, 5xx ratio, p95 latency, HPA at max,
  restarts) and the Grafana dashboard ConfigMap.

Local cluster: `minikube start --addons=ingress,metrics-server`, `minikube image load clinicflow-backend:local
clinicflow-frontend:local`, then install with `-f helm/clinicflow/values-dev.yaml` and open
<http://clinicflow.192.168.49.2.nip.io>.

### Autoscaling demo

```bash
kubectl apply -f scripts/load-test-job.yaml     # 4 in-cluster pods hammer /api/appointments and /api/stats
kubectl get hpa -n clinicflow -w                # tested on minikube: cpu 4% → 312%, replicas 2 → 4 → 6
kubectl delete -f scripts/load-test-job.yaml    # replicas fall back to 2 after ~2-3 minutes
```

The HPA needs resource requests (set in the chart) and a metrics provider (`metrics-server` EKS add-on).

## 11. Monitoring — Prometheus + Grafana

```bash
kubectl port-forward -n monitoring svc/kube-prometheus-stack-prometheus 9090:9090   # Status → Targets
kubectl port-forward -n monitoring svc/kube-prometheus-stack-grafana 3001:80        # admin / clinicflow-demo
./scripts/traffic.sh http://<ingress-host> 600                                      # realistic traffic
```

Grafana dashboard **"ClinicFlow – API & Clinic Overview"** is provisioned automatically from the chart:
requests/s, p95 latency, 5xx ratio, ready backend pods, requests by endpoint, p50/p95/p99 latency,
responses by status class, appointments booked by specialty, status changes & rejected double bookings,
HPA current/desired/max replicas, CPU and memory per pod.

## 12. Troubleshooting labs

`./troubleshooting/lab.sh break <n>` / `fix <n>` — full guide in
[`troubleshooting/README.md`](troubleshooting/README.md):

1. **ImagePullBackOff** on the real backend after a bad release (old pods keep serving thanks to `maxUnavailable: 0`) → `rollout undo` / `helm rollback`
2. **Service without endpoints** — selector and targetPort do not match the pods
3. **CrashLoopBackOff** — wrong `DATABASE_URL`, found with `kubectl logs --previous`
4. **Pending** — requests larger than any node

## 13. Final presentation flow

1. Open ClinicFlow through the Ingress, book an appointment, try a double booking (`409`), check the patient in.
2. Swagger `/docs`: create / read / update / delete.
3. `kubectl exec -n clinicflow clinicflow-postgres-0 -- psql -U clinicflow -c 'select id, status, scheduled_at from appointments;'`
4. Change something visible (e.g. the clinic name in `frontend/src/components/Sidebar.jsx`), commit, push.
5. Watch the pipeline: tests → build → Trivy → GHCR → kind smoke test → GitOps promote → verify;
   in the Argo CD UI the app goes OutOfSync → Syncing → Synced/Healthy on the bot's commit.
6. GHCR package page: new SHA tag. 7. Trivy output in the job log / Security tab.
8. `terraform/` code and AWS console (VPC, EKS, node group).
9. `kubectl get pods,svc,ingress -n clinicflow`, `kubectl get applications -n argocd`, `helm list -A`.
10. Refresh the browser: footer shows the new build SHA, change is live — zero downtime.
11. HPA load test; Grafana panels move. 12. Break and fix lab 1 or 2 live.

## 14. Design decisions & production notes

* **PostgreSQL in the cluster** is fine for a classroom; production should use **Amazon RDS** (Multi-AZ,
  automated backups, patching, point-in-time recovery) and pass its endpoint via `existingSecret`.
* **Migrations at container start** — every replica runs `alembic upgrade head`; a PostgreSQL advisory lock
  (`alembic/env.py`) makes concurrent replicas take turns. (The first EKS deploy, before the lock, showed the
  race: two pods created `alembic_version` at once and one restarted.) A Helm pre-upgrade Job is the
  alternative for very large deployments.
* **No TLS** — the classroom has no domain. With one: cert-manager + Let's Encrypt and `ingress.tls: true`.
* **ingress-nginx** matches the course; the chart only needs `ingress.className` changed to move to another
  controller (e.g. AWS Load Balancer Controller or Gateway API).
* **GitHub OIDC subject** — this repository's tokens use GitHub's *immutable* subject format
  `repo:ankit14-dev@<owner-id>/clinicflow@<repo-id>:environment:production`; the IAM trust policy accepts both
  that and the classic `repo:ankit14-dev/clinicflow:…` form (`terraform/github-oidc.tf`).
* **Cost control** — single NAT gateway, no KMS key / control-plane logs, `scripts/eks-down.sh` the same day.

## 15. Known issues & limitations

| Issue | Impact | Mitigation / next step |
|---|---|---|
| The AWS account cannot create load balancers (`OperationNotPermitted` from ELB) | No NLB/ALB; one t3.small edge node in a public subnet runs ingress-nginx on ports 80/443 | It is a single point of entry: fine for a demo, not HA. With ELB access set `public_ingress_node = false` (NLB) or use the AWS Load Balancer Controller |
| No domain → no TLS | Traffic is plain HTTP to an IP address | Route 53 domain + cert-manager/Let's Encrypt (`ingress.tls: true`) |
| PostgreSQL runs in the cluster, single replica | Node loss = downtime until the pod reschedules (data survives on EBS); no automated backups | Amazon RDS Multi-AZ via `postgresql.existingSecret` + external host |
| Edge node's public IP changes if the node is replaced | URL changes | Elastic IP on the node, or a load balancer + DNS |
| Argo CD renders Helm charts offline | Chart's `lookup()` password generation can't run; `helm test` hooks are ignored; `helm list -n clinicflow` is empty on EKS | DB Secret created by `argocd-up.sh`; CI verify job replaces `helm test`; Helm release is visible in the CI kind job |
| Argo CD UI only via `kubectl port-forward`, initial admin password | Not exposed publicly (intentional) | SSO (Dex/OIDC) and an Ingress with TLS for a team setup |
| Grafana admin password is a demo value in `monitoring/` | Acceptable only because Grafana is not exposed | Use `grafana.admin.existingSecret` |
| Migrations run at container start | Serialized by a PostgreSQL advisory lock; long migrations delay pod readiness | Pre-sync Argo CD hook Job for heavy migrations |
| Single NAT gateway, no KMS key / control-plane logs | Lower cost, less resilience/auditability | One NAT per AZ, envelope encryption and control-plane logging for production |
| Cluster is short-lived | Must be recreated for each demo (~25 min: `terraform apply` + `eks-up.sh`) | Remote state (S3 backend) for team use |

## 16. Rubric evidence map

| Module | Evidence in this repo | Screenshot to add in `docs/screenshots/` |
|---|---|---|
| M1 App | `backend/app/`, `backend/alembic/versions/`, `frontend/`, `docker-compose.yml` | app in browser |
| M2 Tests | `backend/tests/` (25), `pytest.ini`, `conftest.py` | `pytest -v` all passed |
| M3 Git | this repo, `.gitignore` | commit history (≥ 10 commits) |
| M4 Docker | both Dockerfiles (multi-stage, non-root), compose | `docker compose up --build`, localhost:3000 |
| M5 CI/CD | `.github/workflows/ci-cd.yml` | green run, GHCR packages with SHA tags |
| M6 Trivy | gate + SARIF steps, section 8 above | Trivy step output |
| M7 Terraform | `terraform/`, `terraform.tfvars.example` | `plan`, AWS console VPC + EKS, `destroy` complete |
| M8 K8s + Helm | `k8s/`, `helm/clinicflow/`, `argocd/` | `get pods`, `get svc,ingress`, `helm list -A` + CI kind `helm list`, Argo CD Synced/Healthy, app via Ingress |
| M9 Observability | `monitoring/`, chart ServiceMonitor + dashboard | `/metrics`, Prometheus Targets UP, Grafana panels |
| M10 Docs + demo | this README, `demo/` (video + slides) | — |
