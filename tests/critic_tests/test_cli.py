from click.testing import CliRunner
import pytest

from critic.cli import cli


@pytest.fixture
def invoke():
    def _invoke(*args, **kwargs):
        runner = CliRunner()
        result = runner.invoke(cli, *args, **kwargs)
        return result

    return _invoke


def test_cli(invoke):
    result = invoke(['--help'])
    assert not result.exception
