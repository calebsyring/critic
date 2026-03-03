from datetime import datetime
from unittest import mock

from botocore.exceptions import ClientError
import pytest

from critic.libs.assertions import Assertion
from critic.libs.testing import ProjectFactory, UptimeLogFactory, UptimeMonitorFactory
from critic.models import ProjectModel, UptimeLogModel, UptimeMonitorModel
from critic.tables import ProjectTable, UptimeLogTable, UptimeMonitorTable


class TestTable:
    @pytest.mark.integration
    def test_integration(self):
        # Pretend we've received data via the API
        UptimeMonitorFactory.put(
            project_id='6033aa47-a9f7-4d7f-b7ff-a11ba9b34474',
            slug='my-monitor',
            url='https://example.com/health',
            assertions=[
                Assertion(assertion_string='status_code == 200'),
                Assertion(assertion_string="body contains 'OK'"),
            ],
        )
        out_data = UptimeMonitorTable.get('6033aa47-a9f7-4d7f-b7ff-a11ba9b34474', 'my-monitor')

        # Check one of the values to make sure it's what we expect
        assert str(out_data.url) == 'https://example.com/health'

    @pytest.mark.parametrize('input_as_model', [True, False])
    def test_unit(self, input_as_model):
        # Sometimes we may want to pass input as a dict (not a model). Make sure we handle that.
        in_data = {
            'project_id': '6033aa47-a9f7-4d7f-b7ff-a11ba9b34474',
            'slug': 'my-monitor',
            'url': 'https://example.com/health',
            'frequency_mins': 5,
            'consecutive_fails': 0,
            'next_due_at': '2025-11-10T20:35:00Z',
            'timeout_secs': 30,
            'assertions': [
                Assertion(assertion_string='status_code == 200'),
                Assertion(assertion_string="body contains 'OK'"),
            ],
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

    def test_query_from_monitor_table(self):
        UptimeMonitorFactory.put(
            project_id='6033aa47-a9f7-4d7f-b7ff-a11ba9b34474',
            slug='my-monitor',
            url='https://example.com/health',
            assertions=[
                Assertion(assertion_string='status_code == 200'),
                Assertion(assertion_string="body contains 'OK'"),
            ],
        )

        out_data = UptimeMonitorTable.query('6033aa47-a9f7-4d7f-b7ff-a11ba9b34474')
        assert len(out_data) == 1
        assert str(out_data[0].url) == 'https://example.com/health'

    def test_serialize_unaware_dt(self):
        with pytest.raises(ValueError, match='must be timezone aware'):
            UptimeMonitorTable.get_due_since(datetime.now())

    def test_update_no_updates(self):
        with pytest.raises(ValueError, match='No updates provided'):
            UptimeMonitorTable.update('6033aa47-a9f7-4d7f-b7ff-a11ba9b34474', 'my-monitor', {})

    @mock.patch('critic.libs.ddb.get_client')
    def test_update_error_not_conditional(self, m_get_client):
        # We supress conditional check errors. Make sure that doesn't inadvertently suppress other
        # errors.
        error = ClientError({'Error': {'Code': 'SomeOtherError'}}, 'update_item')
        m_get_client.return_value.update_item.side_effect = error
        with pytest.raises(ClientError) as excinfo:
            UptimeMonitorTable.update(
                '6033aa47-a9f7-4d7f-b7ff-a11ba9b34474', 'my-monitor', {'a': 1}
            )
        assert excinfo.value == error

    def test_cascade_delete(self):
        # Happy path: deleting a project should delete all its monitors and logs
        del_proj: ProjectModel = ProjectFactory.put()

        del_mon: UptimeMonitorModel = UptimeMonitorFactory.put(project_id=del_proj.id)
        UptimeLogFactory.put(monitor_id=del_mon.id)
        UptimeLogFactory.put(monitor_id=del_mon.id)

        UptimeMonitorFactory.put(project_id=del_proj.id)

        # Sad path: These should all be left untouched
        keep_proj: ProjectModel = ProjectFactory.put()
        keep_mon: UptimeMonitorModel = UptimeMonitorFactory.put(project_id=keep_proj.id)
        keep_log: UptimeLogModel = UptimeLogFactory.put(monitor_id=keep_mon.id)

        # Delete the project
        ProjectTable.delete(del_proj.id)

        # Check the happy path (everything related to the deleted project should be gone)
        assert ProjectTable.get(del_proj.id) is None
        assert UptimeMonitorTable.query(del_mon.project_id) == []
        assert UptimeLogTable.query(del_mon.id) == []

        # Check the sad path (everything not related to the deleted project should be untouched)
        assert ProjectTable.get(keep_proj.id) == keep_proj
        assert UptimeMonitorTable.get(keep_mon.project_id, keep_mon.slug) == keep_mon
        assert UptimeLogTable.get(keep_log.monitor_id, keep_log.timestamp) == keep_log
