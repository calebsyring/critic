from datetime import datetime, timedelta
from decimal import Decimal
import time
from uuid import uuid4

import boto3
from boto3.dynamodb.conditions import Key
import httpx
import pytest

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
        consecutive_fails=0,
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
def assertions_pass(monitor: UptimeMonitor, status_code: int):
    return True


# not sure where to put this for now
def run_checks(monitor: UptimeMonitor):

    start = time.perf_counter()
    try:
        response: httpx.Response = httpx.head(monitor.url, timeout=float(monitor.timeout_secs))
        finished = time.perf_counter()
        time_to_ping = start - finished
    except httpx.TimeoutException:
        response = None  # what do we do for None? Add a failed state?
        time_to_ping = None

    # check response and update state, this will need to work with assertions later on
    if assertions_pass(monitor, response):
        monitor.state = MonitorState.up
        monitor.consecutive_fails = 0
    else:
        monitor.consecutive_fails += 1
        if monitor.consecutive_fails < monitor.failures_before_alerting:
            monitor.state = MonitorState.down

    if monitor.state == MonitorState.down:
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
                            resp_code=response_code,
                            latency_secs=time_to_ping)
    logs_table = dynamodb.Table(namespace_table('UptimeLog'))
    logs_table.put_item(
        Item={
            'monitor_id' : uptime_log.monitor_id,
            'timestamp' : uptime_log.timestamp,
            'status' : uptime_log.status,
            'resp_code' : uptime_log.resp_code,
            'latency_secs' : Decimal(str(uptime_log.latency_secs))
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
    run_checks(monitor)

    # check ddb entries
    response = table.get_item(Key={'project_id': monitor.project_id, 'slug': monitor.slug})
    info = response['Item']

    assert info['state'] == MonitorState.up
    assert datetime.fromisoformat(info['next_due_at']) > datetime.fromisoformat(time_to_check)

    monitor_id = monitor.project_id + monitor.slug
    response = logs_table.get_item(Key={'monitor_id': monitor_id, 'timestamp': time_to_check})
    info = response['Item']
    assert info['status'] == MonitorState.up
    # check logging stuff
