"""
MQTT を subscribe してセンサーデータを InfluxDB に書き込むデータ収集サービス。

起動方法:
    python -m collector.main
"""

import json
import os
import paho.mqtt.client as mqtt
from dotenv import load_dotenv

from .influx_client import EnvInfluxClient
from common import messages

load_dotenv()

# MQTT トピック（prefix の配下全てを購読する）
_TOPIC = os.getenv("MQTT_TOPIC_PREFIX", "iot/environment") + "/#"

# モジュールレベルで初期化して on_message から共有する
_influx = EnvInfluxClient()


def on_connect(
    client: mqtt.Client,
    userdata: object,
    flags: dict,
    reason_code: object,
    properties: object,
) -> None:
    """MQTT ブローカーへの接続完了時に呼ばれるコールバック。

    接続成功後にセンサートピックを subscribe する。

    Args:
        client:      MQTT クライアントインスタンス
        userdata:    ユーザー定義の追加データ（未使用）
        flags:       ブローカーからの接続フラグ
        reason_code: 接続結果コード
        properties:  MQTTv5 プロパティ（MQTTv3 では None）
    """
    print(messages.MQTT_CONNECTED.format(reason_code=reason_code))
    client.subscribe(_TOPIC)
    print(messages.MQTT_SUBSCRIBED.format(topic=_TOPIC))


def on_message(
    client: mqtt.Client,
    userdata: object,
    msg: mqtt.MQTTMessage,
) -> None:
    """MQTT メッセージ受信時に呼ばれるコールバック。

    JSON ペイロードをデコードし、InfluxDB へ書き込む。
    デコードや書き込みに失敗した場合はエラーをログ出力して続行する。

    Args:
        client:   MQTT クライアントインスタンス（未使用）
        userdata: ユーザー定義の追加データ（未使用）
        msg:      受信した MQTT メッセージ
    """
    try:
        payload = json.loads(msg.payload.decode())
        _influx.write(payload)
        print(
            messages.DB_WRITE_OK.format(
                device_id=payload["device_id"],
                temperature=payload["temperature"],
                co2=payload.get("co2"),
            )
        )
    except Exception as e:
        print(messages.MSG_PROCESS_ERROR.format(error=e))


def main() -> None:
    """収集サービスのエントリーポイント。MQTT 接続して無限ループで受信待機する。

    Raises:
        KeyboardInterrupt: Ctrl+C で停止
    """
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(
        os.getenv("MQTT_BROKER_HOST", "localhost"),
        int(os.getenv("MQTT_BROKER_PORT", "1883")),
    )
    print(messages.COLLECTOR_STARTED)
    client.loop_forever()


if __name__ == "__main__":
    main()
