"""
alerter/notifiers.py の単体テスト。

外部 HTTP 通信（LINE Messaging API / Slack Webhook）は httpx をモックして
実際のネットワーク接続なしでテストする。
"""

import pytest
import httpx
from unittest.mock import AsyncMock, MagicMock, patch

from alerter.notifiers import notify_line, notify_slack, notify


class TestNotifyLine:
    """LINE Messaging API Push Message 送信のテスト。"""

    @pytest.mark.asyncio
    async def test_success_returns_true(self):
        """HTTP 200 が返ったとき True を返す。"""
        mock_resp = MagicMock()
        mock_resp.status_code = 200

        with patch("alerter.notifiers.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(return_value=mock_resp)
            mock_client_cls.return_value = mock_client

            result = await notify_line("テストメッセージ")

        assert result is True

    @pytest.mark.asyncio
    async def test_http_error_returns_false(self):
        """HTTP 4xx/5xx のとき False を返す（例外にしない）。"""
        mock_resp = MagicMock()
        mock_resp.status_code = 401

        with patch("alerter.notifiers.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(return_value=mock_resp)
            mock_client_cls.return_value = mock_client

            result = await notify_line("テスト")

        assert result is False

    @pytest.mark.asyncio
    async def test_empty_token_returns_false_without_http_call(self, monkeypatch):
        """LINE_CHANNEL_ACCESS_TOKEN が空のとき HTTP リクエストを送らず False を返す。"""
        monkeypatch.setenv("LINE_CHANNEL_ACCESS_TOKEN", "")

        with patch("alerter.notifiers.httpx.AsyncClient") as mock_client_cls:
            result = await notify_line("テスト")
            mock_client_cls.assert_not_called()

        assert result is False

    @pytest.mark.asyncio
    async def test_empty_user_id_returns_false_without_http_call(self, monkeypatch):
        """LINE_USER_ID が空のとき HTTP リクエストを送らず False を返す。"""
        monkeypatch.setenv("LINE_USER_ID", "")

        with patch("alerter.notifiers.httpx.AsyncClient") as mock_client_cls:
            result = await notify_line("テスト")
            mock_client_cls.assert_not_called()

        assert result is False

    @pytest.mark.asyncio
    async def test_push_payload_contains_user_id_and_message(self, monkeypatch):
        """Push Message のペイロードに user_id とメッセージが含まれる。"""
        monkeypatch.setenv("LINE_CHANNEL_ACCESS_TOKEN", "test-token")
        monkeypatch.setenv("LINE_USER_ID", "U1234567890")
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        captured = {}

        async def fake_post(url, **kwargs):
            captured["json"] = kwargs.get("json")
            return mock_resp

        with patch("alerter.notifiers.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = fake_post
            mock_client_cls.return_value = mock_client

            await notify_line("アラートテスト")

        assert captured["json"]["to"] == "U1234567890"
        assert captured["json"]["messages"][0]["text"] == "アラートテスト"

    @pytest.mark.asyncio
    async def test_network_exception_returns_false(self):
        """ネットワーク例外が発生しても False を返し、例外を呼び出し元に伝播しない。"""
        with patch("alerter.notifiers.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(side_effect=httpx.ConnectError("接続失敗"))
            mock_client_cls.return_value = mock_client

            result = await notify_line("テスト")

        assert result is False


class TestNotifySlack:
    """Slack Webhook 送信のテスト。"""

    @pytest.mark.asyncio
    async def test_success_returns_true(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200

        with patch("alerter.notifiers.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(return_value=mock_resp)
            mock_client_cls.return_value = mock_client

            result = await notify_slack("テストメッセージ")

        assert result is True

    @pytest.mark.asyncio
    async def test_empty_url_returns_false_without_http_call(self, monkeypatch):
        """SLACK_WEBHOOK_URL が空のとき HTTP リクエストを送らず False を返す。"""
        monkeypatch.setenv("SLACK_WEBHOOK_URL", "")

        with patch("alerter.notifiers.httpx.AsyncClient") as mock_client_cls:
            result = await notify_slack("テスト")
            mock_client_cls.assert_not_called()

        assert result is False


class TestNotifyDispatch:
    """NOTIFY_CHANNEL による送信先切り替えのテスト。"""

    @pytest.mark.asyncio
    async def test_line_channel_calls_only_line(self, monkeypatch):
        monkeypatch.setenv("NOTIFY_CHANNEL", "line")

        with (
            patch("alerter.notifiers.notify_line", new=AsyncMock(return_value=True)) as mock_line,
            patch("alerter.notifiers.notify_slack", new=AsyncMock(return_value=True)) as mock_slack,
        ):
            await notify("テスト")
            mock_line.assert_called_once()
            mock_slack.assert_not_called()

    @pytest.mark.asyncio
    async def test_slack_channel_calls_only_slack(self, monkeypatch):
        monkeypatch.setenv("NOTIFY_CHANNEL", "slack")

        with (
            patch("alerter.notifiers.notify_line", new=AsyncMock(return_value=True)) as mock_line,
            patch("alerter.notifiers.notify_slack", new=AsyncMock(return_value=True)) as mock_slack,
        ):
            await notify("テスト")
            mock_line.assert_not_called()
            mock_slack.assert_called_once()

    @pytest.mark.asyncio
    async def test_both_channel_calls_both(self, monkeypatch):
        monkeypatch.setenv("NOTIFY_CHANNEL", "both")

        with (
            patch("alerter.notifiers.notify_line", new=AsyncMock(return_value=True)) as mock_line,
            patch("alerter.notifiers.notify_slack", new=AsyncMock(return_value=True)) as mock_slack,
        ):
            await notify("テスト")
            mock_line.assert_called_once()
            mock_slack.assert_called_once()
