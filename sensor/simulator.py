"""
センサなしでデモ用の模擬データを MQTT に流すシミュレーター。

サイン波 + ランダムノイズで自然な変動を生成するため、グラフが単調にならず
デモ映えする（要件 F-SIM-1）。PC だけで動作確認・デモ撮影が可能（要件 F-SIM-3）。
"""

import json
import time
import random
import math
from datetime import datetime, timezone
import paho.mqtt.client as mqtt

from .config import config
from common import messages

# サイン波の位相を管理するグローバル変数（自然な変動のため状態を保持）
_phase: float = 0.0


def _next_value(base: float, amplitude: float, noise_sigma: float) -> float:
    """サイン波 + ガウスノイズで自然な変動値を生成する。

    Args:
        base: ベース値（平均値）
        amplitude: サイン波の振れ幅
        noise_sigma: ガウスノイズの標準偏差

    Returns:
        生成した浮動小数点値（小数点1桁）
    """
    global _phase
    _phase += 0.05
    drift = amplitude * math.sin(_phase)
    return round(base + drift + random.gauss(0, noise_sigma), 1)


def _build_payload() -> dict:
    """現在の模擬センサーデータを辞書形式で生成する。

    Returns:
        sensor_main.py と同一フォーマットのペイロード辞書（要件 F-SIM-2）
    """
    return {
        "device_id":   config.device_id,
        "timestamp":   datetime.now(timezone.utc).isoformat(),
        "temperature": _next_value(base=24.0, amplitude=3.0, noise_sigma=0.2),
        "humidity":    _next_value(base=55.0, amplitude=8.0, noise_sigma=0.5),
        "co2":         int(_next_value(base=600, amplitude=200, noise_sigma=10)),
        "pressure":    _next_value(base=1013.0, amplitude=2.0, noise_sigma=0.1),
    }


def main() -> None:
    """シミュレーターのメインループ。MQTT 接続後、一定間隔でデータを publish する。

    Raises:
        KeyboardInterrupt: Ctrl+C で停止
    """
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.connect(config.broker_host, config.broker_port)
    client.loop_start()

    print(messages.SIMULATOR_STARTED.format(device_id=config.device_id))
    print(messages.SIMULATOR_STOP_HINT)

    while True:
        payload = _build_payload()
        topic = f"{config.topic_prefix}/{config.device_id}"
        client.publish(topic, json.dumps(payload))
        print(
            messages.SIMULATOR_LOG.format(
                temperature=payload["temperature"],
                humidity=payload["humidity"],
                co2=payload["co2"],
            )
        )
        time.sleep(config.read_interval_sec)


if __name__ == "__main__":
    main()
