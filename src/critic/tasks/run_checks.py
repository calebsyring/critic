from datetime import datetime, timedelta
from decimal import Decimal
import logging
import time

import boto3
from boto3.dynamodb.conditions import Key
import httpx

from critic.libs.ddb import namespace_table
from critic.models import MonitorState, UptimeLog, UptimeMonitorModel


# TODO
def send_slack_alerts(monitor: UptimeMonitorModel):
    pass


# TODO
def send_email_alerts(monitor: UptimeMonitorModel):
    pass


# TODO
def assertions_pass(monitor: UptimeMonitorModel, repsonse: httpx.Response):
    return (
        repsonse is not None
    )  # this will handle exceptions from http, but not 404 or other errors


def run_checks(monitor: UptimeMonitorModel, http_client: httpx.Client):
    if monitor.state == MonitorState.paused:
        return

    start = time.perf_counter()
    try:
        response: httpx.Response = http_client.head(
            monitor.url, timeout=float(monitor.timeout_secs)
        )
        finished = time.perf_counter()
        time_to_ping = finished - start
    except httpx.TimeoutException:
        response = None
        # if we get some error, like a 404 that can be handled in assertions
        # if there is a timeout, that should be handled here
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
    monitor.next_due_at = (
        datetime.fromisoformat(monitor.next_due_at) + timedelta(minutes=monitor.frequency_mins)
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
            ':c': monitor.consecutive_fails,
        },
    )
    response_code = None
    if response:
        response_code = response.status_code
    # update logs
    monitor_id : str = monitor.project_id + monitor.slug
    uptime_log = UptimeLog(
        monitor_id=(monitor_id),
        timestamp=copy_of_original_next_due,
        status=monitor.state,
        resp_code=response_code,
        latency_secs=time_to_ping,
    )
    logs_table = dynamodb.Table(namespace_table('UptimeLog'))

    logs_table.put_item(
        Item={
            'monitor_id': uptime_log.monitor_id,
            'timestamp': uptime_log.timestamp,
            'status': uptime_log.status,
            # well set it to 0 if there is no response is given
            'resp_code': uptime_log.resp_code if uptime_log.resp_code else 0,
            # well set latency to -1 if there is no response given
            'latency_secs': Decimal(
                str(uptime_log.latency_secs) if uptime_log.latency_secs else -1
            ),
        }
    )
