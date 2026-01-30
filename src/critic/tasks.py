from datetime import UTC, datetime, timedelta
import logging
import time

import boto3
import httpx
import mu

from critic.libs.ddb import UPTIME_MONITOR
from critic.models import MonitorState, UptimeLog, UptimeMonitorModel
from critic.tables import UptimeLogTable, UptimeMonitorTable


log = logging.getLogger(__name__)


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
    log.info(f'Starting check for monitor: {monitor}')
    dynamodb = boto3.resource('dynamodb')
    monitor_table = dynamodb.Table(UptimeMonitorTable.namespace(UPTIME_MONITOR))

    monitor.next_due_at = monitor.next_due_at + timedelta(minutes=monitor.frequency_mins)

    # if paused update the time and return
    if monitor.state == MonitorState.paused:
        monitor_table.update_item(
            Key={'project_id': str(monitor.project_id), 'slug': monitor.slug},
            UpdateExpression='SET next_due_at = :n',
            ExpressionAttributeValues={':n': monitor.next_due_at.isoformat()},
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

    # this might be correct for the tzinfo?
    logtime_stamp = datetime.now(tz=monitor.next_due_at.tzinfo).isoformat()

    # update ddb, should only need to send keys, state and nextdue
    monitor_table.update_item(
        Key={'project_id': str(monitor.project_id), 'slug': monitor.slug},
        UpdateExpression='SET #state = :s, next_due_at = :n, consecutive_fails = :c',
        # we will need to redefine #state to the state category used above because state is a
        # reserved word for ddb
        ExpressionAttributeNames={'#state': 'state'},
        ExpressionAttributeValues={
            ':s': monitor.state,
            ':n': monitor.next_due_at.isoformat(),
            ':c': monitor.consecutive_fails,
        },
    )

    response_code = response.status_code if response else None
    # update logs
    monitor_id: str = str(monitor.project_id) + monitor.slug
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


@mu.task
def run_due_checks():
    """
    This task is invoked by an EventBridge rule once a minute. It queries for all monitors that are
    due and invokes `run_check` for each one.
    """
    now = datetime.now(UTC)
    log.info(f'Triggering due checks at {now.isoformat()}')

    # Round `now` to the nearest minute in case there is a slight inaccuracy in scheduling
    rounded_now = now.replace(second=0, microsecond=0)
    if now.second >= 30:
        rounded_now = rounded_now + timedelta(minutes=1)

    # Trigger `run_check` for each due monitor.
    due_monitors = UptimeMonitorTable.get_due_since(rounded_now)
    for monitor in due_monitors:
        run_checks.invoke(str(monitor.project_id), monitor.slug)

    log.info(f'Due checks triggered for {len(due_monitors)} monitors in {datetime.now(UTC) - now}')
