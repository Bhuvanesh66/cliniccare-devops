data "aws_availability_zones" "available" {
  state = "available"

  filter {
    name   = "opt-in-status"
    values = ["opt-in-not-required"]
  }
}

data "aws_caller_identity" "current" {}

locals {
  name = var.project
  azs  = slice(data.aws_availability_zones.available.names, 0, 2)

  tags = {
    Project     = var.project
    Environment = var.environment
    ManagedBy   = "terraform"
    Repository  = var.github_repository
  }
}

# ---------------------------------------------------------------- network

# Two availability zones, each with a public subnet (load balancers, NAT) and
# a private subnet (worker nodes). One NAT gateway keeps the classroom bill low;
# production would use one per AZ.
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "6.7.3"

  name = "${local.name}-vpc"
  cidr = var.vpc_cidr
  azs  = local.azs

  public_subnets  = [for i, _ in local.azs : cidrsubnet(var.vpc_cidr, 8, 101 + i)]
  private_subnets = [for i, _ in local.azs : cidrsubnet(var.vpc_cidr, 8, 1 + i)]

  enable_nat_gateway   = true
  single_nat_gateway   = true
  enable_dns_hostnames = true
  enable_dns_support   = true

  # Lets the AWS Load Balancer Controller find where to put load balancers.
  public_subnet_tags = {
    "kubernetes.io/role/elb" = 1
  }
  private_subnet_tags = {
    "kubernetes.io/role/internal-elb" = 1
  }
}

# ---------------------------------------------------------------- cluster

module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "21.29.0"

  name               = local.name
  kubernetes_version = var.kubernetes_version

  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnets

  endpoint_public_access       = true
  endpoint_public_access_cidrs = var.cluster_endpoint_public_access_cidrs

  # Cluster access is granted only through EKS access entries (below), never
  # through the legacy aws-auth ConfigMap.
  authentication_mode = "API"
  # The root user cannot be an access entry, so admin access goes to the
  # eks-admin role instead of whoever runs terraform.
  enable_cluster_creator_admin_permissions = false

  # Pod Identity is used instead of IRSA, so no cluster OIDC provider is needed.
  enable_irsa = false

  # Never slip into extended support (6x the control-plane price).
  upgrade_policy = {
    support_type = "STANDARD"
  }

  # Control-plane logs to CloudWatch are off to keep the lab cheap.
  enabled_log_types           = []
  create_cloudwatch_log_group = false

  addons = {
    vpc-cni = {
      before_compute = true
      # Enforce Kubernetes NetworkPolicies (the chart restricts who can reach PostgreSQL).
      configuration_values = jsonencode({ enableNetworkPolicy = "true" })
    }
    eks-pod-identity-agent = {
      before_compute = true
    }
    kube-proxy = {}
    coredns    = {}
    # Dynamic EBS volumes for PersistentVolumeClaims, with a default gp3 StorageClass.
    aws-ebs-csi-driver = {
      configuration_values = jsonencode({ defaultStorageClass = { enabled = true } })
      pod_identity_association = [{
        role_arn        = aws_iam_role.ebs_csi.arn
        service_account = "ebs-csi-controller-sa"
      }]
    }
    # CPU/memory metrics for `kubectl top` and the Horizontal Pod Autoscaler.
    metrics-server = {}
  }

  eks_managed_node_groups = {
    general = {
      ami_type       = "AL2023_x86_64_STANDARD"
      instance_types = var.node_instance_types
      capacity_type  = "ON_DEMAND"

      min_size     = var.node_group_size.min
      desired_size = var.node_group_size.desired
      max_size     = var.node_group_size.max

      labels = {
        workload = "general"
      }
    }
  }

  access_entries = {
    # People: the operator IAM user assumes this role to run kubectl and helm.
    eks_admin = {
      principal_arn = aws_iam_role.eks_admin.arn
      policy_associations = {
        cluster_admin = {
          policy_arn   = "arn:aws:eks::aws:cluster-access-policy/AmazonEKSClusterAdminPolicy"
          access_scope = { type = "cluster" }
        }
      }
    }
    # Pipeline: admin inside the application namespace only. The extra group is
    # bound (k8s/ci-deployer-rbac.yaml) to the Prometheus Operator resources,
    # which the EKS access policies do not cover.
    github_deploy = {
      principal_arn     = aws_iam_role.github_deploy.arn
      kubernetes_groups = ["cliniccare-deployers"]
      policy_associations = {
        namespace_admin = {
          policy_arn = "arn:aws:eks::aws:cluster-access-policy/AmazonEKSAdminPolicy"
          access_scope = {
            type       = "namespace"
            namespaces = [var.app_namespace]
          }
        }
      }
    }
  }
}
