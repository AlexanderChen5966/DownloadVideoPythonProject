# P6：有聲書下載器（download_audiobook）— 多來源、按章節分檔

> **狀態：⏳ 待實作**
> **優先級：P6（功能擴充）**
> **建立日期：2026-09-29**
> **完成日期：—**
> **實際影響檔案：預估 6 個**（`server.py`、`download_cli.py`、`utils/response.py`、`utils/rss_parser.py`，新增 `tools/audiobook_downloader/` 模組）
> **前置依賴：P0–P3 皆已完成；P5 建議先行（共用 manifest 概念與 `MANIFEST_INVALID`，若 P5 未實作則本任務一併補上，見任務 1）**

---

## 需求描述

教學現場需要的不是單集 Podcast，而是一整套「有聲書」：可能是老師自錄的分章講解、自有版權的故事音檔，也可能是公開授權的 Podcast 節目。現有 `podcast_downloader` 一次只能下一集（`tools/podcast_downloader.py:15`，`episode_index` 單一整數），沒有列章節、多選、整套打包的能力。

本任務新增獨立的有聲書下載器：**多種來源輸入，正規化成同一種「章節清單」，再按章節下載成多個 mp3＋總 manifest**，方便老師挑章節在課堂播放。

## 目標

- 新增 `tools/audiobook_downloader/` 模組：來源正規化、章節下載、打包（含 ID3 章節標籤）
- 支援兩種來源：(a) 自有音檔 manifest（本地 JSON 或 URL）；(b) 公開 Podcast RSS（整檔節目映射為一書、集數映射為章節）
- 新增 `download_audiobook` MCP tool（第 11 個工具）＋ `query_audiobook` 預覽工具（第 12 個）
- `download_cli.py` 新增 `--audiobook-manifest`／`--audiobook-rss` 模式
- 章節多選＋歷史跳過＋`ctx.report_progress` 進度回報＋單章失敗不中斷
- 版權閘門沿用 P5：`rights` 聲明＋白名單（詳見「實作注意事項」）

---

## 影響範圍分析

| 檔案 | 修改原因 |
|------|---------|
| `tools/audiobook_downloader/`（新增） | 來源正規化、章節下載核心、打包；與 P5 的 `tools/ebook_downloader/` 平級 |
| `utils/rss_parser.py` | 新增 `list_episodes()`＋抽共用 enclosure 解析（只加函式＋抽取，不改 `parse_rss_feed`／`get_feed_info` 行為） |
| `server.py` | 新增 `download_audiobook`、`query_audiobook` 兩個 tool（thin-wrapper，仿 `server.py:559-581`） |
| `utils/response.py` | 沿用 P5 的 `MANIFEST_INVALID`；若 P5 未實作，本任務加同一列（冪等，見任務 1） |
| `download_cli.py` | 新增 audiobook 參數組＋獨立分支（仿 `download_cli.py:467-524`） |
| 不修改 | `tools/podcast_downloader.py`（單集流程保留，供舊 Prompt 沿用）、`utils/audio_downloader.py`、`utils/sanitizer.py`、`utils/download_history.py`、`whitelist.json` 結構 |

---

## 實作任務

### 任務 0：實作前必讀

> | 項目 | 必須做法 | 出處 |
> |------|---------|------|
> | 所有輸出檔名 | `sanitize_filename()`（`utils/sanitizer.py:68`）；Podcast 集數標題常含 `EP143｜` 等符號與不可見空白 | [ISSUE-004](../issues/ISSUE-004-Invisible-Whitespace-In-Filenames.md) |
> | 覆寫判斷 | `resolve_existing_path()` ＋ `os.path.samefile()`，禁止字串比較 | [ISSUE-005](../issues/ISSUE-005-Case-Insensitive-Path-Comparison-Data-Loss.md) |
> | 白名單 | MCP 工具一律 `skip_whitelist=False`；注意 `download_podcast` 內部對 enclosure URL 會**二次驗證**（`tools/podcast_downloader.py:54-60`）——本任務直接調 `download_audio_direct`，enclosure URL 也要先過一次白名單，不可沿用 `skip_whitelist=True` 的捷徑（`tools/podcast_downloader.py:62-67` 的寫法是單集舊流程的特例，不複製） |

### 任務 1：自有音檔 manifest `tools/audiobook_downloader/manifest.py`

```jsonc
{
  "book": "自編教材・有聲版",
  "cover": "https://.../cover.jpg",   // 可選
  "chapters": [
    {"id": "ch01", "title": "第一課", "audio": "https://.../ch01.mp3"},
    {"id": "ch02", "title": "第二課", "audio": "https://.../ch02.mp3"}
  ]
}
```

- `load_audiobook_manifest(source) -> dict`：本地路徑或 URL（URL 先過白名單）；缺 `book`／`chapters`／任一章缺 `id+title+audio` → 呼叫端回 `error_response("MANIFEST_INVALID", ...)`
- `MANIFEST_INVALID` 若 P5 已在 `utils/response.py` 對照表加過則直接沿用，否則本任務加同一列（同名同義，之後 P5 實作時跳過重複添加）
- 與 P5 的書籍 manifest 是不同 schema（本任務無 `pages`），**不強行共用解析器**；若 P5 已合併，可把 URL 讀取＋白名單＋JSON 載入抽成小函式共用，否則各自獨立（不要為了共用而提前重構）

### 任務 2：RSS 列集清單 `utils/rss_parser.py`（加法修改）

```python
def list_episodes(url: str, limit: int = 100) -> Dict[str, Any]:
    """
    列出 RSS 全部集數（給有聲書「章節清單」用）。
    回傳 {"success", "podcast_title", "total_episodes",
            "episodes": [{"index", "title", "audio_url", "published"}]}
    """
```

- 把現有 enclosure 抽取邏輯（`utils/rss_parser.py:77-96`）抽成 `_extract_audio_url(episode) -> str | None`，`parse_rss_feed` 改調它（行為不變，只是搬移）
- 無 enclosure 的集數：`audio_url=None`，由下載核心跳過並記入 `failures`（不要在列清單時丟掉，使用者要看得到缺了哪集）
- `limit` 防爆：集數上千的節目只取前 N 集並在回傳註明 `truncated=True`

### 任務 3：來源正規化＋章節下載 `tools/audiobook_downloader/downloader.py`

```python
async def download_audiobook_chapters(
    chapters: list[dict],   # 已正規化：[{id, title, audio_url}]
    book_title: str,
    output_dir: str,
    ctx=None,
    processed: int = 0, total: int = 0,  # 跨來源累計進度（保留擴充位，首版可只傳單書）
) -> dict:
```

- 正規化（寫在 MCP tool 層或本模組的 `normalize_source()`，二選一，文件內統一）：
  - manifest 來源 → `[{id, title, audio_url=audio}]`
  - RSS 來源 → 任務 2 的 episodes → `[{id=f"ep{index:03d}", title, audio_url}]`，`audio_url=None` 者標記跳過
- 逐章調 `download_audio_direct(url, output_dir, filename=sanitize_filename(f"{id}_{title}"), skip_whitelist=False)`（`utils/audio_downloader.py:26-40`）
- 每章完成：`ctx.report_progress`（仿 `server.py:222-223`）；單章失敗記 `failures[]` 繼續下一章
- 歷史 key：`f"abook:{source_sha1[:12]}:{chapter_id}"`，沿用 `is_downloaded`／`add_record`（`utils/download_history.py:25,37`），全命中章節進 `skipped`

### 任務 4：打包 `tools/audiobook_downloader/packager.py`

輸出結構（`downloads/audiobooks/<書名>/`）：

```
<書名>/
├── ch01_第一課.mp3
├── ch02_第二課.mp3
├── cover.jpg          # manifest 有給才下
├── manifest.json      # {"book", "source_type": "manifest|rss", "source": ..., "chapters": [{id, title, file, audio_url}]}
└── <書名>.zip         # 可選（--no-zip 跳過）
```

- ID3 標籤：用 FFmpeg（專案既有依賴）`ffmpeg -i in.mp3 -c copy -metadata title="<章標題>" -metadata album="<書名>" out.mp3；失敗不中斷（標籤是加分項，檔案本體優先）
- zip 打包前 `os.path.samefile()` 防自覆蓋（任務 0，ISSUE-005）

### 任務 5：MCP 工具 `server.py`

```python
@mcp.tool()
async def query_audiobook(
    source: str,          # manifest 路徑/URL，或 RSS URL（二選一自動判斷：is_rss_url → RSS，否則 manifest）
    ctx: Context = None,
) -> dict:
    """預覽有聲書章節清單（不下載）。回傳書名、來源類型與 [{id, title}]，供挑章節。"""

@mcp.tool()
async def download_audiobook(
    source: str,
    chapters: list[str] | None = None,   # None = 全書；否則只下指定章節 id
    output_dir: str = "./downloads/audiobooks",
    rights: Literal["own", "licensed"] = "own",
    license_note: str = "",
    make_zip: bool = True,
    ctx: Context = None,
) -> dict:
```

- 來源判斷：`is_rss_url(source)`（`utils/rss_parser.py:10`）→ RSS 流程，否則 manifest 流程；RSS 流程的 `rights` 預設仍為 `own`（公開 RSS 不等於放棄版權，見注意事項 1）
- `rights="licensed"` 時 `license_note` 必填（缺則 `MISSING_PARAM`）
- 回傳 `success_response(book, source_type, chapters=[{id, title, file, status}], skipped=[...], failures=[...], package_path)`

### 任務 6：CLI `download_cli.py`

```bash
python download_cli.py --audiobook-manifest ./mybook.json --chapters ch01 ch03 -o ./audiobooks
python download_cli.py --audiobook-rss https://feeds.example.com/show.rss --chapters ep000 ep005 --no-zip
```

- 新增 `audiobook_group`：`--audiobook-manifest`、`--audiobook-rss`（互斥，`add_mutually_exclusive_group`）、`--chapters nargs="*"`、`--no-zip`
- 出現任一 `--audiobook-*` 即走獨立分支（仿 `download_cli.py:516-524`），沿用 `print_summary()` 輸出

---

## 實作注意事項

1. **版權閘門（必做）**：公開 RSS ≠ 可任意重製散佈。`rights` 聲明＋白名單雙把關沿用 P5；教學合理使用範圍由使用者自行負責，工具只記錄 `rights`＋`license_note` 到回傳與 manifest.json 以備查。訂閱制／DRM 內容排除原則同 P5 注意事項 1–2。
2. **不動舊 Podcast 流程**：`tools/podcast_downloader.py` 單集下載與 `download_podcast_series` Prompt 保持原樣；新工具是並列的「整套書」流程，不重構舊程式。
3. **檔名長度**：`{id}_{title}.mp3` 可能過長（Podcast 標題常數十中文字），`sanitize_filename` 後再截斷至 100 字元（保留副檔名），截斷前先做全形→半形？不做，只截斷，避免引入新的正規化爭議。
4. **不要過度設計**：整書合併單檔、章節轉場音、播放器頁都不在本文件範圍；先讓分章多檔＋manifest 落地。

---

## 修改摘要

| 項目 | 說明 |
|------|------|
| 新增模組 | `tools/audiobook_downloader/`（manifest.py、downloader.py、packager.py） |
| RSS 解析 | `list_episodes()` 新增＋`_extract_audio_url()` 抽取（行為不變） |
| 新增 MCP 工具 | `download_audiobook`（第 11 個）、`query_audiobook`（第 12 個） |
| CLI | `--audiobook-manifest`／`--audiobook-rss` 互斥組＋`--chapters`＋`--no-zip` |
| error_code | 沿用 P5 的 `MANIFEST_INVALID`（缺則補） |
| 歷史紀錄 | 複用，key 改為 `abook:{hash}:{chapter}` |
| 不修改 | `tools/podcast_downloader.py`、`parse_rss_feed`／`get_feed_info` 行為、白名單結構 |

---

## 執行步驟

```
步驟 1：utils/rss_parser.py 加 list_episodes＋抽 _extract_audio_url（任務 2）
  → 先跑既有 podcast 單集下載確認行為沒變

步驟 2：新增 tools/audiobook_downloader/（任務 1、3、4）
  → manifest 解析 → downloader → packager 順序實作

步驟 3：utils/response.py 確認 MANIFEST_INVALID 存在（有則跳過）

步驟 4：server.py 加兩個 MCP 工具（任務 5）→ 重啟 MCP server

步驟 5：download_cli.py 加參數組與分支（任務 6）

步驟 6：手動驗證（開發環境）
  → [ ] 自編 manifest（2 章）CLI 下載：檢查目錄、manifest.json、ID3（ffprobe 看 title/album）
  → [ ] 用一個公開測試 RSS（如 feedparser 自帶範例等級的小節目）只下指定 2 集，確認其餘跳過
  → [ ] 同一來源重跑：全章進 skipped，不重下
  → [ ] 章節 id 打錯 → MANIFEST_INVALID；RSS 無 enclosure 的集 → 記入 failures 且流程繼續
  → [ ] 集數標題含特殊符號／NBSP：repr 檢查輸出檔名已清洗且 ≤100 字元
  → [ ] 經 MCP 呼叫：進度回報正常、回傳含 package_path；未加白名單網域 → WHITELIST_DENIED
  → [ ] 舊 podcast_downloader 單集流程回歸正常（未被改壞）
```

---

## 相關檔案

| 檔案 | 修改性質 |
|------|---------|
| `tools/audiobook_downloader/` | 新增（manifest.py、downloader.py、packager.py） |
| `utils/rss_parser.py` | 修改（加 `list_episodes`＋抽 `_extract_audio_url`；`parse_rss_feed` 行為不變，`utils/rss_parser.py:30-124`） |
| `server.py` | 修改（兩個 `@mcp.tool()`；podcast 工具 `server.py:463` 不動） |
| `utils/response.py` | 修改或不修改（MANIFEST_INVALID 有則沿用，無則加一列） |
| `download_cli.py` | 修改（audiobook 互斥參數組＋獨立分支） |
| `download_history.json` | 執行期寫入（key 規則見任務 3） |
| `tools/podcast_downloader.py` | 不修改（`tools/podcast_downloader.py:15-78` 維持單集流程） |
| `README.md` | 修改（工具一覽 10→12 個、專案結構補 audiobook_downloader，實作完成後更新） |
