from moto import mock_aws
import pytest


@pytest.fixture(autouse=True)
def mock_aws_all():
    """Make sure none of these tests are actually hitting AWS."""
    with mock_aws():
        yield
