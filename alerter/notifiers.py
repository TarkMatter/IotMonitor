"""
LINE Notify・Slack Webhook への通知送信モジュール。

送信先は環境変数 NOTIFY_CHANNEL (line | slack | both) で切り替える。
各関数は非同期（async）で実装し、httpx を使う（要件 F-A-3）。
"""

import os
import httpx
from dotenv import load_dotenv

from common import messages

load_dotenv()

# LINE Notify API エンドポイント
_LINE_API_URL = "https://notify-api.line.me/api/notify"
# HTTP タイムアウト（秒）
_REQUEST_TIMEOUT = 5.0


async def notify_line(message: str) -> bool:
    """LINE Notify でメッセージを送信する。

    環境変数 LINE_NOTIFY_TOKEN が未設定の場合は何もせず False を返す。

    Args:
        message: 送信するメッセージ本文

    Returns:
        送信成功なら True、失敗・未設定なら False
    """
    token = os.getenv("LINE_NOTIFY_TOKEN", "")
    if not token:
        return False
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                _LINE_API_URL,
                headers={"Authorization": f"Bearer {token}"},
                data={"message": f"\n{message}"},
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
