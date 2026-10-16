# GitHub Actions -> AWS without stored access keys:
# the deploy job presents a short-lived OIDC token, AWS checks it came from THIS repo's
# "production" environment and returns temporary credentials for this role.
resource "aws_iam_openid_connect_provider" "github" {
  count          = var.github_repository == "" ? 0 : 1
  url            = "https://token.actions.githubusercontent.com"
  client_id_list = ["sts.amazonaws.com"]
}

data "aws_iam_policy_document" "github_trust" {
  count = var.github_repository == "" ? 0 : 1

  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]
    principals {
      type        = "Federated"
      identifiers = [aws_iam_openid_connect_provider.github[0].arn]
    }
    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }
    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:sub"
      values = [
        "repo:${var.github_repository}:environment:${var.github_environment}",
        # immutable subject format (newer repositories): owner and repo carry their numeric IDs
        format("repo:%s@%d/%s@%d:environment:%s",
          split("/", var.github_repository)[0], var.github_repository_ids.owner_id,
          split("/", var.github_repository)[1], var.github_repository_ids.repository_id,
        var.github_environment),
      ]
    }
  }
}

resource "aws_iam_role" "github_deploy" {
  count                = var.github_repository == "" ? 0 : 1
  name                 = "${var.project}-github-deploy"
  assume_role_policy   = data.aws_iam_policy_document.github_trust[0].json
  max_session_duration = 3600
}

# AWS-side permission is only "find the cluster"; what it may do *inside* Kubernetes
# is granted by the EKS access entry in main.tf.
data "aws_iam_policy_document" "github_deploy" {
  statement {
    actions   = ["eks:DescribeCluster"]
    resources = [module.eks.cluster_arn]
  }
}

resource "aws_iam_role_policy" "github_deploy" {
  count  = var.github_repository == "" ? 0 : 1
  name   = "describe-eks-cluster"
  role   = aws_iam_role.github_deploy[0].id
  policy = data.aws_iam_policy_document.github_deploy.json
}
