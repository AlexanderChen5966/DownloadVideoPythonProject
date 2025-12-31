# Media Processor Skills

媒體處理工具集，提供音訊、視訊、圖片的下載、轉換、壓縮等功能。

## 快速開始

### 安裝依賴

```bash
# 安裝 FFmpeg
brew install ffmpeg  # macOS
# apt install ffmpeg  # Ubuntu

# 安裝 Python 套件
pip install pillow requests
```

### 基本使用

```bash
# 轉換音訊
python scripts/convert_audio.py input.wav output.mp3

# 下載圖片
python scripts/download_image.py https://example.com/pic.png output.jpg

# 直接下載
python scripts/download_direct.py https://example.com/audio.mp3

# 批量轉換
python scripts/batch_convert.py \
    --input-dir ./audio_files \
    --output-dir ./converted \
    --format mp3

# 提取音訊
python scripts/extract_audio.py video.mp4 audio.mp3

# 壓縮媒體
python scripts/compress_media.py video.mp4 compressed.mp4 --target-size 50MB
```

## Scripts 列表

| Script | 功能 | 範例 |
|--------|------|------|
| `convert_audio.py` | 音訊格式轉換 | `python scripts/convert_audio.py input.wav output.mp3 2` |
| `download_image.py` | 下載並轉換圖片為 JPG | `python scripts/download_image.py <url> output.jpg` |
| `download_direct.py` | 直接下載音訊/視訊 URL | `python scripts/download_direct.py <url> ./downloads` |
| `batch_convert.py` | 批量轉換 | `python scripts/batch_convert.py --input-dir ./audio --output-dir ./converted --format mp3` |
| `extract_audio.py` | 從影片提取音訊 | `python scripts/extract_audio.py video.mp4 audio.mp3` |
| `compress_media.py` | 壓縮媒體檔案 | `python scripts/compress_media.py input.mp4 output.mp4 --target-size 50MB` |

## 詳細文檔

請參閱 [SKILL.md](./SKILL.md) 獲取完整的使用指南、範例和最佳實踐。

## 與 MCP Server 的關係

這些 Scripts 補充 media-downloader MCP Server 的功能：

- **MCP Tools**: 處理複雜任務 (YouTube 下載、HLS 串流、Podcast 訂閱)
- **Skills Scripts**: 處理簡單任務 (格式轉換、圖片下載、檔案壓縮)

## 版本

- v2.0 (2025-12-31): 從 MCP Server 重構而來
  - 6 個 Scripts 工具
  - 支援批量處理和並行操作
  - 完整的錯誤處理和進度顯示
