resource "aws_iam_openid_connect_provider" "github" {
  provider       = aws.test
  url            = "https://token.actions.githubusercontent.com"
  client_id_list = ["sts.amazonaws.com"]
}

resource "aws_iam_role" "github_actions_role" {
  provider = aws.test
  name     = "github-actions-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Federated = aws_iam_openid_connect_provider.github.arn
        }
        Action = "sts:AssumeRoleWithWebIdentity"
        Condition = {
          StringLike = {
            "token.actions.githubusercontent.com:sub" = "repo:calebsyring/critic:*"
          }
        }
      }
    ]
  })
}


resource "aws_iam_role_policy_attachment" "github_actions_attach_ddb" {
  provider   = aws.test
  role       = aws_iam_role.github_actions_role.name
  policy_arn = aws_iam_policy.lambda_dynamodb_test["ci"].arn
}
