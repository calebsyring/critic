## Integration Testing

### Quickstart

1. Create a mise.local.toml with:
```
[env]
CRITIC_NAMESPACE = "<your-unique-namespace, e.g. csyring>"
```

2. Then add your namespace to the `developers` list in `terraform/locals.tf`.

3. `terraform plan -out tf.plan` (in terraform/)

4. `terraform apply tf.plan`

5. `env-config test` (in project root)

6. Create a mu-test.toml with your desired mu config. You can copy mu-prod.toml, but note that you may need to update any hardcoded account ids.

7. `mu provision && mu deploy`

8. `pytest -m integration`

### CI

CI runs integration tests via an assumed role. See github_actions.tf for details.

CI has namespaced resources in the test account (e.g. UptimeMonitor-ci) just like devs.
