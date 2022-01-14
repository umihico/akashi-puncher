locals {
  envyml = yamldecode(file("../env.yml"))
}

resource "aws_iam_role" "user_role" {
  name = "${local.envyml.project_name}-slack-user-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Sid    = ""
        Principal = {
          Service = "chatbot.amazonaws.com"
        }
      },
    ]
  })
  inline_policy {
    name = "${local.envyml.project_name}-slack-user-role-inline-policy"
    policy = jsonencode({
      Version = "2012-10-17"
      Statement = [
        {
          Action   = ["*"]
          Effect   = "Allow"
          Resource = "*"
        },
      ]
    })
  }
}

resource "aws_iam_role" "chatbot_role" {
  name = "${local.envyml.project_name}-chatbot-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Sid    = ""
        Principal = {
          Service = "chatbot.amazonaws.com"
        }
      },
    ]
  })
}

resource "aws_cloudformation_stack" "network" {
  name          = local.envyml.project_name
  capabilities  = ["CAPABILITY_NAMED_IAM"]
  template_body = <<-STACK
  Resources:
    ChatbotConfiguration:
      Type: AWS::Chatbot::SlackChannelConfiguration
      Properties:
        ConfigurationName: "${local.envyml.project_name}"
        IamRoleArn: "${aws_iam_role.chatbot_role.arn}"
        SlackChannelId: "${local.envyml.slack_channel_id}"
        SlackWorkspaceId: "${local.envyml.slack_workspace_id}"
  STACK
}
