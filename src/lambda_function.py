from typing import Any, Dict
import time
from dataclasses import dataclass, asdict
from uuid import uuid4

import boto3
import mypy_boto3_dynamodb as dynamodb

TEST_TABLE = "test-items"
times = 100
resource: dynamodb.DynamoDBServiceResource = boto3.resource("dynamodb")
table = resource.Table(TEST_TABLE)


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


def show_cost1():
    # 計測開始
    start = time.time()
    for i in range(times):
        boto3.resource("dynamodb")

    # 計測終了
    return (time.time() - start) / times


def show_cost2():
    # 計測開始
    start = time.time()
    for i in range(times):
        boto3.resource("dynamodb").Table(TEST_TABLE)

    # 計測終了
    return (time.time() - start) / times


def good_pattern():
    # データ準備
    items = [Item(str(uuid4()), i) for i in range(times)]

    # 計測開始
    start = time.time()
    for item in items:
        table.put_item(Item=item.to_dict())

    # 計測終了
    return (time.time() - start) / times


def bad_pattern():
    # データ準備
    items = [Item(str(uuid4()), i) for i in range(times)]

    # 計測開始
    start = time.time()
    for item in items:
        table = boto3.resource("dynamodb").Table(TEST_TABLE)
        table.put_item(Item=item.to_dict())

    # 計測終了
    return (time.time() - start) / times


def lambda_handler(event, context):
    if event["case"] == "show1":
        avg_time = show_cost1()
        return f"avg_time: {avg_time}[sec]"

    if event["case"] == "show2":
        avg_time = show_cost2()
        return f"avg_time: {avg_time}[sec]"

    if event["case"] == "good":
        avg_time = good_pattern()
        return f"avg_time: {avg_time}[sec]"

    if event["case"] == "bad":
        avg_time = bad_pattern()
        return f"avg_time: {avg_time}[sec]"

    if event["case"] == "delete":
        delete_items()


if __name__ == "__main__":
    lambda_handler({"case": "delete"}, None)
