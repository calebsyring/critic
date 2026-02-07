from collections.abc import Callable
import threading

import boto3
from polyfactory.factories.pydantic_factory import ModelFactory
from pydantic import BaseModel

from critic.libs.ddb import Table, get_client
from critic.models import UptimeMonitorModel
from critic.tables import UptimeMonitorTable


def create_tables():
    client = get_client()
    client.create_table(
        TableName=Table.namespace('Project'),
        AttributeDefinitions=[
            {'AttributeName': 'id', 'AttributeType': 'S'},
        ],
        KeySchema=[
            {'AttributeName': 'id', 'KeyType': 'HASH'},
        ],
        BillingMode='PAY_PER_REQUEST',
    )

    client.create_table(
        TableName=Table.namespace('UptimeMonitor'),
        AttributeDefinitions=[
            # Key attributes
            {'AttributeName': 'project_id', 'AttributeType': 'S'},
            {'AttributeName': 'slug', 'AttributeType': 'S'},
            # GSI attributes
            {'AttributeName': 'GSI_PK', 'AttributeType': 'S'},
            {'AttributeName': 'next_due_at', 'AttributeType': 'S'},
        ],
        KeySchema=[
            {'AttributeName': 'project_id', 'KeyType': 'HASH'},  # Partition key
            {'AttributeName': 'slug', 'KeyType': 'RANGE'},  # Sort key
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

    client.create_table(
        TableName=Table.namespace('UptimeLog'),
        AttributeDefinitions=[
            {'AttributeName': 'monitor_id', 'AttributeType': 'S'},
            {'AttributeName': 'timestamp', 'AttributeType': 'S'},
        ],
        KeySchema=[
            {'AttributeName': 'monitor_id', 'KeyType': 'HASH'},
            {'AttributeName': 'timestamp', 'KeyType': 'RANGE'},
        ],
        BillingMode='PAY_PER_REQUEST',
    )


def _clear_table(table_name: str):
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


def clear_tables():
    for table_name in [Table.namespace(t) for t in ('Project', 'UptimeMonitor', 'UptimeLog')]:
        _clear_table(table_name)


def race(func: Callable, *args, **kwargs):
    """
    Runs the given function twice at the same time. Useful for testing race conditions.
    """
    # Barrier forces threads to start together
    barrier = threading.Barrier(2)

    def worker():
        barrier.wait()
        func(*args, **kwargs)

    t1 = threading.Thread(target=worker)
    t2 = threading.Thread(target=worker)

    t1.start()
    t2.start()

    t1.join()
    t2.join()


class PutMixin:
    __table__: type[Table]

    @classmethod
    def put(cls, **kwargs) -> BaseModel:
        item = cls.build(**kwargs)
        cls.__table__.put(item)
        return item


class UptimeMonitorFactory(PutMixin, ModelFactory):
    __model__ = UptimeMonitorModel
    __table__ = UptimeMonitorTable
    __use_defaults__ = True
