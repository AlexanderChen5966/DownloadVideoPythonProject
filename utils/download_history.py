"""
下載歷史紀錄管理
自動偵測並跳過已下載的 URL，避免重複下載
"""

import json
import os
from datetime import datetime
from pathlib import Path

HISTORY_FILE = Path(__file__).parent.parent / "download_history.json"
MAX_RECORDS = 500


def load_history() -> dict:
    if not HISTORY_FILE.exists():
        return {"downloads": []}
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {"downloads": []}


def is_downloaded(url: str) -> dict | None:
    """檢查 URL 是否已下載過且檔案仍存在，回傳紀錄或 None"""
    history = load_history()
    for entry in history["downloads"]:
        if entry["url"] == url and entry.get("success"):
            file_path = entry.get("file_path", "")
            if file_path and os.path.exists(file_path):
                return entry
    return None


def add_record(url: str, file_path: str, file_size: int, success: bool):
    """新增下載紀錄，超過 500 筆時自動清理最舊的紀錄"""
    history = load_history()
    history["downloads"].append({
        "url": url,
        "file_path": file_path,
        "file_size": file_size,
        "success": success,
        "timestamp": datetime.now().isoformat()
    })
    history["downloads"] = history["downloads"][-MAX_RECORDS:]
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except IOError:
        pass
