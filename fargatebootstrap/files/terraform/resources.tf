provider "aws" {
  region     = "${var.region}"
  version = "= 2.7"
}

provider "github" {
  token        = "${var.github_provider_token}"
  organization = "${var.organization}"
}

data "aws_kms_alias" "s3kmskey" {
  name = "alias/aws/s3"
}
