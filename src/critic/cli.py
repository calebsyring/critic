import os
from uuid import UUID

import click

from critic.models import UptimeMonitorModel
from critic.tables import ProjectTable, UptimeMonitorTable


@click.group()
def cli():
    pass


@cli.command()
@click.argument('project_id', type=click.UUID)
@click.argument('count', type=int)
def put_fake_monitors(project_id: UUID, count: int):
    """
    Required arguments: project_id, count

    1. Creates project if it doesn't already exist

    2. Puts `count` number of "fake" monitors into the project
    """
    if os.environ.get('AWS_PROFILE') != 'critic-qa':
        raise Exception('This command should only be run in the critic-qa account')

    # Create project if it doesn't exist
    existing_project = ProjectTable.get(project_id)
    if not existing_project:
        click.echo(f'Creating project {project_id}...')
        ProjectTable.put({'id': project_id, 'name': 'FAKE'})
    else:
        click.echo(f'Project {project_id} already exists')

    # Create fake monitors
    click.echo(f'Creating {count} fake monitors...')
    for i in range(count):
        monitor = UptimeMonitorModel(
            project_id=project_id,
            slug=str(i),
            url='https://google.com',
        )
        UptimeMonitorTable.put(monitor)
        click.echo(f'  Put monitor: {project_id}/{i}')

    click.echo(f'Successfully created {count} monitors in project {project_id}')


@cli.command()
@click.argument('project_id', type=click.UUID)
def del_fake_monitors(project_id: UUID):
    """
    Required arguments: project_id

    Deletes `count` number of "fake" monitors from the project
    """
    if os.environ.get('AWS_PROFILE') != 'critic-qa':
        raise Exception('This command should only be run in the critic-qa account')

    monitors = UptimeMonitorTable.query(project_id)

    click.echo(f'Deleting {len(monitors)} monitors from project {project_id}...')
    for m in monitors:
        UptimeMonitorTable.delete(project_id, m.slug)
        click.echo(f'  Deleted monitor: {project_id}/{m.slug}')

    click.echo(f'Successfully deleted {len(monitors)} monitors from project {project_id}')


if __name__ == '__main__':
    # Allows running CLI commands directly.
    cli()
