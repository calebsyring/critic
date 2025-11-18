import time
from uuid import uuid4

import boto3
import pytest

from critic.models import MonitorState, UptimeMonitor


@pytest.fixture
def get_uptime_monitor():
    return UptimeMonitor(
        project_id=uuid4(),
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
    import requests

    # ping website
    start = time.perf_counter()

    try:
        response = requests.head(monitor.url, timeout=monitor.timeout_secs)
        finished = time.perf_counter()
        time_to_ping = start - finished
    except requests.RequestException:
        response = None  # what do we do for None? Add a failed state?
        time_to_ping = None

    # check response and update state
    if response.status_code == 200:
        monitor.state = MonitorState.up
    elif response.status_code is not None:
        monitor.state = MonitorState.down

    # update re-run time
    monitor.next_due_at = (time.time() + monitor.frequency_mins * 6000)
    
    # update ddb
    item = {
            'project_id' : monitor.project_id,
            'slug' : monitor.slug,
            'GSI_PK': 'MONITOR',
            'state' : monitor.state,
            'url' : monitor.url,
            'next_due_at' : monitor.next_due_at,
            'timeout' : 5,
        }
    # update logs?
