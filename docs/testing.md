## Integration Testing

### Quickstart

1. Create a mise.local.toml with:
```
[env]
CRITIC_NAMESPACE = "<your-unique-namespace, e.g. csyring>"
CRITIC_SRC = "<path to project root>"
```

2. Then add your namespace to the `developers` list in `terraform/locals.tf`.

3. `terraform plan -out tf.plan` (in terraform/)

4. `terraform apply tf.plan`

5. `env-config test` (in project root)

6. Create a mu-test.toml:

```
project-org = 'Level 12'
image-name = 'critic'

policy_arns = [
    'arn:aws:iam::411307359980:policy/CriticDDBAccessTest-<your-unique-namespace>'
]
```

7. `mu provision && mu deploy`

8. `pytest -m integration`

### Vs. Unit Tests

Integration tests are marked with `@pytest.mark.integration`. They will hit the live API with whatever the active profile is. However, there are checks in place to ensure that tests are not run against resources outside the test account. (See uses of `CRITIC_TEST_AWS_ACCT_ID`)

Any tests not marked integration tests are assumed to be unit tests, and AWS is automatically mocked with [moto](https://github.com/getmoto/moto) for safety. DDB tables are available via moto in unit tests.

### CI

CI runs integration tests via an assumed role. See github_actions.tf for details.

CI has namespaced resources in the test account (e.g. UptimeMonitor-ci) just like devs.
