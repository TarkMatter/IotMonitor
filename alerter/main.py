"""
MQTT を subscribe して閾値チェック → LINE/Slack アラート通知するサービス。

同一デバイスの連続アラートを ALERT_COOLDOWN_MINUTES で抑制する（要件 F-A-4）。

起動方法:
    python -m alerter.main
"""

import asyncio
import json
import os
from datetime import datetime, timedelta, timezone

import paho.mqtt.client as mqtt
from dotenv import load_dotenv

from .notifiers import notify
from .thresholds import check
from common import messages

load_dotenv()

# MQTT トピック（prefix の配下全てを購読する）
_TOPIC    = os.getenv("MQTT_TOPIC_PREFIX", "iot/environment") + "/#"
# クールダウン期間（分単位の環境変数を timedelta に変換）
_COOLDOWN = timedelta(minutes=int(os.getenv("ALERT_COOLDOWN_MINUTES", "15")))

# デバイスごとの最終通知時刻（インメモリ、サービス再起動でリセットされる）
_last_alerted: dict[str, datetime] = {}


def _should_notify(device_id: str) -> bool:
    """デバイスがクールダウン中でないかを判定する。

    Args:
        device_id: 判定対象のデバイス識別子

    Returns:
        通知すべき場合 True、クールダウン中は False
    """
    last = _last_alerted.get(device_id)
    return last is None or datetime.now(timezone.utc) - last > _COOLDOWN


def on_connect(
    client: mqtt.Client,
    userdata: object,
    flags: dict,
    reason_code: object,
    properties: object,
) -> None:
    """MQTT ブローカーへの接続完了時に呼ばれるコールバック。

    Args:
        client:      MQTT クライアントインスタンス
        userdata:    ユーザー定義の追加データ（未使用）
        flags:       ブローカーからの接続フラグ
        reason_code: 接続結果コード
        properties:  MQTTv5 プロパティ
    """
    print(messages.MQTT_CONNECTED.format(reason_code=reason_code))
    client.subscribe(_TOPIC)
    print(messages.MQTT_SUBSCRIBED.format(topic=_TOPIC))


def on_message(
    client: mqtt.Client,
    userdata: object,
    msg: mqtt.MQTTMessage,
) -> None:
    """MQTT メッセージ受信時に閾値チェックとアラート送信を行うコールバック。

    クールダウン中のデバイスは通知せずログだけ出力する。
    デコードや通知に失敗した場合はエラーをログ出力して続行する。

    Args:
        client:   MQTT クライアントインスタンス（未使用）
        userdata: ユーザー定義の追加データ（未使用）
        msg:      受信した MQTT メッセージ
    """
    try:
        payload  = json.loads(msg.payload.decode())
        device   = payload.get("device_id", "unknown")
        alert_msgs = check(payload)

        if not alert_msgs:
            return

        if _should_notify(device):
            text = messages.ALERT_TEXT_HEADER.format(device_id=device) + "\n".join(alert_msgs)
            # paho の on_message は同期コンテキストのため asyncio.run で非同期通知を実行する
            asyncio.run(notify(text))
            _last_alerted[device] = datetime.now(timezone.utc)
            print(messages.ALERT_NOTIFIED.format(device_id=device))
        else:
            print(messages.ALERT_COOLDOWN.format(device_id=device))

    except Exception as e:
        print(messages.GENERAL_ERROR.format(error=e))


def main() -> None:
    """アラートサービスのエントリーポイント。MQTT 接続して無限ループで受信待機する。

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
    print(messages.ALERTER_STARTED)
    client.loop_forever()


if __name__ == "__main__":
    main()
