import boto3
from boto3.dynamodb.conditions import Key


def _table(table_name: str, ddb: boto3.resources.base.ServiceResource | None = None):
    return (ddb or boto3.resource('dynamodb')).Table(table_name)


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
            bw.put_item(Item={'project_id': project_id, 'slug': slug})
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
