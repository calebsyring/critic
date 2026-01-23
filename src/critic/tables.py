from datetime import datetime

from critic.libs.ddb import CONSTANT_GSI_PK, Table, deserialize, get_client, serialize

from .models import UptimeMonitorModel


class UptimeMonitorTable(Table):
    base_name = 'UptimeMonitor'
    model = UptimeMonitorModel
    partition_key = 'project_id'
    sort_key = 'slug'

    @classmethod
    def get_due_since(cls, timestamp: datetime) -> list[UptimeMonitorModel]:
        response = get_client().query(
            TableName=cls.name(),
            IndexName='NextDueIndex',
            KeyConditionExpression='GSI_PK = :pk AND next_due_at <= :timestamp',
            ExpressionAttributeValues=serialize(
                {
                    ':pk': CONSTANT_GSI_PK,
                    ':timestamp': timestamp,
                }
            ),
        )
        return [cls.model(**deserialize(item)) for item in response['Items']]
