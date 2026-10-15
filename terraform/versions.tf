terraform {
  required_version = ">= 1.10.0, < 2.0.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 6.59, < 7.0"
    }
  }

  # State is kept locally (git-ignored). For a team, use the S3 backend with
  # state locking instead, e.g.:
  # backend "s3" {
  #   bucket       = "<state-bucket>"
  #   key          = "cliniccare/terraform.tfstate"
  #   region       = "ap-south-1"
  #   use_lockfile = true
  # }
}

provider "aws" {
  region = var.region

  # Every resource Terraform creates carries these tags, so the whole
  # project can be found (and its cost tracked) in the AWS console.
  default_tags {
    tags = local.tags
  }
}
