"""
pytest 共通フィクスチャ。

テスト間で共有する設定・モックオブジェクトをここで定義する。
環境変数はテスト実行前に上書きして外部サービスへの依存を排除する。
"""

import os
import pytest


@pytest.fixture(autouse=True)
def isolate_env(monkeypatch):
    """全テストで環境変数を安全なダミー値に上書きする。

    本番の .env が存在しても外部サービス（LINE・Slack・InfluxDB）に
    誤って接続しないようにする。
    """
    monkeypatch.setenv("INFLUXDB_URL",   "http://localhost:8086")
    monkeypatch.setenv("INFLUXDB_TOKEN", "test-token")
    monkeypatch.setenv("INFLUXDB_ORG",   "TestOrg")
    monkeypatch.setenv("INFLUXDB_BUCKET","test-bucket")
    monkeypatch.setenv("LINE_NOTIFY_TOKEN", "dummy-line-token")
    monkeypatch.setenv("SLACK_WEBHOOK_URL", "http://localhost/dummy-slack")
    monkeypatch.setenv("NOTIFY_CHANNEL",    "line")
    monkeypatch.setenv("ALERT_TEMP_HIGH",   "35.0")
    monkeypatch.setenv("ALERT_TEMP_LOW",    "5.0")
    monkeypatch.setenv("ALERT_HUMIDITY_HIGH","80.0")
    monkeypatch.setenv("ALERT_HUMIDITY_LOW", "20.0")
    monkeypatch.setenv("ALERT_CO2_HIGH",    "1500")
    monkeypatch.setenv("ALERT_COOLDOWN_MINUTES", "15")
    monkeypatch.setenv("MQTT_BROKER_HOST",  "localhost")
    monkeypatch.setenv("MQTT_BROKER_PORT",  "1883")
    monkeypatch.setenv("MQTT_TOPIC_PREFIX", "iot/environment")
    monkeypatch.setenv("DEVICE_ID",         "test-device")
    monkeypatch.setenv("DEVICE_READ_INTERVAL_SEC", "1")


@pytest.fixture
def normal_payload():
    """閾値内の正常なセンサーペイロード。"""
    return {
        "device_id":   "test-device",
        "temperature": 24.0,
        "humidity":    55.0,
        "co2":         600,
        "pressure":    1013.0,
    }


@pytest.fixture
def high_temp_payload():
    """高温アラートを発報するペイロード（temperature=36.0）。"""
    return {
        "device_id":   "test-device",
        "temperature": 36.0,
        "humidity":    55.0,
        "co2":         600,
        "pressure":    1013.0,
    }


@pytest.fixture
def multi_alert_payload():
    """温度・湿度・CO₂ が全て閾値超過するペイロード。"""
    return {
        "device_id":   "test-device",
        "temperature": 36.0,
        "humidity":    85.0,
        "co2":         2000,
        "pressure":    1013.0,
    }
