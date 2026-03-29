# Lambda + API Gateway — serverless compute layer

variable "environment" { type = string }
variable "aws_region" { type = string }
variable "lambda_memory_mb" { type = number }
variable "lambda_timeout" { type = number }
variable "private_subnet_ids" { type = list(string) }
variable "security_group_id" { type = string }
variable "dynamodb_table_arn" { type = string }
variable "s3_bucket_arn" { type = string }
variable "kms_key_arn" { type = string }
variable "cognito_user_pool_arn" { type = string }
variable "cognito_client_id" { type = string }
variable "lambda_execution_role_arn" { type = string }
variable "lambda_execution_role_name" { type = string }
variable "vector_backend" { type = string }
variable "s3_vectors_bucket_name" { type = string }

# Lambda — Query Orchestrator
resource "aws_lambda_function" "query" {
  function_name = "healthstream-${var.environment}-query"
  role          = var.lambda_execution_role_arn
  kms_key_arn   = var.kms_key_arn
  handler       = "app.api.lambda_handler.handler"
  runtime       = "python3.13"
  memory_size   = var.lambda_memory_mb
  timeout       = var.lambda_timeout
  architectures = ["arm64"]

  # Placeholder — actual deployment uses CI/CD pipeline
  filename = "${path.module}/placeholder.zip"

  vpc_config {
    subnet_ids         = var.private_subnet_ids
    security_group_ids = [var.security_group_id]
  }

  environment {
    variables = {
      VECTOR_BACKEND    = var.vector_backend
      LLM_BACKEND       = "bedrock"
      EMBEDDER_BACKEND  = "bedrock"
      MOCK_AUTH         = "true"
      AWS_REGION        = var.aws_region
      S3_VECTORS_BUCKET = var.s3_vectors_bucket_name
    }
  }

  reserved_concurrent_executions = 100

  tags = { Name = "healthstream-query" }
}

# IAM policy for Lambda to access DynamoDB and S3
resource "aws_iam_role_policy" "lambda_data_access" {
  name = "healthstream-${var.environment}-data-access"
  role = var.lambda_execution_role_name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "DynamoDBAccess"
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:Query",
          "dynamodb:Scan",
          "dynamodb:BatchWriteItem",
        ]
        Resource = [
          var.dynamodb_table_arn,
          "${var.dynamodb_table_arn}/index/*",
        ]
      },
      {
        Sid    = "S3VectorsAccess"
        Effect = "Allow"
        Action = [
          "s3vectors:QueryVectors",
          "s3vectors:PutVectors",
          "s3vectors:DeleteVectors",
          "s3vectors:CreateVectorIndex",
          "s3vectors:DescribeVectorIndex",
          "s3vectors:ListVectorIndexes",
        ]
        Resource = "*"
      },
      {
        Sid    = "S3DocumentAccess"
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket",
        ]
        Resource = [
          var.s3_bucket_arn,
          "${var.s3_bucket_arn}/*",
        ]
      },
    ]
  })
}

# API Gateway — REST API
resource "aws_apigatewayv2_api" "main" {
  name          = "healthstream-${var.environment}"
  protocol_type = "HTTP"

  cors_configuration {
    allow_headers = ["Content-Type", "Authorization"]
    allow_methods = ["GET", "POST", "DELETE", "OPTIONS"]
    allow_origins = ["https://myair.resmed.com"]
    max_age       = 3600
  }

  tags = { Name = "healthstream-api" }
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.main.id
  name        = "$default"
  auto_deploy = true

  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.api_access.arn
    format = jsonencode({
      requestId      = "$context.requestId"
      ip             = "$context.identity.sourceIp"
      requestTime    = "$context.requestTime"
      httpMethod     = "$context.httpMethod"
      routeKey       = "$context.routeKey"
      status         = "$context.status"
      protocol       = "$context.protocol"
      responseLength = "$context.responseLength"
      integrationLatency = "$context.integrationLatency"
    })
  }
}

resource "aws_cloudwatch_log_group" "api_access" {
  name              = "/aws/apigateway/healthstream-${var.environment}"
  retention_in_days = 90

  tags = { Name = "healthstream-api-logs" }
}

resource "aws_apigatewayv2_integration" "lambda" {
  api_id                 = aws_apigatewayv2_api.main.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.query.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "default" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "$default"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"

  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

resource "aws_apigatewayv2_authorizer" "cognito" {
  api_id           = aws_apigatewayv2_api.main.id
  authorizer_type  = "JWT"
  identity_sources = ["$request.header.Authorization"]
  name             = "cognito-jwt"

  jwt_configuration {
    audience = [var.cognito_client_id]
    issuer   = "https://cognito-idp.${var.aws_region}.amazonaws.com/${split("/", var.cognito_user_pool_arn)[1]}"
  }
}

resource "aws_lambda_permission" "api_gateway" {
  statement_id  = "AllowAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.query.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.main.execution_arn}/*/*"
}

output "api_endpoint" { value = aws_apigatewayv2_api.main.api_endpoint }
output "lambda_query_function_name" { value = aws_lambda_function.query.function_name }
