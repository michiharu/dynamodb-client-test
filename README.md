# クライアントのインスタンス化コストってどれぐらい？

AWS 公式ドキュメントの[Lambda を使用する際のベストプラクティス](https://docs.aws.amazon.com/ja_jp/lambda/latest/dg/best-practices.html)には以下のように記述されています。

> AWS のサービスのクライアントは、ハンドラではなく初期化コードでインスタンス化する必要があります。これにより、AWS Lambda コンテナは、コンテナの有効期間中は既存の接続を再利用することができます。

DynamoDB や S3 などのクライアントオブジェクトは Lambda の初期化処理でインスタンス化しましょう、ということですね。

私はこのドキュメントから、クライアントのインスタンス化ってどれぐらいの処理時間なのか気になりました。ベストプラクティスに沿って開発していれば要らないトリビアですが、折角検証したので記事にしました。

# 検証概要

この記事では DynamoDB クライアントを対象に、インスタンス化のコスト検証と、実際にありそうな good と bad のケースを用意してパフォーマンス検証を実施しました。尚、検証のためにそれぞれの処理を 100 回繰り返して時間を計測し、その平均値を算出しました。

### インスタンス化のコスト検証のケース

1. DynamoDB 用クライアントのインスタンス化
1. DynamoDB の Table オブジェクトのインスタンス化

### Good パターン, Bad パターンのパフォーマンス検証

1. Good: 初期化処理でインスタンス化した Table オブジェクトを使用して`put_item()`
1. Bad: 毎回 DynamoDB 用クライアントをインスタンス化して`put_item()`

# 前提

### Lambda

- Python3.8
- メモリー : 128MB

### DynamoDB

- テーブル名: test-items
- プライマリパーティションキー: id (文字列)
- プライマリソートキー: - (無し)
- 読み込み/書き込みキャパシティーモード : オンデマンド

### 「クライアント」という表現について(注意)

今回検証するのは DynamoDB の**リソースオブジェクト**のインスタンス化としました。

Boto3 は、公式ドキュメントでは[AWS SDK for Python](https://aws.amazon.com/jp/sdk-for-python/)として紹介されていますが、Boto3 には２種類の API が提供されており、その特徴について以下のように説明されています。

> Boto3 には、2 つの異なるレベルの API があります。クライアント（「低レベル」）API では、下層の HTTP API 操作との 1 対 1 のマッピングが提供されます。 リソース API では、明示的なネットワーク呼び出しが表示されず、属性にアクセスしアクションを実行するためのリソースオブジェクトとコレクションが提供されます。

私はこの説明を「まずやりたいことをリソース API を使ってシンプルに実現できそうか考え、そうでない場合のみクライアント API を使うことを検討すべし」と解釈しています。

ですので、私にとってはリソースオブジェクトの方が使う頻度が高いので、リソースオブジェクトを検証対象にしました。

この記事には「DynamoDB 用クライアント」などの表現で「クライアント」という言葉がたくさん登場していますが、HTTP リクエストをいい感じに扱ってくれるオブジェクトとしてクライアントという表現を使用しています。今回の検証に限ってそれらはすべて Boto3 のリソースオブジェクトのことであり、低レベル API であるクライアントオブジェクトと混同されませんようご注意ください。

# DynamoDB 用クライアントのインスタンス化

DynamoDB 用クライアントのインスタンス化を 100 回繰り返して平均処理時間を計測します。

### 結果 63 ミリ秒(平均値)

### コード

```python
def show_cost1():
    # 計測開始
    start = time.time()
    for i in range(times):
        boto3.resource("dynamodb")

    # 計測終了
    return (time.time() - start) / times
```

###### コメント

へ〜

# DynamoDB の Table オブジェクトのインスタンス化

DynamoDB の Table オブジェクトのインスタンス化を 100 回繰り返して平均処理時間を計測します。

### 結果 90 ミリ秒(平均値)

### コード

```python
def show_cost2():
    # 計測開始
    start = time.time()
    for i in range(times):
        boto3.resource("dynamodb").Table(TEST_TABLE)

    # 計測終了
    return (time.time() - start) / times
```

###### コメント

へ〜 へ〜 へ〜 Table オブジェクトのインスタンス化は、DynamoDB 用クライアント(resourse)のインスタンス化に、追加で 27 ミリ秒も掛かるんですね。予想よりもコストが高い印象です。

# Good パターン, Bad パターンのパフォーマンス検証

`put_item()`する際に、生成済みクライアントオブジェクトを使うパターンとクライアントを都度生成するパターンで試します。100 回繰り返し処理させて平均の処理時間を計測します。実務でレコードをテーブルに 100 回追加するようなケースでは[batch_writer()](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/dynamodb.html#DynamoDB.Table.batch_writer)を使いましょう。あくまで`put_item()`の平均の処理時間を計測するためのコードなので、その点はご留意ください。

書き込むデータのスキーマを表現したクラスは次の通りです。

```python
@dataclass
class Item:
    id: str
    count: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
```

## Good パターン

初期化処理でインスタンス化した Table オブジェクトを使用して`put_item()`

### 結果 39 ミリ秒(平均値)

###  コード

```python
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

def good_pattern():
    # データ準備
    items = [Item(str(uuid4()), i) for i in range(times)]

    # 計測開始
    start = time.time()
    for item in items:
        table.put_item(Item=item.to_dict())

    # 計測終了
    return (time.time() - start) / times
```

###### コメント

へ〜

### Bad パターン

毎回 DynamoDB 用クライアントをインスタンス化して`put_item()`

### 結果 257 ミリ秒(平均値)

```python
import boto3
import mypy_boto3_dynamodb as dynamodb

TEST_TABLE = "test-items"
times = 100

@dataclass
class Item:
    id: str
    count: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

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
```

###### コメント

へ〜！！！！ めっちゃ遅い。約 6~7 倍も掛かるんですね。

# 検証コード全体

検証用コードのリポジトリはこちらです。→ [dynamodb-client-test](https://github.com/michiharu/dynamodb-client-test/settings)

```python
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
```

# まとめ

公式ドキュメントはよく読んで、ベストプラクティスを意識して実装しましょう。
