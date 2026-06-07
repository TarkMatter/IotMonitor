#!/usr/bin/env bash
# =============================================================================
# デモ一括起動スクリプト
#
# 使い方:
#   bash scripts/start_demo.sh
#
# 前提:
#   - .venv が作成済みで pip install -e ".[dev]" 済みであること
#   - .env が配置済みであること
#   - Docker がインストール・起動済みであること
# =============================================================================

set -euo pipefail

# プロジェクトルートに移動（スクリプトの場所から1つ上）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "${SCRIPT_DIR}")"
cd "${PROJECT_DIR}"

# 仮想環境のアクティベート
if [[ -f ".venv/bin/activate" ]]; then
    # shellcheck disable=SC1091
    source .venv/bin/activate
else
    echo "[ERROR] .venv が見つかりません。先に python -m venv .venv && pip install -e '.[dev]' を実行してください。"
    exit 1
fi

echo "=============================="
echo " IotMonitor デモ起動"
echo "=============================="

# --- Step 1: Docker インフラ起動 ---
echo "[1/4] インフラ（Mosquitto / InfluxDB / Grafana）を起動中..."
docker-compose up -d
echo "      InfluxDB  → http://localhost:8086"
echo "      Grafana   → http://localhost:3000  (admin / admin)"

# InfluxDB の起動を待機（最大 30 秒）
echo "      InfluxDB の起動待機中..."
for i in $(seq 1 30); do
    if curl -sf http://localhost:8086/health > /dev/null 2>&1; then
        echo "      InfluxDB 起動確認 (${i}秒)"
        break
    fi
    sleep 1
done

# --- Step 2: データ収集サービス起動（バックグラウンド）---
echo "[2/4] データ収集サービスを起動中..."
python -m collector.main &
COLLECTOR_PID=$!
echo "      PID: ${COLLECTOR_PID}"

# --- Step 3: アラートサービス起動（バックグラウンド）---
echo "[3/4] アラートサービスを起動中..."
python -m alerter.main &
ALERTER_PID=$!
echo "      PID: ${ALERTER_PID}"

# --- Step 4: シミュレーター起動（フォアグラウンド）---
echo "[4/4] センサーシミュレーターを起動中..."
echo "      Ctrl+C で全サービスを停止します"
echo "=============================="

# Ctrl+C で子プロセスも一緒に終了させる
cleanup() {
    echo ""
    echo "[STOP] サービスを停止中..."
    kill "${COLLECTOR_PID}" "${ALERTER_PID}" 2>/dev/null || true
    echo "[STOP] 完了"
    exit 0
}
trap cleanup INT TERM

python -m sensor.simulator
