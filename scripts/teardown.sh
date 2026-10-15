#!/usr/bin/env bash
# Remove everything, in the order that avoids orphaned AWS resources:
#   1. the app release - deleting its Ingress makes the controller delete the ALB
#   2. wait until the ALB is really gone (it holds network interfaces and
#      security groups in the VPC, which would block the VPC deletion)
#   3. monitoring and the controller
#   4. terraform destroy
#   5. switch the pipeline's deploy job off
set -euo pipefail

cd "$(dirname "$0")/.."
TF="${TERRAFORM:-terraform}"
export AWS_PAGER=""
REGION=$("$TF" -chdir=terraform output -raw region)
CLUSTER=$("$TF" -chdir=terraform output -raw cluster_name)
CONTEXT="${KUBE_CONTEXT:-$CLUSTER}"

if kubectl --context "$CONTEXT" get ns >/dev/null 2>&1; then
  echo "==> uninstall ClinicCare (deletes the Ingress, the ALB and the database volume)"
  helm --kube-context "$CONTEXT" uninstall cliniccare -n cliniccare --wait --timeout 10m 2>/dev/null || true

  echo "==> wait for the load balancer to be deleted"
  for _ in $(seq 1 60); do
    if ! aws elbv2 describe-load-balancers --region "$REGION" --names cliniccare >/dev/null 2>&1; then
      echo "    load balancer gone"
      break
    fi
    sleep 10
  done

  echo "==> uninstall monitoring and the load balancer controller"
  helm --kube-context "$CONTEXT" uninstall kube-prometheus-stack -n monitoring --wait 2>/dev/null || true
  helm --kube-context "$CONTEXT" uninstall aws-load-balancer-controller -n kube-system --wait 2>/dev/null || true
  # Remaining PVCs would leave EBS volumes behind after the cluster is gone.
  kubectl --context "$CONTEXT" delete pvc --all -n cliniccare --wait=true 2>/dev/null || true
else
  echo "Cluster not reachable; skipping in-cluster cleanup."
fi

echo "==> terraform destroy"
"$TF" -chdir=terraform destroy -auto-approve

if command -v gh >/dev/null 2>&1; then
  scripts/configure-github.sh --disable || true
fi
echo "Teardown complete."
