import os

import click

from critic.monitor_utility import create_monitors, delete_monitors
from critic.tables import UptimeMonitorTable


@click.group()
def cli():
    pass


def _default_monitor_table_name() -> str:
    # Allow overriding the exact DynamoDB table name if needed.
    # Otherwise use the generic Critic table name.
    return os.environ.get('MONITOR_TABLE_NAME', UptimeMonitorTable.name())


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


if __name__ == '__main__':
    # Allows running CLI commands directly.
    cli()
