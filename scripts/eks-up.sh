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
helm repo update >/dev/null

echo "==> kube-prometheus-stack (Prometheus Operator, Prometheus, Grafana) — installed first: it provides the CRDs"
helm upgrade --install kube-prometheus-stack prometheus-community/kube-prometheus-stack --version 92.9.0 \
  -n monitoring --create-namespace -f monitoring/kube-prometheus-stack-values.yaml --wait --timeout 15m

echo "==> ingress-nginx controller (creates an internet-facing AWS NLB)"
helm upgrade --install ingress-nginx ingress-nginx/ingress-nginx --version 4.15.1 \
  -n ingress-nginx --create-namespace -f monitoring/ingress-nginx-values.yaml --wait --timeout 10m

echo "==> waiting for the load balancer hostname"
for _ in $(seq 1 60); do
  LB=$(kubectl get svc -n ingress-nginx ingress-nginx-controller -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
  [ -n "$LB" ] && break; sleep 5
done
echo
echo "Cluster ready. Ingress load balancer: http://$LB/  (DNS can take 2-3 minutes to resolve)"
echo "Next: deploy the app — either push to main with the repo variable EKS_DEPLOY=true, or manually:"
echo "  helm upgrade --install clinicflow helm/clinicflow -n clinicflow -f helm/clinicflow/values-eks.yaml \\"
echo "    --set backend.image.tag=<git-sha> --set frontend.image.tag=<git-sha> --wait"
