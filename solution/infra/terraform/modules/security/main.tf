# KMS, Cognito, IAM — HIPAA security controls

variable "environment" { type = string }
variable "aws_region" { type = string }

data "aws_caller_identity" "current" {}

# KMS CMK for data encryption at rest
resource "aws_kms_key" "healthstream" {
  description             = "HealthStream RAG data encryption key"
  deletion_window_in_days = 30
  enable_key_rotation     = true

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "RootAccountAccess"
        Effect = "Allow"
        Principal = { AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root" }
        Action   = "kms:*"
        Resource = "*"
      },
      {
        Sid    = "CloudTrailEncrypt"
        Effect = "Allow"
        Principal = { Service = "cloudtrail.amazonaws.com" }
        Action = [
          "kms:GenerateDataKey*",
          "kms:DescribeKey",
        ]
        Resource = "*"
        Condition = {
          StringEquals = { "aws:SourceAccount" = data.aws_caller_identity.current.account_id }
        }
      },
      {
        Sid    = "CloudWatchLogsEncrypt"
        Effect = "Allow"
        Principal = { Service = "logs.${var.aws_region}.amazonaws.com" }
        Action = [
          "kms:Encrypt*",
          "kms:Decrypt*",
          "kms:ReEncrypt*",
          "kms:GenerateDataKey*",
          "kms:Describe*",
          "kms:CreateGrant",
        ]
        Resource = "*"
        Condition = {
          ArnLike = {
            "kms:EncryptionContext:aws:logs:arn" = "arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:log-group:*"
          }
        }
      },
      {
        Sid    = "DynamoDBAndS3Encrypt"
        Effect = "Allow"
        Principal = { AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root" }
        Action = [
          "kms:Decrypt",
          "kms:GenerateDataKey*",
          "kms:CreateGrant",
          "kms:DescribeKey",
        ]
        Resource = "*"
        Condition = {
          StringEquals = {
            "kms:ViaService" = [
              "dynamodb.${var.aws_region}.amazonaws.com",
              "s3.${var.aws_region}.amazonaws.com",
            ]
          }
        }
      },
    ]
  })

  tags = { Name = "healthstream-${var.environment}-cmk" }
}

resource "aws_kms_alias" "healthstream" {
  name          = "alias/healthstream-${var.environment}"
  target_key_id = aws_kms_key.healthstream.key_id
}

# Cognito User Pool — JWT authentication with patient_id claim
resource "aws_cognito_user_pool" "patients" {
  name = "healthstream-${var.environment}-patients"

  password_policy {
    minimum_length    = 12
    require_lowercase = true
    require_numbers   = true
    require_symbols   = true
    require_uppercase = true
  }

  # Custom attribute — appears in JWT as "custom:patient_id"
  # Backend must extract via claims["custom:patient_id"]
  schema {
    name                = "patient_id"
    attribute_data_type = "String"
    mutable             = false
    required            = false

    string_attribute_constraints {
      min_length = 1
      max_length = 256
    }
  }

  account_recovery_setting {
    recovery_mechanism {
      name     = "verified_email"
      priority = 1
    }
  }

  tags = { Name = "healthstream-${var.environment}-cognito" }
}

resource "aws_cognito_user_pool_client" "app" {
  name         = "healthstream-${var.environment}-app"
  user_pool_id = aws_cognito_user_pool.patients.id

  explicit_auth_flows = [
    "ALLOW_REFRESH_TOKEN_AUTH",
    "ALLOW_USER_SRP_AUTH",
  ]

  token_validity_units {
    access_token  = "hours"
    id_token      = "hours"
    refresh_token = "days"
  }

  access_token_validity  = 1
  id_token_validity      = 1
  refresh_token_validity = 30
}

# IAM Role for Lambda
resource "aws_iam_role" "lambda_execution" {
  name = "healthstream-${var.environment}-lambda"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy" "lambda_permissions" {
  name = "healthstream-${var.environment}-lambda-permissions"
  role = aws_iam_role.lambda_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "VPCAccess"
        Effect = "Allow"
        Action = [
          "ec2:CreateNetworkInterface",
          "ec2:DescribeNetworkInterfaces",
          "ec2:DeleteNetworkInterface",
          "ec2:AssignPrivateIpAddresses",
          "ec2:UnassignPrivateIpAddresses",
        ]
        Resource = "*"
      },
      {
        Sid    = "BedrockInvoke"
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream",
        ]
        Resource = [
          "arn:aws:bedrock:${var.aws_region}::foundation-model/*",
          "arn:aws:bedrock:${var.aws_region}:${data.aws_caller_identity.current.account_id}:inference-profile/*",
          "arn:aws:bedrock:eu-west-1::inference-profile/*",
          "arn:aws:bedrock:eu-central-1::inference-profile/*",
        ]
      },
      {
        Sid    = "ComprehendMedical"
        Effect = "Allow"
        Action = ["comprehendmedical:DetectPHI"]
        Resource = "*"
      },
      {
        Sid    = "KMSDecrypt"
        Effect = "Allow"
        Action = [
          "kms:Decrypt",
          "kms:GenerateDataKey",
        ]
        Resource = aws_kms_key.healthstream.arn
      },
      {
        Sid    = "CloudWatchLogs"
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
        ]
        Resource = "arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:*"
      },
    ]
  })
}

output "kms_key_arn" { value = aws_kms_key.healthstream.arn }
output "cognito_user_pool_id" { value = aws_cognito_user_pool.patients.id }
output "cognito_user_pool_arn" { value = aws_cognito_user_pool.patients.arn }
output "lambda_execution_role_arn" { value = aws_iam_role.lambda_execution.arn }
output "lambda_execution_role_name" { value = aws_iam_role.lambda_execution.name }
output "cognito_client_id" { value = aws_cognito_user_pool_client.app.id }
