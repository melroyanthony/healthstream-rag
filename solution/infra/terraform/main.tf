# HealthStream RAG — AWS Infrastructure
# Region: eu-west-1 (Ireland) — S3 Vectors GA, GDPR-friendly

terraform {
  required_version = ">= 1.7"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.70"
    }
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "healthstream-rag"
      Environment = var.environment
      ManagedBy   = "terraform"
      CostCenter  = "resmed-assessment"
    }
  }
}

# --- Variables ---

variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "eu-west-1"
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "demo"
}

variable "vector_backend" {
  description = "Vector store backend: s3vectors or opensearch"
  type        = string
  default     = "s3vectors"

  validation {
    condition     = contains(["s3vectors", "opensearch"], var.vector_backend)
    error_message = "vector_backend must be s3vectors or opensearch"
  }
}

variable "lambda_memory_mb" {
  description = "Lambda function memory in MB"
  type        = number
  default     = 1024
}

variable "lambda_timeout" {
  description = "Lambda function timeout in seconds"
  type        = number
  default     = 30
}

# --- Modules ---

module "networking" {
  source      = "./modules/networking"
  environment = var.environment
  aws_region  = var.aws_region
}

module "security" {
  source      = "./modules/security"
  environment = var.environment
  aws_region  = var.aws_region
}

module "storage" {
  source         = "./modules/storage"
  environment    = var.environment
  vector_backend = var.vector_backend
  kms_key_arn    = module.security.kms_key_arn
}

module "compute" {
  source                    = "./modules/compute"
  environment               = var.environment
  aws_region                = var.aws_region
  lambda_memory_mb          = var.lambda_memory_mb
  lambda_timeout            = var.lambda_timeout
  vpc_id                    = module.networking.vpc_id
  private_subnet_ids        = module.networking.private_subnet_ids
  security_group_id         = module.networking.lambda_security_group_id
  dynamodb_table_arn        = module.storage.dynamodb_table_arn
  s3_bucket_arn             = module.storage.s3_bucket_arn
  kms_key_arn               = module.security.kms_key_arn
  cognito_user_pool_arn     = module.security.cognito_user_pool_arn
  cognito_client_id         = module.security.cognito_client_id
  lambda_execution_role_arn = module.security.lambda_execution_role_arn
}

module "monitoring" {
  source            = "./modules/monitoring"
  environment       = var.environment
  aws_region        = var.aws_region
  kms_key_arn       = module.security.kms_key_arn
  lambda_query_name = module.compute.lambda_query_function_name
}

# --- Outputs ---

output "api_endpoint" {
  description = "API Gateway endpoint URL"
  value       = module.compute.api_endpoint
}

output "cognito_user_pool_id" {
  description = "Cognito User Pool ID"
  value       = module.security.cognito_user_pool_id
}

output "s3_vectors_bucket" {
  description = "S3 Vectors bucket name"
  value       = module.storage.s3_vectors_bucket_name
}
