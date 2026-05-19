# 多媒體下載與轉檔 MCP Server

> **版本：v4.0.0** | 更新日期：2026-05-19

一個由 Claude AI Agent 透過 MCP（Model Context Protocol）控制的自動化媒體處理系統。

---

## 版本紀錄

### v4.0.0（2026-05-19）— 架構全面升級

- **P0**：修復 yt-dlp 硬編碼路徑（動態偵測 venv / PATH），精簡工具 13 → 8 個
- **P1**：統一回傳結構（error_code 標準化），SSL 驗證改為 fallback 模式，合併重複下載邏輯
- **P2**：MCP Context 進度回報、下載歷史紀錄（自動跳過已下載）、YouTube Playlist 支援
- **P3**：新增 3 個 MCP Resources、6 個 Prompt 操作流程、字幕下載、`query_formats` 格式查詢工具

### v3.0.0（2026-05-19）— 專案整理與自動修復

- 新增 `start_mcp.sh` 啟動包裝腳本，每次啟動自動更新 yt-dlp 並清除快取
- 歸檔過時檔案，整理 `docs/` 目錄

### v2.1.0（2026-03-03）— 修復 YouTube JavaScript Runtime

- 加入 `--js-runtimes node:...` 和 `--remote-components ejs:github`

### v2.0.0（2025-12-31）— MCP Server 大幅升級

- MCP Server 增加至 13 個工具，新增 HLS / Podcast / 白名單功能

### v1.0.0（2025-12-10）— 初始版本

- 基礎 YouTube 下載與 MP3 轉換，Claude Desktop MCP 整合

---

## 功能特色

- **批量下載**：支援 YouTube 單影片、Playlist、頻道 URL 同時下載多個
- **下載進度**：Agent 可即時收到每個 URL 的下載進度通知
- **歷史紀錄**：自動跳過已下載的 URL（檔案存在才跳過）
- **字幕下載**：下載影片時同步取得 SRT 字幕
- **格式查詢**：下載前查詢可用畫質和字幕語言
- **HLS 串流下載**：下載 `.m3u8` 串流並自動轉為 MP4
- **Podcast 下載**：支援 RSS Feed 解析和直接音檔連結
- **格式轉換**：使用 FFmpeg 轉換為 MP3
- **圖片下載**：下載圖片並轉換為 JPG
- **網路白名單**：限制下載來源，防止誤操作
- **自動修復**：每次啟動自動更新 yt-dlp、補裝套件、清除快取
- **MCP Resources**：白名單狀態、yt-dlp 版本、下載歷史可直接查閱（不佔工具位）
- **MCP Prompts**：6 個操作流程卡片，引導 Agent 最佳操作路徑

---

## 系統需求

- **Python 3.10+**
- **yt-dlp**：YouTube 及各平台影音下載
- **FFmpeg**：音視頻轉檔
- **Node.js**：YouTube n-challenge 解密（建議安裝）

### macOS 安裝

```bash
brew install yt-dlp ffmpeg node
```

---

## 安裝步驟

```bash
# 1. 克隆專案
git clone <your-repo-url>
cd DownloadVideoPythonProject

# 2. 建立虛擬環境
python -m venv .venv
source .venv/bin/activate

# 3. 安裝 Python 套件
pip install -r requirements.txt

# 4. 測試啟動
python server.py
```

---

## 使用方法

### Claude Desktop 整合（推薦）

編輯 Claude Desktop 配置檔：

**macOS**：`~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "media-downloader": {
      "command": "/bin/bash",
      "args": [
        "/你的專案路徑/DownloadVideoPythonProject/start_mcp.sh"
      ]
    }
  }
}
```

> 使用 `start_mcp.sh` 啟動：每次啟動自動更新 yt-dlp、補裝缺少套件、清除快取，解決 yt-dlp 因 YouTube 反爬蟲更新而失效的問題。

設定完成後**重啟 Claude Desktop**，即可透過對話使用所有功能。

### CLI 工具

```bash
# 下載單一音檔
python download_cli.py "https://www.youtube.com/watch?v=xxxxx"

# 下載並指定輸出目錄
python download_cli.py "url" -o ./my_downloads

# 批量下載
python download_cli.py "url1" "url2" "url3"

# 查看完整說明
python download_cli.py --help
```

---

## 對話使用範例

以下為在 Claude Desktop 中與 Agent 對話的實際用法。

### 下載 YouTube 影片音檔

```
下載這個 YouTube 影片的音檔：
https://www.youtube.com/watch?v=xxxxx
```

Agent 會自動呼叫 `download_media`，下載過程中回報進度，完成後告知檔案位置。

### 下載整個 Playlist

```
下載這個 YouTube 播放清單的所有音檔，存到 ./music：
https://www.youtube.com/playlist?list=PLxxxxx
```

`download_media` 支援 playlist URL，yt-dlp 自動展開逐一下載。

### 下載影片並附帶繁中字幕

```
下載這部影片，要有繁體中文字幕：
https://www.youtube.com/watch?v=xxxxx
```

Agent 會先呼叫 `query_formats` 確認字幕語言，再以 `subtitles=True, sub_lang="zh-TW"` 下載，字幕 `.srt` 儲存在影片同目錄。

### 查詢可用格式

```
查詢這個影片有哪些可用畫質和字幕語言：
https://www.youtube.com/watch?v=xxxxx
```

呼叫 `query_formats`，回傳格式清單（解析度、副檔名）和可用字幕語言代碼。

### 下載 Podcast

```
下載這個 Podcast 的最新一集：
https://feeds.example.com/podcast.rss
```

```
下載第 3 集（index=2）：
https://feeds.example.com/podcast.rss  episode_index=2
```

### 下載 HLS 串流

```
幫我下載這個 m3u8 串流，輸出為 ./downloads/video.mp4：
https://example.com/stream/index.m3u8
```

### 管理白名單

```
列出目前的白名單規則
```

```
新增 *.example.com 到白名單
```

```
移除 example.com
```

### 查看下載歷史

```
顯示最近的下載紀錄
```

Agent 會自動讀取 `data://download-history` Resource，回傳最近 20 筆紀錄。

### 診斷 MCP 狀態

```
幫我診斷一下 MCP 是否正常，yt-dlp 版本是否最新
```

在輸入框輸入 `/` 選取 `check_mcp_health`，或直接在對話中說「用 check_mcp_health 診斷」，Agent 會依序讀取版本、白名單、下載紀錄並給出建議。

---

## MCP 工具一覽（8 個）

| 工具 | 說明 |
|------|------|
| `download_media` | yt-dlp 下載影音，支援 playlist、字幕、進度回報、歷史跳過 |
| `convert_to_mp3` | FFmpeg 轉換音視頻為 MP3 |
| `download_and_convert_image` | 下載圖片並轉換為 JPG |
| `podcast_downloader` | Podcast 下載（RSS Feed 或直接音檔連結） |
| `download_hls_tool` | HLS (.m3u8) 串流下載並轉為 MP4 |
| `direct_download_audio` | 純 HTTP 下載音檔（不依賴 yt-dlp） |
| `whitelist_manage` | 白名單查詢、新增、移除、啟用/停用 |
| `query_formats` | 查詢 URL 可用的影片格式與字幕語言 |

## MCP Resources（3 個，不佔工具位）

Resources 是唯讀資料，需透過 Claude Desktop UI **手動附加**到對話中才能讓 Agent 讀取。
Agent **不會**主動偵測並讀取 Resource，自然語言也無法直接觸發（yt-dlp 版本、下載歷史都沒有對應工具）。

| URI | 說明 |
|-----|------|
| `config://whitelist` | 白名單規則和啟用狀態 |
| `status://ytdlp-version` | yt-dlp 版本號和執行路徑 |
| `data://download-history` | 最近 20 筆下載紀錄 |

### 使用步驟（Claude Desktop）

1. 在對話輸入框左下角點擊 **`+`** 按鈕
2. 選擇 **「Add from MCP」** 或 **「MCP Resources」**
3. 找到 `media-downloader` 伺服器，選取要附加的 Resource
4. Resource 會顯示為對話中的附件，Agent 即可讀取其內容
5. 輸入問題，例如：

```
根據剛才附加的 Resource，yt-dlp 目前版本是多少？
```

```
根據附加的下載歷史，最近下載了哪些檔案？
```

> **注意**：Claude Desktop UI 的 Resource 入口位置隨版本不同可能有差異，若找不到 `+` 選單，可改用下方「直接指定 URI」的方式。

### 備用方式：直接在對話中指定 URI

若 UI 無法附加，可明確告訴 Agent 要讀取哪個 Resource：

```
請使用 MCP resource 讀取 status://ytdlp-version，告訴我 yt-dlp 版本
```

```
請用 MCP resource 讀取 data://download-history，列出最近的下載紀錄
```

---

## MCP Prompts（6 個）

Prompts 是預設的操作流程說明，有兩種使用方式：

### 方式一：透過 Claude Desktop UI（推薦）

**`+` 按鈕：**
1. 點擊對話輸入框左下角的 **`+`** 按鈕
2. 選擇 **「MCP Prompts」** 或對應的 `media-downloader` 項目
3. 點選 Prompt 名稱後自動帶入流程說明

**`/` 斜線指令：**
1. 在對話輸入框直接輸入 **`/`**
2. 從彈出清單找到 Prompt 名稱並點選

> 首次設定或修改 Prompt 後需**重啟 Claude Desktop** 才會出現在清單中。

### 方式二：在對話中直接呼叫

```
使用 batch_download_youtube 流程，下載這幾個 URL：
https://www.youtube.com/watch?v=aaa
```

```
用 check_mcp_health 診斷一下目前 MCP 狀態
```

Agent 先取得 Prompt 的步驟說明，再依序呼叫對應工具。

| Prompt | 適用情境 |
|--------|---------|
| `batch_download_youtube` | YouTube 批量下載音檔的完整流程 |
| `download_with_subtitles` | 下載影片同時取得字幕 |
| `download_podcast_series` | Podcast RSS 整季下載 |
| `download_hls_stream` | HLS 串流下載 |
| `manage_whitelist` | 白名單完整設定流程（含常用規則建議） |
| `check_mcp_health` | 診斷 MCP 狀態（版本 / 白名單 / 歷史紀錄） |

---

## 專案結構

```
DownloadVideoPythonProject/
├── server.py                    # MCP 伺服器主程式（8 Tools + 3 Resources + 6 Prompts）
├── start_mcp.sh                 # 啟動包裝腳本（自動更新 yt-dlp）
├── download_cli.py              # CLI 下載工具
├── requirements.txt             # Python 套件依賴
├── whitelist.json               # 白名單設定檔
├── claude_desktop_config.example.json  # Claude Desktop 設定範例
├── tools/
│   ├── podcast_downloader.py    # Podcast 下載
│   └── hls_downloader/          # HLS 串流下載模組
├── utils/
│   ├── audio_downloader.py      # 音檔直接下載（SSL fallback）
│   ├── download_history.py      # 下載歷史紀錄管理
│   ├── path_resolver.py         # yt-dlp / Node.js 路徑動態偵測
│   ├── response.py              # 統一回傳結構（success_response / error_response）
│   ├── whitelist_validator.py   # 白名單驗證
│   ├── rss_parser.py            # RSS Feed 解析
│   └── sanitizer.py             # 檔名清洗
├── docs/
│   ├── shared/                  # 需求文件（P0–P3 全部完成）
│   ├── guides/                  # 使用指南（白名單、HLS）
│   ├── spec/                    # 功能規格書
│   ├── issues/                  # 問題紀錄
│   └── archive/                 # 歸檔（過時文件與腳本）
├── downloads/                   # 下載檔案目錄
└── images/                      # 圖片儲存目錄
```

---

## 常見問題

### yt-dlp 下載失敗（YTDLP_FAILED）

重啟 Claude Desktop，`start_mcp.sh` 會自動執行 `pip install --upgrade yt-dlp` 和 `yt-dlp --rm-cache-dir`。

手動更新：

```bash
source .venv/bin/activate
pip install --upgrade yt-dlp
yt-dlp --rm-cache-dir
```

### Claude Desktop 無法連接 MCP Server

1. 確認 `claude_desktop_config.json` 中的路徑正確（絕對路徑）
2. 按 ⌘Q 完全退出後重開 Claude Desktop
3. 查看日誌：

```bash
tail -f ~/Library/Logs/Claude/mcp-server-media-downloader.log
```

### 白名單驗證失敗（WHITELIST_DENIED）

在 Claude Desktop 輸入：

```
列出白名單規則，並把 youtube.com 和 *.googlevideo.com 加入
```

詳細說明：[白名單指南](docs/guides/WHITELIST_GUIDE.md)

### HLS 下載相關問題

參閱：[HLS 設定指南](docs/guides/HLS_SETUP_GUIDE.md)

### 重複下載同一個 URL

`download_media` 會自動查詢歷史紀錄，已下載且檔案存在時回傳 `status: skipped`，不重複下載。若需強制重新下載，請先刪除 `download_history.json`。

---

## 安全注意事項

- 僅下載有版權或授權的內容
- 建議啟用白名單功能，限制下載來源
- `download_history.json` 已排除於 git 追蹤之外

---

## 授權

MIT License
