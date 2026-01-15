from critic.libs.ddb import Table

from .models import UptimeLog, UptimeMonitorModel


class UptimeMonitorTable(Table):
    name = 'UptimeMonitor'
    model = UptimeMonitorModel
    partition_key = 'project_id'
    sort_key = 'slug'


class UptimeLogTable(Table):
    name = 'UptimeLog'
    model = UptimeLog
    partition_key = 'monitor_id'
    sort_key = 'timestamp'
