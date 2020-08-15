from typing import Any, Dict
import time
from dataclasses import dataclass, asdict
from uuid import uuid4

import boto3
import mypy_boto3_dynamodb as dynamodb

resource: dynamodb.DynamoDBServiceResource = boto3.resource("dynamodb")

TEST_TABLE = "test-items"
times = 1000


@dataclass
class Item:
    id: str
    count: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def get_records(table, **kwargs):
    while True:
        response = table.scan(**kwargs)
        for item in response["Items"]:
            yield item
        if "LastEvaluatedKey" not in response:
            break
        kwargs.update(ExclusiveStartKey=response["LastEvaluatedKey"])


def delete_items():
    table = resource.Table(TEST_TABLE)
    with table.batch_writer() as batch:
        for record in get_records(table):
            batch.delete_item(Key={"id": record["id"]})


def put_items_good_pattern():
    start = time.time()
    for i in range(times):
        item = Item(str(uuid4()), i)
        table = resource.Table(TEST_TABLE)
        table.put_item(Item=item.to_dict())
    return time.time() - start


def put_items_bad_pattern():
    start = time.time()
    for i in range(times):
        item = Item(str(uuid4()), i)
        resource: dynamodb.DynamoDBServiceResource = boto3.resource("dynamodb")
        table = resource.Table(TEST_TABLE)
        table.put_item(Item=item.to_dict())
    return time.time() - start


def lambda_handler(event, context):
    if event["case"] == "good":
        elapsed_time = put_items_good_pattern()
        return f"elapsed_time: {elapsed_time}[sec]"

    if event["case"] == "bad":
        elapsed_time = put_items_bad_pattern()
        return f"elapsed_time: {elapsed_time}[sec]"

    if event["case"] == "delete":
        delete_items()


if __name__ == "__main__":
    lambda_handler({"good": False, "bad": False, "delete": True}, None)
