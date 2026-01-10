import boto3
from boto3.dynamodb.conditions import Key

from critic.libs.ddb import floats_to_decimals
from critic.models import UptimeMonitorModel


def _table(table_name: str, ddb: boto3.resources.base.ServiceResource | None = None):
    return (ddb or boto3.resource('dynamodb')).Table(table_name)


def _monitor_item(project_id: str, slug: str) -> dict:
    # Build monitor data that passes UptimeMonitorModel validation.
    inst = UptimeMonitorModel(
        project_id=project_id,
        slug=slug,
        url='https://www.google.com',
        frequency_mins=5,
        next_due_at='2025-11-10T20:35:00Z',
        timeout_secs=30,
        assertions={'status_code': 200},
        failures_before_alerting=2,
        alert_slack_channels=[],
        alert_emails=[],
        realert_interval_mins=60,
    )

    # Resource API expects plain python types (NOT DynamoDB AttributeValue format).
    plain = inst.model_dump(mode='json', exclude_none=True)
    return floats_to_decimals(plain)


def create_monitors(
    table_name: str,
    project_id: str,
    prefix: str,
    count: int,
    ddb: boto3.resources.base.ServiceResource | None = None,
) -> int:
    t = _table(table_name, ddb)

    with t.batch_writer() as bw:
        for i in range(1, count + 1):
            slug = f'{prefix}-{i:04d}'
            bw.put_item(Item=_monitor_item(project_id=project_id, slug=slug))

    return count


def delete_monitors(
    table_name: str,
    project_id: str,
    prefix: str,
    ddb: boto3.resources.base.ServiceResource | None = None,
) -> int:
    t = _table(table_name, ddb)
    resp = t.query(
        KeyConditionExpression=Key('project_id').eq(project_id),
        ProjectionExpression='project_id, slug',
    )
    items = resp.get('Items', [])
    to_delete = [item for item in items if item['slug'].startswith(prefix)]

    with t.batch_writer() as bw:
        for item in to_delete:
            bw.delete_item(Key={'project_id': item['project_id'], 'slug': item['slug']})

    return len(to_delete)
