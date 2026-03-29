# S3 Vectors, DynamoDB, S3 — data storage layer

variable "environment" { type = string }
variable "vector_backend" { type = string }
variable "kms_key_arn" { type = string }

data "aws_caller_identity" "current" {}

# S3 Vectors bucket (primary vector store) — only when vector_backend = s3vectors
resource "aws_s3_bucket" "vectors" {
  count  = var.vector_backend == "s3vectors" ? 1 : 0
  bucket = "healthstream-${var.environment}-vectors-${data.aws_caller_identity.current.account_id}"

  tags = { Name = "healthstream-vectors" }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "vectors" {
  count  = var.vector_backend == "s3vectors" ? 1 : 0
  bucket = aws_s3_bucket.vectors[0].id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = var.kms_key_arn
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_versioning" "vectors" {
  count  = var.vector_backend == "s3vectors" ? 1 : 0
  bucket = aws_s3_bucket.vectors[0].id
  versioning_configuration { status = "Enabled" }
}

resource "aws_s3_bucket_public_access_block" "vectors" {
  count                   = var.vector_backend == "s3vectors" ? 1 : 0
  bucket                  = aws_s3_bucket.vectors[0].id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# S3 bucket for raw encrypted health records
resource "aws_s3_bucket" "documents" {
  bucket = "healthstream-${var.environment}-documents-${data.aws_caller_identity.current.account_id}"

  tags = { Name = "healthstream-documents" }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "documents" {
  bucket = aws_s3_bucket.documents.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = var.kms_key_arn
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_versioning" "documents" {
  bucket = aws_s3_bucket.documents.id
  versioning_configuration { status = "Enabled" }
}

resource "aws_s3_bucket_public_access_block" "documents" {
  bucket                  = aws_s3_bucket.documents.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# DynamoDB — patient documents, sessions, metadata, BM25 corpus
resource "aws_dynamodb_table" "patient_documents" {
  name         = "healthstream-${var.environment}-patient-documents"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "patient_id"
  range_key    = "chunk_id"

  attribute {
    name = "patient_id"
    type = "S"
  }

  attribute {
    name = "chunk_id"
    type = "S"
  }

  attribute {
    name = "source_type"
    type = "S"
  }

  global_secondary_index {
    name            = "source-type-index"
    hash_key        = "patient_id"
    range_key       = "source_type"
    projection_type = "ALL"
  }

  point_in_time_recovery { enabled = true }

  server_side_encryption {
    enabled     = true
    kms_key_arn = var.kms_key_arn
  }

  tags = { Name = "healthstream-patient-documents" }
}

resource "aws_dynamodb_table" "sessions" {
  name         = "healthstream-${var.environment}-sessions"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "patient_id"
  range_key    = "timestamp"

  attribute {
    name = "patient_id"
    type = "S"
  }

  attribute {
    name = "timestamp"
    type = "S"
  }

  point_in_time_recovery { enabled = true }

  server_side_encryption {
    enabled     = true
    kms_key_arn = var.kms_key_arn
  }

  ttl {
    attribute_name = "expires_at"
    enabled        = true
  }

  tags = { Name = "healthstream-sessions" }
}

output "dynamodb_table_arn" { value = aws_dynamodb_table.patient_documents.arn }
output "s3_bucket_arn" { value = aws_s3_bucket.documents.arn }
output "s3_vectors_bucket_name" { value = var.vector_backend == "s3vectors" ? aws_s3_bucket.vectors[0].bucket : "" }
