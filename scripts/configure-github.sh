#!/usr/bin/env bash
# Point the GitHub Actions deploy job at the cluster Terraform created:
#   - "production" environment, deployable from main only
#   - repository variables the workflow reads (no secrets are needed: AWS
#     access uses GitHub's OIDC token and the deploy role's trust policy)
#
#   scripts/configure-github.sh            # enable deploys
#   scripts/configure-github.sh --disable  # after terraform destroy
set -euo pipefail

cd "$(dirname "$0")/.."
TF="${TERRAFORM:-terraform}"
REPO="${GITHUB_REPOSITORY:-$(gh repo view --json nameWithOwner -q .nameWithOwner)}"

if [[ "${1:-}" == "--disable" ]]; then
  gh variable set DEPLOY_ENABLED --repo "$REPO" --body false
  echo "Deploys disabled for $REPO (CI still tests, scans and pushes images)."
  exit 0
fi

echo "==> environment 'production' on $REPO (main branch only)"
gh api --method PUT "repos/$REPO/environments/production" --input - >/dev/null <<'JSON'
{ "deployment_branch_policy": { "protected_branches": false, "custom_branch_policies": true } }
JSON
gh api --method POST "repos/$REPO/environments/production/deployment-branch-policies" \
  -f name=main -f type=branch >/dev/null 2>&1 || true # already exists on re-runs

echo "==> repository variables"
gh variable set AWS_REGION --repo "$REPO" --body "$("$TF" -chdir=terraform output -raw region)"
gh variable set EKS_CLUSTER_NAME --repo "$REPO" --body "$("$TF" -chdir=terraform output -raw cluster_name)"
gh variable set AWS_DEPLOY_ROLE_ARN --repo "$REPO" --body "$("$TF" -chdir=terraform output -raw github_deploy_role_arn)"
gh variable set DEPLOY_ENABLED --repo "$REPO" --body true
gh variable list --repo "$REPO"
