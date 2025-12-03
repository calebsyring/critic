import time
from unittest.mock import patch

import boto3

from critic.app import run_due_checks
from critic.libs.ddb import serializer


@patch('mu.invoke')
def test_run_due_checks(mock_invoke):
    client = boto3.client('dynamodb', region_name='us-east-2')
    client.create_table(
        TableName='Monitor',
        AttributeDefinitions=[
            {'AttributeName': 'project_id', 'AttributeType': 'S'},
            {'AttributeName': 'id', 'AttributeType': 'S'},
            {'AttributeName': 'GSI_PK', 'AttributeType': 'S'},
            {'AttributeName': 'next_due_at', 'AttributeType': 'N'},
        ],
        KeySchema=[
            {'AttributeName': 'project_id', 'KeyType': 'HASH'},
            {'AttributeName': 'id', 'KeyType': 'RANGE'},
        ],
        GlobalSecondaryIndexes=[
            {
                'IndexName': 'NextDueIndex',
                'KeySchema': [
                    {'AttributeName': 'GSI_PK', 'KeyType': 'HASH'},
                    {'AttributeName': 'next_due_at', 'KeyType': 'RANGE'},
                ],
                'Projection': {'ProjectionType': 'ALL'},
            }
        ],
        BillingMode='PAY_PER_REQUEST',
    )

    now = int(time.time())

    items = [
        {'project_id': 'p1', 'id': '1', 'GSI_PK': 'DUE_MONITOR', 'next_due_at': now - 10},
        {'project_id': 'p2', 'id': '2', 'GSI_PK': 'DUE_MONITOR', 'next_due_at': now},
        {'project_id': 'p3', 'id': '3', 'GSI_PK': 'DUE_MONITOR', 'next_due_at': now + 100},
    ]

    for item in items:
        client.put_item(
            TableName='Monitor',
            Item={k: serializer.serialize(v) for k, v in item.items()},
        )

    result = run_due_checks()

    assert result['count'] == 2
    assert mock_invoke.call_count == 2

    called_ids = {call.kwargs['payload']['id'] for call in mock_invoke.call_args_list}
    assert called_ids == {'1', '2'}
