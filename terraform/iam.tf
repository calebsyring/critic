# IAM policy for lambda to access DynamoDB tables - prod
resource "aws_iam_policy" "lambda_dynamodb_prod" {
  provider = aws.prod
  name     = "CriticDDBAccessProd"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "dynamodb:*"
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
  name     = "CriticDDBAccessQA"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "dynamodb:*"
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

# IAM policy for lambda to access DynamoDB tables - dev (per developer)
resource "aws_iam_policy" "lambda_dynamodb_dev" {
  for_each = local.developers

  provider = aws.dev
  name     = "CriticDDBAccessDev-${each.key}"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "dynamodb:*"
        ]
        Resource = [
          aws_dynamodb_table.project_dev[each.key].arn,
          aws_dynamodb_table.uptime_monitor_dev[each.key].arn,
          aws_dynamodb_table.uptime_log_dev[each.key].arn,
          "${aws_dynamodb_table.uptime_monitor_dev[each.key].arn}/index/*"
        ]
      }
    ]
  })
}

# IAM policy for lambda to access DynamoDB tables - test (per namespace)
resource "aws_iam_policy" "lambda_dynamodb_test" {
  for_each = local.test_namespaces

  provider = aws.test
  name     = "CriticDDBAccessTest-${each.key}"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "dynamodb:*"
        ]
        Resource = [
          aws_dynamodb_table.project_test[each.key].arn,
          aws_dynamodb_table.uptime_monitor_test[each.key].arn,
          aws_dynamodb_table.uptime_log_test[each.key].arn,
          "${aws_dynamodb_table.uptime_monitor_test[each.key].arn}/index/*"
        ]
      }
    ]
  })
}

# Admin access group for IUS devs - test
resource "aws_iam_group" "ius_devs_test" {
  provider = aws.test
  name     = "IUSDevs"
}

resource "aws_iam_policy" "mfa_self_manage" {
  provider = aws.test
  name     = "MFASelfManage"

  policy = jsonencode({
    "Version" : "2012-10-17",
    "Statement" : [
      {
        "Sid" : "AllowListActions",
        "Effect" : "Allow",
        "Action" : [
          "iam:ListUsers",
          "iam:ListVirtualMFADevices"
        ],
        "Resource" : "*"
      },
      {
        "Sid" : "AllowUserToCreateVirtualMFADevice",
        "Effect" : "Allow",
        "Action" : [
          "iam:CreateVirtualMFADevice"
        ],
        "Resource" : "arn:aws:iam::*:mfa/*"
      },
      {
        "Sid" : "AllowUserToManageTheirOwnMFA",
        "Effect" : "Allow",
        "Action" : [
          "iam:EnableMFADevice",
          "iam:GetMFADevice",
          "iam:ListMFADevices",
          "iam:ResyncMFADevice"
        ],
        "Resource" : "arn:aws:iam::*:user/$${aws:username}"
      },
      {
        "Sid" : "AllowUserToDeactivateTheirOwnMFAOnlyWhenUsingMFA",
        "Effect" : "Allow",
        "Action" : [
          "iam:DeactivateMFADevice"
        ],
        "Resource" : [
          "arn:aws:iam::*:user/$${aws:username}"
        ],
        "Condition" : {
          "Bool" : {
            "aws:MultiFactorAuthPresent" : "true"
          }
        }
      }
    ]
  })
}

resource "aws_iam_group_policy_attachment" "ius_devs_admin_test" {
  provider   = aws.test
  group      = aws_iam_group.ius_devs_test.name
  policy_arn = "arn:aws:iam::aws:policy/AdministratorAccess"
}

resource "aws_iam_group_policy_attachment" "ius_devs_manage_mfa_test" {
  provider   = aws.test
  group      = aws_iam_group.ius_devs_test.name
  policy_arn = aws_iam_policy.mfa_self_manage.arn
}
