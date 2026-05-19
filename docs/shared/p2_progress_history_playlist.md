# P2：下載進度回報、歷史紀錄、播放清單支援

> **狀態：⏳ 待實作**
> **優先級：P2（加值）**
> **建立日期：2026-05-19**
> **預估影響檔案：4 個**
> **前置依賴：P0 + P1 完成後再做**

---

## 需求描述

三項加值功能，提升使用體驗：
1. 大檔案下載時 Agent 無法回報進度，使用者以為系統卡住
2. 同一個 URL 可能被重複下載，浪費頻寬和空間
3. YouTube playlist 只能一個一個 URL 貼，不支援整個清單下載

## 目標

- 下載過程中 Agent 能回報進度百分比
- 自動偵測並跳過已下載的 URL
- 支援 YouTube playlist URL 一次下載整個清單

---

## 影響範圍分析

| 檔案 | 修改原因 |
|------|---------|
| `server.py` | `download_media` 加入 Context 進度回報、playlist 支援 |
| `utils/download_history.py`（新增） | 下載歷史紀錄管理 |
| `utils/audio_downloader.py` | 加入進度回報 callback |
| `download_history.json`（新增，自動產生） | 歷史紀錄資料檔 |

---

## 實作任務

### 任務 1：下載進度回報

利用 FastMCP 的 `Context` 物件回報進度。

**修改 `server.py` 的 `download_media`：**

```python
from fastmcp import Context

@mcp.tool()
async def download_media(
    urls: list[str],
    output_dir: str = "./downloads",
    format: Literal["audio", "video", "best", "mp4", "mp3", "webm"] = "audio",
    ctx: Context = None
) -> dict:
    for i, url in enumerate(urls):
        if ctx:
            await ctx.report_progress(
                progress=i,
                total=len(urls),
                message=f"下載中 ({i+1}/{len(urls)}): {url[:60]}..."
            )
        # ... 下載邏輯 ...

    if ctx:
        await ctx.report_progress(
            progress=len(urls),
            total=len(urls),
            message="全部下載完成"
        )
```

**FastMCP Context 說明：**
- `ctx.report_progress(progress, total, message)` 會透過 MCP protocol 的 `notifications/progress` 通知 Agent
- Agent（Claude Desktop / Claude Code）收到後可即時回報給使用者
- `ctx` 由 FastMCP 自動注入，不需要呼叫者傳入

### 任務 2：下載歷史紀錄

**新增 `utils/download_history.py`**

```python
import json
import os
from datetime import datetime
from pathlib import Path

HISTORY_FILE = Path(__file__).parent.parent / "download_history.json"


def load_history() -> dict:
    if not HISTORY_FILE.exists():
        return {"downloads": []}
    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def is_downloaded(url: str) -> dict | None:
    """檢查 URL 是否已下載過，回傳紀錄或 None"""
    history = load_history()
    for entry in history["downloads"]:
        if entry["url"] == url and entry.get("success"):
            file_path = entry.get("file_path", "")
            if os.path.exists(file_path):
                return entry
    return None


def add_record(url: str, file_path: str, file_size: int, success: bool):
    """新增下載紀錄"""
    history = load_history()
    history["downloads"].append({
        "url": url,
        "file_path": file_path,
        "file_size": file_size,
        "success": success,
        "timestamp": datetime.now().isoformat()
    })
    # 只保留最近 500 筆
    history["downloads"] = history["downloads"][-500:]
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)
```

**整合到 `download_media`：**

```python
from utils.download_history import is_downloaded, add_record

# 在下載前檢查
existing = is_downloaded(url)
if existing:
    saved_files.append({
        "url": url,
        "status": "skipped",
        "reason": "already_downloaded",
        "file_path": existing["file_path"]
    })
    continue

# 下載成功後記錄
add_record(url, file_path, file_size, success=True)
```

### 任務 3：YouTube Playlist 支援

yt-dlp 原生支援 playlist URL，只需要調整輸出解析邏輯。

**修改 `download_media`：**

```python
# yt-dlp 已原生支援 playlist URL，例如：
# https://www.youtube.com/playlist?list=PLxxxxx
# 不需要特殊處理，只需要加入 --yes-playlist 參數

cmd.append("--yes-playlist")

# 加入 --print after_move:filepath 取得實際儲存路徑
cmd.extend(["--print", "after_move:filepath"])
```

**同時更新工具的 docstring 讓 Agent 知道支援 playlist：**

```python
async def download_media(
    urls: list[str],
    ...
) -> dict:
    """
    使用 yt-dlp 下載 YouTube 影片或音檔，支援批量下載多個 URL

    Args:
        urls: 要下載的媒體 URL 列表
              支援單一影片、播放清單（playlist）、頻道 URL
    """
```

---

## 新增檔案的 .gitignore

```
download_history.json
```

---

## 驗證清單

- [ ] 下載多個 URL 時，Agent 能收到進度通知
- [ ] 重複下載相同 URL 時，顯示 `skipped` 且不重新下載
- [ ] 已下載但檔案已刪除時，重新下載而非跳過
- [ ] YouTube playlist URL 能一次下載整個清單
- [ ] `download_history.json` 已加入 `.gitignore`
- [ ] 歷史紀錄超過 500 筆時自動清理舊紀錄
- [ ] 單一 URL 下載仍正常運作（不受 playlist 改動影響）
