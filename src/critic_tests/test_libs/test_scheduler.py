from __future__ import annotations

import time

import boto3
import httpx
import respx

from critic.libs.scheduler import run_due_once
from critic.libs.store import put_monitor


def _create_table():
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


@respx.mock
def test_scheduler_runs_due_and_updates():
    """
    Verifies that:
    1. A due monitor (next_due_at <= now) is found by the scheduler.
    2. The check is executed (mocked HTTP OK).
    3. The monitor is updated with 'up' state and new next_due_at.
    """
    _create_table()

    now = int(time.time())
    # Mock a healthy response for the monitor's URL
    respx.get('https://example.com/health').mock(
        return_value=httpx.Response(200, text='OK - healthy')
    )

    # Prepare a monitor item that is due
    monitor = {
        'project_id': 'web-prod',
        'id': '6033aa47-a9f7-4d7f-b7ff-a11ba9b34474',
        'state': 'new',
        'url': 'https://example.com/health',
        'interval': 1,
        'next_due_at': now - 10,  # Due now
        'timeout': 5,
        'assertions': {'status_code': 200, 'body_contains': 'OK'},
        'failures_before_alerting': 1,
        'alert_slack_channels': ['#ops'],
        'alert_emails': ['alerts@example.com'],
        'realert_interval': 600,
        'GSI_PK': 'DUE_MONITOR',
    }

    # Store into mocked DDB (Moto)
    put_monitor(monitor, table='Monitor')

    # Run the scheduler once
    updated_items = run_due_once(table='Monitor')

    # Validate results
    assert len(updated_items) == 1
    updated = updated_items[0]
    assert updated['state'] == 'up'
    assert updated['next_due_at'] > now
    assert updated['GSI_PK'] == 'DUE_MONITOR'
    assert updated['last_status_code'] == 200
