from datetime import UTC, datetime, timedelta
import logging
import time

import httpx
import mu

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

    # if paused update the time and return
    if monitor.state == MonitorState.paused:
        UptimeMonitorTable.update(
            monitor.project_id,
            monitor.slug,
            next_due_at=monitor.next_due_at + timedelta(minutes=monitor.frequency_mins),
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
    state = MonitorState.up
    consecutive_fails = 0
    if not assertions_pass(monitor, response):
        state = MonitorState.down
        consecutive_fails = monitor.consecutive_fails + 1
        if consecutive_fails >= monitor.failures_before_alerting:
            if monitor.alert_slack_channels:
                send_slack_alerts(monitor)
            if monitor.alert_emails:
                send_email_alerts(monitor)

    # update ddb, should only need to send keys, state and nextdue
    UptimeMonitorTable.update(
        monitor.project_id,
        monitor.slug,
        state=state,
        consecutive_fails=consecutive_fails,
        next_due_at=monitor.next_due_at + timedelta(minutes=monitor.frequency_mins),
    )

    response_code = response.status_code if response else None
    # update logs
    uptime_log = UptimeLog(
        monitor_id=f'{monitor.project_id}/{monitor.slug}',
        timestamp=datetime.now(UTC),
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
    due and invokes `run_checks` for each one.
    """
    now = datetime.now(UTC)
    log.info(f'Triggering due checks at {now.isoformat()}')

    # Round `now` to the nearest minute in case there is a slight inaccuracy in scheduling
    rounded_now = now.replace(second=0, microsecond=0)
    if now.second >= 30:
        rounded_now = rounded_now + timedelta(minutes=1)

    # Trigger `run_checks` for each due monitor.
    due_monitors = UptimeMonitorTable.get_due_since(rounded_now)
    for monitor in due_monitors:
        run_checks.invoke(str(monitor.project_id), monitor.slug)

    log.info(f'Due checks triggered for {len(due_monitors)} monitors in {datetime.now(UTC) - now}')
