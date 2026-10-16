#!/usr/bin/env bash
# Tear everything down so the AWS bill stops. Order matters:
# Kubernetes created an NLB (ingress-nginx Service) and EBS volumes (PostgreSQL PVC) that Terraform does
# not know about. They must go first, otherwise `terraform destroy` hangs on the VPC (the NLB still has
# network interfaces in the subnets) and the EBS volumes keep billing.
set -euo pipefail
echo "==> removing Kubernetes-created AWS resources"
# Argo CD first: with selfHeal on it would recreate anything deleted underneath it.
# Deleting the Application (resources finalizer) removes everything it deployed.
kubectl delete application clinicflow -n argocd --wait=true --timeout=5m 2>/dev/null || true
helm uninstall argocd -n argocd --wait 2>/dev/null || true
helm uninstall clinicflow -n clinicflow --wait 2>/dev/null || true   # pre-GitOps installs
kubectl delete pvc --all -n clinicflow --wait=true 2>/dev/null || true          # -> deletes the EBS volumes (reclaimPolicy Delete)
helm uninstall kube-prometheus-stack -n monitoring --wait 2>/dev/null || true
kubectl delete pvc --all -n monitoring --wait=true 2>/dev/null || true
helm uninstall ingress-nginx -n ingress-nginx --wait 2>/dev/null || true         # -> deletes the NLB

echo "==> waiting for the load balancer to disappear"
VPC_ID=$(terraform -chdir=terraform output -raw vpc_id)
REGION=$(terraform -chdir=terraform output -raw region)
for _ in $(seq 1 30); do
  n=$(aws elbv2 describe-load-balancers --region "$REGION" \
        --query "length(LoadBalancers[?VpcId=='$VPC_ID'])" --output text 2>/dev/null || echo 0)
  [ "$n" = "0" ] && break; echo "  $n load balancer(s) still deleting..."; sleep 10
done

echo "==> terraform destroy"
terraform -chdir=terraform destroy -auto-approve

echo "==> leftovers check (should all be empty)"
aws ec2 describe-volumes --region "$REGION" --filters Name=tag:kubernetes.io/created-for/pvc/namespace,Values=clinicflow,monitoring \
  --query 'Volumes[].VolumeId' --output text
aws ec2 describe-vpcs --region "$REGION" --filters Name=tag:Project,Values=clinicflow --query 'Vpcs[].VpcId' --output text
