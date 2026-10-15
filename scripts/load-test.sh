#!/usr/bin/env bash
# HPA demo: start the in-cluster k6 load test and watch the autoscaler react.
#   scripts/load-test.sh            # run and watch for ~7 minutes
# Grafana's "Autoscaler: API replicas" panel shows the same thing graphically.
set -euo pipefail

cd "$(dirname "$0")/.."
NS="${NAMESPACE:-cliniccare}"

kubectl -n "$NS" delete job cliniccare-load-test --ignore-not-found --wait=true
kubectl -n "$NS" apply -f scripts/load-test-job.yaml

echo "Watching the HPA (Ctrl+C to stop watching; the load test keeps running)..."
for _ in $(seq 1 28); do
  date +%T
  kubectl -n "$NS" get hpa cliniccare-backend --no-headers
  kubectl -n "$NS" top pods -l app.kubernetes.io/component=backend --no-headers 2>/dev/null || true
  echo
  sleep 15
done
kubectl -n "$NS" logs job/cliniccare-load-test --tail=30 || true
