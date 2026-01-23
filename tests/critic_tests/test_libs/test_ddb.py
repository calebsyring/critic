from datetime import datetime

import pytest

from critic.models import UptimeMonitorModel
from critic.tables import UptimeMonitorTable


class TestDDB:
    @pytest.mark.integration
    def test_integration(self):
        # Pretend we've received data via the API
        IN_DATA = {
            'project_id': '6033aa47-a9f7-4d7f-b7ff-a11ba9b34474',
            'slug': 'my-monitor',
            'url': 'https://example.com/health',
            'frequency_mins': 5,
            'next_due_at': '2025-11-10T20:35:00Z',
            'timeout_secs': 30,
            'assertions': {'status_code': 200, 'body_contains': 'OK'},
            'failures_before_alerting': 2,
            'alert_slack_channels': ['#ops'],
            'alert_emails': ['alerts@example.com'],
            'realert_interval_mins': 60,
        }

        # Put data in
        UptimeMonitorTable.put(IN_DATA)

        # Get it back out
        out_data = UptimeMonitorTable.get('6033aa47-a9f7-4d7f-b7ff-a11ba9b34474', 'my-monitor')

        # Check one of the values to make sure it's what we expect
        assert str(out_data.url) == 'https://example.com/health'

    @pytest.mark.parametrize('input_as_model', [True, False])
    def test_unit(self, input_as_model):
        # Pretend we've received data via the API
        in_data = {
            'project_id': '6033aa47-a9f7-4d7f-b7ff-a11ba9b34474',
            'slug': 'my-monitor',
            'url': 'https://example.com/health',
            'frequency_mins': 5,
            'next_due_at': '2025-11-10T20:35:00Z',
            'timeout_secs': 30,
            'assertions': {'status_code': 200, 'body_contains': 'OK'},
            'failures_before_alerting': 2,
            'alert_slack_channels': ['#ops'],
            'alert_emails': ['alerts@example.com'],
            'realert_interval_mins': 60,
        }

        if input_as_model:
            in_data = UptimeMonitorModel(**in_data)

        # Put data in
        UptimeMonitorTable.put(in_data)

        # Get it back out
        out_data = UptimeMonitorTable.get('6033aa47-a9f7-4d7f-b7ff-a11ba9b34474', 'my-monitor')

        # Check one of the values to make sure it's what we expect
        assert str(out_data.url) == 'https://example.com/health'

    def test_missing_sort_key(self):
        # The table has a sort key, but we haven't provided one to get(), so this should raise an
        # error.
        with pytest.raises(ValueError):
            UptimeMonitorTable.get('6033aa47-a9f7-4d7f-b7ff-a11ba9b34474')

    def test_serialize_unaware_dt(self):
        with pytest.raises(ValueError, match='must be timezone aware'):
            UptimeMonitorTable.get_due_since(datetime.now())
