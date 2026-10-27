#!/usr/bin/env bash
# Install Argo CD and hand the ClinicFlow deployment over to GitOps.
# Usage (repo root, kubectl pointing at the cluster): ./scripts/argocd-up.sh
set -euo pipefail
NS=clinicflow

echo "==> Argo CD"
helm repo add argo https://argoproj.github.io/argo-helm >/dev/null
for _ in 1 2 3 4 5; do helm repo update argo >/dev/null && break; echo "  helm repo update failed, retrying..."; sleep 10; done
helm upgrade --install argocd argo/argo-cd --version 10.10.5 -n argocd --create-namespace \
  -f argocd/argocd-values.yaml --wait --timeout 10m

echo "==> database Secret (Argo CD renders charts offline, so the chart cannot generate it)"
kubectl apply -f k8s/namespace.yaml -f k8s/limitrange.yaml
if ! kubectl get secret clinicflow-db -n "$NS" >/dev/null 2>&1; then
  kubectl create secret generic clinicflow-db -n "$NS" \
    --from-literal=postgres-password="$(head -c 18 /dev/urandom | base64 | tr -dc 'A-Za-z0-9')"
fi

# A release installed earlier by `helm upgrade` keeps its pods, Services and PVC: Argo CD adopts them
# in place. Only Helm's own release records are removed so the two tools never fight over it.
if kubectl get secret -n "$NS" -l owner=helm,name=clinicflow -o name | grep -q .; then
  echo "==> handing the existing Helm release over to Argo CD (resources stay running)"
  kubectl delete secret -n "$NS" -l owner=helm,name=clinicflow
fi

echo "==> ClinicFlow Application"
kubectl apply -f argocd/clinicflow-application.yaml
for _ in $(seq 1 60); do
  s=$(kubectl get application clinicflow -n argocd -o jsonpath='{.status.sync.status}/{.status.health.status}' 2>/dev/null || true)
  echo "  sync/health: ${s:-pending}"
  [ "$s" = "Synced/Healthy" ] && break; sleep 10
done
echo
echo "Argo CD UI: kubectl port-forward -n argocd svc/argocd-server 8080:80   ->  http://localhost:8080  (admin)"
echo "Password:   kubectl get secret -n argocd argocd-initial-admin-secret -o jsonpath='{.data.password}' | base64 -d; echo"
