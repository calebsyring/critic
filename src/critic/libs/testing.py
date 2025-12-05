import boto3

from critic.libs.ddb import namespace_table


def create_tables():
    client = boto3.client('dynamodb', region_name='us-east-2')

    client.create_table(
        TableName=namespace_table('Project'),
        AttributeDefinitions=[
            {'AttributeName': 'id', 'AttributeType': 'S'},
        ],
        KeySchema=[
            {'AttributeName': 'id', 'KeyType': 'HASH'},
        ],
        BillingMode='PAY_PER_REQUEST',
    )

    client.create_table(
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
            {'AttributeName': 'project_id', 'KeyType': 'HASH'},
            {'AttributeName': 'slug', 'KeyType': 'RANGE'},
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

    client.create_table(
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
