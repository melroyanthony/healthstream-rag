# Lambda + API Gateway — serverless compute layer

variable "environment" { type = string }
variable "aws_region" { type = string }
variable "lambda_memory_mb" { type = number }
variable "lambda_timeout" { type = number }
variable "private_subnet_ids" { type = list(string) }
variable "security_group_id" { type = string }
variable "dynamodb_table_arn" { type = string }
variable "dynamodb_sessions_table_arn" { type = string }
variable "s3_bucket_arn" { type = string }
variable "kms_key_arn" { type = string }
variable "cognito_user_pool_arn" { type = string }
variable "cognito_client_id" { type = string }
variable "lambda_execution_role_arn" { type = string }
variable "lambda_execution_role_name" { type = string }
variable "vector_backend" { type = string }
variable "s3_vectors_bucket_name" { type = string }
variable "ecr_image_uri" { type = string }
variable "allowed_origins" {
  description = "List of allowed CORS origins for the API gateway"
  type        = list(string)
}
variable "provisioned_concurrency" {
  description = "Number of provisioned concurrent executions for inference Lambda (0 to disable)"
  type        = number
  default     = 0
}

# Lambda log group — explicit with KMS encryption and retention
resource "aws_cloudwatch_log_group" "lambda_query" {
  name              = "/aws/lambda/healthstream-${var.environment}-query"
  retention_in_days = 90
  kms_key_id        = var.kms_key_arn

  tags = { Name = "healthstream-lambda-query-logs" }
}

# Lambda — Query Orchestrator
resource "aws_lambda_function" "query" {
  function_name = "healthstream-${var.environment}-query"
  role          = var.lambda_execution_role_arn
  kms_key_arn   = var.kms_key_arn
  package_type  = "Image"
  image_uri     = "${var.ecr_image_uri}:latest"
  memory_size   = var.lambda_memory_mb
  timeout       = var.lambda_timeout
  architectures = ["arm64"]
  publish       = true

  lifecycle {
    ignore_changes = [image_uri]
  }

  vpc_config {
    subnet_ids         = var.private_subnet_ids
    security_group_ids = [var.security_group_id]
  }

  environment {
    variables = {
      VECTOR_BACKEND    = var.vector_backend
      LLM_BACKEND       = "bedrock"
      EMBEDDER_BACKEND  = "bedrock"
      MOCK_AUTH         = "false"
      APP_AWS_REGION    = var.aws_region
      S3_VECTORS_BUCKET = var.s3_vectors_bucket_name
    }
  }

  reserved_concurrent_executions = -1  # unreserved (use account default for demo)

  # DLQ applies to async invocations only. API Gateway invokes synchronously,
  # so HTTP failures are returned directly to the caller. DLQ captures failures
  # from async invocation sources (e.g., future SQS/EventBridge triggers).
  dead_letter_config {
    target_arn = aws_sqs_queue.dlq.arn
  }

  tags = { Name = "healthstream-query" }
}

# Dead Letter Queue — captures async invocation failures
resource "aws_sqs_queue" "dlq" {
  name                      = "healthstream-${var.environment}-query-dlq"
  message_retention_seconds = 1209600  # 14 days
  sqs_managed_sse_enabled   = true
  tags                      = { Name = "healthstream-query-dlq" }
}

resource "aws_sqs_queue_policy" "dlq" {
  queue_url = aws_sqs_queue.dlq.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid       = "AllowLambdaServiceToSendMessages"
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action    = "sqs:SendMessage"
      Resource  = aws_sqs_queue.dlq.arn
      Condition = {
        ArnEquals = { "aws:SourceArn" = aws_lambda_function.query.arn }
      }
    }]
  })
}

resource "aws_cloudwatch_metric_alarm" "dlq_messages" {
  alarm_name          = "healthstream-${var.environment}-dlq-messages"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "ApproximateNumberOfMessagesVisible"
  namespace           = "AWS/SQS"
  period              = 60
  statistic           = "Maximum"
  threshold           = 0
  alarm_description   = "Failed Lambda invocations detected in DLQ"
  dimensions = {
    QueueName = aws_sqs_queue.dlq.name
  }
  tags = { Name = "healthstream-dlq-alarm" }
}

# Lambda alias + Provisioned Concurrency (eliminates cold starts)
resource "aws_lambda_alias" "live" {
  name             = "live"
  function_name    = aws_lambda_function.query.function_name
  function_version = aws_lambda_function.query.version

  lifecycle {
    ignore_changes = [function_version]
  }
}

resource "aws_lambda_provisioned_concurrency_config" "inference" {
  count                             = var.provisioned_concurrency > 0 ? 1 : 0
  function_name                     = aws_lambda_function.query.function_name
  qualifier                         = aws_lambda_alias.live.name
  provisioned_concurrent_executions = var.provisioned_concurrency
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
          "dynamodb:BatchWriteItem",
        ]
        Resource = [
          var.dynamodb_table_arn,
          "${var.dynamodb_table_arn}/index/*",
          var.dynamodb_sessions_table_arn,
          "${var.dynamodb_sessions_table_arn}/index/*",
        ]
      },
      {
        Sid    = "S3VectorsAccess"
        Effect = "Allow"
        Action = [
          "s3vectors:CreateVectorBucket",
          "s3vectors:GetVectorBucket",
          "s3vectors:CreateIndex",
          "s3vectors:GetIndex",
          "s3vectors:ListIndexes",
          "s3vectors:DeleteIndex",
          "s3vectors:PutVectors",
          "s3vectors:QueryVectors",
          "s3vectors:DeleteVectors",
          "s3vectors:GetVectors",
          "s3vectors:ListVectors",
        ]
        # S3 Vectors (GA Dec 2025) uses bucket-level ARNs but vector index
        # operations require wildcard — no index-level ARN scoping available yet
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
    allow_origins = var.allowed_origins
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
  kms_key_id        = var.kms_key_arn

  tags = { Name = "healthstream-api-logs" }
}

resource "aws_apigatewayv2_integration" "lambda" {
  api_id                 = aws_apigatewayv2_api.main.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_alias.live.invoke_arn
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
  qualifier     = aws_lambda_alias.live.name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.main.execution_arn}/*/*"
}

output "api_endpoint" { value = aws_apigatewayv2_api.main.api_endpoint }
output "lambda_query_function_name" { value = aws_lambda_function.query.function_name }
