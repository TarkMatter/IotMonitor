"""
センサなしでデモ用の模擬データを MQTT に流すシミュレーター。

サイン波 + ランダムノイズで自然な変動を生成するため、グラフが単調にならず
デモ映えする（要件 F-SIM-1）。PC だけで動作確認・デモ撮影が可能（要件 F-SIM-3）。

複数デバイスは DEVICE_IDS 環境変数にカンマ区切りで指定する。
各デバイスは独立したスレッドで並行してデータを publish する。
"""

import json
import math
import os
import random
import threading
import time
from datetime import datetime, timezone

import paho.mqtt.client as mqtt
from dotenv import load_dotenv

from .config import config
from common import messages

load_dotenv()

# デバイスごとのサイン波位相を管理する辞書（スレッドセーフに読み書きするため Lock を使用）
_phases: dict[str, float] = {}
_phases_lock = threading.Lock()


def _next_value(device_id: str, base: float, amplitude: float, noise_sigma: float) -> float:
    """デバイスごとのサイン波 + ガウスノイズで自然な変動値を生成する。

    デバイスごとに位相を独立管理することで、複数デバイスが同期して
    同じ値を出力しないようにする。

    Args:
        device_id:   デバイス識別子（位相管理のキー）
        base:        ベース値（平均値）
        amplitude:   サイン波の振れ幅
        noise_sigma: ガウスノイズの標準偏差

    Returns:
        生成した浮動小数点値（小数点1桁）
    """
    with _phases_lock:
        phase = _phases.get(device_id, random.uniform(0, 2 * math.pi))
        phase += 0.05
        _phases[device_id] = phase
    drift = amplitude * math.sin(phase)
    return round(base + drift + random.gauss(0, noise_sigma), 1)


def _build_payload(device_id: str, base_temp: float = 24.0) -> dict:
    """指定デバイスの模擬センサーデータを辞書形式で生成する。

    デバイスごとに base_temp をずらすことで、複数デバイスが
    異なる環境条件を表現する。

    Args:
        device_id: デバイス識別子
        base_temp: 温度のベース値（デバイスごとに変えて差異を出す）

    Returns:
        sensor_main.py と同一フォーマットのペイロード辞書（要件 F-SIM-2）
    """
    return {
        "device_id":   device_id,
        "timestamp":   datetime.now(timezone.utc).isoformat(),
        "temperature": _next_value(device_id, base=base_temp,  amplitude=3.0,  noise_sigma=0.2),
        "humidity":    _next_value(device_id, base=55.0,        amplitude=8.0,  noise_sigma=0.5),
        "co2":         int(_next_value(device_id, base=600,     amplitude=200,  noise_sigma=10)),
        "pressure":    _next_value(device_id, base=1013.0,      amplitude=2.0,  noise_sigma=0.1),
        # PM2.5 は室内外の状況を模擬（屋外に近い値から清潔な室内まで変動）
        "pm25":        round(abs(_next_value(device_id, base=12.0, amplitude=8.0, noise_sigma=1.0)), 1),
    }


def _device_loop(
    client: mqtt.Client,
    device_id: str,
    base_temp: float,
    interval_sec: int,
) -> None:
    """1 デバイス分のデータ送信ループ。スレッドとして起動される。

    Args:
        client:      共有 MQTT クライアント
        device_id:   このスレッドが担当するデバイス識別子
        base_temp:   温度シミュレーションのベース値
        interval_sec: publish 間隔（秒）
    """
    topic = f"{config.topic_prefix}/{device_id}"
    while True:
        payload = _build_payload(device_id, base_temp)
        client.publish(topic, json.dumps(payload))
        print(
            f"[{device_id}] " + messages.SIMULATOR_LOG.format(
                temperature=payload["temperature"],
                humidity=payload["humidity"],
                co2=payload["co2"],
            ) + f"  PM2.5:{payload['pm25']}μg/m³"
        )
        time.sleep(interval_sec)


def main() -> None:
    """シミュレーターのメインループ。

    DEVICE_IDS 環境変数にカンマ区切りで複数デバイス ID を指定できる。
    未設定の場合は config.device_id（単一デバイス）にフォールバックする。
    各デバイスをスレッドで並行起動し、Ctrl+C で全スレッドを停止する。

    Raises:
        KeyboardInterrupt: Ctrl+C で停止
    """
    # DEVICE_IDS=raspi-01,raspi-02 のようにカンマ区切りで複数指定可能
    device_ids_env = os.getenv("DEVICE_IDS", "")
    device_ids = [d.strip() for d in device_ids_env.split(",") if d.strip()] or [config.device_id]

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.connect(config.broker_host, config.broker_port)
    client.loop_start()

    print(messages.SIMULATOR_STARTED.format(device_id=", ".join(device_ids)))
    print(messages.SIMULATOR_STOP_HINT)

    threads: list[threading.Thread] = []
    for i, device_id in enumerate(device_ids):
        # デバイスごとに温度ベースを 2℃ずつずらして環境差を表現する
        base_temp = 24.0 + i * 2.0
        t = threading.Thread(
            target=_device_loop,
            args=(client, device_id, base_temp, config.read_interval_sec),
            daemon=True,
        )
        t.start()
        threads.append(t)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
