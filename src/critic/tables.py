from critic.libs.ddb import Table

from .models import UptimeMonitorModel


class UptimeMonitorTable(Table):
    name = 'UptimeMonitor'
    model = UptimeMonitorModel
    partition_key = 'project_id'
    sort_key = 'slug'
