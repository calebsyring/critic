import time
from uuid import uuid4

import boto3
from boto3.dynamodb.conditions import Key
import pytest

from critic.libs.testing import create_uptime_monitor_table


# make sure db is working properly
def test_create_monitor_table():

    create_uptime_monitor_table()

    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('Monitor')
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
    assert items[0]['state'] == 'new'
    assert items[0]['url'] == 'google.com'
    assert items[0]['next_due_at'] == now
    assert items[0]['timeout'] == 5


def test_remove_from_monitor_table():
    # reused code, may need to be refactored? Maybe setup time, create table and return resource as global
    create_uptime_monitor_table()
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('Monitor')
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
    )

    table.delete_item(Key={'project_id': random_uuid_str, 'slug': 'test_slug'})
    monitor_info = table.query(KeyConditionExpression=Key('project_id').eq(random_uuid_str))
    items = monitor_info['Items']
    assert len(items) == 0
