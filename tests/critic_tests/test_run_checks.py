from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock
from uuid import uuid4

import boto3
import httpx
import pytest

from critic.libs.ddb import namespace_table
from critic.models import MonitorState, UptimeMonitorModel
from critic.tables import UptimeMonitorTable
from critic.tasks.run_checks import run_checks


@pytest.fixture
def get_uptime_monitor():
    return UptimeMonitorModel(
        project_id=str(uuid4()),
        slug='test-slug',
        state=MonitorState.new,
        url='https://google.com',
        frequency_mins=1,
        consecutive_fails=1,
        next_due_at=datetime.now().isoformat(),
        timeout_secs=3,
        failures_before_alerting=2,
        realert_interval_mins=1,
    )


def test_run_checks(get_uptime_monitor):
    monitor: UptimeMonitorModel = get_uptime_monitor

    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(namespace_table('UptimeMonitor'))
    logs_table = dynamodb.Table(namespace_table('UptimeLog'))
    table.put_item(
        Item={
            'project_id': monitor.project_id,
            'slug': monitor.slug,
            'GSI_PK': 'MONITOR',
            'state': monitor.state,
            'url': monitor.url,
            'consecutive_fails': monitor.consecutive_fails,
            'next_due_at': monitor.next_due_at,
            'timeout_secs': Decimal(str(monitor.timeout_secs)),
            'failures_before_alerting': monitor.failures_before_alerting,
            'realert_interval_mins': monitor.realert_interval_mins,
        }
    )

    time_to_check = monitor.next_due_at
    client: httpx.Client = httpx.Client()
    run_checks(monitor, client)
    client.close()
    # check ddb entries
    response = table.get_item(Key={'project_id': monitor.project_id, 'slug': monitor.slug})
    info = response['Item']

    # check that monitor is up, next due at is later, and consecutive fails is 0 because of passing
    assert info['state'] == MonitorState.up
    assert datetime.fromisoformat(info['next_due_at']) > datetime.fromisoformat(time_to_check)
    assert info['consecutive_fails'] == 0

    monitor_id = monitor.project_id + monitor.slug
    response = logs_table.get_item(Key={'monitor_id': monitor_id, 'timestamp': time_to_check})
    info = response['Item']

    # check logging stuff
    assert info['status'] == MonitorState.up
    assert info['resp_code'] > 0
    assert info['latency_secs'] > 0


# def test_run_check_fail_with_consec_fails_above_threshold(get_uptime_monitor):
#     monitor: UptimeMonitorModel = get_uptime_monitor

#     mock_client = MagicMock()
#     mock_client.head.side_effect = httpx.TimeoutException('Connection timed out')

#     dynamodb = boto3.resource('dynamodb')
#     logs_table = dynamodb.Table(namespace_table('UptimeLog'))
#     UptimeMonitorTable.put(monitor)

#     time_to_check = monitor.next_due_at

#     # Inject the mock client
#     run_checks(monitor, http_client=mock_client)

#     response : UptimeMonitorModel = UptimeMonitorTable.get(monitor.project_id, monitor.slug)
#     # Monitor should be down with 2 consec fails
#     assert response.state == MonitorState.down
#     assert response.consecutive_fails == 2

#     monitor_id = str(monitor.project_id) + monitor.slug
#     response = logs_table.get_item(Key={'monitor_id': monitor_id, 'timestamp': time_to_check})
#     info = response['Item']

#     # log should have resp of 0 since there was a timeout, and a latency of -1
#     assert info['status'] == MonitorState.down
#     assert info['resp_code'] == 0
#     assert info['latency_secs'] == -1


def test_run_check_fail_with_consec_fails_below_threshold(get_uptime_monitor):
    monitor: UptimeMonitorModel = get_uptime_monitor
    monitor.consecutive_fails = 0
    monitor.state = MonitorState.up

    mock_client = MagicMock()
    mock_client.head.side_effect = httpx.TimeoutException('Connection timed out')

    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(namespace_table('UptimeMonitor'))
    logs_table = dynamodb.Table(namespace_table('UptimeLog'))

    table.put_item(
        Item={
            'project_id': monitor.project_id,
            'slug': monitor.slug,
            'GSI_PK': 'MONITOR',
            'state': monitor.state,
            'url': monitor.url,
            'consecutive_fails': monitor.consecutive_fails,
            'next_due_at': monitor.next_due_at,
            'timeout_secs': Decimal(str(monitor.timeout_secs)),
            'failures_before_alerting': monitor.failures_before_alerting,
            'realert_interval_mins': monitor.realert_interval_mins,
        }
    )

    time_to_check = monitor.next_due_at
    run_checks(monitor, http_client=mock_client)

    response = table.get_item(Key={'project_id': monitor.project_id, 'slug': monitor.slug})
    info = response['Item']
    assert info['state'] == MonitorState.up
    assert info['consecutive_fails'] == 1

    monitor_id = str(monitor.project_id) + monitor.slug
    response = logs_table.get_item(Key={'monitor_id': monitor_id, 'timestamp': time_to_check})
    info = response['Item']
    # log should have resp of 0 since there was a timeout, and a latency of -1
    assert info['status'] == MonitorState.up
    assert info['resp_code'] == 0
    assert info['latency_secs'] == -1


# what are we doing for next due time when paused?
def test_run_check_fail_with_paused_monitor(get_uptime_monitor):
    monitor: UptimeMonitorModel = get_uptime_monitor
    monitor.state = MonitorState.paused

    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(namespace_table('UptimeMonitor'))
    logs_table = dynamodb.Table(namespace_table('UptimeLog'))

    table.put_item(
        Item={
            'project_id': str(monitor.project_id),
            'slug': monitor.slug,
            'GSI_PK': 'MONITOR',
            'state': monitor.state,
            'url': monitor.url,
            'consecutive_fails': monitor.consecutive_fails,
            'next_due_at': monitor.next_due_at,
            'timeout_secs': Decimal(str(monitor.timeout_secs)),
            'failures_before_alerting': monitor.failures_before_alerting,
            'realert_interval_mins': monitor.realert_interval_mins,
        }
    )

    time_to_check = monitor.next_due_at
    client: httpx.Client = httpx.Client()
    run_checks(monitor, client)
    client.close()

    monitor_id = str(monitor.project_id) + monitor.slug
    response = logs_table.get_item(Key={'monitor_id': monitor_id, 'timestamp': time_to_check})
    # does not have item because no log is created since the monitor is paused
    assert 'Item' not in response
