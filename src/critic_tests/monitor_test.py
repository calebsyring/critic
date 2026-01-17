import boto3
from boto3.dynamodb.conditions import Key
from moto import mock_aws

from critic.monitor_utility import create_monitors, delete_monitors
from critic.tables import UptimeMonitorTable


def _create_test_table(ddb):
    # Create a DynamoDB table.
    table = ddb.create_table(
        TableName=UptimeMonitorTable.name,
        KeySchema=[
            {'AttributeName': UptimeMonitorTable.partition_key, 'KeyType': 'HASH'},
            {'AttributeName': UptimeMonitorTable.sort_key, 'KeyType': 'RANGE'},
        ],
        AttributeDefinitions=[
            {'AttributeName': UptimeMonitorTable.partition_key, 'AttributeType': 'S'},
            {'AttributeName': UptimeMonitorTable.sort_key, 'AttributeType': 'S'},
        ],
        BillingMode='PAY_PER_REQUEST',
    )
    table.wait_until_exists()
    return table


@mock_aws
def test_create_and_delete_monitors():
    # Test creating and deleting monitors in DynamoDB.
    ddb = boto3.resource('dynamodb', region_name='us-east-1')
    table = _create_test_table(ddb)

    project_id = '00000000-0000-0000-0000-000000000001'
    prefix = 'stress'

    created = create_monitors(
        table_name=table.name,
        project_id=project_id,
        prefix=prefix,
        count=10,
        ddb=ddb,
    )
    assert created == 10

    resp = table.query(KeyConditionExpression=Key('project_id').eq(project_id))
    assert len(resp['Items']) == 10

    deleted = delete_monitors(
        table_name=table.name,
        project_id=project_id,
        prefix=prefix,
        ddb=ddb,
    )
    assert deleted == 10

    resp_after = table.query(KeyConditionExpression=Key('project_id').eq(project_id))
    assert resp_after['Items'] == []


@mock_aws
def test_delete_only_matches_prefix():
    # Test that delete_monitors only deletes items matching the given prefix.
    ddb = boto3.resource('dynamodb', region_name='us-east-1')
    table = _create_test_table(ddb)

    project_id = '00000000-0000-0000-0000-000000000001'
    prefix = 'stress'

    create_monitors(table.name, project_id, prefix, 5, ddb=ddb)
    create_monitors(table.name, project_id, 'other', 3, ddb=ddb)

    resp_before = table.query(KeyConditionExpression=Key('project_id').eq(project_id))
    assert len(resp_before['Items']) == 8

    deleted = delete_monitors(table.name, project_id, prefix, ddb=ddb)
    assert deleted == 5

    resp_after = table.query(KeyConditionExpression=Key('project_id').eq(project_id))
    remaining_slugs = {item['slug'] for item in resp_after['Items']}
    assert remaining_slugs == {f'other-{i:04d}' for i in range(1, 4)}
