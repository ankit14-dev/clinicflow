#!/usr/bin/env bash
# Live troubleshooting demo:  ./troubleshooting/lab.sh break 1..4 | fix 1..4 | clean
set -euo pipefail
cd "$(dirname "$0")"
NS=clinicflow
FILES=("" 02-broken-service.yaml 03-crashloop-bad-db.yaml 04-pending-resources.yaml)
# lab 3 must run the real backend image, otherwise it fails with ImagePullBackOff instead of CrashLoopBackOff
IMAGE=$(kubectl get deploy clinicflow-backend -n "$NS" -o jsonpath='{.spec.template.spec.containers[0].image}')

case "${1:-}-${2:-}" in
  # lab 1 breaks the REAL backend: a release whose image tag was never pushed
  break-1) kubectl set image deploy/clinicflow-backend -n "$NS" backend="${IMAGE%:*}:does-not-exist" ;;
  break-[2-4]) sed "s|ghcr.io/ankit14-dev/clinicflow-backend:REPLACE_WITH_SHA|$IMAGE|" "${FILES[$2-1]}" | kubectl apply -f - ;;
  fix-1) kubectl rollout undo deploy/clinicflow-backend -n "$NS" && kubectl rollout status deploy/clinicflow-backend -n "$NS" ;;
  fix-2) kubectl patch svc lab-broken-service -n "$NS" --type merge \
           -p '{"spec":{"selector":{"app.kubernetes.io/component":"backend"},"ports":[{"port":8000,"targetPort":"http"}]}}' ;;
  fix-3) kubectl set env deploy/lab-bad-db -n "$NS" DATABASE_URL- \
         && kubectl patch deploy lab-bad-db -n "$NS" --type json -p '[{"op":"add","path":"/spec/template/spec/containers/0/envFrom","value":[{"configMapRef":{"name":"clinicflow-config"}}]},{"op":"add","path":"/spec/template/spec/containers/0/env","value":[{"name":"POSTGRES_PASSWORD","valueFrom":{"secretKeyRef":{"name":"clinicflow-db","key":"postgres-password"}}},{"name":"DATABASE_URL","value":"postgresql+psycopg://$(POSTGRES_USER):$(POSTGRES_PASSWORD)@$(POSTGRES_HOST):5432/$(POSTGRES_DB)"}]}]' ;;
  fix-4) kubectl set resources deploy/lab-too-big -n "$NS" --requests=cpu=10m,memory=16Mi --limits=cpu=50m,memory=32Mi ;;
  clean-) for f in "${FILES[@]:1}"; do kubectl delete -f "$f" --ignore-not-found; done ;;
  *) echo "usage: $0 break|fix <1-4>  |  $0 clean"; exit 1 ;;
esac
