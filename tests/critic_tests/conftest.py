import os

import boto3
from botocore.exceptions import ClientError, NoCredentialsError
import pytest


def get_aws_account_id():
    try:
        sts_client = boto3.client('sts')
        response = sts_client.get_caller_identity()
        return response['Account']
    except (NoCredentialsError, ClientError):
        return None


def pytest_configure(config):
    config.addinivalue_line(
        'markers',
        'integration: use live AWS apis (use -m "not integration" to skip)',
    )

    # Make sure we're working against the test account.
    test_account_id = os.environ['CRITIC_TEST_AWS_ACCT_ID']
    account_id = get_aws_account_id()
    if account_id and account_id != test_account_id:
        pytest.exit(
            f'ERROR: Tests are not running against the expected test AWS account '
            f'(expected {test_account_id}, got {account_id}). You probably forgot to run '
            '`env-config test`.',
            returncode=1,
        )
