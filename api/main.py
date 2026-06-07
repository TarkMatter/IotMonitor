"""
IoT 環境モニター REST API。

Grafana 以外のクライアント（スマートフォンアプリ・外部システム連携等）から
センサーデータを取得するためのエンドポイントを提供する。

起動方法:
    uvicorn api.main:app --reload
"""

from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse

from collector.influx_client import EnvInfluxClient
from reporter.main import generate_monthly_report

# API メタデータ
_API_TITLE   = "IoT 環境モニター API"
_API_VERSION = "1.0.0"

app    = FastAPI(title=_API_TITLE, version=_API_VERSION)
influx = EnvInfluxClient()


@app.get("/api/v1/data", summary="センサーデータ一覧取得")
def get_data(
    hours: int = Query(24, ge=1, le=8760, description="過去何時間分（1〜8760）"),
    device_id: str | None = Query(None, description="デバイスIDでフィルタ"),
) -> list[dict]:
    """過去 N 時間のセンサーデータを取得する。

    Args:
        hours:     取得する期間（時間）。1〜8760 の範囲で指定
        device_id: 特定デバイスに絞り込む場合に指定。省略時は全デバイス

    Returns:
        センサーデータの辞書リスト
    """
    return influx.query_recent(hours=hours, device_id=device_id)


@app.get("/api/v1/latest", summary="最新センサーデータ取得")
def get_latest(
    device_id: str | None = Query(None, description="デバイスIDでフィルタ"),
) -> dict:
    """最新のセンサーデータを 1 件取得する。

    Args:
        device_id: 特定デバイスに絞り込む場合に指定。省略時は全デバイス中の最新

    Returns:
        最新のセンサーデータ辞書。データが存在しない場合は空辞書

    Raises:
        HTTPException(404): データが 1 件も存在しない場合
    """
    data = influx.query_recent(hours=1, device_id=device_id)
    if not data:
        raise HTTPException(status_code=404, detail="データが見つかりません")
    return data[-1]


@app.get("/api/v1/report", summary="月次 Excel レポートのダウンロード")
def download_report(
    year: int = Query(..., ge=2020, le=2099, description="レポート対象年"),
    month: int = Query(..., ge=1, le=12, description="レポート対象月（1〜12）"),
    device_id: str | None = Query(None, description="デバイスIDでフィルタ"),
) -> FileResponse:
    """指定年月の Excel レポートを生成してダウンロードレスポンスとして返す。

    レポートファイルは一時ディレクトリに生成される。

    Args:
        year:      レポート対象年（2020〜2099）
        month:     レポート対象月（1〜12）
        device_id: 特定デバイスに絞り込む場合に指定

    Returns:
        Excel ファイルのダウンロードレスポンス

    Raises:
        HTTPException(500): レポート生成に失敗した場合
    """
    import tempfile

    try:
        output_dir = tempfile.mkdtemp()
        report_path: Path = generate_monthly_report(
            year=year,
            month=month,
            device_id=device_id,
            output_dir=output_dir,
        )
        return FileResponse(
            path=str(report_path),
            filename=report_path.name,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"レポート生成失敗: {e}") from e


@app.get("/health", summary="ヘルスチェック")
def health_check() -> dict:
    """サービスの死活確認用エンドポイント。

    Returns:
        ステータスと現在時刻を含む辞書
    """
    return {"status": "ok", "time": datetime.utcnow().isoformat()}
