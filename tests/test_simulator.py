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
        result = _next_value("dev-1", base=24.0, amplitude=3.0, noise_sigma=0.2)
        assert isinstance(result, float)

    def test_rounds_to_one_decimal(self):
        """小数点1桁に丸められていること。"""
        result = _next_value("dev-1", base=24.0, amplitude=3.0, noise_sigma=0.2)
        assert result == round(result, 1)

    def test_within_reasonable_range(self):
        """ベース値 ± 振れ幅 + 3σ の範囲内に収まること（統計的に 99.7% の確率）。"""
        base, amplitude, sigma = 24.0, 3.0, 0.2
        margin = amplitude + sigma * 3
        for _ in range(100):
            result = _next_value("dev-1", base=base, amplitude=amplitude, noise_sigma=sigma)
            assert base - margin <= result <= base + margin, f"範囲外の値: {result}"

    def test_different_devices_have_independent_phases(self):
        """デバイスが異なれば位相が独立していること（同一値にならない）。"""
        vals_a = [_next_value("device-a", base=24.0, amplitude=3.0, noise_sigma=0.0) for _ in range(5)]
        vals_b = [_next_value("device-b", base=24.0, amplitude=3.0, noise_sigma=0.0) for _ in range(5)]
        # 位相が独立していれば、全て同一になることはほぼない
        assert vals_a != vals_b


class TestBuildPayload:
    """_build_payload() のペイロード構造テスト。"""

    _REQUIRED_KEYS = {"device_id", "timestamp", "temperature", "humidity", "co2", "pressure", "pm25"}

    def test_contains_all_required_keys(self):
        payload = _build_payload("test-device")
        assert self._REQUIRED_KEYS <= payload.keys()

    def test_temperature_is_float(self):
        assert isinstance(_build_payload("test-device")["temperature"], float)

    def test_co2_is_int(self):
        """CO₂ は int で返ること（整数 ppm 単位）。"""
        assert isinstance(_build_payload("test-device")["co2"], int)

    def test_pm25_is_float(self):
        """PM2.5 は float で返ること（μg/m³ 単位）。"""
        assert isinstance(_build_payload("test-device")["pm25"], float)

    def test_pm25_is_non_negative(self):
        """PM2.5 は非負値であること（abs() を使っているため）。"""
        for _ in range(30):
            assert _build_payload("test-device")["pm25"] >= 0.0

    def test_timestamp_is_iso_format(self):
        """タイムスタンプが ISO 8601 形式であること。"""
        from datetime import datetime
        ts = _build_payload("test-device")["timestamp"]
        datetime.fromisoformat(ts)

    def test_timestamp_is_utc(self):
        """タイムスタンプが UTC（+00:00）で記録されること。"""
        ts = _build_payload("test-device")["timestamp"]
        assert "+00:00" in ts

    def test_device_id_matches_argument(self):
        """device_id が引数の値と一致すること。"""
        assert _build_payload("raspi-02")["device_id"] == "raspi-02"

    def test_base_temp_shifts_temperature(self):
        """base_temp が高いほど平均温度が高くなること（複数デバイスの差異表現）。"""
        samples_low  = [_build_payload("dev", base_temp=20.0)["temperature"] for _ in range(50)]
        samples_high = [_build_payload("dev2", base_temp=30.0)["temperature"] for _ in range(50)]
        assert sum(samples_high) / len(samples_high) > sum(samples_low) / len(samples_low)

    def test_consecutive_payloads_differ(self):
        """連続して生成したペイロードが同一にならないこと（ノイズが機能している）。"""
        payloads = [_build_payload("test-device") for _ in range(10)]
        temperatures = [p["temperature"] for p in payloads]
        assert len(set(temperatures)) > 1
