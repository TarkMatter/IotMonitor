"""
アプリケーション全体で使用するメッセージ文字列定数。

コード内にメッセージを直書きすると多言語化・変更時の修正漏れが起きるため、
ここに集約する。呼び出し側では .format() または f-string 展開して使用する。
"""

# --- MQTT 接続 ---
MQTT_CONNECTED = "[MQTT] ブローカー接続: {reason_code}"
MQTT_SUBSCRIBED = "[MQTT] subscribe: {topic}"
MQTT_PUBLISHED = "[MQTT] {payload}"

# --- データ収集サービス ---
COLLECTOR_STARTED = "収集サービス起動"
DB_WRITE_OK = "[DB] 書き込み完了: {device_id} 温度:{temperature}℃  CO₂:{co2}ppm"
MSG_PROCESS_ERROR = "[ERROR] メッセージ処理失敗: {error}"

# --- アラートサービス ---
ALERTER_STARTED = "アラートサービス起動"
ALERT_NOTIFIED = "[ALERT] 通知送信: {device_id}"
ALERT_COOLDOWN = "[ALERT] クールダウン中: {device_id}"
ALERT_TEXT_HEADER = "【IoTモニター アラート】\nデバイス: {device_id}\n"
GENERAL_ERROR = "[ERROR] {error}"

# --- センサー読み取り ---
SENSOR_STARTED = "センサ読み取り開始 (デバイスID: {device_id})"
SENSOR_CO2_READ_ERROR = "[CO2] 読み取りエラー: {error}"
SENSOR_ERROR = "[ERROR] {error}"

# --- シミュレーター ---
SIMULATOR_STARTED = "シミュレーター起動 (デバイスID: {device_id})"
SIMULATOR_STOP_HINT = "Ctrl+C で停止"
SIMULATOR_LOG = "[SIM] 温度:{temperature}℃  湿度:{humidity}%  CO₂:{co2}ppm"

# --- アラート閾値超過メッセージ ---
THRESHOLD_TEMP_HIGH = "🌡️ 高温警告: {value}℃ (閾値: {threshold}℃)"
THRESHOLD_TEMP_LOW = "🌡️ 低温警告: {value}℃ (閾値: {threshold}℃)"
THRESHOLD_HUMIDITY_HIGH = "💧 高湿度警告: {value}% (閾値: {threshold}%)"
THRESHOLD_HUMIDITY_LOW = "💧 低湿度警告: {value}% (閾値: {threshold}%)"
THRESHOLD_CO2_HIGH = "🌬️ CO₂濃度警告: {value}ppm (閾値: {threshold}ppm)"

# --- 外部通知 ---
LINE_SEND_ERROR = "[LINE] 送信失敗: {error}"
SLACK_SEND_ERROR = "[Slack] 送信失敗: {error}"

# --- レポート ---
REPORT_GENERATED = "レポート生成: {path}"
