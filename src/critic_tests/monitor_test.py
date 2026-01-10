import boto3
from boto3.dynamodb.conditions import Key
from moto import mock_aws

from critic.monitor_utility import create_monitors, delete_monitors


TABLE_NAME = 'UptimeMonitor'


def _create_test_table():
    ddb = boto3.resource('dynamodb', region_name='us-east-2')
    table = ddb.create_table(
        TableName=TABLE_NAME,
        KeySchema=[
            {'AttributeName': 'project_id', 'KeyType': 'HASH'},  # partition key
            {'AttributeName': 'slug', 'KeyType': 'RANGE'},  # sort key
        ],
        AttributeDefinitions=[
            {'AttributeName': 'project_id', 'AttributeType': 'S'},
            {'AttributeName': 'slug', 'AttributeType': 'S'},
        ],
        BillingMode='PAY_PER_REQUEST',
    )
    table.wait_until_exists()
    return ddb, table


@mock_aws
def test_create_and_delete_monitors():
    ddb, table = _create_test_table()

    project_id = 'project-123'
    prefix = 'stress'

    # Create 10 monitors
    created = create_monitors(
        table_name=TABLE_NAME,
        project_id=project_id,
        prefix=prefix,
        count=10,
        ddb=ddb,
    )
    assert created == 10

    # Verify they exist
    resp = table.query(
        KeyConditionExpression=Key('project_id').eq(project_id),
    )
    assert len(resp['Items']) == 10
    print('Items Before Deletion: \n', resp['Items'])

    # Delete them
    deleted = delete_monitors(
        table_name=TABLE_NAME,
        project_id=project_id,
        prefix=prefix,
        ddb=ddb,
    )
    assert deleted == 10

    # Verify table is empty for that project
    resp_after = table.query(
        KeyConditionExpression=Key('project_id').eq(project_id),
    )
    assert resp_after['Items'] == []
    print('Items After Deletion: \n', resp_after['Items'])


@mock_aws
def test_delete_only_matches_prefix():
    ddb, table = _create_test_table()

    project_id = 'project-123'
    prefix = 'stress'

    # Create two sets. One with the prefix, one without
    create_monitors(TABLE_NAME, project_id, prefix, 5, ddb=ddb)
    create_monitors(TABLE_NAME, project_id, 'other', 3, ddb=ddb)

    resp_before = table.query(
        KeyConditionExpression=Key('project_id').eq(project_id),
    )
    assert len(resp_before['Items']) == 8
    print('Items Before Deletion: \n', resp_before['Items'])

    deleted = delete_monitors(
        table_name=TABLE_NAME,
        project_id=project_id,
        prefix=prefix,
        ddb=ddb,
    )
    assert deleted == 5

    resp_after = table.query(
        KeyConditionExpression=Key('project_id').eq(project_id),
    )
    # Only the other monitors should remain
    remaining_slugs = {item['slug'] for item in resp_after['Items']}
    assert remaining_slugs == {f'other-{i:04d}' for i in range(1, 4)}
    print('Items After Deletion: \n', resp_after['Items'])
