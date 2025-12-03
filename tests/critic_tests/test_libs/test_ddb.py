import boto3
import pytest

from critic.libs.ddb import deserializer, namespace_table, serializer
from critic.models import UptimeMonitor


def clear_table(table_name: str):
    """Delete all items from a DDB table without deleting the table itself."""
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(table_name)

    # Only project the key(s) to reduce read cost
    key_schema = table.key_schema

    # Build safe aliases for key attributes
    expr_attr_names = {}
    projection_parts = []
    for key in key_schema:
        attr = key['AttributeName']
        alias = f'#{attr}'
        expr_attr_names[alias] = attr
        projection_parts.append(alias)
    projection = ', '.join(projection_parts)

    scan_kwargs = {
        'ProjectionExpression': projection,
        'ExpressionAttributeNames': expr_attr_names,
    }

    with table.batch_writer() as batch:
        while True:
            response = table.scan(**scan_kwargs)

            for item in response['Items']:
                batch.delete_item(Key=item)

            if 'LastEvaluatedKey' not in response:
                break

            scan_kwargs['ExclusiveStartKey'] = response['LastEvaluatedKey']


@pytest.fixture
def ddb():
    client = boto3.client('dynamodb')

    yield client

    # Clear all table items after each test for a clean slate.
    TABLES = ('Project', 'UptimeMonitor', 'UptimeLog')
    for t in TABLES:
        clear_table(namespace_table(t))


@pytest.fixture
def ddb_put(ddb):
    def put_item(**kwargs):
        kwargs['TableName'] = namespace_table(kwargs['TableName'])
        return ddb.put_item(**kwargs)

    return put_item


@pytest.fixture
def ddb_get(ddb):
    def get_item(**kwargs):
        kwargs['TableName'] = namespace_table(kwargs['TableName'])
        return ddb.get_item(**kwargs)

    return get_item


@pytest.mark.integration
class TestDDB:
    def test_it(self, ddb_put, ddb_get):
        # Pretend we've received data via the API
        API_DATA = {
            'project_id': '6033aa47-a9f7-4d7f-b7ff-a11ba9b34474',
            'slug': 'my-monitor',
            'url': 'https://example.com/health',
            'frequency_mins': 5,
            'next_due_at': '2025-11-10T20:35:00Z',
            'timeout_secs': 30,
            'assertions': {'status_code': 200, 'body_contains': 'OK'},
            'failures_before_alerting': 2,
            'alert_slack_channels': ['#ops'],
            'alert_emails': ['alerts@example.com'],
            'realert_interval_mins': 60,
        }
        # Double-check data is valid
        UptimeMonitor(**API_DATA)

        # Convert the data to DDB JSON format and store it
        ddb_item = {k: serializer.serialize(v) for k, v in API_DATA.items()}
        ddb_put(TableName='UptimeMonitor', Item=ddb_item)

        # Retrieve the data and convert it back to a standard dict
        ddb_item = ddb_get(
            TableName='UptimeMonitor',
            Key={
                'project_id': {'S': '6033aa47-a9f7-4d7f-b7ff-a11ba9b34474'},
                'slug': {'S': 'my-monitor'},
            },
        )['Item']
        ddb_data = {k: deserializer.deserialize(v) for k, v in ddb_item.items()}

        # Check one of the values to make sure it's what we expect
        assert ddb_data['url'] == 'https://example.com/health'
