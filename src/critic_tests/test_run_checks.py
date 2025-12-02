import time
from uuid import uuid4

import boto3
import pytest

from critic.models import MonitorState, UptimeMonitor


@pytest.fixture
def get_uptime_monitor():
    return UptimeMonitor(
        project_id=str(uuid4()),
        slug='test-slug',
        url='google.com',
        timeout_secs=3,
    )


def test_run_checks():
    client = boto3.client('dynamodb', region_name='us-east-2')
    assert client is not None
    # run test function

    # check if the function worked by checking ddb for log entries!


# not sure where to put this for now
def run_checks(monitor: UptimeMonitor):
    import httpx

    # ping website
    start = time.perf_counter()

    try:
        response = httpx.head(monitor.url, timeout=monitor.timeout_secs)
        finished = time.perf_counter()
        time_to_ping = start - finished
    except httpx.TimeoutException:
        response = None  # what do we do for None? Add a failed state?
        time_to_ping = None

    # check response and update state, this will need to work with assertions later on
    if response is None:
        ## we will need some sort of way to check the amount of failures before alerting has happened?
        # I think we will need a consecutive failures field to be added
        monitor.state = MonitorState.down
    elif assertions_pass(monitor, response):
        monitor.state = MonitorState.up
    
    if monitor.state == MonitorState.down:
        if monitor.alert_slack_channels:
            send_alerts_slack(monitor)
        if monitor.alert_emails:
            send_email_alerts(monitor)

    # update re-run time, I think this is better than 
    monitor.next_due_at = time.time() + (monitor.frequency_mins * 6000)

    # update ddb, should only need to send keys, state and nextdue
    item = {
        'project_id': monitor.project_id,
        'slug': monitor.slug,
        'GSI_PK': 'MONITOR',
        'state': monitor.state,
        'next_due_at': monitor.next_due_at,
    }
    
    # update logs?



    def send_alerts_slack(monitor: UptimeMonitor):
        pass

    def send_email_alerts(monitor: UptimeMonitor):
        pass

    def assertions_pass(monitor: UptimeMonitor, status_code: int):
        return True