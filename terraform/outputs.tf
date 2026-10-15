output "region" {
  value = var.region
}

output "cluster_name" {
  value = module.eks.cluster_name
}

output "cluster_version" {
  value = module.eks.cluster_version
}

output "cluster_endpoint" {
  value = module.eks.cluster_endpoint
}

output "vpc_id" {
  value = module.vpc.vpc_id
}

output "public_subnet_ids" {
  value = module.vpc.public_subnets
}

output "private_subnet_ids" {
  value = module.vpc.private_subnets
}

output "operator_user_name" {
  description = "IAM user for kubectl/helm; create its access key with scripts/setup-operator-profile.sh."
  value       = aws_iam_user.operator.name
}

output "eks_admin_role_arn" {
  value = aws_iam_role.eks_admin.arn
}

output "github_deploy_role_arn" {
  description = "Set as the AWS_DEPLOY_ROLE_ARN variable in GitHub (scripts/configure-github.sh does it)."
  value       = aws_iam_role.github_deploy.arn
}

output "configure_kubectl" {
  description = "Run after scripts/setup-operator-profile.sh."
  value       = "aws eks update-kubeconfig --region ${var.region} --name ${module.eks.cluster_name} --alias ${module.eks.cluster_name} --profile ${var.project}-operator --role-arn ${aws_iam_role.eks_admin.arn}"
}
