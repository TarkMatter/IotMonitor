"""
センサー・MQTT 接続の設定モジュール。

全設定値は環境変数から取得し、ハードコードを禁止する（要件 NF-M-1）。
"""

from dataclasses import dataclass
import os
from dotenv import load_dotenv

load_dotenv()


@dataclass
class SensorConfig:
    """センサーおよび MQTT 接続に関する設定値。

    Args:
        broker_host: MQTT ブローカーのホスト名
        broker_port: MQTT ブローカーのポート番号
        topic_prefix: MQTT トピックプレフィックス
        device_id: デバイス識別子（複数台管理時に使用）
        bme280_i2c_address: BME280 の I2C アドレス（0x76 または 0x77）
        mhz19_uart_port: MH-Z19B の UART デバイスパス
        read_interval_sec: センサー読み取り間隔（秒）
    """

    # MQTT 接続設定
    broker_host: str = os.getenv("MQTT_BROKER_HOST", "localhost")
    broker_port: int = int(os.getenv("MQTT_BROKER_PORT", "1883"))
    topic_prefix: str = os.getenv("MQTT_TOPIC_PREFIX", "iot/environment")
    device_id: str = os.getenv("DEVICE_ID", "raspi-01")

    # センサーハードウェア設定
    bme280_i2c_address: int = 0x76    # 0x77 の場合は要変更
    mhz19_uart_port: str = "/dev/ttyS0"

    # 読み取り間隔（要件 F-S-5）
    read_interval_sec: int = int(os.getenv("DEVICE_READ_INTERVAL_SEC", "10"))


config = SensorConfig()
