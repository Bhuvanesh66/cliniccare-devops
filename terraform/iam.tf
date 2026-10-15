# ---------------------------------------------------------------- people

# A dedicated, low-privilege IAM user for day-to-day work (kubectl, helm,
# read-only console views) instead of the account root user. Its access key
# is created outside Terraform (scripts/setup-operator-profile.sh), so no
# secret is ever written to the Terraform state.
resource "aws_iam_user" "operator" {
  name          = "${local.name}-operator"
  force_destroy = true # lets `terraform destroy` remove the user's access keys too
}

resource "aws_iam_user_policy_attachment" "operator_view_only" {
  user       = aws_iam_user.operator.name
  policy_arn = "arn:aws:iam::aws:policy/job-function/ViewOnlyAccess"
}

data "aws_iam_policy_document" "operator" {
  statement {
    sid       = "AssumeEksAdmin"
    actions   = ["sts:AssumeRole"]
    resources = [aws_iam_role.eks_admin.arn]
  }
  statement {
    sid       = "ConsoleSignInForScreenshots"
    actions   = ["sts:GetFederationToken"]
    resources = ["*"]
  }
  statement {
    sid = "DescribeClusterResources"
    actions = [
      "eks:Describe*",
      "eks:List*",
      "ec2:Describe*",
      "elasticloadbalancing:Describe*",
      "autoscaling:Describe*",
    ]
    resources = ["*"]
  }
}

resource "aws_iam_user_policy" "operator" {
  name   = "assume-eks-admin"
  user   = aws_iam_user.operator.name
  policy = data.aws_iam_policy_document.operator.json
}

# Cluster administrators assume this role (short-lived credentials); its
# Kubernetes permissions come from the EKS access entry in main.tf.
data "aws_iam_policy_document" "eks_admin_trust" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "AWS"
      identifiers = [aws_iam_user.operator.arn]
    }
  }
}

resource "aws_iam_role" "eks_admin" {
  name                 = "${local.name}-eks-admin"
  assume_role_policy   = data.aws_iam_policy_document.eks_admin_trust.json
  max_session_duration = 3600
}

data "aws_iam_policy_document" "describe_cluster" {
  statement {
    actions   = ["eks:DescribeCluster", "eks:ListClusters"]
    resources = ["*"]
  }
}

resource "aws_iam_role_policy" "eks_admin_describe" {
  name   = "describe-cluster"
  role   = aws_iam_role.eks_admin.id
  policy = data.aws_iam_policy_document.describe_cluster.json
}

# ---------------------------------------------------------------- pipeline

# GitHub Actions authenticates with short-lived OIDC tokens: no AWS keys are
# stored in GitHub at all.
resource "aws_iam_openid_connect_provider" "github" {
  count           = var.create_github_oidc_provider ? 1 : 0
  url             = "https://token.actions.githubusercontent.com"
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = []
}

data "aws_iam_openid_connect_provider" "github" {
  count = var.create_github_oidc_provider ? 0 : 1
  url   = "https://token.actions.githubusercontent.com"
}

locals {
  github_oidc_provider_arn = (var.create_github_oidc_provider
    ? aws_iam_openid_connect_provider.github[0].arn
  : data.aws_iam_openid_connect_provider.github[0].arn)
}

# Only jobs running in this repository's "production" environment (which is
# restricted to the main branch) can assume the deploy role.
data "aws_iam_policy_document" "github_deploy_trust" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]
    principals {
      type        = "Federated"
      identifiers = [local.github_oidc_provider_arn]
    }
    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }
    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:sub"
      values   = ["repo:${var.github_repository}:environment:${var.github_environment}"]
    }
  }
}

resource "aws_iam_role" "github_deploy" {
  name                 = "${local.name}-github-deploy"
  assume_role_policy   = data.aws_iam_policy_document.github_deploy_trust.json
  max_session_duration = 3600
}

resource "aws_iam_role_policy" "github_deploy_describe" {
  name   = "describe-cluster"
  role   = aws_iam_role.github_deploy.id
  policy = data.aws_iam_policy_document.describe_cluster.json
}

# ---------------------------------------------------------------- in-cluster add-ons

# EKS Pod Identity: pods of a given service account receive these roles'
# credentials, with no access keys anywhere.
data "aws_iam_policy_document" "pod_identity_trust" {
  statement {
    actions = ["sts:AssumeRole", "sts:TagSession"]
    principals {
      type        = "Service"
      identifiers = ["pods.eks.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "ebs_csi" {
  name               = "${local.name}-ebs-csi"
  assume_role_policy = data.aws_iam_policy_document.pod_identity_trust.json
}

resource "aws_iam_role_policy_attachment" "ebs_csi" {
  role       = aws_iam_role.ebs_csi.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonEBSCSIDriverPolicy"
}

resource "aws_iam_role" "lb_controller" {
  name               = "${local.name}-aws-lb-controller"
  assume_role_policy = data.aws_iam_policy_document.pod_identity_trust.json
}

# Official policy for aws-load-balancer-controller v3.6.0 (docs/install/iam_policy.json).
resource "aws_iam_policy" "lb_controller" {
  name   = "${local.name}-aws-lb-controller"
  policy = file("${path.module}/policies/aws-load-balancer-controller.json")
}

resource "aws_iam_role_policy_attachment" "lb_controller" {
  role       = aws_iam_role.lb_controller.name
  policy_arn = aws_iam_policy.lb_controller.arn
}

resource "aws_eks_pod_identity_association" "lb_controller" {
  cluster_name    = module.eks.cluster_name
  namespace       = "kube-system"
  service_account = "aws-load-balancer-controller"
  role_arn        = aws_iam_role.lb_controller.arn
}
