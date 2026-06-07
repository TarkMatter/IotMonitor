"""
api/main.py の結合テスト。

FastAPI の TestClient を使い、InfluxDB クライアントをモックして
実際の DB 接続なしでエンドポイントの動作を検証する。
"""

import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

# テスト開始前に InfluxDB クライアントをモックしてインポート時の接続を防ぐ
_MOCK_INFLUX = MagicMock()
with patch("collector.influx_client.EnvInfluxClient", return_value=_MOCK_INFLUX):
    from api.main import app

client = TestClient(app)

# テスト用のダミーセンサーデータ
_SAMPLE_RECORDS = [
    {
        "time":        "2026-06-07T10:00:00+00:00",
        "device_id":   "raspi-01",
        "temperature": 24.0,
        "humidity":    55.0,
        "co2":         600,
        "pressure":    1013.0,
    },
    {
        "time":        "2026-06-07T10:00:10+00:00",
        "device_id":   "raspi-01",
        "temperature": 24.2,
        "humidity":    55.5,
        "co2":         610,
        "pressure":    1013.1,
    },
]


class TestHealthEndpoint:
    """/health エンドポイントのテスト。"""

    def test_returns_200(self):
        resp = client.get("/health")
        assert resp.status_code == 200

    def test_status_ok(self):
        resp_json = client.get("/health").json()
        assert resp_json["status"] == "ok"

    def test_contains_time_field(self):
        assert "time" in client.get("/health").json()


class TestGetDataEndpoint:
    """/api/v1/data エンドポイントのテスト。"""

    def setup_method(self):
        _MOCK_INFLUX.query_recent.return_value = _SAMPLE_RECORDS

    def test_returns_200(self):
        resp = client.get("/api/v1/data")
        assert resp.status_code == 200

    def test_returns_list(self):
        resp = client.get("/api/v1/data")
        assert isinstance(resp.json(), list)

    def test_default_hours_24(self):
        client.get("/api/v1/data")
        _MOCK_INFLUX.query_recent.assert_called_with(hours=24, device_id=None)

    def test_custom_hours_passed_to_influx(self):
        client.get("/api/v1/data?hours=48")
        _MOCK_INFLUX.query_recent.assert_called_with(hours=48, device_id=None)

    def test_device_id_filter_passed_to_influx(self):
        client.get("/api/v1/data?device_id=raspi-01")
        _MOCK_INFLUX.query_recent.assert_called_with(hours=24, device_id="raspi-01")

    def test_returns_empty_list_when_no_data(self):
        _MOCK_INFLUX.query_recent.return_value = []
        resp = client.get("/api/v1/data")
        assert resp.json() == []

    def test_hours_out_of_range_returns_422(self):
        """hours が 0 以下のとき FastAPI のバリデーションエラー 422 を返す。"""
        resp = client.get("/api/v1/data?hours=0")
        assert resp.status_code == 422


class TestGetLatestEndpoint:
    """/api/v1/latest エンドポイントのテスト。"""

    def setup_method(self):
        _MOCK_INFLUX.query_recent.return_value = _SAMPLE_RECORDS

    def test_returns_200(self):
        resp = client.get("/api/v1/latest")
        assert resp.status_code == 200

    def test_returns_last_record(self):
        resp = client.get("/api/v1/latest")
        # _SAMPLE_RECORDS の末尾レコードが返る
        assert resp.json()["co2"] == 610

    def test_returns_404_when_no_data(self):
        _MOCK_INFLUX.query_recent.return_value = []
        resp = client.get("/api/v1/latest")
        assert resp.status_code == 404

    def test_device_id_filter_passed_to_influx(self):
        client.get("/api/v1/latest?device_id=raspi-01")
        _MOCK_INFLUX.query_recent.assert_called_with(hours=1, device_id="raspi-01")
