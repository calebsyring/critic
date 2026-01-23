from unittest import mock

from freezegun import freeze_time
import pytest

from critic.libs.testing import UptimeMonitorFactory
from critic.tasks import run_due_checks


class TestRunDueChecks:
    @pytest.mark.parametrize('kickoff_time', ['2026-01-01 12:00:01', '2026-01-01 11:59:59'])
    @mock.patch('critic.tasks.run_check.invoke')
    def test_run_due_checks(self, m_run_check, kickoff_time):
        due = UptimeMonitorFactory.put(next_due_at='2026-01-01 12:00:00Z')
        # Not due
        UptimeMonitorFactory.put(next_due_at='2026-01-01 12:01:00Z')

        with freeze_time(kickoff_time, tz_offset=0):
            run_due_checks()

        m_run_check.assert_called_once_with(str(due.project_id), due.slug)
