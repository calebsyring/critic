from datetime import datetime, timedelta
from decimal import Decimal
import time
from uuid import uuid4

import boto3
from boto3.dynamodb.conditions import Key
import httpx
import pytest
from unittest.mock import MagicMock

from critic.libs.ddb import namespace_table
from critic.models import MonitorState, UptimeLog, UptimeMonitor


@pytest.fixture
def get_uptime_monitor():
    return UptimeMonitor(
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


# TODO
def send_slack_alerts(monitor: UptimeMonitor):
    pass


# TODO
def send_email_alerts(monitor: UptimeMonitor):
    pass


# TODO
def assertions_pass(monitor: UptimeMonitor, repsonse: httpx.Response):
    return repsonse is not None #this will handle exceptions from http, but not 404 or other errors


# not sure where to put this for now
def run_checks(monitor: UptimeMonitor, http_client : httpx.Client):
    print("checking if paused")
    print(monitor.state)
    if monitor.state == MonitorState.paused:
        print("returning because paused")
        return

    start = time.perf_counter()
    try:
        response: httpx.Response = http_client.head(monitor.url, timeout=float(monitor.timeout_secs))
        finished = time.perf_counter()
        time_to_ping = finished - start
    except httpx.TimeoutException:
        response = None
        #if we get some error, like a 404 that can be handled in assertions
        #if there is a timeout, that should be handled here
        time_to_ping = None

    # check response and update state, this will need to work with assertions later on
    if assertions_pass(monitor, response):
        monitor.state = MonitorState.up
        monitor.consecutive_fails = 0
    else:
        monitor.consecutive_fails += 1
        if monitor.consecutive_fails >= monitor.failures_before_alerting:
            monitor.state = MonitorState.down
            if monitor.alert_slack_channels:
                send_slack_alerts(monitor)
            if monitor.alert_emails:
                send_email_alerts(monitor)

    copy_of_original_next_due = monitor.next_due_at
    monitor.next_due_at = (datetime.fromisoformat(monitor.next_due_at)
                           + timedelta(minutes=monitor.frequency_mins)
                           ).isoformat()

    # update ddb, should only need to send keys, state and nextdue
    dynamodb = boto3.resource('dynamodb')
    monitor_table = dynamodb.Table(namespace_table('UptimeMonitor'))
    monitor_table.update_item(
        Key={'project_id': monitor.project_id, 'slug': monitor.slug},
        UpdateExpression='SET #state = :s, next_due_at = :n, consecutive_fails = :c', 
        # we will need to redefine #state to the state category used above because state is a
        # reserved word for ddb
        ExpressionAttributeNames={'#state': 'state'},
        ExpressionAttributeValues={
            ':s': monitor.state,
            ':n': monitor.next_due_at,
            ':c': monitor.consecutive_fails
        },
    )
    response_code = None
    if response:
        response_code = response.status_code
    # update logs
    monitor_id = monitor.project_id + monitor.slug
    uptime_log = UptimeLog(monitor_id=(monitor_id),
                            timestamp=copy_of_original_next_due,
                            status=monitor.state,
                            resp_code=response_code ,
                            latency_secs=time_to_ping)
    logs_table = dynamodb.Table(namespace_table('UptimeLog'))

    logs_table.put_item(
        Item={
            'monitor_id' : uptime_log.monitor_id,
            'timestamp' : uptime_log.timestamp,
            'status' : uptime_log.status,
            # well set it to 0 if there is no response is given
            'resp_code' : uptime_log.resp_code if uptime_log.resp_code else 0,
            # well set latency to -1 if there is no response given
            'latency_secs' :
                Decimal(str(uptime_log.latency_secs) if uptime_log.latency_secs else -1)
        }
    )



def test_run_checks(get_uptime_monitor):
    monitor: UptimeMonitor = get_uptime_monitor

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
    client : httpx.Client = httpx.Client()
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

def test_run_check_fail_with_consec_fails_above_threshold(get_uptime_monitor):
    monitor: UptimeMonitor = get_uptime_monitor

    mock_client = MagicMock()
    mock_client.head.side_effect = httpx.TimeoutException("Connection timed out")

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

    # Inject the mock client
    run_checks(monitor, http_client=mock_client)


    response = table.get_item(Key={'project_id': monitor.project_id, 'slug': monitor.slug})
    info = response['Item']

    # Monitor should be down with 2 consec fails
    assert info['state'] == MonitorState.down
    assert info['consecutive_fails'] == 2

    monitor_id = monitor.project_id + monitor.slug
    response = logs_table.get_item(Key={'monitor_id': monitor_id, 'timestamp': time_to_check})
    info = response['Item']

    #log should have resp of 0 since there was a timeout, and a latency of -1
    assert info['status'] == MonitorState.down
    assert info['resp_code'] == 0
    assert info['latency_secs'] == -1

def test_run_check_fail_with_consec_fails_below_threshold(get_uptime_monitor):
    monitor: UptimeMonitor = get_uptime_monitor
    monitor.consecutive_fails = 0
    monitor.state = MonitorState.up

    mock_client = MagicMock()
    mock_client.head.side_effect = httpx.TimeoutException("Connection timed out")

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

    monitor_id = monitor.project_id + monitor.slug
    response = logs_table.get_item(Key={'monitor_id': monitor_id, 'timestamp': time_to_check})
    info = response['Item']
    #log should have resp of 0 since there was a timeout, and a latency of -1
    assert info['status'] == MonitorState.up
    assert info['resp_code'] == 0
    assert info['latency_secs'] == -1

#what are we doing for next due time when paused?
def test_run_check_fail_with_paused_monitor(get_uptime_monitor):
    monitor: UptimeMonitor = get_uptime_monitor
    monitor.state = MonitorState.paused
    

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
    client : httpx.Client = httpx.Client()
    run_checks(monitor, client)
    client.close()

    monitor_id = monitor.project_id + monitor.slug
    response = logs_table.get_item(Key={'monitor_id': monitor_id, 'timestamp': time_to_check})
    #does not have item because no log is created since the monitor is paused
    assert 'Item' not in response
