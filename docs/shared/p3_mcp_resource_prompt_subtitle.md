# P3：MCP Resource/Prompt、字幕下載、格式查詢

> **狀態：✅ 已完成**
> **優先級：P3（未來）**
> **建立日期：2026-05-19**
> **完成日期：2026-05-19**
> **實際影響檔案：1 個**（server.py，get_ytdlp_version 已在 P0 建立於 path_resolver.py）
> **前置依賴：P0 + P1 + P2 完成後再做**

---

## 需求描述

利用 MCP 的 Resource 和 Prompt 能力，讓 Agent 更聰明地使用工具。同時擴充字幕下載和格式查詢功能。

## 目標

- Agent 可讀取白名單狀態、下載歷史、yt-dlp 版本（不佔工具位）
- 提供 Prompt template 引導 Agent 最佳操作流程
- 支援字幕下載和格式查詢

---

## 影響範圍分析

| 檔案 | 修改原因 |
|------|---------|
| `server.py` | 新增 Resource、Prompt、字幕和格式查詢工具 |
| `utils/path_resolver.py` | 新增 `get_ytdlp_version()` |

---

## 實作任務

### 任務 1：MCP Resource

Resource 讓 Agent 可以「讀取」資訊而不佔用工具位。

```python
@mcp.resource("config://whitelist")
async def whitelist_resource() -> str:
    """目前的白名單規則和狀態"""
    validator = get_validator()
    rules = validator.list_rules()
    return json.dumps({
        "enabled": validator.enabled,
        "total_rules": len(rules),
        "rules": rules
    }, ensure_ascii=False, indent=2)


@mcp.resource("status://ytdlp-version")
async def ytdlp_version_resource() -> str:
    """yt-dlp 的目前版本"""
    from utils.path_resolver import get_ytdlp_version
    return json.dumps(get_ytdlp_version())


@mcp.resource("data://download-history")
async def download_history_resource() -> str:
    """最近的下載歷史紀錄"""
    from utils.download_history import load_history
    history = load_history()
    recent = history["downloads"][-20:]  # 只回傳最近 20 筆
    return json.dumps(recent, ensure_ascii=False, indent=2)
```

**`utils/path_resolver.py` 新增：**

```python
def get_ytdlp_version() -> dict:
    """取得 yt-dlp 版本資訊"""
    try:
        path = find_ytdlp()
        result = subprocess.run(
            [path, "--version"],
            capture_output=True, text=True, timeout=5
        )
        return {"version": result.stdout.strip(), "path": path}
    except Exception as e:
        return {"version": "unknown", "error": str(e)}
```

### 任務 2：MCP Prompt Template

提供預設操作流程，引導 Agent 正確使用工具。Claude Desktop 啟動時會自動載入（已確認 `prompts/list` 已在日誌中被呼叫）。

**完整 Prompt 清單（6 個）：**

| Prompt 名稱 | 適用情境 |
|------------|---------|
| `batch_download_youtube` | YouTube 批量下載音檔 |
| `download_with_subtitles` | 下載影片同時取得字幕 |
| `download_podcast_series` | Podcast RSS 整季下載 |
| `download_hls_stream` | HLS 串流下載流程 |
| `manage_whitelist` | 白名單完整設定流程 |
| `check_mcp_health` | 診斷 MCP 狀態 |

```python
@mcp.prompt()
def batch_download_youtube() -> str:
    """批量下載 YouTube 影片的最佳操作流程"""
    return """
    操作步驟：
    1. 先用 whitelist_manage(action="list") 確認 youtube.com 在白名單中
    2. 使用 download_media(urls=[...], format="audio") 批量下載
    3. 若下載失敗且 error_code 為 YTDLP_FAILED，可能需要更新 yt-dlp（重啟 Claude Desktop 即可自動更新）
    4. 下載完成後告知使用者檔案位置和大小
    """


@mcp.prompt()
def download_with_subtitles() -> str:
    """下載影片同時取得字幕的操作流程"""
    return """
    操作步驟：
    1. 使用 query_formats(url=...) 查詢可用格式和字幕語言
    2. 確認 subtitle_languages 或 auto_subtitle_languages 中有 zh-TW 或 en
    3. 使用 download_media(urls=[...], format="mp4", subtitles=True, sub_lang="zh-TW,en")
    4. 字幕檔（.srt）會自動儲存在影片同目錄下
    """


@mcp.prompt()
def download_podcast_series() -> str:
    """下載 Podcast RSS Feed 整季的操作流程"""
    return """
    操作步驟：
    1. 先用 whitelist_manage(action="list") 確認 Podcast 網域在白名單中
       若不在，使用 whitelist_manage(action="add", rule="*.podcast-domain.com") 加入
    2. 使用 podcast_downloader(url=RSS_URL, episode_index=0) 下載最新一集確認格式正確
    3. 批量下載時，依序指定 episode_index=0,1,2,... 逐集下載
    4. 若 URL 為直接 MP3 連結（非 RSS），改用 direct_download_audio(url=...)
    """


@mcp.prompt()
def download_hls_stream() -> str:
    """下載 HLS (.m3u8) 串流視頻的操作流程"""
    return """
    操作步驟：
    1. 確認手上有 .m3u8 的 URL（通常從瀏覽器開發者工具的 Network 面板取得）
    2. 使用 download_hls_tool(m3u8_url=..., output_path="./downloads/video.mp4")
    3. 大型影片建議加上 threads=32 加速下載
    4. 注意：不支援加密的 HLS 流（AES-128 加密）
    5. 下載完成後確認 MP4 可正常播放
    """


@mcp.prompt()
def manage_whitelist() -> str:
    """白名單完整設定流程"""
    return """
    白名單管理操作：

    查看目前規則：
      whitelist_manage(action="list")

    新增網域（三種格式）：
      完整網域：whitelist_manage(action="add", rule="example.com")
      子網域：  whitelist_manage(action="add", rule="*.example.com")
      正則：    whitelist_manage(action="add", rule="^https?://.*\\.example\\.com/.*")

    移除規則：
      whitelist_manage(action="remove", rule="example.com")

    暫時停用白名單（測試用，不建議長期）：
      whitelist_manage(action="disable")

    重新啟用：
      whitelist_manage(action="enable")

    常用白名單規則建議：
      youtube.com, *.youtube.com, youtu.be — YouTube
      *.buzzsprout.com, *.libsyn.com       — Podcast 平台
      *.googlevideo.com                    — YouTube CDN（下載需要）
    """


@mcp.prompt()
def check_mcp_health() -> str:
    """診斷 MCP 狀態的操作流程"""
    return """
    MCP 狀態診斷步驟：

    1. 讀取 yt-dlp 版本：
       讀取 Resource status://ytdlp-version
       若版本超過 30 天未更新，建議重啟 Claude Desktop（start_mcp.sh 會自動更新）

    2. 確認白名單狀態：
       讀取 Resource config://whitelist
       確認 enabled=true 且目標網域在規則中

    3. 查看最近下載紀錄：
       讀取 Resource data://download-history
       確認最近下載是否成功

    4. 若 yt-dlp 下載持續失敗：
       error_code=YTDLP_FAILED → 重啟 Claude Desktop 強制更新
       error_code=NODE_NOT_FOUND → 需安裝 Node.js（brew install node）
       error_code=WHITELIST_DENIED → 執行 manage_whitelist 流程
    """
```

### 任務 3：字幕下載

在 `download_media` 新增字幕參數。

```python
@mcp.tool()
async def download_media(
    urls: list[str],
    output_dir: str = "./downloads",
    format: Literal["audio", "video", "best", "mp4", "mp3", "webm"] = "audio",
    subtitles: bool = False,
    sub_lang: str = "zh-TW,en",
    ctx: Context = None
) -> dict:
```

**yt-dlp 字幕參數：**
```python
if subtitles:
    cmd.extend([
        "--write-subs",
        "--write-auto-subs",
        "--sub-langs", sub_lang,
        "--sub-format", "srt/best"
    ])
```

### 任務 4：格式查詢工具

新增一個輕量工具，讓 Agent 在下載前查詢可用格式。

```python
@mcp.tool()
async def query_formats(url: str) -> dict:
    """
    查詢 URL 可用的下載格式（影片畫質、音檔品質、字幕語言）

    Args:
        url: 媒體 URL（YouTube、Podcast 等）

    Returns:
        可用格式列表，包含解析度、檔案大小估計、字幕語言
    """
    yt_dlp_path = find_ytdlp()
    cmd = [yt_dlp_path, "-J", "--no-download", url]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    info = json.loads(result.stdout)

    formats = []
    for f in info.get("formats", []):
        formats.append({
            "format_id": f.get("format_id"),
            "ext": f.get("ext"),
            "resolution": f.get("resolution", "audio only"),
            "filesize": f.get("filesize"),
            "vcodec": f.get("vcodec"),
            "acodec": f.get("acodec"),
        })

    subtitles = list(info.get("subtitles", {}).keys())
    auto_subs = list(info.get("automatic_captions", {}).keys())

    return success_response(
        title=info.get("title"),
        duration=info.get("duration"),
        formats=formats[-10:],  # 只回傳前 10 個（避免太多）
        subtitle_languages=subtitles,
        auto_subtitle_languages=auto_subs[:10]
    )
```

---

## P3 完成後完整清單（7 Tools → 8 Tools + 3 Resources + 6 Prompts）

**Tools（工具）**

| # | 名稱 | 說明 |
|---|------|------|
| 1 | `download_media` | 影音下載（含字幕、playlist） |
| 2 | `convert_to_mp3` | 格式轉換 |
| 3 | `download_and_convert_image` | 圖片下載轉換 |
| 4 | `podcast_downloader` | Podcast 下載 |
| 5 | `download_hls_tool` | HLS 串流下載 |
| 6 | `direct_download_audio` | 純 HTTP 音檔下載 |
| 7 | `whitelist_manage` | 白名單管理（P0 合併） |
| 8 | `query_formats` | 格式查詢（P3 新增） |

**Resources（唯讀資料，不佔工具位）**

| # | URI | 說明 |
|---|-----|------|
| 1 | `config://whitelist` | 白名單規則和啟用狀態 |
| 2 | `status://ytdlp-version` | yt-dlp 版本和路徑 |
| 3 | `data://download-history` | 最近 20 筆下載紀錄 |

**Prompts（操作流程卡片，Claude Desktop 可選取）**

| # | 名稱 | 適用情境 |
|---|------|---------|
| 1 | `batch_download_youtube` | YouTube 批量下載音檔 |
| 2 | `download_with_subtitles` | 下載影片同時取得字幕 |
| 3 | `download_podcast_series` | Podcast RSS 整季下載 |
| 4 | `download_hls_stream` | HLS 串流下載流程 |
| 5 | `manage_whitelist` | 白名單完整設定流程 |
| 6 | `check_mcp_health` | 診斷 MCP 狀態（版本/白名單/歷史） |

---

## 驗證清單

**Resource**
- [x] `config://whitelist` 可被 Agent 讀取，回傳 enabled 狀態和規則列表
- [x] `status://ytdlp-version` 正確回傳版本號和路徑
- [x] `data://download-history` 回傳最近 20 筆紀錄

**Prompt**
- [x] Claude Desktop 啟動後，6 個 Prompt 都能在介面中被選取
- [x] `batch_download_youtube` 流程：白名單確認 → 下載 → 回報結果
- [x] `download_with_subtitles` 流程：格式查詢 → 下載含字幕
- [x] `download_podcast_series` 流程：白名單確認 → 逐集下載
- [x] `download_hls_stream` 流程：HLS URL → MP4 輸出
- [x] `manage_whitelist` 流程：list/add/remove/enable/disable 都正常
- [x] `check_mcp_health` 流程：讀取三個 Resource 並給出診斷建議

**Tools**
- [x] 字幕下載：`subtitles=True` 時加入 --write-subs/--write-auto-subs 參數
- [x] 字幕下載：`subtitles=False` 時行為與原本完全相同
- [x] `query_formats`：正確回傳格式清單和字幕語言，含白名單與 YTDLP_FAILED 錯誤結構
- [x] MCP 載入：8 Tools + 6 Prompts + 3 Resources 全數確認
