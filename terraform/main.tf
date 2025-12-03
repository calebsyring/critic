terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    profile      = "critic-prod"
    bucket       = "critic-tf-state"
    region       = "us-east-2"
    key          = "terraform/state.tfstate"
    use_lockfile = true
    encrypt      = true
  }
}

# Provider configurations for each account
provider "aws" {
  alias   = "prod"
  profile = "critic-prod"
  region  = "us-east-2"
}

provider "aws" {
  alias   = "qa"
  profile = "critic-qa"
  region  = "us-east-2"
}

provider "aws" {
  alias   = "dev"
  profile = "critic-dev"
  region  = "us-east-2"
}

locals {
  developers = toset(["csyring"])
}
