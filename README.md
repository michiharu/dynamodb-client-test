# dynamodb-client-test

このリポジトリは、AWS の Lambda で DynamoDB のクライアントを扱う際のパフォーマンスを検証するためのコードです。

より具体的には、「Lambda から DynamoDB に`put_item()`で 1 レコードを登録するための平均処理時間の確認」のためのコードです。

## 検証ケース

以下の２つのケースについて検証します。

- good pattern: DynamoDB 用クライアントを初期化処理で準備する
- bad pattern: DynamoDB 用クライアントを`put_item()`の直前で用意する

good pattarn は AWS 公式ドキュメントによるベストプラクティスです。

## 検証結果

- good pattarn: "avg_time: 0.06340438890457153[sec]"
- bad pattern: "avg_time: 0.2664264960289002[sec]"
