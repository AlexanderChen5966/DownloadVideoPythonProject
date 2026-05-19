# 多媒體下載與轉檔 MCP Server

> **版本：v3.0.0** | 更新日期：2026-05-19

一個由 Claude AI Agent 透過 MCP（Model Context Protocol）控制的自動化媒體處理系統。

---

## 版本紀錄

### v3.0.0（2026-05-19）— 專案整理與自動修復

- 新增 `start_mcp.sh` 啟動包裝腳本，每次啟動自動更新 yt-dlp 並清除快取
- 更新 Claude Desktop 設定，改用包裝腳本啟動 MCP
- 歸檔過時檔案（`analyze_json.py`、`batch_download.py`、`temp_data.json`）
- 整理 `docs/` 目錄，分類為 guides、spec、issues、archive
- 移除過時的 Skills 混合架構描述（實際未成功運作）
- 將 `spec/` 搬入 `docs/spec/` 統一管理
- `temp_data.json` 加入 `.gitignore`

### v2.1.0（2026-03-03）— 修復 YouTube JavaScript Runtime

- 在 yt-dlp 指令加入 `--js-runtimes node:/opt/homebrew/bin/node`
- 加入 `--remote-components ejs:github` 允許下載官方 JS challenge 解密腳本

### v2.0.0（2025-12-31）— MCP Server 大幅升級

- MCP Server 增加至 13 個工具
- 新增 HLS 串流下載、Podcast RSS 下載、音檔直接下載
- 新增網路白名單安全機制
- 同時支援 Claude Desktop 和 Claude Code

### v1.0.0（2025-12-10）— 初始版本

- 基礎 YouTube 下載與 MP3 轉換
- 檔案管理與圖片下載轉換
- Claude Desktop MCP 整合

---

## 功能特色

- **批量下載**：支援 YouTube、Podcast 等多個網址同時下載
- **HLS 串流下載**：下載 HLS (.m3u8) 串流視頻並自動轉換為 MP4
- **格式轉換**：自動將影片/音檔轉換為 MP3 格式
- **Podcast 下載**：支援 RSS Feed 解析和直接 MP3 連結
- **音檔直接下載**：純 HTTP 下載，不依賴 yt-dlp
- **檔案管理**：建立目錄、列出檔案、開啟資料夾
- **網路白名單**：限制下載來源，提高安全性
- **自動修復**：啟動時自動更新 yt-dlp 和套件，清除過期快取
- **AI 整合**：完全由 Claude AI Agent 控制操作

## 系統需求

- **Python 3.10+**
- **yt-dlp**：下載 YouTube 影片
- **FFmpeg**：音視頻轉檔
- **Node.js**：YouTube n-challenge 解密

### macOS 安裝

```bash
brew install yt-dlp ffmpeg node
```

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

# 4. 測試
python server.py
```

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

使用 `start_mcp.sh` 啟動的好處：每次啟動自動更新 yt-dlp、補裝缺少套件、清除快取。

設定完成後重啟 Claude Desktop，即可透過對話使用所有功能。

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

## MCP 工具一覽

| 工具 | 說明 |
|------|------|
| `download_media` | 使用 yt-dlp 下載 YouTube 影片/音檔，支援批量 |
| `convert_to_mp3` | 使用 FFmpeg 將音視頻轉換為 MP3 |
| `download_and_convert_image` | 下載圖片並轉換為 JPG |
| `podcast_downloader` | 下載 Podcast（RSS Feed 或直接連結） |
| `download_hls_tool` | 下載 HLS (.m3u8) 串流並轉為 MP4 |
| `direct_download_audio` | 純 HTTP 下載音檔（不依賴 yt-dlp） |
| `ensure_directory` | 確保目錄存在 |
| `list_files` | 列出目錄中的檔案 |
| `open_file` | 使用系統預設應用程式開啟檔案 |
| `whitelist_add_rule` | 新增白名單規則 |
| `whitelist_remove_rule` | 移除白名單規則 |
| `whitelist_list_rules` | 列出所有白名單規則 |
| `whitelist_set_enabled` | 啟用/停用白名單 |

## 專案結構

```
DownloadVideoPythonProject/
├── server.py                    # MCP 伺服器主程式
├── start_mcp.sh                 # 啟動包裝腳本（自動更新套件）
├── download_cli.py              # CLI 下載工具
├── requirements.txt             # Python 套件依賴
├── whitelist.json               # 白名單設定檔
├── claude_desktop_config.example.json  # Claude Desktop 設定範例
├── tools/                       # MCP 工具實作
│   ├── podcast_downloader.py    #   Podcast 下載
│   └── hls_downloader/          #   HLS 串流下載模組
├── utils/                       # 共用工具
│   ├── audio_downloader.py      #   音檔直接下載
│   ├── whitelist_validator.py   #   白名單驗證
│   ├── rss_parser.py            #   RSS Feed 解析
│   └── sanitizer.py             #   檔名清洗
├── docs/                        # 文件
│   ├── guides/                  #   使用指南
│   ├── spec/                    #   功能規格書
│   ├── issues/                  #   問題紀錄
│   └── archive/                 #   歸檔（過時文件與腳本）
├── downloads/                   # 下載檔案目錄
└── images/                      # 圖片儲存目錄
```

## 常見問題

### yt-dlp 下載失敗（JavaScript runtime 錯誤）

```bash
# 更新 yt-dlp
source .venv/bin/activate
pip install --upgrade yt-dlp
yt-dlp --rm-cache-dir
```

如果使用 `start_mcp.sh` 啟動，每次開機會自動執行上述更新。

### Claude Desktop 無法連接 MCP Server

1. 確認 `claude_desktop_config.json` 中的路徑正確
2. 按 ⌘Q 完全退出後重開 Claude Desktop
3. 檢查日誌：`tail -f ~/Library/Logs/Claude/mcp-server-media-downloader.log`

### 白名單驗證失敗

在 Claude Desktop 對話中輸入「列出所有白名單規則」，確認目標網域已加入。

詳細說明：[白名單指南](docs/guides/WHITELIST_GUIDE.md) | [HLS 設定指南](docs/guides/HLS_SETUP_GUIDE.md)

## 安全注意事項

- 僅下載有版權或授權的內容
- 建議啟用白名單功能，限制下載來源
- 定期檢查和更新白名單規則

## 授權

MIT License
