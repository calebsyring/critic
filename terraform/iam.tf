# IAM policy for lambda to access DynamoDB tables - prod
resource "aws_iam_policy" "lambda_dynamodb_prod" {
  provider = aws.prod
  name     = "CriticDynamoDBAccess"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:DeleteItem",
          "dynamodb:Query",
          "dynamodb:Scan"
        ]
        Resource = [
          aws_dynamodb_table.project_prod.arn,
          aws_dynamodb_table.uptime_monitor_prod.arn,
          aws_dynamodb_table.uptime_log_prod.arn,
          "${aws_dynamodb_table.uptime_monitor_prod.arn}/index/*"
        ]
      }
    ]
  })
}

# IAM policy for lambda to access DynamoDB tables - qa
resource "aws_iam_policy" "lambda_dynamodb_qa" {
  provider = aws.qa
  name     = "CriticDynamoDBAccess"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:DeleteItem",
          "dynamodb:Query",
          "dynamodb:Scan"
        ]
        Resource = [
          aws_dynamodb_table.project_qa.arn,
          aws_dynamodb_table.uptime_monitor_qa.arn,
          aws_dynamodb_table.uptime_log_qa.arn,
          "${aws_dynamodb_table.uptime_monitor_qa.arn}/index/*"
        ]
      }
    ]
  })
}

# IAM policy for lambda to access DynamoDB tables - dev
resource "aws_iam_policy" "lambda_dynamodb_dev" {
  provider = aws.dev
  name     = "CriticDynamoDBAccess"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:DeleteItem",
          "dynamodb:Query",
          "dynamodb:Scan"
        ]
        Resource = concat(
          [for dev in local.developers : aws_dynamodb_table.project_dev[dev].arn],
          [for dev in local.developers : aws_dynamodb_table.uptime_monitor_dev[dev].arn],
          [for dev in local.developers : aws_dynamodb_table.uptime_log_dev[dev].arn],
          [for dev in local.developers : "${aws_dynamodb_table.uptime_monitor_dev[dev].arn}/index/*"]
        )
      }
    ]
  })
}
