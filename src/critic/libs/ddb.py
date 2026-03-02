from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
import os
from typing import Any
from uuid import UUID

from boto3 import client
from boto3.dynamodb.types import TypeDeserializer, TypeSerializer
from botocore.exceptions import ClientError
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


@dataclass
class CascadeRelationship:
    child_table: type['Table']
    # Given the parent's partition and sort keys, return the child's partition key for querying
    get_child_query_key: Callable[[Any, Any | None], Any]
    # Given the child, return the child's partition and sort key for deletion
    get_child_delete_keys: Callable[[BaseModel], tuple[Any, Any | None]]


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
        names, values, clauses = cls.alias({cls.partition_key: partition_value})

        response = get_client().query(
            TableName=cls.name(),
            KeyConditionExpression=clauses[0],
            ExpressionAttributeNames=names,
            ExpressionAttributeValues=values,
        )

        items = response.get('Items', [])
        print(items)
        return [cls.model(**deserialize(item)) for item in items]

    @staticmethod
    def alias(data: dict, val_suffix: str = '') -> tuple[dict, dict, list]:
        """
        Serializes a dict of key-value pairs and returns:
        1. A dict mapping aliased keys to actual keys (often used as ExpressionAttributeNames)
           Ex. {'#key1': 'key1', '#key2': 'key2'}
        2. A dict mapping aliased values to actual values (often used as ExpressionAttributeValues)
           Ex. {':key1': 'value1', ':key2': 'value2'}
        3. A list of aliased key-value pairs in DDB expression format (often used in *Expression)
           Ex. ['#key1 = :key1', '#key2 = :key2']

        Sometimes you may want to use the same key with different values in different expressions.
        For example, the condition expression may require a key to have one value while the update
        expression will set it to another. In that case, you can pass a suffix to differentiate
        them.

        You can then safely combine the results of multiple calls to this function into
        ExpressionAttributeValues. You'll have something that looks like this:
        {':key-suffix1': 'value1', ':key-suffix2': 'value2'}
        """
        data = serialize(data)
        names = {f'#{k}': k for k in data}
        values = {f':{k}{val_suffix}': v for k, v in data.items()}
        clauses = [f'#{k} = :{k}{val_suffix}' for k in data]
        return names, values, clauses

    @staticmethod
    def alias_all(*data: dict) -> tuple[dict, dict, list[list]]:
        """
        Calls alias() for each dict and returns the combined results. See alias() for more info.
        """
        names, values, clauses = {}, {}, []
        for i, d in enumerate(data):
            n, v, c = Table.alias(d, f'_{i}')
            names |= n
            values |= v
            clauses.append(c)
        return names, values, clauses

    @classmethod
    def update(
        cls,
        partition_value: Any,
        sort_value: Any | None = None,
        updates: dict | None = None,
        condition: dict | None = None,
    ) -> bool:
        if not updates:
            raise ValueError('No updates provided')

        if condition:
            names, values, clauses = cls.alias_all(updates, condition)
            update_clauses, cond_clauses = clauses
        else:
            names, values, update_clauses = cls.alias(updates)

        kwargs = {
            'TableName': cls.name(),
            'Key': cls.key(partition_value, sort_value),
            'UpdateExpression': 'SET ' + ', '.join(update_clauses),
            'ExpressionAttributeNames': names,
            'ExpressionAttributeValues': values,
        }
        if condition:
            kwargs['ConditionExpression'] = ' AND '.join(cond_clauses)

        try:
            get_client().update_item(**kwargs)
        except ClientError as e:
            if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                return False
            raise
        return True

    @classmethod
    def cascade_relationships(cls) -> list[CascadeRelationship]:
        return []

    @classmethod
    def delete(cls, partition_value: Any, sort_value: Any | None = None):
        for rel in cls.cascade_relationships():
            child_partition_key = rel.get_child_query_key(partition_value, sort_value)
            for child in rel.child_table.query(child_partition_key):
                rel.child_table.delete(*rel.get_child_delete_keys(child))

        get_client().delete_item(
            TableName=cls.name(),
            Key=cls.key(partition_value, sort_value),
        )
