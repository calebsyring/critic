import logging
from unittest import mock

from freezegun import freeze_time
import pytest

from critic.libs.testing import UptimeMonitorFactory
from critic.libs.uptime import MonitorNotFoundError
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
    @mock.patch('critic.tasks.UptimeCheck')
    def test_runs_check(self, m_uptime_check):
        run_checks('6033aa47-a9f7-4d7f-b7ff-a11ba9b34474', 'my-monitor')
        m_uptime_check.assert_called_once_with('6033aa47-a9f7-4d7f-b7ff-a11ba9b34474', 'my-monitor')
        m_uptime_check.return_value.run.assert_called_once_with()

    @mock.patch('critic.tasks.UptimeCheck')
    def test_handles_not_found(self, m_uptime_check, caplog):
        caplog.set_level(logging.INFO)
        m_uptime_check.side_effect = MonitorNotFoundError
        run_checks('6033aa47-a9f7-4d7f-b7ff-a11ba9b34474', 'my-monitor')
        assert 'not found, skipping' in caplog.text
