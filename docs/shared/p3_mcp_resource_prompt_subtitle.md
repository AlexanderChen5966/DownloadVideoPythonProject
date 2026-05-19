# P3：MCP Resource/Prompt、字幕下載、格式查詢

> **狀態：⏳ 待實作**
> **優先級：P3（未來）**
> **建立日期：2026-05-19**
> **預估影響檔案：2 個**
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

提供預設操作流程，引導 Agent 正確使用工具。

```python
@mcp.prompt()
def batch_download_youtube() -> str:
    """批量下載 YouTube 影片的最佳操作流程"""
    return """
    操作步驟：
    1. 先用 whitelist_manage(action="list") 確認 youtube.com 在白名單中
    2. 使用 download_media(urls=[...], format="audio") 批量下載
    3. 若下載失敗且 error_code 為 YTDLP_FAILED，可能需要更新 yt-dlp
    4. 下載完成後告知使用者檔案位置和大小
    """


@mcp.prompt()
def download_with_subtitles() -> str:
    """下載影片同時取得字幕的操作流程"""
    return """
    操作步驟：
    1. 使用 query_formats(url=...) 查詢可用格式和字幕語言
    2. 使用 download_media(urls=[...], format="mp4", subtitles=True, sub_lang="zh-TW")
    3. 字幕檔會自動儲存在影片同目錄下
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

## P3 完成後工具清單（7 → 9）

| # | 類型 | 名稱 | 說明 |
|---|------|------|------|
| 1 | Tool | `download_media` | 影音下載（含字幕、playlist） |
| 2 | Tool | `convert_to_mp3` | 格式轉換 |
| 3 | Tool | `download_and_convert_image` | 圖片下載轉換 |
| 4 | Tool | `podcast_downloader` | Podcast 下載 |
| 5 | Tool | `download_hls_tool` | HLS 串流下載 |
| 6 | Tool | `direct_download_audio` | 純 HTTP 音檔下載 |
| 7 | Tool | `whitelist_manage` | 白名單管理 |
| 8 | Tool | `query_formats` | 格式查詢（P3 新增） |
| 9 | Resource | `config://whitelist` | 白名單狀態（唯讀） |
| 10 | Resource | `status://ytdlp-version` | yt-dlp 版本（唯讀） |
| 11 | Resource | `data://download-history` | 下載歷史（唯讀） |
| 12 | Prompt | `batch_download_youtube` | 批量下載流程 |
| 13 | Prompt | `download_with_subtitles` | 字幕下載流程 |

---

## 驗證清單

- [ ] `config://whitelist` Resource 可被 Agent 讀取
- [ ] `status://ytdlp-version` 正確回傳版本號
- [ ] `data://download-history` 回傳最近 20 筆紀錄
- [ ] Prompt template 可在 Claude Desktop 中被選取使用
- [ ] 字幕下載：中文字幕正確儲存為 .srt 檔
- [ ] 字幕下載：`subtitles=False` 時不影響原有行為
- [ ] `query_formats` 回傳正確的格式清單
- [ ] `query_formats` 對無效 URL 回傳結構化錯誤
