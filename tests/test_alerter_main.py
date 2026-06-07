"""
alerter/main.py の単体テスト。

クールダウン判定（_should_notify）と メッセージ受信処理（on_message）を
モジュールレベル状態を分離しながらテストする。
"""

import json
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import alerter.main as alerter_main


@pytest.fixture(autouse=True)
def reset_cooldown_state():
    """各テスト前後に _last_alerted をクリアしてテスト間の状態汚染を防ぐ。"""
    alerter_main._last_alerted.clear()
    yield
    alerter_main._last_alerted.clear()


def _make_msg(payload: dict) -> MagicMock:
    """on_message に渡す MQTTMessage のモックを生成する。"""
    msg = MagicMock()
    msg.payload = json.dumps(payload).encode()
    return msg


class TestShouldNotify:
    """_should_notify() のクールダウン判定テスト。"""

    def test_first_call_returns_true(self):
        """通知履歴がないデバイスは常に通知すべき。"""
        assert alerter_main._should_notify("new-device") is True

    def test_within_cooldown_returns_false(self):
        """最終通知からクールダウン期間内は通知しない。"""
        # 直前に通知済みとして記録する
        alerter_main._last_alerted["raspi-01"] = datetime.now(timezone.utc)
        assert alerter_main._should_notify("raspi-01") is False

    def test_after_cooldown_returns_true(self):
        """クールダウン期間を超えた場合は再通知する。"""
        # クールダウン期間よりも古い時刻を記録する
        past = datetime.now(timezone.utc) - alerter_main._COOLDOWN - timedelta(seconds=1)
        alerter_main._last_alerted["raspi-01"] = past
        assert alerter_main._should_notify("raspi-01") is True

    def test_different_devices_are_independent(self):
        """デバイスごとにクールダウン状態は独立している。"""
        alerter_main._last_alerted["raspi-01"] = datetime.now(timezone.utc)
        # raspi-01 はクールダウン中でも raspi-02 は別扱い
        assert alerter_main._should_notify("raspi-01") is False
        assert alerter_main._should_notify("raspi-02") is True


class TestOnMessage:
    """on_message() のメッセージ処理テスト。"""

    def test_normal_payload_does_not_notify(self, normal_payload):
        """閾値内のペイロードは通知しない。"""
        with patch("alerter.main.notify", new=AsyncMock()) as mock_notify:
            alerter_main.on_message(None, None, _make_msg(normal_payload))
            mock_notify.assert_not_called()

    def test_alert_payload_calls_notify(self, high_temp_payload):
        """閾値超過ペイロードは notify() を呼ぶ。"""
        with patch("alerter.main.notify", new=AsyncMock()) as mock_notify:
            alerter_main.on_message(None, None, _make_msg(high_temp_payload))
            mock_notify.assert_called_once()

    def test_alert_payload_records_last_alerted(self, high_temp_payload):
        """通知後に _last_alerted が更新される。"""
        with patch("alerter.main.notify", new=AsyncMock()):
            alerter_main.on_message(None, None, _make_msg(high_temp_payload))
        assert "test-device" in alerter_main._last_alerted

    def test_cooldown_suppresses_second_notify(self, high_temp_payload):
        """クールダウン中の 2 回目の受信は通知しない。"""
        with patch("alerter.main.notify", new=AsyncMock()) as mock_notify:
            # 1 回目
            alerter_main.on_message(None, None, _make_msg(high_temp_payload))
            # 2 回目（クールダウン中）
            alerter_main.on_message(None, None, _make_msg(high_temp_payload))
            # notify は 1 回だけ呼ばれる
            assert mock_notify.call_count == 1

    def test_notify_text_contains_device_id(self, high_temp_payload):
        """通知テキストにデバイスIDが含まれる。"""
        captured = {}

        async def capture_notify(text: str):
            captured["text"] = text

        with patch("alerter.main.notify", new=capture_notify):
            alerter_main.on_message(None, None, _make_msg(high_temp_payload))

        assert "test-device" in captured["text"]

    def test_invalid_json_does_not_raise(self):
        """不正な JSON ペイロードを受け取っても例外を上に伝播しない。"""
        msg = MagicMock()
        msg.payload = b"not valid json"
        # 例外が出なければテスト成功
        alerter_main.on_message(None, None, msg)

    def test_missing_device_id_uses_unknown(self):
        """device_id がないペイロードでも 'unknown' としてクールダウン管理される。"""
        payload = {"temperature": 36.0, "humidity": 50.0, "co2": 600}
        with patch("alerter.main.notify", new=AsyncMock()):
            alerter_main.on_message(None, None, _make_msg(payload))
        assert "unknown" in alerter_main._last_alerted
