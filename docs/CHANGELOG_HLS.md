# HLS Downloader 更新日誌

## 2025-11-27 - 新增 HLS 視頻下載功能

### 新增功能

#### 1. HLS Downloader MCP Tool
新增完整的 HLS 視頻下載器，支援以下功能：

- **M3U8 解析** (`tools/hls_downloader/parser.py`)
  - 支援 HTTP/HTTPS m3u8 playlist
  - 自動識別 master playlist 和 media playlist
  - 自動選擇最高畫質變體
  - 支援相對路徑和絕對路徑 URL

- **並行下載** (`tools/hls_downloader/segment_downloader.py`)
  - 使用 ThreadPoolExecutor 並行下載 TS segments
  - 可設定並行線程數（1-32）
  - 自動重試機制（預設 3 次）
  - 超時保護（預設 30 秒）
  - 下載進度回調

- **視頻轉換** (`tools/hls_downloader/converter.py`)
  - FFmpeg concat demuxer 方法（推薦）
  - Direct copy 方法（快速）
  - Re-encode 方法（相容性高）
  - 自動處理 AAC 位元流
  - 錯誤時自動降級到備用方法

- **元數據提取** (`tools/hls_downloader/metadata.py`)
  - 使用 FFprobe 提取視頻資訊
  - 時長、解析度、比特率
  - 視頻編碼器、音頻編碼器
  - 格式化顯示

- **主下載器** (`tools/hls_downloader/downloader.py`)
  - 整合所有功能模組
  - 完整的錯誤處理
  - 自動清理暫存檔案
  - 詳細的結果回報

#### 2. MCP Server 整合

在 `server.py` 中新增：

```python
Tool(
    name="download_hls",
    description="下載 HLS (.m3u8) 串流視頻並轉換為 MP4 格式",
    inputSchema={...}
)
```

**輸入參數:**
- `m3u8_url`: M3U8 playlist URL (必填)
- `output_path`: 輸出 MP4 檔案路徑 (必填)
- `threads`: 並行線程數，預設 8 (選填)
- `select_highest_quality`: 是否選擇最高畫質，預設 true (選填)

**輸出結果:**
```json
{
  "success": true,
  "output_file": "/path/to/video.mp4",
  "duration": "12:34",
  "resolution": "1920x1080",
  "bitrate": "5.2 Mbps",
  "video_codec": "h264",
  "audio_codec": "aac",
  "file_size": 123456789,
  "total_segments": 150,
  "conversion_method": "concat_demuxer"
}
```

#### 3. 依賴更新

在 `requirements.txt` 中新增：
```
m3u8>=3.5.0
```

### 文件結構

```
tools/hls_downloader/
├── __init__.py              # 模組入口
├── downloader.py            # 主下載器（整合所有功能）
├── parser.py                # M3U8 解析器
├── segment_downloader.py    # TS segment 並行下載器
├── converter.py             # TS 合併和 MP4 轉換器
├── metadata.py              # 視頻元數據提取器
└── README.md                # 使用文檔

spec/
├── hls_video_downloader_spec.md  # 原始規格書
└── hls_usage_examples.md         # 使用範例
```

### 技術亮點

1. **模組化設計**
   - 功能完全解耦，各模組獨立運作
   - 便於維護和擴展
   - 符合單一職責原則

2. **錯誤處理完善**
   - 多層級錯誤捕獲
   - 自動重試機制
   - 降級備用方案

3. **效能優化**
   - 並行下載提升速度
   - FFmpeg concat demuxer 避免重新編碼
   - 串流寫入減少記憶體使用

4. **使用者體驗**
   - 詳細的錯誤訊息
   - 完整的元數據資訊
   - 自動清理暫存檔案

### 使用範例

#### 基本使用
```json
{
  "tool": "download_hls",
  "m3u8_url": "https://example.com/video.m3u8",
  "output_path": "./downloads/video.mp4"
}
```

#### 進階使用
```json
{
  "tool": "download_hls",
  "m3u8_url": "https://example.com/master.m3u8",
  "output_path": "./downloads/high_quality.mp4",
  "threads": 32,
  "select_highest_quality": true
}
```

### 系統需求

- Python 3.7+
- FFmpeg (必須安裝)
- FFprobe (通常隨 FFmpeg 一起安裝)

### 已知限制

1. 不支援加密的 HLS 流（AES-128）
2. 不支援 FairPlay DRM
3. 需要外部依賴 FFmpeg

### 未來改進計劃

1. 支援 HLS 加密流解密
2. 支援即時進度報告
3. 支援斷點續傳
4. 增加下載速度限制選項
5. 支援代理設定

### 相關 Issue

- 符合規格書要求: `spec/hls_video_downloader_spec.md`
- 完整的模組化拆分
- 詳細的錯誤處理
- 完善的文檔

### 貢獻者

- Claude Code AI Assistant

### 參考資料

- [HLS 規範](https://datatracker.ietf.org/doc/html/rfc8216)
- [FFmpeg 文檔](https://ffmpeg.org/documentation.html)
- [m3u8 Python Library](https://github.com/globocom/m3u8)
