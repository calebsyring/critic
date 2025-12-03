import os

from boto3.dynamodb.types import TypeDeserializer, TypeSerializer


serializer = TypeSerializer()
deserializer = TypeDeserializer()


def namespace_table(table_name: str) -> str:
    return f'{table_name}-{os.environ["CRITIC_NAMESPACE"]}'
