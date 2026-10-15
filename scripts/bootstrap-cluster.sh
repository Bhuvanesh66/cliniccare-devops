#!/usr/bin/env bash
# Prepare a freshly created EKS cluster for ClinicCare:
#   1. kubeconfig for the eks-admin role (via the operator profile)
#   2. namespace (restricted Pod Security) and the pipeline's extra RBAC
#   3. AWS Load Balancer Controller (turns the Ingress into an ALB)
#   4. kube-prometheus-stack (Prometheus + Grafana) with a random Grafana password
#
# Run from the repository root after `terraform apply` and
# scripts/setup-operator-profile.sh. Safe to re-run.
set -euo pipefail

cd "$(dirname "$0")/.."
TF="${TERRAFORM:-terraform}"
PROFILE="${OPERATOR_PROFILE:-cliniccare-operator}"
LBC_CHART_VERSION="3.6.0"
KPS_CHART_VERSION="92.8.0"
export AWS_PAGER=""

tf_output() { "$TF" -chdir=terraform output -raw "$1"; }
REGION=$(tf_output region)
CLUSTER=$(tf_output cluster_name)
VPC_ID=$(tf_output vpc_id)
ADMIN_ROLE=$(tf_output eks_admin_role_arn)

echo "==> kubeconfig for $CLUSTER ($REGION) as $ADMIN_ROLE"
aws eks update-kubeconfig --region "$REGION" --name "$CLUSTER" --alias "$CLUSTER" \
  --profile "$PROFILE" --role-arn "$ADMIN_ROLE"
kubectl get nodes -o wide

echo "==> namespace and pipeline RBAC"
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/ci-deployer-rbac.yaml

echo "==> AWS Load Balancer Controller $LBC_CHART_VERSION"
helm repo add eks https://aws.github.io/eks-charts --force-update >/dev/null
helm upgrade --install aws-load-balancer-controller eks/aws-load-balancer-controller \
  --version "$LBC_CHART_VERSION" --namespace kube-system \
  --set clusterName="$CLUSTER" \
  --set region="$REGION" \
  --set vpcId="$VPC_ID" \
  --set serviceAccount.create=true \
  --set serviceAccount.name=aws-load-balancer-controller \
  --wait --timeout 10m

echo "==> kube-prometheus-stack $KPS_CHART_VERSION"
kubectl create namespace monitoring --dry-run=client -o yaml | kubectl apply -f -
if ! kubectl -n monitoring get secret grafana-admin >/dev/null 2>&1; then
  kubectl -n monitoring create secret generic grafana-admin \
    --from-literal=admin-user=admin \
    --from-literal=admin-password="$(openssl rand -base64 24 | tr -d '/+=' | cut -c1-24)"
fi
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts --force-update >/dev/null
helm upgrade --install kube-prometheus-stack prometheus-community/kube-prometheus-stack \
  --version "$KPS_CHART_VERSION" --namespace monitoring \
  -f monitoring/kube-prometheus-stack-values.yaml \
  --wait --timeout 15m

echo
echo "Cluster ready. Next: scripts/configure-github.sh, then push to main (or re-run the pipeline)."
echo "Grafana password: kubectl -n monitoring get secret grafana-admin -o jsonpath='{.data.admin-password}' | base64 -d"
