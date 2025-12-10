# Project table - prod
resource "aws_dynamodb_table" "project_prod" {
  provider = aws.prod
  name     = "Project"

  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "id"

  attribute {
    name = "id"
    type = "S"
  }
}

# Project table - qa
resource "aws_dynamodb_table" "project_qa" {
  provider = aws.qa
  name     = "Project"

  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "id"

  attribute {
    name = "id"
    type = "S"
  }
}

# Project table - dev (per developer)
resource "aws_dynamodb_table" "project_dev" {
  for_each = local.developers

  provider = aws.dev
  name     = "Project-${each.key}"

  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "id"

  attribute {
    name = "id"
    type = "S"
  }
}

# Project table - test (per developer + ci)
resource "aws_dynamodb_table" "project_test" {
  for_each = local.test_namespaces

  provider = aws.test
  name     = "Project-${each.key}"

  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "id"

  attribute {
    name = "id"
    type = "S"
  }
}

# UptimeMonitor table - prod
resource "aws_dynamodb_table" "uptime_monitor_prod" {
  provider = aws.prod
  name     = "UptimeMonitor"

  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "project_id"
  range_key    = "slug"

  attribute {
    name = "project_id"
    type = "S"
  }

  attribute {
    name = "slug"
    type = "S"
  }

  attribute {
    name = "GSI_PK"
    type = "S"
  }

  attribute {
    name = "next_due_at"
    type = "S"
  }

  global_secondary_index {
    name            = "NextDueIndex"
    hash_key        = "GSI_PK"
    range_key       = "next_due_at"
    projection_type = "ALL"
  }
}

# UptimeMonitor table - qa
resource "aws_dynamodb_table" "uptime_monitor_qa" {
  provider = aws.qa
  name     = "UptimeMonitor"

  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "project_id"
  range_key    = "slug"

  attribute {
    name = "project_id"
    type = "S"
  }

  attribute {
    name = "slug"
    type = "S"
  }

  attribute {
    name = "GSI_PK"
    type = "S"
  }

  attribute {
    name = "next_due_at"
    type = "S"
  }

  global_secondary_index {
    name            = "NextDueIndex"
    hash_key        = "GSI_PK"
    range_key       = "next_due_at"
    projection_type = "ALL"
  }
}

# UptimeMonitor table - dev (per developer)
resource "aws_dynamodb_table" "uptime_monitor_dev" {
  for_each = local.developers

  provider = aws.dev
  name     = "UptimeMonitor-${each.key}"

  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "project_id"
  range_key    = "slug"

  attribute {
    name = "project_id"
    type = "S"
  }

  attribute {
    name = "slug"
    type = "S"
  }

  attribute {
    name = "GSI_PK"
    type = "S"
  }

  attribute {
    name = "next_due_at"
    type = "S"
  }

  global_secondary_index {
    name            = "NextDueIndex"
    hash_key        = "GSI_PK"
    range_key       = "next_due_at"
    projection_type = "ALL"
  }
}

# UptimeMonitor table - test (per developer + ci)
resource "aws_dynamodb_table" "uptime_monitor_test" {
  for_each = local.test_namespaces

  provider = aws.test
  name     = "UptimeMonitor-${each.key}"

  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "project_id"
  range_key    = "slug"

  attribute {
    name = "project_id"
    type = "S"
  }

  attribute {
    name = "slug"
    type = "S"
  }

  attribute {
    name = "GSI_PK"
    type = "S"
  }

  attribute {
    name = "next_due_at"
    type = "S"
  }

  global_secondary_index {
    name            = "NextDueIndex"
    hash_key        = "GSI_PK"
    range_key       = "next_due_at"
    projection_type = "ALL"
  }
}

# UptimeLog table - prod
resource "aws_dynamodb_table" "uptime_log_prod" {
  provider = aws.prod
  name     = "UptimeLog"

  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "monitor_id"
  range_key    = "timestamp"

  attribute {
    name = "monitor_id"
    type = "S"
  }

  attribute {
    name = "timestamp"
    type = "S"
  }
}

# UptimeLog table - qa
resource "aws_dynamodb_table" "uptime_log_qa" {
  provider     = aws.qa
  name         = "UptimeLog"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "monitor_id"
  range_key    = "timestamp"

  attribute {
    name = "monitor_id"
    type = "S"
  }

  attribute {
    name = "timestamp"
    type = "S"
  }
}

# UptimeLog table - dev (per developer)
resource "aws_dynamodb_table" "uptime_log_dev" {
  for_each = local.developers

  provider = aws.dev
  name     = "UptimeLog-${each.key}"

  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "monitor_id"
  range_key    = "timestamp"

  attribute {
    name = "monitor_id"
    type = "S"
  }

  attribute {
    name = "timestamp"
    type = "S"
  }
}

# UptimeLog table - test (per developer + ci)
resource "aws_dynamodb_table" "uptime_log_test" {
  for_each = local.test_namespaces

  provider = aws.test
  name     = "UptimeLog-${each.key}"

  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "monitor_id"
  range_key    = "timestamp"

  attribute {
    name = "monitor_id"
    type = "S"
  }

  attribute {
    name = "timestamp"
    type = "S"
  }
}
