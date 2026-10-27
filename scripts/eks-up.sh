#!/usr/bin/env bash
# After `terraform apply`: connect kubectl and install the cluster add-ons ClinicFlow needs.
# Usage: ./scripts/eks-up.sh            (run from the repo root)
set -euo pipefail
REGION=$(terraform -chdir=terraform output -raw region)
CLUSTER=$(terraform -chdir=terraform output -raw cluster_name)

echo "==> kubeconfig for $CLUSTER ($REGION)"
aws eks update-kubeconfig --region "$REGION" --name "$CLUSTER"
kubectl get nodes -o wide

echo "==> bootstrap manifests: namespace, LimitRange, default gp3 StorageClass"
kubectl apply -f k8s/namespace.yaml -f k8s/limitrange.yaml -f k8s/storageclass-gp3.yaml
# gp2 must stop being default, otherwise two default StorageClasses exist
kubectl annotate storageclass gp2 storageclass.kubernetes.io/is-default-class=false --overwrite 2>/dev/null || true

helm repo add prometheus-community https://prometheus-community.github.io/helm-charts >/dev/null
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx >/dev/null
for _ in 1 2 3 4 5; do helm repo update >/dev/null && break; echo "  helm repo update failed, retrying..."; sleep 10; done

echo "==> kube-prometheus-stack (Prometheus Operator, Prometheus, Grafana) — installed first: it provides the CRDs"
helm upgrade --install kube-prometheus-stack prometheus-community/kube-prometheus-stack --version 92.9.0 \
  -n monitoring --create-namespace -f monitoring/kube-prometheus-stack-values.yaml --wait --timeout 15m

MODE=$(terraform -chdir=terraform output -raw ingress_mode)
if [ "$MODE" = "public-node" ]; then
  echo "==> ingress-nginx controller on the public edge node (hostNetwork :80, no AWS load balancer)"
  helm upgrade --install ingress-nginx ingress-nginx/ingress-nginx --version 4.15.1 \
    -n ingress-nginx --create-namespace -f monitoring/ingress-nginx-public-node-values.yaml --wait --timeout 10m
  URL_HOST=$(kubectl get nodes -l ingress=public -o jsonpath='{.items[0].status.addresses[?(@.type=="ExternalIP")].address}')
else
  echo "==> ingress-nginx controller (creates an internet-facing AWS NLB)"
  helm upgrade --install ingress-nginx ingress-nginx/ingress-nginx --version 4.15.1 \
    -n ingress-nginx --create-namespace -f monitoring/ingress-nginx-values.yaml --wait --timeout 10m
  echo "==> waiting for the load balancer hostname"
  for _ in $(seq 1 60); do
    URL_HOST=$(kubectl get svc -n ingress-nginx ingress-nginx-controller -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
    [ -n "$URL_HOST" ] && break; sleep 5
  done
fi
echo
echo "Cluster ready. Application entry point: http://$URL_HOST/"

# GitOps: Argo CD deploys ClinicFlow from helm/clinicflow + values-gitops.yaml on main
"$(dirname "$0")/argocd-up.sh"
