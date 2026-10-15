#!/usr/bin/env bash
# Apply one broken scenario, wait for the symptom, and print the commands
# (and their output) an engineer would use to diagnose it.
#   troubleshooting/run-scenario.sh 3          # break, then diagnose
#   troubleshooting/run-scenario.sh cleanup    # remove every lab resource
set -euo pipefail

cd "$(dirname "$0")"
NS="${NAMESPACE:-cliniccare}"
k() { echo "\$ kubectl $*"; kubectl -n "$NS" "$@" || true; echo; }

if [[ "${1:-}" == "cleanup" ]]; then
  kubectl -n "$NS" delete deploy,svc,pod -l lab=troubleshooting --ignore-not-found
  exit 0
fi

file=$(ls "0${1:?usage: run-scenario.sh <1-5|cleanup>}"-*.yaml)
image=$(kubectl -n "$NS" get deploy cliniccare-backend -o jsonpath='{.spec.template.spec.containers[0].image}')
sed "s|IMAGE|$image|" "$file" | kubectl -n "$NS" apply -f -
echo "Applied $file - waiting 45s for the symptom to appear..."
sleep 45

case "$1" in
  1)
    k get pods -l app=broken-image
    k describe pod -l app=broken-image
    ;;
  2)
    k get svc broken-service
    k get endpointslices -l kubernetes.io/service-name=broken-service
    k get pods -l app.kubernetes.io/name=cliniccare --show-labels
    ;;
  3)
    k get pods -l app=broken-readiness
    k describe pod -l app=broken-readiness
    k logs deploy/broken-readiness --tail=15
    ;;
  4)
    k get pods -l app=broken-crashloop
    k logs deploy/broken-crashloop --previous --tail=15
    k describe pod -l app=broken-crashloop
    ;;
  5)
    k get deploy broken-pod-security
    k get pods -l app=broken-pod-security
    k get events --field-selector reason=FailedCreate
    ;;
esac
