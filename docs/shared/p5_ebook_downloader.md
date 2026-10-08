# P5：電子書下載器（download_ebook）— 教學用離線包

> **狀態：⏳ 待實作**
> **優先級：P5（功能擴充）**
> **建立日期：2026-09-29**
> **完成日期：—**
> **實際影響檔案：預估 5 個**（`server.py`、`download_cli.py`、`utils/response.py`，新增 `tools/ebook_downloader/` 模組）
> **前置依賴：P0–P3 皆已完成**

---

## 需求描述

教學場景需要在無網路的教室環境使用電子書：把「逐頁圖＋逐頁導讀音檔」結構的有聲電子書，**按章節挑著下載**成離線包帶走。內容結構參考已驗證的業界做法（巧連智數位典藏有聲書 `storySource`：每頁一組 `{audio: mp3, poster: webp, id}`，音檔 `ended` 事件驅動 Turn.js 翻頁——見本次調研紀錄）。

下載入口要同時支援 MCP 工具（Agent 對話觸發）與 CLI（老師本機批次作業），並沿用本專案既有基礎設施：白名單、統一回傳結構、下載歷史、MCP 進度回報。

## 目標

- 新增 `tools/ebook_downloader/` 模組：manifest 解析、章節下載、離線包輸出
- 新增 `download_ebook` MCP tool（第 9 個工具）＋ `query_ebook_manifest` 預覽工具（第 10 個）
- `download_cli.py` 新增 `--ebook-manifest` 模式
- 章節粒度下載＋歷史跳過＋`ctx.report_progress` 進度回報
- 離線包內含 `manifest.json`（相對路徑版 storySource 結構），可選打包成 zip 方便攜帶
- 版權閘門：`rights` 聲明參數＋白名單雙重把關（詳見「實作注意事項」）

---

## 影響範圍分析

| 檔案 | 修改原因 |
|------|---------|
| `tools/ebook_downloader/`（新增） | manifest 解析器、章節下載核心、離線包組裝；仿 `tools/hls_downloader/` 的子模組形式 |
| `server.py` | 新增 `download_ebook`、`query_ebook_manifest` 兩個 tool（仿 `direct_download_audio` 的 thin-wrapper 寫法，`server.py:559-581`） |
| `utils/response.py` | error_code 對照表新增 `MANIFEST_INVALID`（manifest 缺欄位／章節不存在，不應重試） |
| `download_cli.py` | 新增 `--ebook-manifest`、`--chapters`、`--no-zip` 參數組（仿既有 Widevine 參數組寫法，`download_cli.py:467-512`） |
| `download_history.json` | 複用，不新增檔案；以 `manifest_hash + chapter_id` 作為去重 key（見任務 6） |
| 不修改 | `whitelist.json` 結構、`utils/audio_downloader.py`、`utils/sanitizer.py`、`utils/download_history.py`（全部直接複用） |

---

## 實作任務

### 任務 0：實作前必讀（沿用 P4 文件的同類缺陷教訓）

> | 項目 | 必須做法 | 出處 |
> |------|---------|------|
> | 所有輸出檔名 | `sanitize_filename()`（`utils/sanitizer.py:68`） | [ISSUE-004](../issues/ISSUE-004-Invisible-Whitespace-In-Filenames.md)：標題含 NBSP 等不可見字元會寫出無法操作的檔名 |
> | 檔案存在／覆寫判斷 | `resolve_existing_path()` ＋ `os.path.samefile()`，禁止字串比較 | [ISSUE-005](../issues/ISSUE-005-Case-Insensitive-Path-Comparison-Data-Loss.md)：macOS 不分大小寫，字串比較會讓程式同時讀寫同一檔案 |
> | 白名單 | MCP 工具一律 `skip_whitelist=False`（仿 `server.py:580`） | 專案安全慣例，README「安全注意事項」 |

### 任務 1：manifest 解析器 `tools/ebook_downloader/manifest.py`

輸入是一份書籍 manifest（本地 JSON 路徑或 http(s) URL），描述整書章節與每頁資源：

```jsonc
{
  "book": "自編教材・第一冊",
  "chapters": [
    {
      "id": "ch01",
      "title": "第一課",
      "pages": [
        {"id": "p01", "image": "https://.../p01.webp", "audio": "https://.../p01.mp3"},
        {"id": "p02", "image": "https://.../p02.webp", "audio": "https://.../p02.mp3"}
      ]
    }
  ]
}
```

- 解析函式簽名：`load_manifest(source: str) -> dict`（URL 則先經白名單 `get_validator().validate()`，`utils/whitelist_validator.py:123`）
- 欄位校驗失敗 → 呼叫端回 `error_response("MANIFEST_INVALID", ...)`（需先在 `utils/response.py:1-18` 對照表加一列）
- 提供 `list_chapters(manifest) -> [{id, title, page_count}]` 供預覽工具使用

### 任務 2：章節下載核心 `tools/ebook_downloader/downloader.py`

```python
async def download_chapter(
    manifest: dict,
    chapter_id: str,
    output_dir: str,
    ctx=None,            # FastMCP Context，CLI 傳 None
    total_pages: int = 0, processed_pages: int = 0,  # 跨章節累計進度用
) -> dict:
```

- 逐頁下載：音檔複用 `download_audio_direct(url, output_dir, filename, skip_whitelist=False)`（`utils/audio_downloader.py:26-40`，自帶白名單＋Content-Type 檢查＋SSL fallback＋串流寫檔）；頁圖用同款 HTTP 模式（白名單→HEAD 驗 Content-Type→串流寫檔），允許 `image/jpeg/png/webp`
- 檔名：`{page_id}.{ext}`，全部經 `sanitize_filename()`（任務 0）
- 每完成一頁：`if ctx: await ctx.report_progress(processed, total, f"{chapter_title} {page_id}")`（仿 `server.py:222-223`）
- 單頁失敗不中斷整章：記錄到 `failures[]` 後繼續，最後回傳成功頁數＋失敗清單（教學現場寧可缺一頁也不要整章報廢）
- 寫入歷史：`add_record(key, file_path, file_size, success)`（`utils/download_history.py:37`），key 格式見任務 6

### 任務 3：離線包組裝 `tools/ebook_downloader/packager.py`

輸出結構（`downloads/ebooks/<書名>/<chapter_id>/`）：

```
ch01/
├── pages/            # p01.webp, p02.webp, ...
├── audio/            # p01.mp3, p02.mp3, ...
├── manifest.json     # 相對路徑版 storySource：{"chapter":..., "content":[{"id","image":"pages/p01.webp","audio":"audio/p01.mp3"}]}
└── ch01.zip          # 可選（--no-zip 跳過），單檔方便隨身碟攜帶
```

- `manifest.json` 刻意鏡像巧連智 `storySource.content` 的 `{audio, poster, id}` 形狀（相對路徑），之後要套 Turn.js 播放器可無痛接上
- zip 打包前用 `os.path.samefile()` 確認輸出 zip 與來源目錄不是同一路徑（任務 0，ISSUE-005）

### 任務 4：MCP 工具 `server.py`

```python
@mcp.tool()
async def query_ebook_manifest(
    manifest_source: str,
    ctx: Context = None,
) -> dict:
    """預覽電子書章節清單（不下載）。回傳書名與 [{id, title, page_count}]，供 Agent 與使用者挑章節。"""

@mcp.tool()
async def download_ebook(
    manifest_source: str,
    chapters: list[str] | None = None,   # None = 全書；否則只下指定章節 id
    output_dir: str = "./downloads/ebooks",
    rights: Literal["own", "licensed"] = "own",
    license_note: str = "",
    make_zip: bool = True,
    ctx: Context = None,
) -> dict:
    """按章節下載電子書離線包。每章先查歷史跳過已完成者，逐頁下載＋進度回報＋組 manifest.json（可選 zip）。"""
```

- `rights="licensed"` 時 `license_note` 為必填（缺則 `MISSING_PARAM`）；`rights` 僅接受這兩個值
- 章節 id 不存在 → `MANIFEST_INVALID`，不應重試
- 回傳 `success_response(book, chapters=[{id, title, pages_ok, pages_fail, failures, package_path}], skipped=[...])`

### 任務 5：CLI `download_cli.py`

```bash
python download_cli.py --ebook-manifest ./mybook.json --chapters ch01 ch03 -o ./ebooks
python download_cli.py --ebook-manifest https://example.com/book.json --no-zip --no-whitelist
```

- 新增 `ebook_group` argument group（仿 Widevine 組，`download_cli.py:467-512`）：`--ebook-manifest`、`--chapters nargs="*"`、`--no-zip`
- `--ebook-manifest` 出現時走獨立分支（仿 `--detect-drm`／`--decrypt-widevine` 分支，`download_cli.py:516-524`），不與既有 URL 下載流程混用
- 沿用 `print_summary()` 格式輸出總結

### 任務 6：歷史去重 key

`utils/download_history.py` 的 `is_downloaded(url)` 以整條 URL 比對，不適用章節粒度。本任務**不改該檔**，改為呼叫端組 key：

```python
key = f"ebook:{manifest_sha1[:12]}:{chapter_id}:{page_id}"
is_downloaded(key)   # 命中且檔案存在 → 跳過該頁
```

- `download_ebook` 開頭先對每章每頁查歷史，全命中且檔案存在 → 該章進 `skipped`，不重下（呼應 README「自動跳過已下載」行為）
- 失敗頁不寫成功紀錄，下次重跑會自動補下

---

## 實作注意事項

1. **版權閘門（必做）**：`rights` 參數只是聲明，真正的 enforcement 靠白名單——未授權來源預設擋下。**明確排除**：訂閱制平台中條款禁止下載的內容不在本工具支援範圍（例：巧連智數位典藏學習網 FAQ「資料與功能限制」qa/11 明載「僅提供在線瀏覽，無法下載」；會員條款亦禁止複製散佈）。本工具只處理使用者擁有版權或已獲授權的教材 manifest。
2. **DRM 內容不碰**：若 manifest 指向的音檔／頁圖需要 DRM 解密（如 Widevine/FairPlay），超出本工具範圍——參考 P4 做法，解密流程只做手動研究用途，不包進自動下載器。
3. **頁圖 Content-Type 白名單**：`image/jpeg/png/webp/gif`；音檔沿用 `download_audio_direct` 既有判斷（`utils/audio_downloader.py:63-65`）。
4. **不要過度設計**：離線閱讀器（Turn.js 播放頁）不在本文件範圍；先讓離線包＋`manifest.json` 落地，播放器另開任務文件。

---

## 修改摘要

| 項目 | 說明 |
|------|------|
| 新增模組 | `tools/ebook_downloader/`（manifest.py、downloader.py、packager.py） |
| 新增 MCP 工具 | `download_ebook`（第 9 個）、`query_ebook_manifest`（第 10 個） |
| CLI | `--ebook-manifest`、`--chapters`、`--no-zip` 參數組＋獨立分支 |
| error_code | 新增 `MANIFEST_INVALID` |
| 歷史紀錄 | 複用，key 改為 `ebook:{hash}:{chapter}:{page}` |
| 不修改 | 白名單結構、audio_downloader、sanitizer、history 模組本體 |

---

## 執行步驟

```
步驟 1：新增 tools/ebook_downloader/（任務 1–3）
  → 先寫 manifest 解析＋校驗，再寫 downloader，最後 packager

步驟 2：utils/response.py 加 MANIFEST_INVALID
  → 只加對照表註解一列，不動函式簽名

步驟 3：server.py 加兩個 MCP 工具（任務 4）
  → 放在 direct_download_audio 之後；重啟 MCP server 生效

步驟 4：download_cli.py 加參數組與分支（任務 5）

步驟 5：手動驗證（開發環境）
  → [ ] 用一份自編 manifest（含 2 章、每章 2–3 頁）跑 CLI 全書下載，檢查目錄結構與 manifest.json
  → [ ] 只指定單一章節重跑，確認另一章節被跳過（歷史去重）
  → [ ] manifest 缺欄位／章節 id 打錯，確認回 MANIFEST_INVALID
  → [ ] 未加白名單的來源網域，確認回 WHITELIST_DENIED
  → [ ] 檔名含中文＋特殊字元的章節標題，確認輸出檔名已清洗（repr 檢查無 NBSP）
  → [ ] 經 MCP 呼叫 download_ebook，確認 ctx 進度回報正常、回傳含 package_path
  → [ ] zip 內檔案可解開且與來源一致（抽查 1 章）
```

---

## 相關檔案

| 檔案 | 修改性質 |
|------|---------|
| `tools/ebook_downloader/` | 新增（manifest.py、downloader.py、packager.py，可加 `__init__.py` 匯出） |
| `server.py` | 修改（兩個 `@mcp.tool()`，仿 `direct_download_audio`，`server.py:559-581`） |
| `utils/response.py` | 修改（對照表加 `MANIFEST_INVALID`，`utils/response.py:1-18`） |
| `download_cli.py` | 修改（ebook 參數組＋獨立分支，仿 `download_cli.py:467-524`） |
| `download_history.json` | 執行期寫入（格式不變，key 規則見任務 6） |
| `utils/audio_downloader.py` | 不修改，直接複用（`utils/audio_downloader.py:26`） |
| `utils/sanitizer.py` | 不修改，直接複用（`utils/sanitizer.py:36,68`） |
| `README.md` | 修改（工具一覽 8→10 個、專案結構補 ebook_downloader，實作完成後更新） |
