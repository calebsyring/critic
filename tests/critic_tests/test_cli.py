from click.testing import CliRunner

from critic.cli import cli


# Changed the tests for cli to actually verify that the cli is functioning as intended.
def test_cli_help():
    runner = CliRunner()
    result = runner.invoke(cli, ['--help'])
    assert result.exit_code == 0
    assert 'create-monitors' in result.output
    assert 'delete-monitors' in result.output
