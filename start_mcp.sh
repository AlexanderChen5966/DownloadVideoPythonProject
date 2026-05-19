#!/bin/bash
# MCP 啟動包裝腳本 - 自動更新套件後啟動 server

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_PYTHON="$SCRIPT_DIR/.venv/bin/python"
VENV_PIP="$SCRIPT_DIR/.venv/bin/pip"
LOG_FILE="$SCRIPT_DIR/mcp_startup.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

log "=== MCP 啟動 ==="

# 自動更新 yt-dlp（最常見的失敗原因）
log "更新 yt-dlp..."
"$VENV_PIP" install --upgrade yt-dlp --quiet >> "$LOG_FILE" 2>&1
if [ $? -eq 0 ]; then
    log "yt-dlp 更新完成"
else
    log "yt-dlp 更新失敗，嘗試繼續..."
fi

# 確認所有依賴都已安裝（靜默模式，只補裝缺少的）
"$VENV_PIP" install -r "$SCRIPT_DIR/requirements.txt" --quiet >> "$LOG_FILE" 2>&1

# 清除 yt-dlp 快取（避免快取過期問題）
"$SCRIPT_DIR/.venv/bin/yt-dlp" --rm-cache-dir >> "$LOG_FILE" 2>&1

log "啟動 MCP server..."
exec "$VENV_PYTHON" "$SCRIPT_DIR/server.py"
