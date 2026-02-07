from datetime import UTC, datetime

import pytest

from critic.libs.testing import UptimeMonitorFactory


class TestUptimeMonitorModel:
    def test_next_due_at_utc(self):
        monitor = UptimeMonitorFactory.build(next_due_at='2026-01-01 12:00:00+04:00')
        assert monitor.next_due_at == datetime(2026, 1, 1, 8, 0, 0, tzinfo=UTC)

    def test_next_due_at_unaware(self):
        with pytest.raises(ValueError, match='Input should have timezone info'):
            UptimeMonitorFactory.build(next_due_at='2026-01-01 12:00:00')

    def test_next_due_at_second(self):
        with pytest.raises(ValueError, match='next_due_at must be no more precise than minutes'):
            UptimeMonitorFactory.build(next_due_at='2026-01-01 12:00:01Z')

    def test_next_due_at_microsecond(self):
        with pytest.raises(ValueError, match='next_due_at must be no more precise than minutes'):
            UptimeMonitorFactory.build(next_due_at='2026-01-01 12:00:00.000001Z')
