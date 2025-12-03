## Integration Testing Quickstart

1. Create a mise.local.toml with:
```
[env]
CRITIC_NAMESPACE = "<your-unique-namespace, e.g. csyring>"
```

2. Then add your namespace to the `developers` list in `terraform/locals.tf`.

3. `terraform plan -out tf.plan` (in terraform/)

4. `terraform apply tf.plan`

5. `env-config test` (in project root)

6. `pytest -m integration`

TODO: add and explain how CI runs integration tests
- https://github.com/level12/mu/blob/eb9d5725f2c27144759fa7163761cc3fa2efc4a1/.github/workflows/nox.yaml#L39C1-L43C32
- https://aws.amazon.com/blogs/security/use-iam-roles-to-connect-github-actions-to-actions-in-aws/
