import logging
from unittest import mock

from freezegun import freeze_time
import httpx
import pytest

from critic.libs.testing import UptimeMonitorFactory
from critic.models import MonitorState, UptimeLog, UptimeMonitorModel
from critic.tables import UptimeLogTable, UptimeMonitorTable
from critic.tasks import run_checks, run_due_checks


class TestRunDueChecks:
    @pytest.mark.parametrize('kickoff_time', ['2026-01-01 12:00:01', '2026-01-01 11:59:59'])
    @mock.patch('critic.tasks.run_checks.invoke')
    def test_run_due_checks(self, m_run_check, kickoff_time):
        due = UptimeMonitorFactory.put(next_due_at='2026-01-01 12:00:00Z')
        # Not due
        UptimeMonitorFactory.put(next_due_at='2026-01-01 12:01:00Z')

        with freeze_time(kickoff_time, tz_offset=0):
            run_due_checks()

        m_run_check.assert_called_once_with(str(due.project_id), due.slug)


class TestRunChecks:
    def test_up(self, caplog, httpx_mock):
        monitor: UptimeMonitorModel = UptimeMonitorFactory.put(
            consecutive_fails=1, failures_before_alerting=2, state=MonitorState.up
        )

        caplog.set_level(logging.INFO)

        time_to_check = monitor.next_due_at

        httpx_mock.add_response()
        run_checks(monitor.project_id, monitor.slug)

        # check ddb entries
        assert 'Starting check' in caplog.text  # make sure method is sending log
        response: UptimeMonitorModel = UptimeMonitorTable.get(monitor.project_id, monitor.slug)

        # check that monitor is up, next due at is later, and consecutive fails is 0 because passing
        assert response.state == MonitorState.up
        assert response.next_due_at > time_to_check
        assert response.consecutive_fails == 0

        monitor_id = f'{monitor.project_id}/{monitor.slug}'
        response: UptimeLog = UptimeLogTable.query(monitor_id)[-1]

        # check logging stuff
        assert response.status == MonitorState.up
        assert response.resp_code > 0
        assert response.latency_secs > 0

    def test_down_with_consec_fails_above_threshold(self, httpx_mock):
        monitor: UptimeMonitorModel = UptimeMonitorFactory.put(
            consecutive_fails=1,
            failures_before_alerting=2,
            state=MonitorState.down,
        )

        httpx_mock.add_exception(httpx.TimeoutException('Connection timed out'))
        run_checks(monitor.project_id, monitor.slug)

        response: UptimeMonitorModel = UptimeMonitorTable.get(monitor.project_id, monitor.slug)
        # Monitor should be down with 2 consec fails
        assert response.state == MonitorState.down
        assert response.consecutive_fails == 2

        monitor_id = f'{monitor.project_id}/{monitor.slug}'
        response: UptimeLog = UptimeLogTable.query(monitor_id)[-1]
        # log should have resp of 0 since there was a timeout, and a latency of -1
        assert response.status == MonitorState.down
        assert response.resp_code == 0
        assert response.latency_secs == -1

    def test_down_with_consec_fails_below_threshold(self, httpx_mock):
        monitor: UptimeMonitorModel = UptimeMonitorFactory.put(
            consecutive_fails=0,
            failures_before_alerting=2,
            state=MonitorState.up,
        )

        httpx_mock.add_exception(httpx.TimeoutException('Connection timed out'))

        run_checks(monitor.project_id, monitor.slug)

        response: UptimeMonitorModel = UptimeMonitorTable.get(monitor.project_id, monitor.slug)
        assert response.state == MonitorState.down
        assert response.consecutive_fails == 1

        monitor_id = f'{monitor.project_id}/{monitor.slug}'
        response: UptimeLog = UptimeLogTable.query(monitor_id)[-1]
        # log should have resp of 0 since there was a timeout, and a latency of -1
        assert response.status == MonitorState.up
        assert response.resp_code == 0
        assert response.latency_secs == -1

    # what are we doing for next due time when paused?
    def test_paused(self):
        monitor: UptimeMonitorModel = UptimeMonitorFactory.put(
            consecutive_fails=0,
            failures_before_alerting=2,
            state=MonitorState.paused,
        )
        time_to_check = monitor.next_due_at

        run_checks(monitor.project_id, monitor.slug)

        response: UptimeMonitorModel = UptimeMonitorTable.get(monitor.project_id, monitor.slug)
        assert response.next_due_at > time_to_check
        monitor_id = f'{monitor.project_id}/{monitor.slug}'
        response: UptimeLog = UptimeLogTable.query(monitor_id)
        # does not have item because no log is created since the monitor is paused
        assert response == []
