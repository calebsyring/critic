import os

import boto3
from moto import mock_aws
import pytest

from critic.libs.testing import create_tables


def pytest_collection_modifyitems(session, config, items):
    """If any integration tests exist, validate AWS account ID once."""
    has_integration = any(item.get_closest_marker('integration') is not None for item in items)

    if not has_integration:
        return  # nothing to do — unit tests only

    # Check AWS account ID
    try:
        sts = boto3.client('sts')
        account_id = sts.get_caller_identity()['Account']
    except Exception as e:
        pytest.exit(f'Unable to determine AWS account ID: {e}')

    test_account_id = os.environ['CRITIC_TEST_AWS_ACCT_ID']
    if account_id != test_account_id:
        pytest.exit(
            f'Integration tests require AWS test account (expected {test_account_id},'
            f' got {account_id}). You probably forgot to run `env-config test`'
        )


@pytest.fixture(autouse=True)
def moto_for_unit_tests(request):
    """Automatically mock AWS for all tests EXCEPT those marked integration."""
    if request.node.get_closest_marker('integration'):
        # Integration test → do NOT mock AWS
        yield
    else:
        # Unit test → activate moto
        with mock_aws():
            create_tables()
            yield


def pytest_configure(config):
    config.addinivalue_line(
        'markers',
        'integration: use live AWS apis (use -m "not integration" to skip)',
    )
