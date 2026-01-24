from datetime import datetime, timedelta
import logging
import time

import boto3
import httpx
import mu

from critic.app import app
from critic.libs.ddb import namespace_table
from critic.models import MonitorState, UptimeLog, UptimeMonitorModel
from critic.tables import UptimeLogTable, UptimeMonitorTable


logger = logging.getLogger(__name__)


@app.route('/run_checks/<monitor_id>/<monitor_slug>')
def run_checks_call(monitor_id: str, monitor_slug: str):
    run_checks(monitor_id, monitor_slug)


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


@mu.task
def run_checks(monitor_id: str, monitor_slug: str):
    monitor: UptimeMonitorModel = UptimeMonitorTable.get(monitor_id, monitor_slug)
    logger.info(f'Starting check for monitor: {monitor}')
    dynamodb = boto3.resource('dynamodb')
    monitor_table = dynamodb.Table(namespace_table('UptimeMonitor'))

    monitor.next_due_at = (
        datetime.fromisoformat(monitor.next_due_at) + timedelta(minutes=monitor.frequency_mins)
    ).isoformat()

    # if paused update the time and return
    if monitor.state == MonitorState.paused:
        monitor_table.update_item(
            Key={'project_id': monitor.project_id, 'slug': monitor.slug},
            UpdateExpression='SET next_due_at = :n',
            ExpressionAttributeValues={':n': monitor.next_due_at},
        )
        return

    start = time.perf_counter()
    with httpx.Client() as client:
        try:
            response: httpx.Response = client.head(
                str(monitor.url), timeout=float(monitor.timeout_secs)
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

    logtime_stamp = datetime.now().isoformat()

    # update ddb, should only need to send keys, state and nextdue
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

    response_code = response.status_code if response else None
    # update logs
    monitor_id: str = monitor.project_id + monitor.slug
    uptime_log = UptimeLog(
        monitor_id=(monitor_id),
        timestamp=logtime_stamp,
        status=monitor.state,
        resp_code=response_code,
        latency_secs=time_to_ping,
    )

    if uptime_log.resp_code is None:
        uptime_log.resp_code = 0
    if uptime_log.latency_secs is None:
        uptime_log.latency_secs = -1

    UptimeLogTable.put(uptime_log)
