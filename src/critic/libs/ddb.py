from decimal import Decimal
import os

from boto3 import client
from boto3.dynamodb.types import TypeDeserializer, TypeSerializer
from pydantic import BaseModel


client = client('dynamodb')
serializer = TypeSerializer()
deserializer = TypeDeserializer()


def serialize(data: dict) -> dict:
    """Serialize standard JSON to DynamoDB format."""
    return {k: serializer.serialize(v) for k, v in data.items()}


def deserialize(data: dict) -> dict:
    """Deserialize DynamoDB format to standard JSON."""
    return {k: deserializer.deserialize(v) for k, v in data.items()}


def namespace_table(table_name: str) -> str:
    return f'{table_name}-{os.environ["CRITIC_NAMESPACE"]}'


def floats_to_decimals(value):
    if isinstance(value, float):
        return Decimal(str(value))

    if isinstance(value, list):
        return [floats_to_decimals(v) for v in value]

    if isinstance(value, dict):
        return {k: floats_to_decimals(v) for k, v in value.items()}

    return value


class Table:
    name: str
    model: type[BaseModel]
    partition_key: str
    sort_key: str | None = None

    @staticmethod
    def model_to_ddb(inst: BaseModel) -> dict:
        """Convert a Pydantic model instance to a DynamoDB-compatible dict."""
        plain = inst.model_dump(mode='json', exclude_none=True)
        return serialize(floats_to_decimals(plain))

    @classmethod
    def table_name(cls):
        return namespace_table(cls.name)

    @classmethod
    def put(cls, data: dict | BaseModel):
        if isinstance(data, dict):
            data = cls.model(**data)
        client.put_item(TableName=cls.table_name(), Item=cls.model_to_ddb(data))

    @classmethod
    def get(cls, partition_value: str | int, sort_value: str | int | None = None):
        # Construct key
        key = {cls.partition_key: partition_value}
        if (cls.sort_key is None) is not (sort_value is None):
            raise ValueError('Please make sure sort_value is provided iff table has a sort key.')
        if cls.sort_key is not None:
            key[cls.sort_key] = sort_value

        # Get item
        item = client.get_item(
            TableName=cls.table_name(),
            Key=serialize(key),
        )['Item']
        return cls.model(**deserialize(item))
