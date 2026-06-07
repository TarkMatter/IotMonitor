"""
InfluxDB への書き込み・クエリを担うクライアントモジュール。

全接続情報は環境変数から取得する。直接インスタンス化せず
``EnvInfluxClient`` を利用すること。
"""

import os
from dotenv import load_dotenv
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

load_dotenv()

# 環境変数のデフォルト値定数
_DEFAULT_URL    = "http://localhost:8086"
_DEFAULT_TOKEN  = "my-super-secret-token"
_DEFAULT_ORG    = "IotMonitor"
_DEFAULT_BUCKET = "environment"


class EnvInfluxClient:
    """環境変数から接続情報を読み取る InfluxDB クライアント。

    Attributes:
        _client:    InfluxDB SDK クライアントインスタンス
        _write_api: 同期書き込み API
        _query_api: Flux クエリ API
        _bucket:    書き込み・読み取り対象バケット名
    """

    def __init__(self) -> None:
        """環境変数から接続情報を取得してクライアントを初期化する。"""
        self._client = InfluxDBClient(
            url=os.getenv("INFLUXDB_URL",   _DEFAULT_URL),
            token=os.getenv("INFLUXDB_TOKEN", _DEFAULT_TOKEN),
            org=os.getenv("INFLUXDB_ORG",   _DEFAULT_ORG),
        )
        # SYNCHRONOUS にすることで write() の呼び出し元がエラーを確実に捕捉できる
        self._write_api = self._client.write_api(write_options=SYNCHRONOUS)
        self._query_api = self._client.query_api()
        self._bucket    = os.getenv("INFLUXDB_BUCKET", _DEFAULT_BUCKET)

    def write(self, payload: dict) -> None:
        """センサーデータを InfluxDB の environment メジャメントに書き込む。

        Args:
            payload: MQTT メッセージから復号した辞書。
                     "device_id", "temperature", "humidity" は必須。
                     "co2", "pressure" はオプション。

        Raises:
            influxdb_client.rest.ApiException: InfluxDB への書き込みに失敗した場合
        """
        point = (
            Point("environment")
            .tag("device_id", payload["device_id"])
            .field("temperature", float(payload["temperature"]))
            .field("humidity",    float(payload["humidity"]))
            .field("pressure",    float(payload.get("pressure", 1013.0)))
        )
        if payload.get("co2") is not None:
            point = point.field("co2", int(payload["co2"]))

        self._write_api.write(
            bucket=self._bucket,
            record=point,
            write_precision=WritePrecision.SECONDS,
        )

    def query_recent(self, hours: int = 24, device_id: str | None = None) -> list[dict]:
        """過去 N 時間のセンサーデータを取得する。

        Args:
            hours:     過去何時間分を取得するか（デフォルト: 24）
            device_id: 特定デバイスに絞り込む場合に指定。None で全デバイス取得

        Returns:
            各レコードを辞書にしたリスト。キーは
            "time", "device_id", "temperature", "humidity", "co2", "pressure"
        """
        # デバイスフィルタは device_id が指定された場合のみ Flux クエリに追加する
        device_filter = (
            f'|> filter(fn: (r) => r["device_id"] == "{device_id}")'
            if device_id
            else ""
        )
        flux = f"""
from(bucket: "{self._bucket}")
  |> range(start: -{hours}h)
  |> filter(fn: (r) => r["_measurement"] == "environment")
  {device_filter}
  |> pivot(rowKey:["_time"], columnKey:["_field"], valueColumn:"_value")
  |> sort(columns: ["_time"])
"""
        tables = self._query_api.query(flux)
        return [
            {
                "time":        record.values["_time"].isoformat(),
                "device_id":   record.values.get("device_id"),
                "temperature": record.values.get("temperature"),
                "humidity":    record.values.get("humidity"),
                "co2":         record.values.get("co2"),
                "pressure":    record.values.get("pressure"),
            }
            for table in tables
            for record in table.records
        ]
