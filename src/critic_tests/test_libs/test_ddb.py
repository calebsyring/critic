import boto3

from critic.libs.ddb import deserializer, serializer
from critic.Monitor.MonitorIn import MonitorIn


def test_it():
    # Create the table
    client = create_monitor_table()

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

    put_in_serialized(client, 'Monitor', API_DATA)
    ddb_data = get_deserialized_data(client, 'my-project', API_DATA['id'])

    assert ddb_data['id'] == '6033aa47-a9f7-4d7f-b7ff-a11ba9b34474'


def test_two_inputs():
    client = create_monitor_table()

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

    API_DATA_2 = {
        'project_id': 'my-project_2',
        'id': '6033aa47-a9f7-4d7f-b7ff-a11ba9b34475',
        'url': 'https://example.com/health',
        'interval': 7,
        'next_due_at': 1234567891,  # epoch seconds
        'timeout': 3,
        'assertions': {'status_code': 200, 'body_contains': 'OK'},
        'failures_before_alerting': 3,
        'alert_slack_channels': ['#ops_2'],
        'alert_emails': ['alerts_2@example.com'],
        'realert_interval': 1200,
    }

    MonitorIn(**API_DATA)
    MonitorIn(**API_DATA_2)

    put_in_serialized(client, 'Monitor', API_DATA)
    put_in_serialized(client, 'Monitor', API_DATA_2)
    
    ddb_data_2 = get_deserialized_data(client, 'my-project_2', API_DATA_2['id'])
   
    assert ddb_data_2['id'] == '6033aa47-a9f7-4d7f-b7ff-a11ba9b34475'
 


def create_monitor_table():
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

def get_deserialized_data(client, proj_id : str, data_id : str):
    ddb_item = client.get_item(
        TableName='Monitor', Key={'project_id': {'S': proj_id}, 'id': {'S': data_id}}
    )['Item']

    return {k: deserializer.deserialize(v) for k, v in ddb_item.items()}

def put_in_serialized(client, table_name : str, API_content : dict):
    ddb_item = {k: serializer.serialize(v) for k, v in API_content.items()}
    client.put_item(TableName=table_name, Item=ddb_item)