# Infrastructure


## Mu

### Overview
[Mu](https://github.com/level12/mu) manages key infrastructure for lambda-based Python projects. Outside of the lambda, Mu helps with some other adjacent AWS resources (mostly authentication), but other AWS resources are typically outside of Mu's scope. Critic utilizes DynamoDB, for example, so we have to manage that ourselves.

### Granting the Lambda Access
If you want to grant the Mu lambda access to resources outside of Mu's scope, utilize `policy_arns` in `mu.toml`:
https://github.com/level12/mu/blob/eb9d5725f2c27144759fa7163761cc3fa2efc4a1/examples/mu_hello/mu.toml#L9

### Environments
Mu supports the concept of "environments," which are simply namespaced Mu resources within the same account. The Mu environment only affects the resources Mu manages (the lambda and a few other related things).

*Mu environments should not be confused with account-level environments (dev, qa, and prod).* Mu environments are a layer lower, and multiple Mu environments can exist within a single account-level environment.


## Terraform

We use [terraform](https://developer.hashicorp.com/terraform) to manage all AWS resources not managed by Mu. This includes:
- IAM roles
- DynamoDB tables
- S3 bucket for state

See the `terraform/` directory.


## Accounts/Environments

Three sub/member accounts exist under the Level 12 AWS root/management account:
1. `critic-dev` (used for integration tests, etc.)
2. `critic-qa`
3. `critic-prod`

Region: `us-east-2`

State: There is one centralized terraform state in an S3 bucket on the prod account.


## Auth

Subaccounts are created by default with an IAM role called `OrganizationAccountAccessRole`. The management account can use this IAM role to access resources in the member account.

### Example Config
You aws config should look something like this:
```
[profile level12]
...
[profile critic-dev]
source_profile = level12
role_arn = arn:aws:iam::492149691130:role/OrganizationAccountAccessRole
region = us-east-2
[profile critic-qa]
source_profile = level12
role_arn = arn:aws:iam::089600762287:role/OrganizationAccountAccessRole
region = us-east-2
[profile critic-prod]
source_profile = level12
role_arn = arn:aws:iam::024984659360:role/OrganizationAccountAccessRole
region = us-east-2
```

### In the Console
To access a subaccount in the console, go to https://us-east-2.signin.aws.amazon.com/switchrole and enter the applicable account id / role name in the example config above.

## Tables

See architecture.md for details on specific DDB tables.

In the prod and qa environments, only one DDB table should exist for each conceptual table (Project, UptimeMonitor, UptimeLog).

In the dev environments, there is a version of each DDB table for each developer, suffixed with their username. For example, `Project-csyring`.

To add tables for a new developer, add their username to the `developers` list in `terraform/locals.tf`.
