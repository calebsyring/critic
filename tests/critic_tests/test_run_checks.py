from decimal import Decimal
import time
from uuid import uuid4

import boto3
from boto3.dynamodb.conditions import Key
import pytest

from critic.libs.testing import create_uptime_monitor_table
from critic.models import MonitorState, UptimeMonitor


@pytest.fixture
def get_uptime_monitor():
    return UptimeMonitor(
        project_id=str(uuid4()),
        slug='test-slug',
        state=MonitorState.new,
        url='https://google.com',
        frequency_mins=1,
        next_due_at=int(time.time()),
        timeout_secs=3,
        failures_before_alerting=2,
        realert_interval_mins=1,
    )

#TODO
def send_slack_alerts(monitor: UptimeMonitor):
    pass

#TODO
def send_email_alerts(monitor: UptimeMonitor):
    pass

#TODO
def assertions_pass(monitor: UptimeMonitor, status_code: int):
    return True


# not sure where to put this for now
def run_checks(monitor: UptimeMonitor):
    import httpx

    # ping website
    start = time.perf_counter()

    try:
        response = httpx.head(monitor.url, timeout=float(monitor.timeout_secs))
        finished = time.perf_counter()
        time_to_ping = start - finished
    except httpx.TimeoutException:
        response = None  # what do we do for None? Add a failed state?
        time_to_ping = None

    # check response and update state, this will need to work with assertions later on
    if response is None:
        # we will need some sort of way to check the amount of failures before alerting has happened?
        # I think we will need a consecutive failures field to be added
        monitor.state = MonitorState.down
    elif assertions_pass(monitor, response):
        monitor.state = MonitorState.up

    if monitor.state == MonitorState.down:
        if monitor.alert_slack_channels:
            send_slack_alerts(monitor)
        if monitor.alert_emails:
            send_email_alerts(monitor)

    # update re-run time, I think this is better than
    monitor.next_due_at = time.time() + (monitor.frequency_mins * 6000)

    # update ddb, should only need to send keys, state and nextdue
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('Monitor')
    table.update_item(
        Key={'project_id': monitor.project_id, 'slug': monitor.slug},
        UpdateExpression='SET #state = :s, next_due_at = :n',
        # we will need to redefine #state to the state category used above because state is a reserved word for ddb
        ExpressionAttributeNames={'#state': 'state'},
        ExpressionAttributeValues={
            ':s': monitor.state,
            ':n': int(monitor.next_due_at),  # Ensure this is a number (int/decimal)
        },
    )
    # update logs


def test_run_checks(get_uptime_monitor):
    monitor = get_uptime_monitor

    create_uptime_monitor_table()

    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('Monitor')
    table.put_item(
        Item={
            'project_id': monitor.project_id,
            'slug': monitor.slug,
            'GSI_PK': 'MONITOR',
            'state': monitor.state,
            'url': monitor.url,
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
    assert info['next_due_at'] > time_to_check

    # check logging stuff
