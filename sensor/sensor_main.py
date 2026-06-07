"""
Raspberry Pi 実機で動かすセンサー読み取りスクリプト。

BME280（I2C）で温度・湿度・気圧を、MH-Z19B（UART）で CO₂濃度を読み取り、
MQTT ブローカーに publish する。

起動方法（Raspberry Pi 上で）:
    python -m sensor.sensor_main

依存パッケージ（Raspberry Pi にインストール）:
    pip install bme280 pyserial paho-mqtt python-dotenv
"""

import json
import time
from datetime import datetime, timezone

import paho.mqtt.client as mqtt
import smbus2

from .config import config
from common import messages


def _read_bme280(bus: smbus2.SMBus) -> dict:
    """BME280 センサーから温度・湿度・気圧を読み取る。

    bme280 ライブラリ（python-bme280）を使って補正計算済みの値を返す。
    I2C アドレスは sensor/config.py の bme280_i2c_address を参照する。

    Args:
        bus: 初期化済みの smbus2.SMBus インスタンス（バス番号 1）

    Returns:
        "temperature"（℃）, "humidity"（%）, "pressure"（hPa）を含む辞書

    Raises:
        OSError: I2C 通信エラーが発生した場合
    """
    import bme280  # Raspberry Pi でのみインストール済みを前提

    calibration_params = bme280.load_calibration_params(bus, config.bme280_i2c_address)
    data = bme280.sample(bus, config.bme280_i2c_address, calibration_params)
    return {
        "temperature": round(data.temperature, 1),
        "humidity":    round(data.humidity, 1),
        "pressure":    round(data.pressure, 1),
    }


def _read_mhz19b() -> int | None:
    """MH-Z19B UART センサーから CO₂濃度（ppm）を読み取る。

    コマンドバイト列を送信し、9 バイトのレスポンスから CO₂値を算出する。
    読み取りに失敗した場合は None を返す（呼び出し元は None を許容すること）。

    Returns:
        CO₂濃度（ppm）。読み取り失敗時は None

    Raises:
        serial.SerialException: シリアルポートが開けない場合（上位で捕捉）
    """
    import serial  # pyserial

    try:
        with serial.Serial(config.mhz19_uart_port, baudrate=9600, timeout=1) as ser:
            # MH-Z19B CO₂ 読み取りコマンド
            ser.write(b"\xff\x01\x86\x00\x00\x00\x00\x00\x79")
            resp = ser.read(9)
            if len(resp) == 9 and resp[0] == 0xFF and resp[1] == 0x86:
                return (resp[2] << 8) | resp[3]
    except Exception as e:
        print(messages.SENSOR_CO2_READ_ERROR.format(error=e))
    return None


def main() -> None:
    """センサー読み取りのメインループ。MQTT 接続後、一定間隔でデータを publish する。

    Raises:
        KeyboardInterrupt: Ctrl+C で停止
    """
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.connect(config.broker_host, config.broker_port)
    client.loop_start()

    bus = smbus2.SMBus(1)  # Raspberry Pi の I2C バス番号は 1
    topic = f"{config.topic_prefix}/{config.device_id}"

    print(messages.SENSOR_STARTED.format(device_id=config.device_id))

    while True:
        try:
            bme_data = _read_bme280(bus)
            co2      = _read_mhz19b()

            payload = {
                "device_id":   config.device_id,
                "timestamp":   datetime.now(timezone.utc).isoformat(),
                "temperature": bme_data["temperature"],
                "humidity":    bme_data["humidity"],
                "pressure":    bme_data["pressure"],
                "co2":         co2,
            }
            client.publish(topic, json.dumps(payload))
            print(
                messages.MQTT_PUBLISHED.format(payload=payload)
            )

        except Exception as e:
            print(messages.SENSOR_ERROR.format(error=e))

        time.sleep(config.read_interval_sec)


if __name__ == "__main__":
    main()
