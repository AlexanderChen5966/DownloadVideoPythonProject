# 📺 多媒體下載與轉檔 MCP Server

一個由 Claude AI Agent 透過 MCP（Model Context Protocol）控制的自動化媒體處理系統。

## 🔔 最近更新

### 2025-12-10：MCP Server 路徑問題修復

**修復的問題**：
- ✅ 修復 MCP Server 找不到 yt-dlp 執行檔的問題
- ✅ 改用虛擬環境中的完整路徑（`server.py:400`）
- ✅ 新增完整的 Claude Desktop 整合教學
- ✅ 新增 9 個常見問題排解指南
- ✅ 新增白名單設定說明

**影響範圍**：
- 使用 Claude Desktop MCP 整合的用戶
- 需要重新啟動 Claude Desktop 以套用修復

**升級步驟**：
1. `git pull` 獲取最新版本
2. 確認 `server.py` 中的 `yt_dlp_path` 路徑正確
3. 重啟 Claude Desktop（⌘Q 後重開）

詳細說明請參考 [常見問題排解](#🐛-常見問題排解) 章節。

---

## ✨ 功能特色

- 🎬 **批量下載**：支援 YouTube、Podcast 等多個網址同時下載
- 📡 **HLS 串流下載**：下載 HLS (.m3u8) 串流視頻並自動轉換為 MP4
- 🎵 **格式轉換**：自動將影片/音檔轉換為 MP3 格式
- 📁 **檔案管理**：建立目錄、列出檔案
- 🚀 **快速開啟**：使用系統預設應用程式開啟檔案或資料夾
- 🔒 **網路白名單**：限制下載來源,提高安全性
- 🤖 **AI 整合**：完全由 Claude AI Agent 控制操作

## 📋 系統需求

### 必要工具

1. **Python 3.10+**
2. **yt-dlp**：下載 YouTube 影片
3. **FFmpeg**：音視頻轉檔

### 安裝系統工具

#### macOS
```bash
# 使用 Homebrew 安裝
brew install yt-dlp ffmpeg
```

#### Ubuntu/Debian
```bash
sudo apt update
sudo apt install yt-dlp ffmpeg
```

#### Windows
```powershell
# 使用 Chocolatey 安裝
choco install yt-dlp ffmpeg
```

## 🔧 安裝步驟

### 1. 克隆專案
```bash
git clone <your-repo-url>
cd DownloadVideoPythonProject
```

### 2. 建立虛擬環境
```bash
python -m venv .venv

# macOS/Linux
source .venv/bin/activate

# Windows
.venv\Scripts\activate
```

### 3. 安裝 Python 套件
```bash
pip install -r requirements.txt
```

### 4. 測試安裝
```bash
# 測試 MCP 伺服器
python server.py

# 測試 yt-dlp
yt-dlp --version

# 測試 FFmpeg
ffmpeg -version
```

## 🚀 使用方法

### 方法一：CLI 工具（獨立使用）

專案提供了獨立的 CLI 工具，可以直接在終端機中使用，無需啟動 MCP 伺服器。

#### 基本使用

```bash
# 下載單一音檔
python download_cli.py "https://example.com/audio.mp3"

# 下載並指定輸出目錄
python download_cli.py "https://example.com/audio.mp3" -o ./my_downloads

# 下載並自訂檔名
python download_cli.py "https://example.com/audio.mp3" -n "my_song"

# 批量下載多個音檔
python download_cli.py "url1" "url2" "url3" -o ./downloads

# 下載 YouTube 影片（自動偵測）
python download_cli.py "https://www.youtube.com/watch?v=xxxxx"

# 強制使用 yt-dlp
python download_cli.py "https://example.com/video" --youtube

# 跳過白名單驗證（不建議）
python download_cli.py "https://example.com/audio.mp3" --no-whitelist
```

#### CLI 參數說明

- `urls`: 要下載的 URL（可指定多個）
- `-o, --output`: 輸出目錄（預設：./downloads）
- `-n, --name`: 自訂檔名（不含副檔名，僅適用於單一 URL）
- `--no-whitelist`: 跳過白名單驗證
- `--youtube`: 強制使用 yt-dlp 下載

#### 查看完整說明

```bash
python download_cli.py --help
```

### 方法二：Claude Desktop 整合（推薦）

透過 MCP (Model Context Protocol) 將此工具整合到 Claude Desktop，讓 AI 自動幫你下載和處理媒體檔案。

#### 步驟 1：編輯 Claude Desktop 配置檔

**macOS**:
```bash
code ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

**Windows**:
```bash
code %APPDATA%\Claude\claude_desktop_config.json
```

#### 步驟 2：加入 MCP Server 配置

**⚠️ 重要：使用虛擬環境中的 Python**

```json
{
  "mcpServers": {
    "media-downloader": {
      "command": "/Users/你的用戶名/PycharmProjects/DownloadVideoPythonProject/.venv/bin/python",
      "args": [
        "/Users/你的用戶名/PycharmProjects/DownloadVideoPythonProject/server.py"
      ]
    }
  }
}
```

**記得替換路徑中的「你的用戶名」！**

**Windows 範例**:
```json
{
  "mcpServers": {
    "media-downloader": {
      "command": "C:\\Users\\你的用戶名\\DownloadVideoPythonProject\\.venv\\Scripts\\python.exe",
      "args": [
        "C:\\Users\\你的用戶名\\DownloadVideoPythonProject\\server.py"
      ]
    }
  }
}
```

#### 步驟 3：設定白名單（首次使用）

重新啟動 Claude Desktop 後，在對話中輸入：

```
列出所有白名單規則
```

如果 YouTube 不在白名單中，加入它：

```
將這些網域加入白名單：
- youtube.com
- *.youtube.com
- youtu.be
```

或者停用白名單（不建議）：

```
停用白名單功能
```

#### 步驟 4：開始使用

與 Claude 對話即可使用所有功能：

**下載 YouTube 音檔**：
```
下載這個 YouTube 影片的音檔到 ~/Downloads：
https://www.youtube.com/watch?v=BoZ0Zwab6Oc
```

**批量下載**：
```
下載這些影片：
- https://www.youtube.com/watch?v=xxxxx
- https://www.youtube.com/watch?v=yyyyy
```

**查看下載結果**：
```
列出 ~/Downloads 中的所有 mp3 檔案
```

**開啟下載資料夾**：
```
開啟 ~/Downloads 資料夾
```

### 方法二：直接運行伺服器

```bash
python server.py
```

## 🛠️ 可用工具

### 1. download_media
下載 YouTube 影片或音檔

**參數：**
- `urls` (array): 要下載的 URL 列表
- `output_dir` (string): 輸出目錄，預設 `./downloads`
- `format` (string): 下載格式 - `audio`（僅音檔）、`video`（影片）、`best`（最佳品質）

**範例：**
```json
{
  "urls": ["https://www.youtube.com/watch?v=xxxxx"],
  "output_dir": "./downloads",
  "format": "audio"
}
```

### 2. convert_to_mp3
將音視頻檔案轉換為 MP3

**參數：**
- `input_file` (string): 輸入檔案路徑
- `output_file` (string, 可選): 輸出檔案路徑
- `quality` (integer, 0-9): 音質等級，0 為最高品質

**範例：**
```json
{
  "input_file": "./downloads/video.mp4",
  "output_file": "./downloads/audio.mp3",
  "quality": 2
}
```

### 3. ensure_directory
確保目錄存在，不存在則建立

**參數：**
- `path` (string): 目錄路徑

### 4. list_files
列出目錄中的檔案

**參數：**
- `path` (string): 目錄路徑
- `filter` (string, 可選): 副檔名過濾器（如 `.mp3`）

### 5. open_file
使用系統預設應用程式開啟檔案或資料夾

**參數：**
- `path` (string): 檔案或資料夾路徑

### 6. download_and_convert_image
下載圖片並轉換為 JPG 格式

**參數：**
- `url` (string): 圖片的 HTTP/HTTPS 網址
- `filename` (string, 可選): 自訂輸出檔名（不含副檔名）

### 7. podcast_downloader
下載 Podcast 音檔（支援 RSS Feed 或 MP3 直接連結）

**參數：**
- `url` (string): Podcast RSS Feed URL 或 MP3 直接連結
- `target_dir` (string, 可選): 下載後的存放資料夾路徑，預設 `./downloads`
- `episode_index` (number, 可選): 若來源為 RSS，指定要下載第幾集（0 = 最新），預設 `0`

**範例：**
```json
// 下載 RSS Feed 最新一集
{
  "url": "https://feeds.example.com/podcast.xml",
  "target_dir": "./downloads",
  "episode_index": 0
}

// 下載直接 MP3 連結
{
  "url": "https://example.com/episode.mp3",
  "target_dir": "./downloads"
}
```

**支援的來源：**
- ✅ RSS Feed（自動解析 Podcast RSS 並提取音檔）
- ✅ 直接 MP3 URL
- ✅ 其他音檔格式（M4A, WAV, OGG, FLAC 等）
- ❌ Spotify、Apple Podcast 網頁連結（僅支援 RSS Feed）

### 8. download_hls
下載 HLS (.m3u8) 串流視頻並轉換為 MP4 格式

**參數：**
- `m3u8_url` (string): HLS m3u8 playlist URL
- `output_path` (string): 輸出 MP4 檔案路徑
- `threads` (number, 可選): 並行下載線程數，預設 8，範圍 1-32
- `select_highest_quality` (boolean, 可選): 是否自動選擇最高畫質，預設 true

**範例：**
```json
// 基本使用
{
  "m3u8_url": "https://example.com/video.m3u8",
  "output_path": "./downloads/video.mp4"
}

// 進階使用（高速下載）
{
  "m3u8_url": "https://cdn.example.com/master.m3u8",
  "output_path": "./downloads/high_quality.mp4",
  "threads": 32,
  "select_highest_quality": true
}
```

**功能特點：**
- ✅ 支援 master playlist（自動選擇最高畫質）
- ✅ 並行下載 TS segments（可設定線程數）
- ✅ 自動重試機制（預設 3 次）
- ✅ 使用 FFmpeg concat demuxer 轉換
- ✅ 自動提取視頻元數據
- ✅ 自動清理暫存檔案
- ❌ 不支援加密的 HLS 流

### 9. whitelist_add_rule
新增規則到網路白名單

**參數：**
- `rule` (string): 白名單規則,支援完整網域、萬用字元、正則表達式

**範例：**
```json
// 新增完整網域
{"rule": "example.com"}

// 新增萬用字元規則
{"rule": "*.example.com"}

// 新增正則表達式
{"rule": "^https?://.*\\.example\\.com/.*"}
```

### 10. whitelist_remove_rule
從網路白名單移除規則

**參數：**
- `rule` (string): 要移除的規則

### 11. whitelist_list_rules
列出所有白名單規則和狀態

**回應範例：**
```json
{
  "success": true,
  "enabled": true,
  "total_rules": 6,
  "rules": ["youtube.com", "*.youtube.com", "youtu.be"]
}
```

### 12. whitelist_set_enabled
啟用或停用網路白名單功能

**參數：**
- `enabled` (boolean): true 啟用，false 停用

### 13. direct_download_audio
直接下載音檔 URL（MP3、M4A、WAV 等）

使用純 HTTP 下載，不依賴 yt-dlp。適用於直接音檔連結，不適用於 YouTube 等需要解析的平台。

**參數：**
- `url` (string): 音檔的直接 URL（必須是可直接下載的音檔連結）
- `output_dir` (string, 可選): 下載檔案的輸出目錄路徑，預設 `./downloads`
- `filename` (string, 可選): 自訂檔名（不含副檔名）

**範例：**
```json
// 基本使用
{
  "url": "https://example.com/audio.mp3",
  "output_dir": "./downloads"
}

// 自訂檔名
{
  "url": "https://www.top945.com.tw/Upload/ReadMp3/527/audio.mp3",
  "output_dir": "./downloads",
  "filename": "my_custom_name"
}
```

**功能特點：**
- ✅ 支援多種音檔格式（MP3、M4A、WAV、OGG、FLAC、AAC 等）
- ✅ 自動偵測副檔名（從 Content-Type 或 URL）
- ✅ 串流下載（chunk_size=8192）
- ✅ 白名單驗證
- ✅ Content-Type 檢查
- ✅ 詳細的錯誤處理和分類
- ✅ 自動清洗檔名（移除不合法字元）
- ❌ 不支援需要解析的平台（如 YouTube、Spotify）

**錯誤類型：**
- `whitelist_failed`: 白名單驗證失敗
- `head_request_failed`: HEAD 請求失敗
- `http_error`: HTTP 錯誤（附帶狀態碼）
- `timeout`: 下載逾時
- `invalid_content_type`: Content-Type 不是音檔
- `empty_file`: 下載的檔案為空
- `file_write_failed`: 寫入檔案失敗
- `unexpected_error`: 未預期的錯誤

---

**白名單功能詳細說明請參考**: [WHITELIST_GUIDE.md](docs/WHITELIST_GUIDE.md)

## 📝 使用範例

### 與 Claude 對話範例

**下載並轉換：**
```
幫我下載這個影片並轉成 MP3：
https://www.youtube.com/watch?v=dQw4w9WgXcQ
```

**批量下載：**
```
幫我下載這些 Podcast：
1. https://...
2. https://...
3. https://...
```

**下載 Podcast RSS Feed：**
```
幫我下載這個 Podcast 的最新一集：
https://feeds.megaphone.fm/example-podcast
```

**下載 Podcast 特定集數：**
```
下載這個 RSS Feed 的第 3 集：
https://feeds.example.com/podcast.xml
```

**檢視下載的檔案：**
```
列出 downloads 資料夾中的所有 MP3 檔案
```

**開啟資料夾：**
```
開啟 downloads 資料夾
```

**下載 HLS 串流視頻：**
```
幫我下載這個 m3u8 串流視頻：
https://example.com/video.m3u8
儲存為 ./downloads/stream.mp4
```

**快速下載大型 HLS 視頻：**
```
下載這個視頻，使用 32 個線程加速：
https://cdn.example.com/master.m3u8
```

**管理白名單：**
```
列出目前的白名單規則
```

```
新增 twitch.tv 到白名單
```

```
從白名單移除 twitch.tv
```

```
啟用白名單功能
```

## 🐛 常見問題排解

### 1. MCP Server 找不到 yt-dlp

**症狀**：
```
ERROR: [Errno 2] No such file or directory: 'yt-dlp'
```

**原因**：`server.py` 使用相對命令 `yt-dlp` 而非完整路徑，導致 MCP Server 環境找不到執行檔。

**解決方案**：

已在 `server.py:400` 修復，使用虛擬環境中的完整路徑：

```python
# 修復前
cmd = ["yt-dlp", "-o", f"{output_dir}/%(title)s.%(ext)s"]

# 修復後
yt_dlp_path = "/Users/你的用戶名/PycharmProjects/DownloadVideoPythonProject/.venv/bin/yt-dlp"
cmd = [yt_dlp_path, "-o", f"{output_dir}/%(title)s.%(ext)s"]
```

如果你的專案路徑不同，請修改 `server.py` 中的 `yt_dlp_path`。

**確認 yt-dlp 路徑**：
```bash
# macOS/Linux
which yt-dlp
ls -la .venv/bin/yt-dlp

# Windows
where yt-dlp
dir .venv\Scripts\yt-dlp.exe
```

---

### 2. Claude Desktop 無法連接 MCP Server

**症狀**：
- Claude Desktop 中看不到 MCP 工具
- 日誌顯示連接錯誤

**解決方案**：

1. **確認配置檔路徑正確**：
   ```bash
   # macOS
   cat ~/Library/Application\ Support/Claude/claude_desktop_config.json

   # 確認路徑使用虛擬環境中的 Python
   ```

2. **檢查 MCP Server 日誌**：
   ```bash
   # macOS
   tail -f ~/Library/Logs/Claude/mcp-server-media-downloader.log
   ```

3. **完全重啟 Claude Desktop**：
   - 按 ⌘Q 完全退出（不要只是關閉視窗）
   - 重新開啟 Claude Desktop

4. **驗證 Python 虛擬環境**：
   ```bash
   # 測試 server.py 是否能正常啟動
   /Users/你的用戶名/PycharmProjects/DownloadVideoPythonProject/.venv/bin/python server.py
   ```

---

### 3. YouTube 下載被阻擋（403 Forbidden）

**症狀**：
```
WARNING: Unable to connect to proxy
ERROR: 403 Forbidden
```

**可能原因**：
1. **白名單未設定**：YouTube 不在白名單中
2. **暫時性網路問題**：YouTube 伺服器臨時限制
3. **代理設定衝突**（已排除）

**解決方案**：

**方案 A：設定白名單（推薦）**

在 Claude Desktop 中：
```
將 YouTube 加入白名單：
- youtube.com
- *.youtube.com
- youtu.be
```

**方案 B：停用白名單**

在 Claude Desktop 中：
```
停用白名單功能
```

**方案 C：檢查網路連線**

在終端機測試：
```bash
# 測試是否能連接 YouTube
curl -I https://www.youtube.com/

# 直接使用 yt-dlp 測試（繞過 MCP）
cd ~/Downloads
/你的專案路徑/.venv/bin/yt-dlp -x --audio-format mp3 "YouTube URL"
```

---

### 4. 白名單驗證失敗

**症狀**：
```json
{
  "success": false,
  "error": "白名單驗證失敗",
  "message": "網域 'youtube.com' 不在白名單中"
}
```

**解決方案**：

1. **查看當前白名單**：
   ```
   列出所有白名單規則
   ```

2. **加入缺少的網域**：
   ```
   將 youtube.com 加入白名單
   ```

3. **或直接停用白名單**（不建議）：
   ```
   停用白名單功能
   ```

---

### 5. yt-dlp 版本過舊

**症狀**：
```
WARNING: No supported JavaScript runtime could be found
```

**解決方案**：
```bash
# 在虛擬環境中更新 yt-dlp
source .venv/bin/activate  # macOS/Linux
# 或 .venv\Scripts\activate  # Windows

pip install -U yt-dlp
```

---

### 6. FFmpeg 找不到

**症狀**：
```
ERROR: ffmpeg not found
```

**解決方案**：
```bash
# 確認 FFmpeg 已正確安裝
which ffmpeg  # macOS/Linux
where ffmpeg  # Windows

# macOS 安裝
brew install ffmpeg

# Ubuntu/Debian 安裝
sudo apt install ffmpeg

# Windows 安裝
choco install ffmpeg
```

---

### 7. 權限錯誤

**症狀**：
```
PermissionError: [Errno 13] Permission denied: '/path/to/downloads'
```

**解決方案**：
```bash
# 確保下載目錄有寫入權限
chmod 755 ./downloads

# 或使用 ~/Downloads（用戶主目錄，通常有權限）
```

---

### 8. 下載檔案為空或損壞

**症狀**：
- 下載完成但檔案大小為 0
- MP3 檔案無法播放

**可能原因**：
1. 網路連線中斷
2. 磁碟空間不足
3. 來源 URL 無效

**解決方案**：
```bash
# 檢查磁碟空間
df -h  # macOS/Linux

# 重新下載
# 刪除損壞的檔案後重試

# 使用 --verbose 查看詳細資訊（CLI 模式）
.venv/bin/yt-dlp --verbose "URL"
```

---

### 9. 如何查看詳細日誌

**MCP Server 日誌**（macOS）：
```bash
# 即時查看日誌
tail -f ~/Library/Logs/Claude/mcp-server-media-downloader.log

# 查看最近 50 行
tail -50 ~/Library/Logs/Claude/mcp-server-media-downloader.log

# 搜尋錯誤
grep -i error ~/Library/Logs/Claude/mcp-server-media-downloader.log
```

**測試 yt-dlp 詳細輸出**：
```bash
cd ~/Downloads
.venv/bin/yt-dlp --verbose --print-traffic "YouTube URL"
```

## 📂 專案結構

```
DownloadVideoPythonProject/
├── server.py                        # MCP 伺服器主程式
├── download_cli.py                  # CLI 下載工具（獨立使用）
├── requirements.txt                 # Python 套件相依
├── README.md                        # 說明文件
├── CHANGELOG_HLS.md                 # HLS 功能更新日誌
├── WHITELIST_GUIDE.md               # 白名單功能指南
├── whitelist.json                   # 白名單設定檔
├── .gitignore                       # Git 忽略檔案
├── .claudeignore                    # Claude Code 忽略檔案
├── spec/                            # 規格文件目錄
│   ├── podcast_downloader_mcp_tool_spec.md
│   ├── youtube_video_downloader_spec.md
│   ├── image_downloader_spec.md
│   ├── hls_video_downloader_spec.md # HLS 下載器規格
│   └── hls_usage_examples.md        # HLS 使用範例
├── utils/                           # 工具模組
│   ├── __init__.py
│   ├── sanitizer.py                 # 檔名清洗工具
│   ├── rss_parser.py                # RSS Feed 解析器
│   ├── whitelist_validator.py       # 白名單驗證器
│   └── audio_downloader.py          # 音檔直接下載器
├── tools/                           # MCP 工具實作
│   ├── __init__.py
│   ├── podcast_downloader.py        # Podcast 下載工具
│   └── hls_downloader/              # HLS 視頻下載器
│       ├── __init__.py
│       ├── downloader.py            # 主下載器
│       ├── parser.py                # M3U8 解析器
│       ├── segment_downloader.py    # TS segment 下載器
│       ├── converter.py             # 視頻轉換器
│       ├── metadata.py              # 元數據提取器
│       └── README.md                # HLS 模組說明
├── .venv/                           # 虛擬環境
├── downloads/                       # 下載檔案目錄
└── images/                          # 圖片儲存目錄
```

## 🔒 安全注意事項

- 僅下載有版權或授權的內容
- 下載的檔案僅供個人使用
- 遵守 YouTube 服務條款
- 不要分享或散布受版權保護的內容
- **建議啟用白名單功能**,限制下載來源以提高安全性
- 定期檢查和更新白名單規則

## 📄 授權

MIT License

## 🤝 貢獻

歡迎提交 Issue 或 Pull Request！

## 📧 聯絡方式

如有問題請開 Issue 或聯絡專案維護者。
