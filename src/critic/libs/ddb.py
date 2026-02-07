from datetime import datetime
from decimal import Decimal
import os
from typing import Any
from uuid import UUID

from boto3 import client
from boto3.dynamodb.types import TypeDeserializer, TypeSerializer
from pydantic import AwareDatetime, BaseModel, TypeAdapter

from critic.libs.dt import to_utc


# https://www.reddit.com/r/aws/comments/cwams9/dynamodb_i_need_to_sort_whole_table_by_range_how/
CONSTANT_GSI_PK = 'bogus'
_ddb_client = None


def get_client():
    """
    Get a boto3 DynamoDB client without recreating it if it already exists.
    """
    global _ddb_client
    if _ddb_client is None:
        _ddb_client = client('dynamodb')
    return _ddb_client


class Serializer:
    """Serialize standard JSON to DynamoDB format."""

    _serializer = TypeSerializer()
    _aware_dt_adapter = TypeAdapter(AwareDatetime)

    @staticmethod
    def dt_to_str(value):
        if isinstance(value, datetime):
            # Convert datetime to string in the same way Pydantic does to ensure consistency
            return Serializer._aware_dt_adapter.dump_python(to_utc(value), mode='json')
        return value

    @staticmethod
    def float_to_decimal(value):
        if isinstance(value, float):
            return Decimal(str(value))

        if isinstance(value, UUID):
            return str(value)

        if isinstance(value, list):
            return [Serializer.float_to_decimal(v) for v in value]

        if isinstance(value, dict):
            return {k: Serializer.float_to_decimal(v) for k, v in value.items()}

        return value

    def serialize(self, value):
        value = self.dt_to_str(value)
        value = self.float_to_decimal(value)
        return self._serializer.serialize(value)

    def __call__(self, data: dict) -> dict:
        return {k: self.serialize(v) for k, v in data.items()}


class Deserializer:
    """Deserialize DynamoDB format to standard JSON."""

    _deserializer = TypeDeserializer()

    def __call__(self, data: dict) -> dict:
        return {k: self._deserializer.deserialize(v) for k, v in data.items()}


serialize = Serializer()
deserialize = Deserializer()


class Table:
    base_name: str
    model: type[BaseModel]
    partition_key: str
    sort_key: str | None = None

    @staticmethod
    def model_to_ddb(inst: BaseModel) -> dict:
        """Convert a Pydantic model instance to a DynamoDB-compatible dict."""
        plain = inst.model_dump(mode='json', exclude_none=True)
        return serialize(plain)

    @classmethod
    def ddb_to_model(cls, item: dict) -> BaseModel:
        """Convert a DynamoDB item to a Pydantic model instance."""
        return cls.model(**deserialize(item))

    @staticmethod
    def namespace(table_name: str) -> str:
        return f'{table_name}-{os.environ["CRITIC_NAMESPACE"]}'

    @classmethod
    def name(cls) -> str:
        namespace = os.environ.get('CRITIC_NAMESPACE', '')
        if namespace in ('prod', 'qa'):
            # Prod and QA envs don't have namespaced tables
            return cls.base_name
        return cls.namespace(cls.base_name)

    @classmethod
    def key(cls, partition_value: Any, sort_value: Any | None = None) -> dict:
        key = {cls.partition_key: partition_value}
        if (cls.sort_key is None) is not (sort_value is None):
            raise ValueError('Please make sure sort_value is provided iff table has a sort key.')
        if cls.sort_key is not None:
            key[cls.sort_key] = sort_value
        return serialize(key)

    @classmethod
    def put(cls, data: dict | BaseModel):
        if isinstance(data, dict):
            data = cls.model(**data)
        client = get_client()
        client.put_item(TableName=cls.name(), Item=cls.model_to_ddb(data))

    @classmethod
    def get(cls, partition_value: Any, sort_value: Any | None = None) -> BaseModel | None:
        response = get_client().get_item(
            TableName=cls.name(),
            Key=cls.key(partition_value, sort_value),
        )
        return cls.ddb_to_model(response['Item']) if 'Item' in response else None

    @classmethod
    def query(cls, partition_value: Any) -> list[BaseModel]:
        """Query for all items with the given partition key."""
        # We use aliases for the partition key to avoid reserved word conflicts
        pk_alias = f'#{cls.partition_key}'

        response = get_client().query(
            TableName=cls.name(),
            KeyConditionExpression=f'{pk_alias} = :pk',
            ExpressionAttributeNames={pk_alias: cls.partition_key},
            ExpressionAttributeValues=serialize({':pk': partition_value}),
        )

        items = response.get('Items', [])
        return [cls.model(**deserialize(item)) for item in items]

    @staticmethod
    def alias_exp(data: dict, suffix: str = '') -> tuple[dict, dict, list]:
        """
        Creates aliases for all keys and values in the data. Accepts a suffix for differentiation
        when you want to use the same key with different values in different expressions.
        """
        data = serialize(data)
        # Map aliased keys to actual keys (typically passed as ExpressionAttributeNames)
        names = {f'#{k}{suffix}': k for k in data}
        # Map aliased values to actual values (typically passed as ExpressionAttributeValues)
        values = {f':{k}{suffix}': v for k, v in data.items()}
        # Map aliased key-value pairs in DDB expression format (typically passed in *Expression)
        clauses = [f'#{k}{suffix} = :{k}{suffix}' for k in data]
        return names, values, clauses

    @classmethod
    def update(
        cls,
        partition_value: Any,
        sort_value: Any | None = None,
        updates: dict | None = None,
        condition: dict | None = None,
    ):
        if not updates:
            raise ValueError('No updates provided')

        expr_attr_names, expr_attr_values, set_clauses = cls.alias_exp(updates, 'update')
        kwargs = {
            'TableName': cls.name(),
            'Key': cls.key(partition_value, sort_value),
            'UpdateExpression': 'SET ' + ', '.join(set_clauses),
            'ExpressionAttributeNames': expr_attr_names,
            'ExpressionAttributeValues': expr_attr_values,
        }
        if condition:
            cond_names, cond_values, cond_clauses = cls.alias_exp(condition, 'cond')
            kwargs['ExpressionAttributeNames'] |= cond_names
            kwargs['ExpressionAttributeValues'] |= cond_values
            kwargs['ConditionExpression'] = ' AND '.join(cond_clauses)

        get_client().update_item(**kwargs)

    @classmethod
    def delete(cls, partition_value: Any, sort_value: Any | None = None):
        get_client().delete_item(
            TableName=cls.name(),
            Key=cls.key(partition_value, sort_value),
        )
