# HLS Video Downloader

HLS 視頻下載器 MCP 工具，用於下載 HLS (.m3u8) 串流視頻並轉換為 MP4 格式。

## 功能特性

- ✅ 支援 HTTP/HTTPS m3u8 playlist
- ✅ 自動解析 master playlist（多個解析度）
- ✅ 自動選擇最高畫質
- ✅ 並行下載 TS segments（可設定線程數）
- ✅ 支援重試和錯誤處理
- ✅ 使用 FFmpeg concat demuxer 轉換為 MP4
- ✅ 自動提取視頻元數據（時長、解析度、比特率）
- ✅ 自動清理暫存檔案

## 系統需求

### 必須安裝的外部工具
- **FFmpeg**: 用於視頻轉換
  - macOS: `brew install ffmpeg`
  - Ubuntu/Debian: `sudo apt install ffmpeg`
  - Windows: 下載並安裝 [FFmpeg](https://ffmpeg.org/download.html)

### Python 依賴套件
```bash
pip install m3u8>=3.5.0
pip install requests>=2.31.0
```

## 模組架構

```
tools/hls_downloader/
├── __init__.py              # 模組入口
├── downloader.py            # 主下載器（整合所有功能）
├── parser.py                # M3U8 解析器
├── segment_downloader.py    # TS segment 並行下載器
├── converter.py             # TS 合併和 MP4 轉換器
├── metadata.py              # 視頻元數據提取器
└── README.md                # 本文檔
```

## 使用方式

### 通過 MCP 呼叫

```json
{
  "tool": "download_hls",
  "m3u8_url": "https://example.com/playlist.m3u8",
  "output_path": "./downloads/video.mp4",
  "threads": 8,
  "select_highest_quality": true
}
```

### 參數說明

- `m3u8_url` (必填): HLS m3u8 playlist URL
- `output_path` (必填): 輸出 MP4 檔案路徑
- `threads` (選填): 並行下載線程數，預設 8，範圍 1-32
- `select_highest_quality` (選填): 是否自動選擇最高畫質，預設 true

### 回傳結果

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
  "conversion_method": "concat_demuxer",
  "is_master_playlist": true,
  "selected_variant": {
    "bandwidth": 5200000,
    "resolution": "1920x1080",
    "codecs": "avc1.640028,mp4a.40.2"
  }
}
```

## 工作流程

1. **解析 M3U8 Playlist**
   - 載入 m3u8 文件
   - 檢查是否為 master playlist
   - 若為 master playlist，自動選擇最高畫質

2. **下載 TS Segments**
   - 使用線程池並行下載所有 TS 段落
   - 支援自動重試（預設 3 次）
   - 超時設定（預設 30 秒）

3. **轉換為 MP4**
   - 優先使用 FFmpeg concat demuxer（快速、穩定）
   - 若失敗，回退到合併後重新編碼
   - 自動處理 AAC 位元流

4. **提取元數據**
   - 使用 FFprobe 提取視頻資訊
   - 包含時長、解析度、比特率、編碼器等

5. **清理暫存檔案**
   - 自動刪除下載的 TS 段落
   - 刪除暫存目錄

## 錯誤處理

### 常見錯誤和解決方法

1. **FFmpeg 未安裝**
   - 錯誤: `FFmpeg 執行失敗`
   - 解決: 安裝 FFmpeg

2. **下載失敗**
   - 錯誤: `部分 segments 下載失敗`
   - 解決: 檢查網路連接，增加重試次數

3. **轉換失敗**
   - 錯誤: `轉換為 MP4 失敗`
   - 解決: 檢查 TS 檔案完整性，嘗試重新下載

## 進階功能

### 自訂重試和超時設定

編輯 `segment_downloader.py`:

```python
downloader = SegmentDownloader(
    max_workers=16,      # 增加線程數
    max_retries=5,       # 增加重試次數
    timeout=60,          # 增加超時時間
    retry_delay=3        # 增加重試延遲
)
```

### 使用不同的轉換方法

```python
# 方法 1: Concat demuxer (推薦)
converter.convert_using_concat_demuxer(ts_files, output_mp4, temp_dir)

# 方法 2: Direct copy (快速但可能失敗)
converter.convert_to_mp4_direct_copy(merged_ts, output_mp4)

# 方法 3: Re-encode (慢但相容性高)
converter.convert_to_mp4_reencode(merged_ts, output_mp4)
```

## 效能優化建議

1. **調整線程數**: 根據網路速度和 CPU 核心數調整（建議 8-16）
2. **使用 SSD**: 加快 TS 檔案讀寫速度
3. **網路頻寬**: 確保足夠的下載頻寬
4. **避免重新編碼**: 使用 concat demuxer 可大幅減少轉換時間

## 已知限制

1. 僅支援標準 HLS 格式
2. 不支援加密的 HLS 流（需要解密金鑰）
3. 需要外部依賴 FFmpeg
4. 大型視頻可能需要較長處理時間

## 授權

本工具為內部項目的一部分，遵循項目主要授權協議。
