# EKS demo-day runbook

Everything that costs money happens in one sitting (~2–3 hours, ≈ $1). Do **Part 0 and Part 1 days before**;
they are free. Screenshot names match the rubric evidence map in the main README — save them in
`docs/screenshots/`.

## Part 0 — one-time GitHub setup (free)

1. Create an **empty public** repository `ankit14-dev/clinicflow` on GitHub (no README / .gitignore / license).
2. Push:
   ```bash
   git remote add origin git@github.com:ankit14-dev/clinicflow.git
   git push -u origin main
   ```
3. Actions tab → the first **ClinicFlow CI/CD** run should go green (the EKS deploy job shows as *skipped*).
4. Packages: open each package (`clinicflow-backend`, `clinicflow-frontend`) → *Package settings* →
   *Change visibility* → **Public** (so EKS can pull without an image pull secret) and make sure the
   repository is linked.
5. Settings → Environments → **New environment** → `production`.
6. Settings → Secrets and variables → Actions → **Variables**: `AWS_REGION=ap-south-1`,
   `EKS_CLUSTER_NAME=clinicflow-eks` (the other two come in Part 2).

📸 `01-pytest.png` (local `cd backend && pytest -v`), `02-compose-up.png`, `03-app-localhost.png`,
`04-commit-history.png`, `05-pipeline-green.png`, `06-trivy-output.png`, `07-ghcr-packages.png`.

## Part 1 — AWS permissions (free)

The IAM user needs the EKS policy in [`aws-iam-eks-policy.json`](aws-iam-eks-policy.json) in addition to
its EC2 / IAM / S3 policies. Check:

```bash
aws sts get-caller-identity
aws eks list-clusters --region ap-south-1     # must not say AccessDenied
```

## Part 2 — create the infrastructure (the meter starts)

```bash
cd terraform
terraform init
terraform plan -out clinicflow.tfplan          # 📸 08-terraform-plan.png ("Plan: 69 to add")
terraform apply clinicflow.tfplan              # ~15 min
terraform output
cd ..
./scripts/eks-up.sh                            # ~8 min: kubeconfig, gp3, kube-prometheus-stack, ingress-nginx
```

📸 `09-aws-vpc.png` (VPC console: clinicflow-vpc, 2 public + 2 private subnets),
`10-aws-eks.png` (EKS console: clinicflow-eks Active, node group with 3 nodes).

Turn on CI deploys — repository **Variables**:

* `AWS_DEPLOY_ROLE_ARN` = output of `terraform -chdir=terraform output -raw github_deploy_role_arn`
* `EKS_DEPLOY` = `true`

Then Actions → **ClinicFlow CI/CD** → *Run workflow* on `main` (or push any commit). The *Deploy to AWS EKS*
job installs the release and prints the URL.

## Part 3 — evidence on the running cluster

```bash
# public entry point: the ingress edge node (this account cannot create AWS load balancers)
APP=$(kubectl get nodes -l ingress=public -o jsonpath='{.items[0].status.addresses[?(@.type=="ExternalIP")].address}')
./scripts/seed-demo.sh "http://$APP"
kubectl get pods -n clinicflow -o wide         # 📸 11-get-pods.png (all Running, 2+ backend, 2 frontend)
kubectl get svc -n clinicflow                  # 📸 12-get-svc.png
helm list -n clinicflow                        # 📸 13-helm-list.png
kubectl get ingress,hpa -n clinicflow
```

* Browser `http://$APP/` (also shown as ADDRESS in `kubectl get ingress -n clinicflow`) → 📸 `14-app-via-ingress.png`
* `/metrics` is deliberately not routed through the Ingress (only `/` and `/api` are public), so read it in-cluster:
  `kubectl port-forward -n clinicflow svc/clinicflow-backend 8000:8000` then
  `curl -s localhost:8000/metrics | grep -E 'http_requests_total|clinicflow_'` → 📸 `15-metrics.png`
* `kubectl port-forward -n monitoring svc/kube-prometheus-stack-prometheus 9090:9090` →
  <http://localhost:9090/targets>, search *clinicflow* → both backend pods **UP** → 📸 `16-prometheus-targets.png`
* `./scripts/traffic.sh "http://$APP" 600 &` then
  `kubectl port-forward -n monitoring svc/kube-prometheus-stack-grafana 3001:80` → <http://localhost:3001>
  (admin / clinicflow-demo) → Dashboards → *ClinicFlow – API & Clinic Overview* → 📸 `17-grafana.png`

### HPA

```bash
kubectl apply -f scripts/load-test-job.yaml
kubectl get hpa -n clinicflow -w               # 📸 18-hpa-scaling.png when REPLICAS > 2
kubectl delete -f scripts/load-test-job.yaml
```

### Live pipeline demo (M10)

1. Edit something visible, e.g. `<small>Sunrise Health Clinic</small>` in `frontend/src/components/Sidebar.jsx`.
2. `git commit -am "Rename clinic in sidebar" && git push`
3. Show the jobs running; when *Deploy to AWS EKS* finishes, refresh the browser: new text, new build SHA
   in the sidebar footer. `helm history clinicflow -n clinicflow` shows the new revision.

### Troubleshooting (pick one or two live)

```bash
./troubleshooting/lab.sh break 1    # describe the new pod: ImagePullBackOff; app still serves
./troubleshooting/lab.sh fix 1
./troubleshooting/lab.sh break 2    # Service with no endpoints
./troubleshooting/lab.sh fix 2
./troubleshooting/lab.sh clean
```

## Part 4 — destroy (the meter stops)

1. Repository variable `EKS_DEPLOY` → `false` (so pushes don't try to deploy to a deleted cluster).
2. ```bash
   ./scripts/eks-down.sh               # 📸 19-terraform-destroy.png ("Destroy complete!")
   ```
3. Double-check in the console (ap-south-1): no EKS cluster, no `clinicflow-vpc`, no load balancers,
   no available EBS volumes, no NAT gateway / Elastic IP.

If `terraform destroy` hangs on the VPC or subnets, a load balancer or ENI created by Kubernetes is still
there: delete it in the EC2 console (Load Balancers / Network Interfaces) and run `terraform destroy` again.
