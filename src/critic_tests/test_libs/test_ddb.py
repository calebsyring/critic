import boto3

from critic.libs.ddb import deserializer, serializer
from critic.Monitor.MonitorIn import MonitorIn


def test_it():
    # Create the table
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

    # Pretend we've received data via the API
    API_DATA = {
        'project_id': 'my-project',
        'id': '6033aa47-a9f7-4d7f-b7ff-a11ba9b34474',
        'url': 'https://example.com/health',
        'interval': 5,
        'next_due_at': 1234567890,  # epoch seconds
        'timeout': 5,
        'assertions': {'status_code': 200, 'body_contains': 'OK'},
        'failures_before_alerting': 2,
        'alert_slack_channels': ['#ops'],
        'alert_emails': ['alerts@example.com'],
        'realert_interval': 600,
    }
    # Double-check data is valid
    MonitorIn(**API_DATA)

    # Convert the data to DDB JSON format and store it
    ddb_item = {k: serializer.serialize(v) for k, v in API_DATA.items()}
    client.put_item(TableName='Monitor', Item=ddb_item)

    # Retrieve the data and convert it back to a standard dict
    ddb_item = client.get_item(
        TableName='Monitor', Key={'project_id': {'S': 'my-project'}, 'id': {'S': API_DATA['id']}}
    )['Item']
    ddb_data = {k: deserializer.deserialize(v) for k, v in ddb_item.items()}
    assert ddb_data['id'] == '6033aa47-a9f7-4d7f-b7ff-a11ba9b34474'
