"""
LINE Messaging API・Slack Webhook への通知送信モジュール。

送信先は環境変数 NOTIFY_CHANNEL (line | slack | both) で切り替える。
各関数は非同期（async）で実装し、httpx を使う（要件 F-A-3）。
"""

import os
import httpx
from dotenv import load_dotenv

from common import messages

load_dotenv()

# LINE Messaging API Push Message エンドポイント
_LINE_PUSH_URL = "https://api.line.me/v2/bot/message/push"
# HTTP タイムアウト（秒）
_REQUEST_TIMEOUT = 5.0


async def notify_line(message: str) -> bool:
    """LINE Messaging API の Push Message でメッセージを送信する。

    環境変数 LINE_CHANNEL_ACCESS_TOKEN または LINE_USER_ID が未設定の場合は
    何もせず False を返す。

    Args:
        message: 送信するメッセージ本文

    Returns:
        送信成功なら True、失敗・未設定なら False
    """
    token   = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")
    user_id = os.getenv("LINE_USER_ID", "")
    if not token or not user_id:
        return False
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                _LINE_PUSH_URL,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type":  "application/json",
                },
                json={
                    "to": user_id,
                    "messages": [{"type": "text", "text": message}],
                },
                timeout=_REQUEST_TIMEOUT,
            )
            return resp.status_code == 200
    except Exception as e:
        print(messages.LINE_SEND_ERROR.format(error=e))
        return False


async def notify_slack(message: str) -> bool:
    """Slack Webhook でメッセージを送信する。

    環境変数 SLACK_WEBHOOK_URL が未設定の場合は何もせず False を返す。

    Args:
        message: 送信するメッセージ本文

    Returns:
        送信成功なら True、失敗・未設定なら False
    """
    url = os.getenv("SLACK_WEBHOOK_URL", "")
    if not url:
        return False
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                url,
                json={"text": message},
                timeout=_REQUEST_TIMEOUT,
            )
            return resp.status_code == 200
    except Exception as e:
        print(messages.SLACK_SEND_ERROR.format(error=e))
        return False


async def notify(message: str) -> None:
    """NOTIFY_CHANNEL 設定に基づいて LINE / Slack / 両方にメッセージを送信する。

    Args:
        message: 送信するメッセージ本文
    """
    channel = os.getenv("NOTIFY_CHANNEL", "line").lower()
    if channel in ("line", "both"):
        await notify_line(message)
    if channel in ("slack", "both"):
        await notify_slack(message)
