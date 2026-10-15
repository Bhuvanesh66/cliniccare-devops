#!/usr/bin/env bash
# Create an access key for the Terraform-managed operator IAM user and store
# it as the AWS CLI profile "cliniccare-operator". Run once after
# `terraform apply`, with administrator credentials (e.g. after `aws login`).
#
# The key lives only in ~/.aws/credentials; it is never committed or put in
# Terraform state. `terraform destroy` deletes the user and its keys.
set -euo pipefail

USER_NAME="${OPERATOR_USER:-cliniccare-operator}"
PROFILE="${OPERATOR_PROFILE:-cliniccare-operator}"
REGION="${AWS_REGION:-ap-south-1}"
export AWS_PAGER=""

if aws sts get-caller-identity --profile "$PROFILE" --query Arn --output text 2>/dev/null | grep -q ":user/$USER_NAME$"; then
  echo "Profile $PROFILE already works for $USER_NAME - nothing to do."
  exit 0
fi

# IAM allows two keys per user; remove stale ones so a new key can be created.
for key in $(aws iam list-access-keys --user-name "$USER_NAME" --query 'AccessKeyMetadata[].AccessKeyId' --output text); do
  echo "Deleting stale access key $key"
  aws iam delete-access-key --user-name "$USER_NAME" --access-key-id "$key"
done

read -r key_id secret < <(aws iam create-access-key --user-name "$USER_NAME" \
  --query 'AccessKey.[AccessKeyId,SecretAccessKey]' --output text)

aws configure set aws_access_key_id "$key_id" --profile "$PROFILE"
aws configure set aws_secret_access_key "$secret" --profile "$PROFILE"
aws configure set region "$REGION" --profile "$PROFILE"
unset secret

# New IAM keys take a few seconds to become usable.
for _ in $(seq 1 20); do
  if arn=$(aws sts get-caller-identity --profile "$PROFILE" --query Arn --output text 2>/dev/null); then
    echo "Profile $PROFILE is ready: $arn"
    exit 0
  fi
  sleep 3
done
echo "The new key did not become active in time; re-run this script." >&2
exit 1
