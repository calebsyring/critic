import boto3


def create_uptime_monitor_table():
    client = boto3.client('dynamodb', region_name='us-east-2')
    client.create_table(
        TableName='Monitor',
        AttributeDefinitions=[
            # Primary key
            {'AttributeName': 'project_id', 'AttributeType': 'S'},
            {'AttributeName': 'id', 'AttributeType': 'S'},
            # GSI attributes
            {'AttributeName': 'GSI_PK', 'AttributeType': 'S'},
            {'AttributeName': 'next_due_at', 'AttributeType': 'N'},
        ],
        KeySchema=[
            {'AttributeName': 'project_id', 'KeyType': 'HASH'},  # Partition key
            {'AttributeName': 'id', 'KeyType': 'RANGE'},  # Sort key
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
