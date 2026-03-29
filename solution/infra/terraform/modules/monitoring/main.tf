# CloudWatch + CloudTrail — observability and HIPAA audit

variable "environment" { type = string }
variable "lambda_query_name" { type = string }

# CloudTrail — HIPAA audit trail for all API calls
resource "aws_cloudtrail" "audit" {
  name                       = "healthstream-${var.environment}-audit"
  s3_bucket_name             = aws_s3_bucket.audit_logs.id
  include_global_service_events = true
  is_multi_region_trail      = false
  enable_log_file_validation = true

  event_selector {
    read_write_type           = "All"
    include_management_events = true
  }

  tags = { Name = "healthstream-audit-trail" }
}

resource "aws_s3_bucket" "audit_logs" {
  bucket = "healthstream-${var.environment}-audit-logs"
  tags   = { Name = "healthstream-audit-logs" }
}

resource "aws_s3_bucket_policy" "audit_logs" {
  bucket = aws_s3_bucket.audit_logs.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "CloudTrailAclCheck"
        Effect = "Allow"
        Principal = { Service = "cloudtrail.amazonaws.com" }
        Action   = "s3:GetBucketAcl"
        Resource = aws_s3_bucket.audit_logs.arn
      },
      {
        Sid    = "CloudTrailWrite"
        Effect = "Allow"
        Principal = { Service = "cloudtrail.amazonaws.com" }
        Action   = "s3:PutObject"
        Resource = "${aws_s3_bucket.audit_logs.arn}/AWSLogs/*"
        Condition = {
          StringEquals = { "s3:x-amz-acl" = "bucket-owner-full-control" }
        }
      },
    ]
  })
}

resource "aws_s3_bucket_public_access_block" "audit_logs" {
  bucket                  = aws_s3_bucket.audit_logs.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# CloudWatch Alarms — Lambda errors and latency

resource "aws_cloudwatch_metric_alarm" "lambda_errors" {
  alarm_name          = "healthstream-${var.environment}-lambda-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = 300
  statistic           = "Sum"
  threshold           = 10
  alarm_description   = "Lambda query function error rate elevated"

  dimensions = {
    FunctionName = var.lambda_query_name
  }

  tags = { Name = "healthstream-lambda-errors" }
}

resource "aws_cloudwatch_metric_alarm" "lambda_duration" {
  alarm_name          = "healthstream-${var.environment}-lambda-duration"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  metric_name         = "Duration"
  namespace           = "AWS/Lambda"
  period              = 300
  statistic           = "p95"
  threshold           = 10000
  alarm_description   = "Lambda P95 latency exceeds 10s"

  dimensions = {
    FunctionName = var.lambda_query_name
  }

  tags = { Name = "healthstream-lambda-duration" }
}

# CloudWatch Dashboard
resource "aws_cloudwatch_dashboard" "main" {
  dashboard_name = "healthstream-${var.environment}"

  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "metric"
        x      = 0
        y      = 0
        width  = 12
        height = 6
        properties = {
          title   = "Lambda Query - Invocations & Errors"
          metrics = [
            ["AWS/Lambda", "Invocations", "FunctionName", var.lambda_query_name],
            ["AWS/Lambda", "Errors", "FunctionName", var.lambda_query_name],
          ]
          period = 300
          stat   = "Sum"
          region = "eu-west-1"
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 0
        width  = 12
        height = 6
        properties = {
          title   = "Lambda Query - Duration (P50, P95, P99)"
          metrics = [
            ["AWS/Lambda", "Duration", "FunctionName", var.lambda_query_name, { stat = "p50" }],
            ["AWS/Lambda", "Duration", "FunctionName", var.lambda_query_name, { stat = "p95" }],
            ["AWS/Lambda", "Duration", "FunctionName", var.lambda_query_name, { stat = "p99" }],
          ]
          period = 300
          region = "eu-west-1"
        }
      },
    ]
  })
}
