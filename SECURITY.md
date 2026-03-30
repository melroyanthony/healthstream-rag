# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.x     | Yes                |

## Reporting a Vulnerability

If you discover a security vulnerability in HealthStream RAG, please report it responsibly.

**Do NOT open a public GitHub issue for security vulnerabilities.**

Instead, use GitHub's private security reporting:

1. Navigate to the repository's **Security** tab
2. Click **Report a vulnerability**
3. Follow the prompts to create a private security advisory

Include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

You should receive a response within 48 hours. We will work with you to understand the issue and coordinate a fix before any public disclosure.

## Security Design

HealthStream RAG is designed with HIPAA compliance in mind:

- **Patient Isolation**: `patient_id` is injected from JWT claims, never from user input
- **PHI Redaction**: Personally identifiable health information is redacted before embedding
- **Encryption**: KMS encryption at rest for all data stores (S3, DynamoDB, CloudWatch)
- **Encryption in Transit**: TLS 1.2+ enforced on all API endpoints
- **Audit Trail**: CloudTrail logging for all API calls
- **VPC Isolation**: Lambda runs in private subnets with VPC endpoints (no NAT gateway)
- **WAF**: Web ACL provisioned for rate limiting and common attack patterns; enforcement requires an edge distribution (e.g. CloudFront) in front of API Gateway

See [HIPAA Controls](solution/docs/architecture/c4/hipaa-controls.md) for the full control mapping.
