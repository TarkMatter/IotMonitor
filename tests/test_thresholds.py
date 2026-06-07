"""
alerter/thresholds.py の単体テスト。

check() は外部依存がない純粋関数なのでモック不要。
各閾値の境界値・正常系・複合アラートをカバーする。
"""

import pytest
from alerter.thresholds import Thresholds, check


class TestCheckNormal:
    """正常範囲内のペイロードはアラートが出ないことを確認する。"""

    def test_no_alerts_for_normal_values(self, normal_payload):
        assert check(normal_payload) == []

    def test_no_alerts_when_all_fields_none(self):
        """全フィールドが None のとき（パーシャルデータ）はアラートなし。"""
        result = check({"device_id": "x", "temperature": None, "humidity": None, "co2": None})
        assert result == []

    def test_no_alerts_when_fields_missing(self):
        """センサー値のキーがないペイロードはアラートなし（KeyError にならない）。"""
        result = check({"device_id": "x"})
        assert result == []


class TestTemperatureThreshold:
    """温度アラートの境界値テスト。"""

    def test_high_temp_triggers_alert(self, high_temp_payload):
        alerts = check(high_temp_payload)
        assert len(alerts) == 1
        assert "高温" in alerts[0]
        assert "36.0" in alerts[0]

    def test_temp_exactly_at_high_threshold_triggers(self, monkeypatch):
        """閾値ちょうど（>=）はアラートになる。"""
        monkeypatch.setenv("ALERT_TEMP_HIGH", "35.0")
        # Thresholds を再生成して環境変数を反映させる
        from importlib import reload
        import alerter.thresholds as mod
        reload(mod)
        result = mod.check({"temperature": 35.0, "humidity": 50.0, "co2": 600})
        assert any("高温" in m for m in result)

    def test_temp_below_high_threshold_no_alert(self):
        result = check({"temperature": 34.9, "humidity": 50.0, "co2": 600})
        assert not any("高温" in m for m in result)

    def test_low_temp_triggers_alert(self):
        result = check({"temperature": 4.9, "humidity": 50.0, "co2": 600})
        assert len(result) == 1
        assert "低温" in result[0]

    def test_temp_exactly_at_low_threshold_triggers(self, monkeypatch):
        """閾値ちょうど（<=）はアラートになる。"""
        monkeypatch.setenv("ALERT_TEMP_LOW", "5.0")
        from importlib import reload
        import alerter.thresholds as mod
        reload(mod)
        result = mod.check({"temperature": 5.0, "humidity": 50.0, "co2": 600})
        assert any("低温" in m for m in result)


class TestHumidityThreshold:
    """湿度アラートの境界値テスト。"""

    def test_high_humidity_triggers_alert(self):
        result = check({"temperature": 24.0, "humidity": 81.0, "co2": 600})
        assert any("高湿度" in m for m in result)

    def test_low_humidity_triggers_alert(self):
        result = check({"temperature": 24.0, "humidity": 19.0, "co2": 600})
        assert any("低湿度" in m for m in result)

    def test_humidity_in_range_no_alert(self):
        result = check({"temperature": 24.0, "humidity": 50.0, "co2": 600})
        assert not any("湿度" in m for m in result)


class TestCo2Threshold:
    """CO₂アラートの境界値テスト。"""

    def test_high_co2_triggers_alert(self):
        result = check({"temperature": 24.0, "humidity": 50.0, "co2": 1500})
        assert any("CO₂" in m for m in result)

    def test_co2_below_threshold_no_alert(self):
        result = check({"temperature": 24.0, "humidity": 50.0, "co2": 1499})
        assert not any("CO₂" in m for m in result)

    def test_co2_none_no_alert(self):
        """CO₂ が None のとき（センサー未接続など）はアラートなし。"""
        result = check({"temperature": 24.0, "humidity": 50.0, "co2": None})
        assert not any("CO₂" in m for m in result)


class TestPm25Threshold:
    """PM2.5 アラートの境界値テスト。"""

    def test_high_pm25_triggers_alert(self, high_pm25_payload):
        """PM2.5 が閾値以上のときアラートが出る。"""
        alerts = check(high_pm25_payload)
        assert len(alerts) == 1
        assert "PM2.5" in alerts[0]
        assert "40.0" in alerts[0]

    def test_pm25_below_threshold_no_alert(self):
        """PM2.5 が閾値未満のときアラートなし。"""
        result = check({"temperature": 24.0, "humidity": 50.0, "co2": 600, "pm25": 34.9})
        assert not any("PM2.5" in m for m in result)

    def test_pm25_exactly_at_threshold_triggers(self, monkeypatch):
        """閾値ちょうど（>=）はアラートになる。"""
        monkeypatch.setenv("ALERT_PM25_HIGH", "35.0")
        from importlib import reload
        import alerter.thresholds as mod
        reload(mod)
        result = mod.check({"temperature": 24.0, "humidity": 50.0, "co2": 600, "pm25": 35.0})
        assert any("PM2.5" in m for m in result)

    def test_pm25_none_no_alert(self):
        """PM2.5 が None のとき（センサー未接続）はアラートなし。"""
        result = check({"temperature": 24.0, "humidity": 50.0, "co2": 600, "pm25": None})
        assert not any("PM2.5" in m for m in result)

    def test_pm25_missing_no_alert(self):
        """PM2.5 キー自体がないペイロードはアラートなし（KeyError にならない）。"""
        result = check({"temperature": 24.0, "humidity": 50.0, "co2": 600})
        assert not any("PM2.5" in m for m in result)


class TestMultipleAlerts:
    """複数閾値が同時に超過した場合の動作テスト。"""

    def test_all_thresholds_exceeded_returns_four_alerts(self, multi_alert_payload):
        alerts = check(multi_alert_payload)
        # 高温・高湿度・CO₂・PM2.5 の 4 件
        assert len(alerts) == 4

    def test_alert_messages_contain_actual_values(self, multi_alert_payload):
        alerts = check(multi_alert_payload)
        joined = " ".join(alerts)
        assert "36.0" in joined   # 実際の温度値
        assert "85.0" in joined   # 実際の湿度値
        assert "2000" in joined   # 実際の CO₂値
        assert "40.0" in joined   # 実際の PM2.5値
