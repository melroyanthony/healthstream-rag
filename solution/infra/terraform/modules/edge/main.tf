# WAF Web ACL — rate limiting and basic protection
# Note: HTTP API Gateway (v2) does not support WAF association directly.
# WAF is deployed as a standalone ACL ready for CloudFront or REST API Gateway.

variable "environment" { type = string }
variable "api_endpoint" { type = string }

resource "aws_wafv2_web_acl" "main" {
  name        = "healthstream-${var.environment}-waf"
  scope       = "REGIONAL"
  description = "Rate limiting and protection for HealthStream RAG API"

  default_action {
    allow {}
  }

  rule {
    name     = "rate-limit-per-ip"
    priority = 1

    action {
      block {}
    }

    statement {
      rate_based_statement {
        limit              = 100
        aggregate_key_type = "IP"
      }
    }

    visibility_config {
      sampled_requests_enabled   = true
      cloudwatch_metrics_enabled = true
      metric_name                = "healthstream-rate-limit"
    }
  }

  rule {
    name     = "aws-managed-common"
    priority = 2

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesCommonRuleSet"
        vendor_name = "AWS"
      }
    }

    visibility_config {
      sampled_requests_enabled   = true
      cloudwatch_metrics_enabled = true
      metric_name                = "healthstream-common-rules"
    }
  }

  visibility_config {
    sampled_requests_enabled   = true
    cloudwatch_metrics_enabled = true
    metric_name                = "healthstream-waf"
  }

  tags = { Name = "healthstream-${var.environment}-waf" }
}

# WAF association with API Gateway would go here when migrating to REST API (v1)
# or fronting with CloudFront. HTTP API v2 does not support direct WAF association.
# For production: CloudFront -> WAF -> API Gateway HTTP API

output "waf_acl_arn" { value = aws_wafv2_web_acl.main.arn }
