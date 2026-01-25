# Pulled file contents from src/critic_tests/conftest.py due to
# issues creating and discovering resources in moto when running
# tests in critic_tests/monitor_test.py. This file ensures that the
# pytest fixtures defined in critic_tests/pytest_fixtures.py are
# available for all tests, including those in critic_tests/monitor_test.py.
import os

import boto3
from moto import mock_aws
import pytest

import critic.libs.ddb as ddb_module
from critic.libs.testing import clear_tables, create_tables


def pytest_collection_modifyitems(session, config, items):
    # If any integration tests exist, validate AWS account ID once.
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
    # Automatically mock AWS for all tests EXCEPT those marked integration.
    if request.node.get_closest_marker('integration'):
        # Integration test → do NOT mock AWS
        yield
        # Do cleanup afterward
        clear_tables()
    else:
        # Unit test → activate moto
        os.environ.setdefault('AWS_DEFAULT_REGION', 'us-east-1')
        os.environ.setdefault('CRITIC_NAMESPACE', 'test')

        with mock_aws():
            ddb_module._ddb_client = None  # Reset before moto tables are created
            create_tables()
            yield

    # The DDB module is designed to cache the client. When we're testing unit tests and
    # integration tests, this cache needs to be reset so the integration test doesn't get
    # the mocked client and vice versa.
    ddb_module._ddb_client = None


def pytest_configure(config):
    config.addinivalue_line(
        'markers',
        'integration: use live AWS apis (use -m "not integration" to skip)',
    )
