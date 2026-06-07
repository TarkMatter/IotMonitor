"""
アラート閾値の定義と閾値チェック関数。

閾値は環境変数から取得し、ハードコード禁止（要件 NF-M-1）。
"""

import os
from dataclasses import dataclass
from dotenv import load_dotenv

from common import messages

load_dotenv()


@dataclass
class Thresholds:
    """アラート発報に使用する閾値設定。

    Attributes:
        temp_high:     高温アラート閾値（℃）
        temp_low:      低温アラート閾値（℃）
        humidity_high: 高湿度アラート閾値（%）
        humidity_low:  低湿度アラート閾値（%）
        co2_high:      CO₂濃度アラート閾値（ppm）
    """

    temp_high:     float = float(os.getenv("ALERT_TEMP_HIGH",     "35.0"))
    temp_low:      float = float(os.getenv("ALERT_TEMP_LOW",      "5.0"))
    humidity_high: float = float(os.getenv("ALERT_HUMIDITY_HIGH", "80.0"))
    humidity_low:  float = float(os.getenv("ALERT_HUMIDITY_LOW",  "20.0"))
    co2_high:      int   = int(os.getenv("ALERT_CO2_HIGH",        "1500"))


# モジュールレベルのシングルトン（各サービスから共有して使う）
thresholds = Thresholds()


def check(payload: dict) -> list[str]:
    """センサーペイロードを閾値と比較し、超過した項目の警告メッセージリストを返す。

    温度・湿度・CO₂それぞれについて上限・下限を確認する。
    いずれも None の場合は評価をスキップする。

    Args:
        payload: センサーデータ辞書。"temperature", "humidity", "co2" キーを参照する。

    Returns:
        閾値を超えた項目ごとの警告メッセージ文字列のリスト。
        超過がない場合は空リストを返す。
    """
    alerts: list[str] = []
    temp     = payload.get("temperature")
    humidity = payload.get("humidity")
    co2      = payload.get("co2")

    if temp is not None:
        if temp >= thresholds.temp_high:
            alerts.append(
                messages.THRESHOLD_TEMP_HIGH.format(
                    value=temp, threshold=thresholds.temp_high
                )
            )
        elif temp <= thresholds.temp_low:
            alerts.append(
                messages.THRESHOLD_TEMP_LOW.format(
                    value=temp, threshold=thresholds.temp_low
                )
            )

    if humidity is not None:
        if humidity >= thresholds.humidity_high:
            alerts.append(
                messages.THRESHOLD_HUMIDITY_HIGH.format(
                    value=humidity, threshold=thresholds.humidity_high
                )
            )
        elif humidity <= thresholds.humidity_low:
            alerts.append(
                messages.THRESHOLD_HUMIDITY_LOW.format(
                    value=humidity, threshold=thresholds.humidity_low
                )
            )

    if co2 is not None and co2 >= thresholds.co2_high:
        alerts.append(
            messages.THRESHOLD_CO2_HIGH.format(
                value=co2, threshold=thresholds.co2_high
            )
        )

    return alerts
