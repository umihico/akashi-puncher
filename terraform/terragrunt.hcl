locals {
  envyml          = yamldecode(file("../env.yml"))
  backend_path = "terraform-backend-${run_cmd("aws", "sts", "get-caller-identity", "--profile", "${local.envyml.profile_name}", "--query", "Account", "--output", "text")}-${local.envyml.project_name}"
}
remote_state {
  backend = "s3"
  generate = {
    path              = "remote_state.tf"
    if_exists         = "overwrite"
    disable_signature = true
  }
  config = {
    profile              = local.envyml.profile_name
    region               = local.envyml.project_region
    bucket               = local.backend_path
    key                  = "${path_relative_to_include()}/terraform.tfstate"
    encrypt              = true
    workspace_key_prefix = "workspaces"
    dynamodb_table       = local.backend_path
  }
}

generate "provider" {
  path              = "provider.tf"
  if_exists         = "overwrite"
  disable_signature = true
  contents          = <<EOF
provider "aws" {
  profile = "${local.envyml.profile_name}"
  region  = "${local.envyml.project_region}"
}

provider "aws" {
  alias   = "use1"
  region  = "us-east-1"
  profile = "${local.envyml.profile_name}"
}
EOF
}
