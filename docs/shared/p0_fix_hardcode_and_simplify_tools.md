# P0：修復硬編碼路徑與精簡 MCP 工具

> **狀態：⏳ 待實作**
> **優先級：P0（必做）**
> **建立日期：2026-05-19**
> **預估影響檔案：4 個**

---

## 需求描述

media-downloader MCP 目前有兩個核心問題影響可用性：
1. `yt-dlp` 路徑硬編碼為特定使用者路徑，其他機器無法使用
2. MCP 工具數量過多（13 個），其中低價值和可合併的工具佔了 7 個，增加 Agent 的選擇負擔

## 目標

- `yt-dlp` 路徑改為動態偵測，任何環境都能正常啟動
- MCP 工具從 13 個精簡為 7 個，移除低價值工具、合併白名單工具

---

## 影響範圍分析

| 檔案 | 修改原因 |
|------|---------|
| `server.py:75` | `yt_dlp_path` 硬編碼 |
| `server.py` 全域 | 移除 `ensure_directory`、`list_files`、`open_file`，合併 4 個白名單工具為 1 個 |
| `download_cli.py:88` | `yt-dlp` 用相對路徑，需統一偵測邏輯 |
| `utils/path_resolver.py`（新增） | 共用路徑偵測工具 |

## 風險評估

| 風險項目 | 是否影響 | 說明 |
|---------|---------|------|
| MCP 工具簽名變更 | ✅ 是 | 移除 3 個工具、合併白名單為 1 個，Agent 的舊 prompt 需適配 |
| 向後相容 | ⚠️ 部分 | Claude Desktop 使用者重啟後自動適配，但依賴舊工具名的外部整合會中斷 |
| 路徑偵測失敗 | ⚠️ 可能 | 需要 fallback 機制：venv → PATH → 報錯 |

---

## 實作任務

### 任務 1：建立共用路徑偵測工具

**新增 `utils/path_resolver.py`**

```python
import shutil
import sys
from pathlib import Path


def find_ytdlp() -> str:
    """
    動態偵測 yt-dlp 路徑
    優先順序：venv → PATH → 報錯
    """
    # 1. 同一 venv 下的 yt-dlp
    venv_path = Path(sys.executable).parent / "yt-dlp"
    if venv_path.exists():
        return str(venv_path)

    # 2. 系統 PATH
    system_path = shutil.which("yt-dlp")
    if system_path:
        return system_path

    raise FileNotFoundError(
        "找不到 yt-dlp。請執行: pip install yt-dlp"
    )


def find_node() -> str | None:
    """
    偵測 Node.js 路徑（用於 YouTube n-challenge）
    找不到時回傳 None，不阻斷下載
    """
    return shutil.which("node")
```

### 任務 2：修改 server.py — 路徑偵測

**修改前（server.py:74-80）：**
```python
yt_dlp_path = "/Users/alexander/PycharmProjects/DownloadVideoPythonProject/.venv/bin/yt-dlp"
cmd = [
    yt_dlp_path,
    "--js-runtimes", "node:/opt/homebrew/bin/node",
    "--remote-components", "ejs:github",
    "-o", f"{output_dir}/%(title)s.%(ext)s"
]
```

**修改後：**
```python
from utils.path_resolver import find_ytdlp, find_node

yt_dlp_path = find_ytdlp()
cmd = [
    yt_dlp_path,
    "--remote-components", "ejs:github",
    "-o", f"{output_dir}/%(title)s.%(ext)s"
]

node_path = find_node()
if node_path:
    cmd[1:1] = ["--js-runtimes", f"node:{node_path}"]
```

### 任務 3：修改 download_cli.py — 統一路徑偵測

**修改前（download_cli.py:88）：**
```python
cmd = [
    "yt-dlp",
    "-o", f"{output_dir}/%(title)s.%(ext)s"
]
```

**修改後：**
```python
from utils.path_resolver import find_ytdlp, find_node

yt_dlp_path = find_ytdlp()
cmd = [
    yt_dlp_path,
    "-o", f"{output_dir}/%(title)s.%(ext)s"
]

node_path = find_node()
if node_path:
    cmd[1:1] = ["--js-runtimes", f"node:{node_path}"]
```

### 任務 4：移除低價值工具

從 `server.py` 移除以下 3 個工具（Agent 可用 Bash 直接達成）：

| 移除工具 | Agent 替代方式 |
|---------|---------------|
| `ensure_directory` | `mkdir -p /path` |
| `list_files` | `ls -lah /path` |
| `open_file` | `open /path`（macOS） |

### 任務 5：合併白名單工具

將 4 個白名單工具合併為 1 個：

**移除：**
- `whitelist_add_rule`
- `whitelist_remove_rule`
- `whitelist_list_rules`
- `whitelist_set_enabled`

**新增：**
```python
@mcp.tool()
async def whitelist_manage(
    action: Literal["list", "add", "remove", "enable", "disable"],
    rule: str | None = None
) -> dict:
    """
    管理網路白名單（查詢、新增、移除規則，啟用/停用）

    Args:
        action: 操作類型
            - 'list': 列出所有規則和狀態
            - 'add': 新增規則（需提供 rule）
            - 'remove': 移除規則（需提供 rule）
            - 'enable': 啟用白名單
            - 'disable': 停用白名單
        rule: 白名單規則（add/remove 時必填）
    """
```

---

## 精簡後工具清單（13 → 7）

| # | 工具名稱 | 說明 |
|---|---------|------|
| 1 | `download_media` | YouTube/平台影音下載 |
| 2 | `convert_to_mp3` | 格式轉換 |
| 3 | `download_and_convert_image` | 圖片下載轉換 |
| 4 | `podcast_downloader` | Podcast 下載 |
| 5 | `download_hls_tool` | HLS 串流下載 |
| 6 | `direct_download_audio` | 純 HTTP 音檔下載 |
| 7 | `whitelist_manage` | 白名單管理（合併 4→1） |

---

## 驗證清單

- [ ] `server.py` 中無任何硬編碼的 `/Users/alexander/` 路徑
- [ ] `download_cli.py` 中無任何硬編碼路徑
- [ ] Node.js 路徑改為動態偵測，找不到時不阻斷（僅 warning）
- [ ] MCP 啟動後只顯示 7 個工具
- [ ] `whitelist_manage` 的 5 種 action 都正常運作
- [ ] 在沒有 yt-dlp 的環境中呼叫 `download_media` 會回傳明確錯誤
- [ ] `start_mcp.sh` 包裝腳本仍可正常啟動
- [ ] CLI 工具 `download_cli.py` 仍可正常使用
