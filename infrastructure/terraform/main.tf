# ─────────────────────────────────────────────
# RIPPAA AI Data Platform — AWS Infrastructure
# ─────────────────────────────────────────────
# Terraform configuration for deploying to AWS.
# Uses modular structure for maintainability.

terraform {
  required_version = ">= 1.7.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.70"
    }
  }

  # TODO: Configure S3 backend for remote state
  # backend "s3" {
  #   bucket = "rippaa-terraform-state"
  #   key    = "platform/terraform.tfstate"
  #   region = "ap-southeast-2"
  # }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "rippaa-ai-data-platform"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}

# ── Variables ────────────────────────────────

variable "aws_region" {
  description = "AWS region for all resources"
  type        = string
  default     = "ap-southeast-2"
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "dev"
}

# ── Modules (to be implemented) ──────────────

# module "networking" {
#   source      = "./modules/networking"
#   environment = var.environment
# }

# module "s3" {
#   source      = "./modules/s3"
#   environment = var.environment
# }

# module "rds" {
#   source      = "./modules/rds"
#   environment = var.environment
# }

# module "kafka" {
#   source      = "./modules/kafka"
#   environment = var.environment
# }

# module "ecs" {
#   source      = "./modules/ecs"
#   environment = var.environment
# }
