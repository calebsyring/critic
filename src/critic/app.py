import logging
import os

import click
from flask import Flask
import mu

from critic.monitor_utility import create_monitors, delete_monitors
from critic.tables import UptimeMonitorTable
from critic.tasks import run_due_checks


log = logging.getLogger()

app = Flask(__name__)


@app.route('/')
def hello_world():
    return '<p>Hello, <strong>World</strong>!</p>'


@app.route('/log')
def logs_example():
    log.error('This is an error')
    log.warning('This is a warning')
    log.info('This is an info log')
    log.debug('This is a debug log')
    return 'Logs emitted at debug, info, warning, and error levels'


@app.route('/error')
def error():
    raise RuntimeError('Deliberate runtime error')


@click.group()
def cli():
    pass


def _default_monitor_table_name() -> str:
    # Allow over riding the exact DynamoDB table name if needed.
    # Otherwise use the generic Critic table name.
    return os.environ.get('MONITOR_TABLE_NAME', UptimeMonitorTable.name)


@cli.command('create-monitors')
@click.option('--project-id', required=True)
@click.option('--prefix', default='demo', show_default=True)
@click.option('--count', default=10, type=int, show_default=True)
@click.option('--table-name', default=None)
def create_monitors_cmd(project_id: str, prefix: str, count: int, table_name: str | None):
    # Failsafe added to use default table name if not provided.
    table_name = table_name or _default_monitor_table_name()
    created = create_monitors(
        table_name=table_name,
        project_id=project_id,
        prefix=prefix,
        count=count,
        ddb=None,
    )
    click.echo(f'Created {created} monitors in {table_name}')


@cli.command('delete-monitors')
@click.option('--project-id', required=True)
@click.option('--prefix', required=True)
@click.option('--table-name', default=None)
def delete_monitors_cmd(project_id: str, prefix: str, table_name: str | None):
    table_name = table_name or _default_monitor_table_name()
    deleted = delete_monitors(
        table_name=table_name,
        project_id=project_id,
        prefix=prefix,
        ddb=None,
    )
    click.echo(f'Deleted {deleted} monitors from {table_name}')


# Lambda handler for CLI commands.
class ActionHandler(mu.ActionHandler):
    wsgi_app = app

    @staticmethod
    def cli(event, context):
        action_args = event.get('action-args') or []
        return cli.main(args=action_args, prog_name='critic', standalone_mode=False)
    def run_due_checks(event, context):
        """Triggered by EventBridge rule, invokes `run_due_checks` task."""
        log.info('Invoking run_due_checks')
        run_due_checks.invoke()


lambda_handler = ActionHandler.on_event
