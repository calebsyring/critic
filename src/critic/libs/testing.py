import boto3

from critic.libs.ddb import get_ddb_client, namespace_table


def create_tables():
    get_ddb_client().create_table(
        TableName=namespace_table('Project'),
        AttributeDefinitions=[
            {'AttributeName': 'id', 'AttributeType': 'S'},
        ],
        KeySchema=[
            {'AttributeName': 'id', 'KeyType': 'HASH'},
        ],
        BillingMode='PAY_PER_REQUEST',
    )

    get_ddb_client().create_table(
        TableName=namespace_table('UptimeMonitor'),
        AttributeDefinitions=[
            # Key attributes
            {'AttributeName': 'project_id', 'AttributeType': 'S'},
            {'AttributeName': 'slug', 'AttributeType': 'S'},
            # GSI attributes
            {'AttributeName': 'GSI_PK', 'AttributeType': 'S'},
            {'AttributeName': 'next_due_at', 'AttributeType': 'S'},
        ],
        KeySchema=[
            {'AttributeName': 'project_id', 'KeyType': 'HASH'},  # Partition key
            {'AttributeName': 'slug', 'KeyType': 'RANGE'},  # Sort key
        ],
        GlobalSecondaryIndexes=[
            {
                'IndexName': 'NextDueIndex',
                'KeySchema': [
                    {'AttributeName': 'GSI_PK', 'KeyType': 'HASH'},
                    {'AttributeName': 'next_due_at', 'KeyType': 'RANGE'},
                ],
                'Projection': {'ProjectionType': 'ALL'},
            }
        ],
        BillingMode='PAY_PER_REQUEST',
    )

    get_ddb_client().create_table(
        TableName=namespace_table('UptimeLog'),
        AttributeDefinitions=[
            {'AttributeName': 'monitor_id', 'AttributeType': 'S'},
            {'AttributeName': 'timestamp', 'AttributeType': 'S'},
        ],
        KeySchema=[
            {'AttributeName': 'monitor_id', 'KeyType': 'HASH'},
            {'AttributeName': 'timestamp', 'KeyType': 'RANGE'},
        ],
        BillingMode='PAY_PER_REQUEST',
    )


def _clear_table(table_name: str):
    """Delete all items from a DDB table without deleting the table itself."""
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(table_name)

    # Only project the key(s) to reduce read cost
    key_schema = table.key_schema

    # Build safe aliases for key attributes
    expr_attr_names = {}
    projection_parts = []
    for key in key_schema:
        attr = key['AttributeName']
        alias = f'#{attr}'
        expr_attr_names[alias] = attr
        projection_parts.append(alias)
    projection = ', '.join(projection_parts)

    scan_kwargs = {
        'ProjectionExpression': projection,
        'ExpressionAttributeNames': expr_attr_names,
    }

    with table.batch_writer() as batch:
        while True:
            response = table.scan(**scan_kwargs)

            for item in response['Items']:
                batch.delete_item(Key=item)

            if 'LastEvaluatedKey' not in response:
                break

            scan_kwargs['ExclusiveStartKey'] = response['LastEvaluatedKey']


def clear_tables():
    for table_name in [namespace_table(t) for t in ('Project', 'UptimeMonitor', 'UptimeLog')]:
        _clear_table(table_name)
