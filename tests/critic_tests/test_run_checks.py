from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock
from uuid import uuid4

import boto3
import httpx
import pytest

from critic.libs.ddb import namespace_table
from critic.models import MonitorState, UptimeLog, UptimeMonitorModel
from critic.tables import UptimeLogTable, UptimeMonitorTable
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
    UptimeMonitorTable.put(monitor)

    time_to_check = monitor.next_due_at
    client: httpx.Client = httpx.Client()
    run_checks(monitor, client)
    client.close()
    # check ddb entries
    response: UptimeMonitorModel = UptimeMonitorTable.get(monitor.project_id, monitor.slug)

    # check that monitor is up, next due at is later, and consecutive fails is 0 because of passing
    assert response.state == MonitorState.up
    assert datetime.fromisoformat(response.next_due_at) > datetime.fromisoformat(time_to_check)
    assert response.consecutive_fails == 0

    monitor_id = monitor.project_id + monitor.slug
    response: UptimeLog = UptimeLogTable.get(monitor_id, time_to_check)
    # response = logs_table.get_item(Key={'monitor_id': monitor_id, 'timestamp': time_to_check})

    # check logging stuff
    assert response.status == MonitorState.up
    assert response.resp_code > 0
    assert response.latency_secs > 0


def test_run_check_fail_with_consec_fails_above_threshold(get_uptime_monitor):
    monitor: UptimeMonitorModel = get_uptime_monitor
    time_to_check = monitor.next_due_at
    UptimeMonitorTable.put(monitor)

    mock_client = MagicMock()
    mock_client.head.side_effect = httpx.TimeoutException('Connection timed out')
    # Inject the mock client
    run_checks(monitor, http_client=mock_client)

    response: UptimeMonitorModel = UptimeMonitorTable.get(monitor.project_id, monitor.slug)
    # Monitor should be down with 2 consec fails
    assert response.state == MonitorState.down
    assert response.consecutive_fails == 2

    monitor_id = str(monitor.project_id) + monitor.slug
    response: UptimeLog = UptimeLogTable.get(monitor_id, time_to_check)
    # log should have resp of 0 since there was a timeout, and a latency of -1
    assert response.status == MonitorState.down
    assert response.resp_code == 0
    assert response.latency_secs == -1


def test_run_check_fail_with_consec_fails_below_threshold(get_uptime_monitor):
    monitor: UptimeMonitorModel = get_uptime_monitor
    monitor.consecutive_fails = 0
    monitor.state = MonitorState.up
    UptimeMonitorTable.put(monitor)
    time_to_check = monitor.next_due_at

    mock_client = MagicMock()
    mock_client.head.side_effect = httpx.TimeoutException('Connection timed out')
    run_checks(monitor, http_client=mock_client)

    response: UptimeMonitorModel = UptimeMonitorTable.get(monitor.project_id, monitor.slug)
    assert response.state == MonitorState.up
    assert response.consecutive_fails == 1

    monitor_id = str(monitor.project_id) + monitor.slug
    response: UptimeLog = UptimeLogTable.get(monitor_id, time_to_check)
    # log should have resp of 0 since there was a timeout, and a latency of -1
    assert response.status == MonitorState.up
    assert response.resp_code == 0
    assert response.latency_secs == -1


# what are we doing for next due time when paused?
def test_run_check_fail_with_paused_monitor(get_uptime_monitor):
    monitor: UptimeMonitorModel = get_uptime_monitor
    monitor.state = MonitorState.paused
    UptimeMonitorTable.put(monitor)

    time_to_check = monitor.next_due_at
    client: httpx.Client = httpx.Client()
    run_checks(monitor, client)
    client.close()

    monitor_id = str(monitor.project_id) + monitor.slug
    response: UptimeLog = UptimeLogTable.get(monitor_id, time_to_check)
    # does not have item because no log is created since the monitor is paused
    assert response is None
