from datetime import datetime

from critic.libs.ddb import (
    CONSTANT_GSI_PK,
    CascadeRelationship,
    Table,
    deserialize,
    get_client,
    serialize,
)

from .models import ProjectModel, UptimeLogModel, UptimeMonitorModel


class ProjectTable(Table):
    base_name = 'Project'
    model = ProjectModel
    partition_key = 'id'

    @classmethod
    def cascade_relationships(cls) -> list[CascadeRelationship]:
        return [
            CascadeRelationship(
                UptimeMonitorTable,
                lambda pk, _sk: pk,
                lambda m: (m.project_id, m.slug),
            )
        ]


class UptimeMonitorTable(Table):
    base_name = 'UptimeMonitor'
    model = UptimeMonitorModel
    partition_key = 'project_id'
    sort_key = 'slug'

    @classmethod
    def cascade_relationships(cls) -> list[CascadeRelationship]:
        return [
            CascadeRelationship(
                UptimeLogTable,
                # TODO: have a universal function for this
                lambda pk, sk: UptimeLogModel.monitor_id_from_parts(pk, sk),
                lambda log: (log.monitor_id, log.timestamp),
            )
        ]

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


class UptimeLogTable(Table):
    base_name = 'UptimeLog'
    model = UptimeLogModel
    partition_key = 'monitor_id'
    sort_key = 'timestamp'
