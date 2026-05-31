# IotMonitor 要件定義書

## 1. プロジェクト概要

| 項目 | 内容 |
|---|---|
| プロジェクト名 | IotMonitor |
| バージョン | 0.1.0 |
| 作成日 | 2026-05-31 |
| 目的 | 工場・倉庫・クリーンルーム・オフィスにおける温度・湿度・CO₂のリアルタイム収集・可視化・アラート通知 |
| 対象ユーザー | 工場・倉庫・クリーンルーム・オフィスの環境管理担当者 |
| 収益モデル | 受託開発 ¥20〜60万 ／ カスタマイズ対応 |

---

## 2. 解決する課題

| No. | 課題 |
|---|---|
| C-1 | 温度・湿度・CO₂を人が巡回して手書き記録しており、リアルタイム性がない |
| C-2 | 異常値が出ても担当者が気づかず、製品品質・人体に影響が出る |
| C-3 | 過去データの傾向分析・月次レポート作成に毎回手間がかかる |
| C-4 | センサーを購入しても可視化する仕組みがなく活用できていない |

---

## 3. ハードウェア要件

### 3.1 対応ハードウェア

| 種別 | 型番 | 接続方式 |
|---|---|---|
| メインボード | Raspberry Pi 4B（または 3B+） | — |
| 温度・湿度・気圧センサ | BME280 / BME680 | I2C |
| CO₂センサ | MH-Z19B / SCD40 | UART または I2C |
| PM2.5センサ（オプション） | SDS011 | UART |

### 3.2 材料費目安（最小構成）

| パーツ | 型番 | 価格目安 |
|---|---|---|
| Raspberry Pi 4B 2GB | — | ¥7,000〜 |
| BME280 センサモジュール | GY-BME280 | ¥500〜 |
| MH-Z19B CO₂センサ | MH-Z19B | ¥2,500〜 |
| ジャンパワイヤ・ブレッドボード | — | ¥500〜 |
| **合計（最小構成）** | | **約 ¥11,000〜** |

### 3.3 センサなし（デモ）モード

実機なしでも `simulator.py` によりランダムな模擬データを MQTT に流すことで、PC 単体での動作確認・デモ撮影が可能であること。

---

## 4. システムアーキテクチャ要件

### 4.1 データフロー

```
センサ (Raspberry Pi)
    │ MQTT publish
    ▼
Mosquitto MQTT Broker (Docker)
    │ subscribe
    ▼
データ収集サービス (Python)
    │ write
    ▼
InfluxDB (時系列DB / Docker)
    │ query
    ▼
Grafana ダッシュボード (Docker)
    │
    ▼
ブラウザ (リアルタイム表示)

+-- アラートサービス (Python) ──→ LINE Notify / Slack
+-- レポートサービス (Python) ──→ Excel 月次レポート
```

### 4.2 コンポーネント一覧

| コンポーネント | 種別 | 役割 |
|---|---|---|
| sensor_main.py | Python スクリプト | Raspberry Pi 上でセンサを読み取り、MQTT に publish |
| simulator.py | Python スクリプト | デモ用模擬データを MQTT に publish |
| Mosquitto | Docker コンテナ | MQTT ブローカー |
| collector/main.py | Python サービス | MQTT を subscribe して InfluxDB に書き込む |
| InfluxDB | Docker コンテナ | 時系列センサデータの永続化 |
| Grafana | Docker コンテナ | リアルタイムダッシュボードの可視化 |
| alerter/main.py | Python サービス | 閾値チェック → LINE/Slack アラート通知 |
| reporter/main.py | Python スクリプト | 月次 Excel レポート自動生成 |
| api/main.py | FastAPI サービス | Grafana 以外からデータを取得するための REST API |

---

## 5. 機能要件

### 5.1 センサ読み取り機能

| ID | 要件 |
|---|---|
| F-S-1 | BME280（I2C）から温度・湿度・気圧を読み取れること |
| F-S-2 | MH-Z19B（UART）から CO₂濃度（ppm）を読み取れること |
| F-S-3 | 読み取りデータを JSON 形式で MQTT に publish できること |
| F-S-4 | デバイスIDと UTC タイムスタンプをペイロードに含めること |
| F-S-5 | 読み取り間隔を環境変数 `DEVICE_READ_INTERVAL_SEC` で設定できること（デフォルト: 10秒） |
| F-S-6 | センサ読み取りエラー時もサービスが継続動作すること（エラーログ出力のみ） |

### 5.2 シミュレーター機能

| ID | 要件 |
|---|---|
| F-SIM-1 | 温度・湿度・CO₂・気圧をサイン波＋ランダムノイズで自然な変動データを生成できること |
| F-SIM-2 | 実センサと同一フォーマットの JSON を MQTT に publish できること |
| F-SIM-3 | PC 単体（Raspberry Pi なし）で完全に動作すること |

### 5.3 データ収集機能

| ID | 要件 |
|---|---|
| F-C-1 | MQTT トピック `{prefix}/#` を subscribe し、全デバイスのデータを収集できること |
| F-C-2 | 受信した JSON を解析し、InfluxDB の `environment` 測定（measurement）に書き込めること |
| F-C-3 | InfluxDB 書き込みは SYNCHRONOUS モードで確実に行うこと |
| F-C-4 | メッセージ処理エラー時もサービスが継続動作すること（エラーログ出力のみ） |

### 5.4 可視化機能（Grafana）

| ID | 要件 |
|---|---|
| F-G-1 | ブラウザ（http://localhost:3000）で温度・湿度・CO₂ のリアルタイムゲージを表示できること |
| F-G-2 | 過去24時間の時系列グラフを表示できること |
| F-G-3 | Grafana のダッシュボード定義を JSON としてプロビジョニングできること（設定ファイル管理） |
| F-G-4 | InfluxDB をデータソースとして自動設定できること（プロビジョニング） |

### 5.5 アラート通知機能

| ID | 要件 |
|---|---|
| F-A-1 | 温度・湿度・CO₂が設定閾値を超えた際に通知を送信できること |
| F-A-2 | 通知先として LINE Notify・Slack Webhook のどちらか一方または両方を選択できること |
| F-A-3 | 同一デバイスの連続アラートをクールダウン時間（デフォルト: 15分）で抑制すること |
| F-A-4 | アラートメッセージにデバイスIDと超過値・閾値を含めること |

#### 5.5.1 アラート閾値（デフォルト値）

| 項目 | 上限 | 下限 |
|---|---|---|
| 温度 | 35.0 ℃ | 5.0 ℃ |
| 湿度 | 80.0 % | 20.0 % |
| CO₂ | 1500 ppm | — |

### 5.6 レポート機能

| ID | 要件 |
|---|---|
| F-R-1 | 指定年月のセンサデータを InfluxDB から取得して Excel（.xlsx）に出力できること |
| F-R-2 | Excel には「環境データ」シート（全データ一覧）と「サマリー」シート（平均・最大・最小）を含めること |
| F-R-3 | ファイル名は `env_report_YYYYMM.xlsx` 形式で出力すること |
| F-R-4 | デバイスID指定でフィルタリングした出力ができること |

### 5.7 REST API 機能

| ID | メソッド | パス | 説明 |
|---|---|---|---|
| F-API-1 | GET | `/api/v1/data` | 過去 N 時間のデータを取得（hours・device_id でフィルタ可能） |
| F-API-2 | GET | `/api/v1/latest` | 最新センサデータを取得（device_id でフィルタ可能） |
| F-API-3 | GET | `/api/v1/report` | 指定年月の Excel レポートをダウンロード |

---

## 6. 非機能要件

### 6.1 可用性

| ID | 要件 |
|---|---|
| NF-A-1 | センサ・コレクター・アラートの各サービスはエラー発生時も継続動作すること |
| NF-A-2 | Docker Compose によりインフラサービス（Mosquitto・InfluxDB・Grafana）を一括起動できること |

### 6.2 保守性

| ID | 要件 |
|---|---|
| NF-M-1 | 全ての設定値（ホスト・ポート・閾値・トークン等）は環境変数で管理し、コードへのハードコードを禁止する |
| NF-M-2 | `.env` ファイルは Git にコミットしない。`.env.example` のみリポジトリに含める |
| NF-M-3 | MQTT クライアントは `CallbackAPIVersion.VERSION2` を使用する（paho-mqtt 2.0 以降対応） |

### 6.3 拡張性

| ID | 要件 |
|---|---|
| NF-E-1 | 複数デバイス（device_id）のデータを同一システムで処理できること |
| NF-E-2 | センサ種別の追加（PM2.5・照度・騒音など）に対応できる設計であること |
| NF-E-3 | 通知チャネルの追加（LINE・Slack 以外）を容易に実装できる設計であること |

### 6.4 セキュリティ

| ID | 要件 |
|---|---|
| NF-S-1 | InfluxDB の管理者パスワード・トークンは環境変数で管理すること |
| NF-S-2 | LINE Notify トークン・Slack Webhook URL は環境変数で管理すること |
| NF-S-3 | Grafana の匿名サインアップを無効化すること |

### 6.5 デモ・ポータビリティ

| ID | 要件 |
|---|---|
| NF-P-1 | 実機（Raspberry Pi）なしで PC 単体でデモが可能であること |
| NF-P-2 | 全サービスをスクリプト 1 本（`scripts/start_demo.sh`）で一発起動できること |
| NF-P-3 | デモ動画は 2 分以内で完結するシナリオで撮影・公開できること |

---

## 7. 技術スタック

| 領域 | 採用技術 |
|---|---|
| 言語 | Python 3.11+ |
| センサ読み取り | smbus2（I2C）、pyserial（UART） |
| メッセージング | paho-mqtt 2.0（MQTT クライアント） |
| MQTT ブローカー | Mosquitto 2.x（Docker） |
| 時系列DB | InfluxDB 2.7（Docker） |
| 可視化 | Grafana 10.4（Docker） |
| API フレームワーク | FastAPI + uvicorn |
| HTTP クライアント | httpx（非同期） |
| 通知 | LINE Notify API、Slack Incoming Webhook |
| レポート生成 | openpyxl |
| コンテナ管理 | Docker / Docker Compose |
| パッケージ管理 | pyproject.toml |

---

## 8. ディレクトリ構成

```
IotMonitor/
├── sensor/
│   ├── sensor_main.py       # Raspberry Pi 上で動かすセンサ読み取り
│   ├── simulator.py         # センサなしでデモするシミュレーター
│   └── config.py            # センサ設定・MQTT 接続先
├── collector/
│   ├── __init__.py
│   ├── main.py              # MQTT subscribe → InfluxDB 書き込み
│   └── influx_client.py     # InfluxDB ラッパー
├── alerter/
│   ├── __init__.py
│   ├── main.py              # 閾値チェック → LINE/Slack 通知
│   ├── notifiers.py         # LINE / Slack 通知実装
│   └── thresholds.py        # 閾値定義
├── reporter/
│   ├── __init__.py
│   ├── main.py              # 月次レポート Excel 生成
│   └── template.xlsx        # レポートテンプレート
├── api/
│   ├── __init__.py
│   └── main.py              # FastAPI (データ取得 REST API)
├── docker-compose.yml       # Mosquitto + InfluxDB + Grafana
├── grafana/
│   ├── provisioning/
│   │   ├── datasources/     # InfluxDB 自動設定
│   │   └── dashboards/      # ダッシュボード自動設定
│   └── dashboards/
│       └── environment.json # 環境モニタリング用ダッシュボード定義
├── scripts/
│   └── start_demo.sh        # 全サービス一発起動スクリプト
├── .env.example
├── pyproject.toml
└── CLAUDE.md
```

---

## 9. 環境変数仕様

| 変数名 | デフォルト値 | 説明 |
|---|---|---|
| `MQTT_BROKER_HOST` | `localhost` | MQTT ブローカーのホスト名 |
| `MQTT_BROKER_PORT` | `1883` | MQTT ブローカーのポート番号 |
| `MQTT_TOPIC_PREFIX` | `iot/environment` | MQTT トピックプレフィックス |
| `DEVICE_ID` | `raspi-01` | デバイス識別子 |
| `INFLUXDB_URL` | `http://localhost:8086` | InfluxDB の接続 URL |
| `INFLUXDB_TOKEN` | — | InfluxDB 認証トークン（必須） |
| `INFLUXDB_ORG` | `IotMonitor` | InfluxDB 組織名 |
| `INFLUXDB_BUCKET` | `environment` | InfluxDB バケット名 |
| `LINE_NOTIFY_TOKEN` | — | LINE Notify 認証トークン |
| `SLACK_WEBHOOK_URL` | — | Slack Incoming Webhook URL |
| `NOTIFY_CHANNEL` | `line` | 通知チャネル（`line` \| `slack` \| `both`） |
| `ALERT_TEMP_HIGH` | `35.0` | 高温アラート閾値（℃） |
| `ALERT_TEMP_LOW` | `5.0` | 低温アラート閾値（℃） |
| `ALERT_HUMIDITY_HIGH` | `80.0` | 高湿度アラート閾値（%） |
| `ALERT_HUMIDITY_LOW` | `20.0` | 低湿度アラート閾値（%） |
| `ALERT_CO2_HIGH` | `1500` | 高 CO₂ アラート閾値（ppm） |
| `ALERT_COOLDOWN_MINUTES` | `15` | 連続アラートのクールダウン時間（分） |

---

## 10. 開発フェーズ計画

| フェーズ | 内容 | 目安日数 |
|---|---|---|
| Phase 1 | インフラ構築（Docker Compose、Mosquitto / InfluxDB / Grafana 起動確認） | Day 1〜2 |
| Phase 2 | センサ / シミュレーター実装（pyproject.toml、config.py、simulator.py） | Day 3〜5 |
| Phase 3 | データ収集実装（influx_client.py、collector/main.py） | Day 6〜8 |
| Phase 4 | Grafana ダッシュボード構築（データソース設定、ゲージ・時系列グラフ） | Day 9〜11 |
| Phase 5 | アラート通知実装（notifiers.py、thresholds.py、alerter/main.py） | Day 12〜14 |
| Phase 6 | レポート・API 実装（reporter/main.py、api/main.py） | Day 15〜17 |
| Phase 7 | デモ整備・仕上げ（start_demo.sh、README、デモ動画録画、GitHub 公開） | Day 18〜20 |

---

## 11. デモシナリオ（2分・録画必須）

```
Step 1: Raspberry Pi にセンサを接続してスクリプトを起動
         （実機なしの場合は simulator.py を起動）
Step 2: ブラウザで http://localhost:3000 を開く
         → 温度・湿度・CO₂ のリアルタイムゲージとグラフが動いている
Step 3: センサを手で温めて温度を意図的に上げる
         （シミュレーターの場合はベース値を変更）
         → グラフが上昇 → 閾値超えで LINE にアラートが届く
Step 4: 「過去24時間」タブを開く
         → 時系列グラフで傾向が一目瞭然
Step 5: 「レポート出力」ボタンを押す
         → 月次 Excel レポートが自動生成される
```

---

## 12. 将来の拡張対応メニュー

| オプション | 追加単価目安 |
|---|---|
| センサ種類の追加（PM2.5・照度・騒音） | ¥3〜8万 |
| 複数拠点・複数デバイス対応 | ¥5〜15万 |
| アラートの管理画面（Web で閾値を変更） | ¥10〜20万 |
| 既存 SCADA・基幹システムとの連携 | ¥10〜30万 |
| OPC-UA 対応（PLC 直接接続） | ¥15〜40万 |
| Grafana → 自社デザインの Web 画面に置き換え | ¥10〜20万 |

---

## 13. コーディングルール

- 環境変数はすべて `config.py` または `os.getenv()` で管理（ハードコード禁止）
- MQTT クライアントは `CallbackAPIVersion.VERSION2` を使う（paho-mqtt 2.0 以降）
- InfluxDB への書き込みは `SYNCHRONOUS` モードで確実に行う
- アラートのクールダウンは必ず実装する（センサノイズで通知が連発するのを防ぐ）
- `.env` は絶対に Git にコミットしない（`.env.example` のみコミット対象）
- 全関数に docstring を付ける（引数・戻り値・発生しうる例外を記述）
- 画面表示文字列・エラーメッセージは定数として一か所に集める
