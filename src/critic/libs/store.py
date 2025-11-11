from __future__ import annotations

import os
import time

import boto3
from boto3.dynamodb.conditions import Key

from critic.libs.ddb import deserializer, serializer


def _ddb_client():
    return boto3.client(
        'dynamodb',
        region_name=os.getenv('AWS_REGION', 'us-east-2'),
        endpoint_url=os.getenv('AWS_ENDPOINT_URL') or None,
    )


def _ddb_resource():
    return boto3.resource(
        'dynamodb',
        region_name=os.getenv('AWS_REGION', 'us-east-2'),
        endpoint_url=os.getenv('AWS_ENDPOINT_URL') or None,
    )


def _table_name(default: str = 'Monitor') -> str:
    return os.getenv('DDB_TABLE', default)


def put_monitor(monitor_dict: dict, table: str | None = None):
    """
    Upsert a monitor. Ensures GSI_PK exists for due scanning.
    """
    table = table or _table_name()
    item = {k: serializer.serialize(v) for k, v in monitor_dict.items()}
    if 'GSI_PK' not in item:
        item['GSI_PK'] = serializer.serialize('DUE_MONITOR')
    _ddb_client().put_item(TableName=table, Item=item)
    



def get_monitor(group_id: str, id_: str, table: str | None = None) -> dict | None:
    table = table or _table_name()
    resp = _ddb_client().get_item(
        TableName=table,
        Key={'group_id': {'S': group_id}, 'id': {'S': id_}},
    )
    if 'Item' not in resp:
        return None
    return {k: deserializer.deserialize(v) for k, v in resp['Item'].items()}


def query_due_monitors(
    now: int | None = None, table: str | None = None, index_name: str = 'NextDueIndex'
) -> list[dict]:
    """
    Key("GSI_PK").eq("DUE_MONITOR") & Key("next_due_at").lte(now)
    """
    now = now or int(time.time())
    table = table or _table_name()
    tbl = _ddb_resource().Table(table)
    resp = tbl.query(
        IndexName=index_name,
        KeyConditionExpression=Key('GSI_PK').eq('DUE_MONITOR') & Key('next_due_at').lte(now),
    )
    return resp.get('Items', [])
