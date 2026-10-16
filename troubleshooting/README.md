# Troubleshooting labs

Four failures that happen in real clusters, each with the commands to diagnose it and a fix.
Run them against a deployed `clinicflow` release:

```bash
./troubleshooting/lab.sh break 1    # ... investigate ...
./troubleshooting/lab.sh fix 1
./troubleshooting/lab.sh clean      # remove the lab resources (labs 2-4)
```

| # | Symptom | First command | Root cause | Fix |
|---|---------|---------------|------------|-----|
| 1 | New backend pod `ImagePullBackOff`, rollout stuck | `kubectl describe pod <new-pod>` → *Events: manifest unknown* | a release pointed at an image tag that was never pushed | `kubectl rollout undo deploy/clinicflow-backend` (or `helm rollback clinicflow`) |
| 2 | Service exists, pods Running, requests time out | `kubectl get endpointslices -l kubernetes.io/service-name=lab-broken-service` → no endpoints | selector `component=api` matches no pod; `targetPort` 8080 ≠ container port 8000 | fix selector + `targetPort: http` |
| 3 | `CrashLoopBackOff`, RESTARTS climbing | `kubectl logs <pod> --previous` → `failed to resolve host 'postgres-typo'` | wrong `DATABASE_URL`: migrations fail, the container exits 1 | take DB settings from the `clinicflow-config` ConfigMap + `clinicflow-db` Secret |
| 4 | `Pending`, no node assigned | `kubectl describe pod` → `Insufficient cpu` | requests (8 CPU / 16Gi) larger than any t3.medium node | right-size requests (or add a bigger node group in Terraform) |

## What lab 1 teaches about safe rollouts

The backend Deployment uses `maxUnavailable: 0`, so Kubernetes starts the new (broken) pod *before*
removing any old one. The new pod never becomes Ready, the old ReplicaSet keeps all its pods, and users
see no outage while you investigate:

```bash
kubectl get pods -n clinicflow -l app.kubernetes.io/component=backend   # 1 broken + all old pods Running
curl -s -o /dev/null -w '%{http_code}\n' http://<ingress>/api/stats    # still 200
kubectl rollout history deploy/clinicflow-backend -n clinicflow
```

`kubectl rollout undo` reverts the Deployment directly; `helm rollback clinicflow <revision>` does the
same through Helm and keeps Helm's release history in sync (preferred when the release is managed by CI).

## General checklist

```bash
kubectl get pods -n clinicflow -o wide                     # status, restarts, node
kubectl describe pod <pod> -n clinicflow                   # events: scheduling, pulls, probes
kubectl logs <pod> -n clinicflow [--previous]              # app output (previous = before the last crash)
kubectl get events -n clinicflow --sort-by=.lastTimestamp  # everything that happened, in order
kubectl get endpointslices -n clinicflow                   # does each Service have backends?
kubectl get pods -n clinicflow --show-labels               # compare labels with Service selectors
kubectl top pods -n clinicflow                             # CPU/memory (needs metrics-server)
```
