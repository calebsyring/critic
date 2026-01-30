from critic.libs.ddb import deserialize, get_client, serialize
from critic.monitor_utility import create_monitors, delete_monitors
from critic.tables import UptimeMonitorTable


def _query_project_items(table_name: str, project_id: str) -> list[dict]:
    resp = get_client().query(
        TableName=table_name,
        KeyConditionExpression='project_id = :project_id',
        ExpressionAttributeValues=serialize(
            {
                ':project_id': project_id,
            }
        ),
    )
    return [deserialize(item) for item in resp.get('Items', [])]


def test_create_and_delete_monitors():
    # Test creating and deleting monitors in DynamoDB.
    table_name = UptimeMonitorTable.name()

    project_id = '00000000-0000-0000-0000-000000000001'
    prefix = 'stress'

    created = create_monitors(
        table_name=table_name,
        project_id=project_id,
        prefix=prefix,
        count=10,
        ddb=None,
    )
    assert created == 10

    items = _query_project_items(table_name, project_id)
    assert len(items) == 10

    deleted = delete_monitors(
        table_name=table_name,
        project_id=project_id,
        prefix=prefix,
        ddb=None,
    )
    assert deleted == 10

    items_after = _query_project_items(table_name, project_id)
    assert items_after == []


def test_delete_only_matches_prefix():
    # Test that delete_monitors only deletes items matching the given prefix.
    table_name = UptimeMonitorTable.name()

    project_id = '00000000-0000-0000-0000-000000000001'
    prefix = 'stress'

    create_monitors(table_name, project_id, prefix, 5, ddb=None)
    create_monitors(table_name, project_id, 'other', 3, ddb=None)

    items_before = _query_project_items(table_name, project_id)
    assert len(items_before) == 8

    deleted = delete_monitors(table_name, project_id, prefix, ddb=None)
    assert deleted == 5

    items_after = _query_project_items(table_name, project_id)
    remaining_slugs = {item['slug'] for item in items_after}
    assert remaining_slugs == {f'other-{i:04d}' for i in range(1, 4)}
