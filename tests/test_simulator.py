"""
sensor/simulator.py の単体テスト。

_build_payload() / _next_value() は外部依存がないため
モック不要で純粋なロジックをテストできる。
"""

import pytest
from sensor.simulator import _build_payload, _next_value


class TestNextValue:
    """_next_value() の値範囲テスト。"""

    def test_returns_float(self):
        result = _next_value(base=24.0, amplitude=3.0, noise_sigma=0.2)
        assert isinstance(result, float)

    def test_rounds_to_one_decimal(self):
        """小数点1桁に丸められていること。"""
        result = _next_value(base=24.0, amplitude=3.0, noise_sigma=0.2)
        assert result == round(result, 1)

    def test_within_reasonable_range(self):
        """ベース値 ± 振れ幅 + 3σ の範囲内に収まること（統計的に 99.7% の確率）。"""
        base, amplitude, sigma = 24.0, 3.0, 0.2
        margin = amplitude + sigma * 3
        for _ in range(100):
            result = _next_value(base=base, amplitude=amplitude, noise_sigma=sigma)
            assert base - margin <= result <= base + margin, f"範囲外の値: {result}"


class TestBuildPayload:
    """_build_payload() のペイロード構造テスト。"""

    _REQUIRED_KEYS = {"device_id", "timestamp", "temperature", "humidity", "co2", "pressure"}

    def test_contains_all_required_keys(self):
        payload = _build_payload()
        assert self._REQUIRED_KEYS <= payload.keys()

    def test_temperature_is_float(self):
        assert isinstance(_build_payload()["temperature"], float)

    def test_co2_is_int(self):
        """CO₂ は int で返ること（整数 ppm 単位）。"""
        assert isinstance(_build_payload()["co2"], int)

    def test_timestamp_is_iso_format(self):
        """タイムスタンプが ISO 8601 形式であること。"""
        from datetime import datetime
        ts = _build_payload()["timestamp"]
        # ValueError にならなければ正しい ISO 形式
        datetime.fromisoformat(ts)

    def test_timestamp_is_utc(self):
        """タイムスタンプが UTC（+00:00）で記録されること。"""
        ts = _build_payload()["timestamp"]
        assert "+00:00" in ts

    def test_device_id_matches_config(self):
        """device_id が config の値と一致すること。"""
        from sensor.config import config
        assert _build_payload()["device_id"] == config.device_id

    def test_consecutive_payloads_differ(self):
        """連続して生成したペイロードが同一にならないこと（ノイズが機能している）。"""
        payloads = [_build_payload() for _ in range(10)]
        temperatures = [p["temperature"] for p in payloads]
        # 10 件全て同じ値になる確率は極めて低い
        assert len(set(temperatures)) > 1
