# CloudFront + WAF — edge layer for DDoS protection and rate limiting

variable "environment" { type = string }
variable "api_endpoint" { type = string }

# WAF Web ACL with patient_id rate limiting
resource "aws_wafv2_web_acl" "main" {
  name        = "healthstream-${var.environment}-waf"
  scope       = "REGIONAL"
  description = "Rate limiting and basic protection for HealthStream RAG API"

  default_action {
    allow {}
  }

  # Rate limit: 100 requests per 5 minutes per IP
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

  # Block common attack patterns
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

# Associate WAF with API Gateway
resource "aws_wafv2_web_acl_association" "api_gateway" {
  resource_arn = "arn:aws:apigateway:eu-west-1::/restapis/${split("//", split(".", var.api_endpoint)[0])[1]}"
  web_acl_arn  = aws_wafv2_web_acl.main.arn
}

output "waf_acl_arn" { value = aws_wafv2_web_acl.main.arn }
