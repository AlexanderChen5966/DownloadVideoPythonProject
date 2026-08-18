#!/bin/bash
# MCP 啟動包裝腳本 - 自動更新套件後啟動 server
#
# 注意：本腳本以 STDIO 與 Claude Desktop 溝通，
# 所有診斷輸出都必須導向 $LOG_FILE，絕不可寫入 stdout。

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_PYTHON="$SCRIPT_DIR/.venv/bin/python"
VENV_PIP="$SCRIPT_DIR/.venv/bin/pip"
VENV_YTDLP="$SCRIPT_DIR/.venv/bin/yt-dlp"
LOG_FILE="$SCRIPT_DIR/mcp_startup.log"

# 日誌輪替：超過 1 MB 就轉存為 .1（只保留一份舊檔）
MAX_LOG_BYTES=1048576
if [ -f "$LOG_FILE" ] && [ "$(stat -f%z "$LOG_FILE" 2>/dev/null || echo 0)" -gt "$MAX_LOG_BYTES" ]; then
    mv -f "$LOG_FILE" "$LOG_FILE.1"
fi

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

# pip 共用參數：
# --timeout/--retries 避免離線時 pip 反覆重試，拖住 MCP 啟動
# --disable-pip-version-check 消除 "A new release of pip" 噪音
PIP_OPTS=(--quiet --timeout 10 --retries 1 --disable-pip-version-check)

log "=== MCP 啟動 ==="

# 記錄升級前版本，供稍後判斷是否真的有更新
version_before="$("$VENV_YTDLP" --version 2>/dev/null)"

# 自動更新 yt-dlp（最常見的失敗原因之一）
log "更新 yt-dlp（目前 ${version_before:-unknown}）..."
if "$VENV_PIP" install --upgrade yt-dlp "${PIP_OPTS[@]}" >> "$LOG_FILE" 2>&1; then
    version_after="$("$VENV_YTDLP" --version 2>/dev/null)"
    if [ "$version_before" != "$version_after" ]; then
        log "yt-dlp 已更新：${version_before:-unknown} → ${version_after:-unknown}"
        # 僅在版本真的變動時清快取（舊快取可能與新版不相容）。
        # 平時保留快取，避免每次啟動後首次下載都要重新解析 player JS。
        "$VENV_YTDLP" --rm-cache-dir >> "$LOG_FILE" 2>&1
        log "已清除 yt-dlp 快取"
    else
        log "yt-dlp 已是最新（${version_after:-unknown}），保留快取"
    fi
else
    log "yt-dlp 更新失敗（可能離線），沿用現有版本 ${version_before:-unknown}"
fi

# 確認所有依賴都已安裝（靜默模式，只補裝缺少的）
if ! "$VENV_PIP" install -r "$SCRIPT_DIR/requirements.txt" "${PIP_OPTS[@]}" >> "$LOG_FILE" 2>&1; then
    log "依賴檢查失敗（可能離線），嘗試繼續啟動"
fi

log "啟動 MCP server..."
exec "$VENV_PYTHON" "$SCRIPT_DIR/server.py"
