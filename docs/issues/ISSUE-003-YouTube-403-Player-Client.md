# ISSUE-003: YouTube 下載大量 403 Forbidden（player client 問題）

> **狀態：** ✅ 已解決
> **建立日期：** 2026-08-18
> **分類：** MCP 穩定性 / YouTube 反爬

---

## 問題描述

批次下載 8 支 YouTube 影片時，僅 1 支成功，其餘 7 支全部失敗於相同錯誤：

```
ERROR: unable to download video data: HTTP Error 403: Forbidden
```

失敗清單：

```
_2PnKgJVagY  0anzhInCCLY  LBFg-KYUcNs  dbshcwmIx2M
Cu_y1DUiOhk  bam_WxTq0j4  ROghAVZmm6g
```

### 關鍵症狀：metadata 正常，下載階段才失敗

`yt-dlp -F` 可以完整列出所有格式（含 1080p），代表 **extraction 完全正常**，403 只發生在實際抓取媒體串流時。這個特徵是判斷本問題的決定性線索——它排除了「影片被下架」「地區限制」「網址錯誤」等可能。

---

## 根本原因

yt-dlp 預設挑選的 player client 為 **`android_vr`**，該 client 取得的媒體 URL 會被 YouTube 直接回 403。

這**不是** yt-dlp 版本過舊造成的：

- venv 內 yt-dlp 已是當時最新版 **2026.7.4**
- `pip install --upgrade yt-dlp` 回報 already satisfied
- `yt-dlp -U` 對本問題無效

> ⚠️ 與 [ISSUE-001](ISSUE-001-MCP-Auto-Repair.md) 的重要區別：ISSUE-001 假設「下載失敗 = 套件版本過舊」，並以 `start_mcp.sh` 自動更新解決。本問題屬於**另一類形態**——YouTube 調整反爬後需要改變「呼叫參數」而非「升級版本」，自動更新機制完全無法修復。

---

## Player Client 實測結果

同一支影片（`_2PnKgJVagY`）逐一測試各 client：

| client | 結果 |
|--------|------|
| `android_vr`（預設） | ❌ HTTP Error 403: Forbidden |
| `tv` | ❌ The page needs to be reloaded |
| `web` | ❌ 只剩 storyboard 圖片，無媒體格式 |
| `web_safari` | ❌ 只剩 storyboard 圖片，無媒體格式 |
| `ios` | ⚠️ 高畫質需 GVS PO Token，格式被跳過 |
| `mweb` | ⚠️ 可下載但僅 format 18（360p），DASH 需 PO Token |
| `android` | ⚠️ 僅 360p，部分格式因 SABR-only 實驗缺 URL |
| **`web_embedded`** | ✅ **成功取得 1080p（137+140）並正常合併** |

`web_embedded` 的優勢：**無須 PO Token、無須 cookies**，即可取得完整格式清單。

---

## 解決方案

在 `utils/path_resolver.py` 新增共用 helper，對 YouTube 網址帶入 player client 優先序，由 yt-dlp 依序 fallback；非 YouTube 網址回傳空清單，行為完全不變。

```python
YOUTUBE_PLAYER_CLIENTS = "web_embedded,mweb,default"

def is_youtube_url(url: str) -> bool: ...
def youtube_extractor_args(url: str) -> list[str]: ...
```

實際帶入的參數：

```
--extractor-args youtube:player_client=web_embedded,mweb,default
```

### 修改檔案

| 檔案 | 位置 | 說明 |
|------|------|------|
| `utils/path_resolver.py` | 新增 helper | `YOUTUBE_PLAYER_CLIENTS` / `is_youtube_url()` / `youtube_extractor_args()` |
| `server.py` | `download_media` 下載指令 | MCP 主要下載路徑 |
| `server.py` | 格式查詢（`-J`） | 避免查詢階段同樣受影響 |
| `download_cli.py` | CLI 下載指令 | CLI 路徑 |

---

## 驗證

- 原本失敗的 **7 支影片，改用 `web_embedded` 後全數下載成功**
- 修改後的 `download_cli.py`：`_2PnKgJVagY` → 43 MB 1080p MP4 ✅
- 修改後的 MCP `download_media`：`0anzhInCCLY` → `failed: 0` ✅
- 非 YouTube 網址（如 `vimeo.com`）確認回傳空參數清單，不受影響 ✅

---

## 注意事項

- **MCP server 需重啟才會生效**，Claude Desktop 會沿用啟動時載入的 `server.py`
- **`web_embedded` 不是永久解**。YouTube 每次調整反爬機制都可能讓特定 client 失效。屆時只需修改 `utils/path_resolver.py` 中 `YOUTUBE_PLAYER_CLIENTS` 一行的優先序，三個呼叫點會一併套用
- 刻意**不採用 cookies 方案**（`--cookies-from-browser`）：會將個人 YouTube 帳號憑證帶入下載請求，有帳號被風控的風險，且 macOS 新版 Chrome 的 App-Bound Encryption 也會使讀取困難
- 若日後連 `web_embedded` 也失效，下一步可評估 PO Token provider plugin（如 `bgutil-ytdlp-pot-provider`），可在不登入的情況下產生 GVS PO Token

---

## 相關檔案

```
utils/path_resolver.py       # player client helper
server.py                    # MCP download_media / 格式查詢
download_cli.py              # CLI 下載
docs/issues/ISSUE-001-MCP-Auto-Repair.md   # 另一類失敗形態（版本過舊）
```

## 參考資料

- [yt-dlp PO Token Guide](https://github.com/yt-dlp/yt-dlp/wiki/PO-Token-Guide)
- [yt-dlp #12482 — SABR-only streaming experiment](https://github.com/yt-dlp/yt-dlp/issues/12482)
