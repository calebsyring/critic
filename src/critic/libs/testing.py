import boto3


def create_uptime_monitor_table():
    client = boto3.client('dynamodb', region_name='us-east-2')
    client.create_table(
        TableName='Monitor',
        AttributeDefinitions=[
            # Primary key
            {'AttributeName': 'project_id', 'AttributeType': 'S'},
            {'AttributeName': 'slug', 'AttributeType': 'S'},
            # GSI attributes
            {'AttributeName': 'GSI_PK', 'AttributeType': 'S'},
            {'AttributeName': 'next_due_at', 'AttributeType': 'N'},
        ],
        KeySchema=[
            {'AttributeName': 'project_id', 'KeyType': 'HASH'},  # Partition key
            {'AttributeName': 'slug', 'KeyType': 'RANGE'},  # Sort key
        ],
        GlobalSecondaryIndexes=[
            {
                'IndexName': 'NextDueIndex',
                'KeySchema': [
                    {'AttributeName': 'GSI_PK', 'KeyType': 'HASH'},  # Static value "DUE_MONITOR"
                    {'AttributeName': 'next_due_at', 'KeyType': 'RANGE'},
                ],
                'Projection': {'ProjectionType': 'ALL'},
            }
        ],
        BillingMode='PAY_PER_REQUEST',
    )

    return client


def create_uptime_log_table():
    client = boto3.client('dynamodb', region_name='us-east-2')
    client.create_table(
        TableName='Logging',
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
    return client
