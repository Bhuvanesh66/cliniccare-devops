variable "region" {
  description = "AWS region for every resource."
  type        = string
  default     = "ap-south-1"
}

variable "project" {
  description = "Name prefix for resources (VPC, EKS cluster, IAM roles)."
  type        = string
  default     = "cliniccare"
}

variable "environment" {
  description = "Environment tag value."
  type        = string
  default     = "dev"
}

variable "vpc_cidr" {
  description = "Address range of the VPC; split into 2 public and 2 private subnets."
  type        = string
  default     = "10.20.0.0/16"
}

variable "kubernetes_version" {
  description = "EKS Kubernetes version. Keep it in standard support to avoid extended-support pricing."
  type        = string
  default     = "1.36"
}

variable "node_instance_types" {
  description = "EC2 instance types for the managed node group."
  type        = list(string)
  default     = ["t3.medium"]
}

variable "node_group_size" {
  description = "Managed node group size. t3.medium fits 17 pods per node."
  type = object({
    min     = number
    desired = number
    max     = number
  })
  default = {
    min     = 2
    desired = 3
    max     = 4
  }
}

variable "cluster_endpoint_public_access_cidrs" {
  description = "Networks allowed to reach the public Kubernetes API endpoint (GitHub-hosted runners need it open)."
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "github_repository" {
  description = "owner/name of the GitHub repository whose pipeline may deploy to the cluster."
  type        = string
  default     = "Bhuvanesh66/cliniccare-devops"
}

variable "github_environment" {
  description = "GitHub Actions environment the deploy job runs in; only that job can assume the deploy role."
  type        = string
  default     = "production"
}

variable "create_github_oidc_provider" {
  description = "Create the GitHub Actions OIDC provider. Set false if the account already has one."
  type        = bool
  default     = true
}

variable "app_namespace" {
  description = "Kubernetes namespace the pipeline deploys ClinicCare into."
  type        = string
  default     = "cliniccare"
}
