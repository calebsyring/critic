import time
from uuid import uuid4

import boto3
from boto3.dynamodb.conditions import Key
import pytest


def create_monitor_table():
    client = boto3.client('dynamodb', region_name='us-east-2')
    client.create_table(
        TableName='Monitor',
        AttributeDefinitions=[
            {'AttributeName': 'project_id', 'AttributeType': 'S'},
            {'AttributeName': 'slug', 'AttributeType': 'S'},
            {'AttributeName': 'GSI_PK', 'AttributeType': 'S'},
            {'AttributeName': 'next_due_at', 'AttributeType': 'N'},
        ],
        KeySchema=[
            {'AttributeName': 'project_id', 'KeyType': 'HASH'},
            {'AttributeName': 'slug', 'KeyType': 'RANGE'},
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

    dynamodb = boto3.resource('dynamodb')
    return dynamodb.Table('Monitor')


# make sure db is working properly
def test_create_monitor_table():
    table = create_monitor_table()

    random_uuid_str = str(uuid4())
    now = int(time.time())
    table.put_item(
        Item={
            'project_id': random_uuid_str,
            'slug': 'test_slug',
            'GSI_PK': 'MONITOR',
            'state': 'new',
            'url': 'google.com',
            'next_due_at': now,
            'timeout': 5,
        }
    )  # using the resource instead of the client doesnt require serialization

    monitor_info = table.query(KeyConditionExpression=Key('project_id').eq(random_uuid_str))
    items = monitor_info['Items']
    print('here is the info')
    if items is not None:
        print(items)
    assert items[0]['project_id'] == random_uuid_str
    assert items[0]['slug'] == 'test_slug'
