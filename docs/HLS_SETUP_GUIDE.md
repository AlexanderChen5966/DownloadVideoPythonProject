# HLS 下載器安裝與設定指南

## 📋 前置準備

### 1. 系統需求
- Python 3.7 或更高版本
- FFmpeg（必須）
- FFprobe（通常隨 FFmpeg 一起安裝）

### 2. 檢查現有環境

```bash
# 檢查 Python 版本
python --version  # 應該是 3.7+

# 檢查 FFmpeg
ffmpeg -version

# 檢查 FFprobe
ffprobe -version
```

## 🔧 安裝步驟

### 步驟 1: 安裝 FFmpeg

#### macOS
```bash
# 使用 Homebrew
brew install ffmpeg
```

#### Ubuntu/Debian
```bash
sudo apt update
sudo apt install ffmpeg
```

#### Windows
1. 下載 FFmpeg: https://ffmpeg.org/download.html
2. 解壓縮到 `C:\ffmpeg`
3. 將 `C:\ffmpeg\bin` 加入系統環境變數 PATH

**驗證安裝:**
```bash
ffmpeg -version
ffprobe -version
```

### 步驟 2: 安裝 Python 依賴套件

```bash
# 啟動虛擬環境（如果還沒啟動）
source .venv/bin/activate  # macOS/Linux
.venv\Scripts\activate     # Windows

# 安裝依賴套件
pip install -r requirements.txt
```

### 步驟 3: 驗證安裝

```bash
# 驗證 m3u8 套件
python -c "import m3u8; print('m3u8 安裝成功')"

# 驗證 requests 套件
python -c "import requests; print('requests 安裝成功')"

# 驗證 MCP 套件
python -c "import mcp; print('MCP 安裝成功')"
```

## 🧪 測試 HLS 下載器

### 方法 1: 使用 Python 直接測試

創建測試腳本 `test_hls.py`:

```python
import asyncio
from tools.hls_downloader import download_hls

async def test():
    result = await download_hls(
        m3u8_url="https://example.com/sample.m3u8",  # 替換為實際 URL
        output_path="./downloads/test.mp4",
        threads=8
    )
    print(result)

if __name__ == "__main__":
    asyncio.run(test())
```

運行測試:
```bash
python test_hls.py
```

### 方法 2: 通過 MCP Server 測試

1. 啟動 MCP Server:
```bash
python server.py
```

2. 使用 Claude Desktop 發送請求:
```
幫我下載這個 m3u8 視頻：
https://example.com/sample.m3u8
儲存為 ./downloads/test.mp4
```

## 🔍 常見問題排除

### 問題 1: FFmpeg 未找到

**錯誤訊息:**
```
FileNotFoundError: [Errno 2] No such file or directory: 'ffmpeg'
```

**解決方法:**
1. 確認 FFmpeg 已安裝
2. 檢查 PATH 環境變數

```bash
# macOS/Linux
which ffmpeg

# Windows
where ffmpeg
```

如果找不到，重新安裝 FFmpeg 並確保加入 PATH。

---

### 問題 2: m3u8 模組導入失敗

**錯誤訊息:**
```
ModuleNotFoundError: No module named 'm3u8'
```

**解決方法:**
```bash
pip install m3u8>=3.5.0
```

---

### 問題 3: 虛擬環境問題

**症狀:** 安裝的套件無法導入

**解決方法:**
```bash
# 確認虛擬環境已啟動
which python  # macOS/Linux
where python  # Windows

# 輸出應該指向 .venv 目錄
# 例如: /path/to/project/.venv/bin/python

# 如果不是，重新啟動虛擬環境
source .venv/bin/activate  # macOS/Linux
.venv\Scripts\activate     # Windows
```

---

### 問題 4: 權限錯誤

**錯誤訊息:**
```
PermissionError: [Errno 13] Permission denied
```

**解決方法:**
```bash
# 確保 downloads 目錄有寫入權限
chmod 755 ./downloads

# 或創建目錄
mkdir -p downloads
```

---

### 問題 5: 網路連接問題

**症狀:** 下載時超時或連接失敗

**解決方法:**
1. 檢查網路連接
2. 嘗試使用瀏覽器訪問 m3u8 URL
3. 增加超時時間（編輯 `segment_downloader.py`）

```python
downloader = SegmentDownloader(
    timeout=60  # 增加到 60 秒
)
```

---

### 問題 6: 記憶體不足

**症狀:** 下載大型視頻時程式崩潰

**解決方法:**
1. 減少並行線程數
```json
{
  "threads": 4  // 從 8 減少到 4
}
```

2. 確保有足夠的磁碟空間（至少是視頻大小的 2 倍）

---

## 📊 效能調整

### 根據網路速度調整線程數

| 網路速度 | 建議線程數 |
|---------|-----------|
| < 10 Mbps | 4-8 |
| 10-50 Mbps | 8-16 |
| 50-100 Mbps | 16-24 |
| > 100 Mbps | 24-32 |

### 根據 CPU 調整線程數

```python
import os

# 獲取 CPU 核心數
cpu_count = os.cpu_count()

# 建議線程數為 CPU 核心數的 2-4 倍
recommended_threads = cpu_count * 2
```

## 🔐 安全設定

### 1. 限制下載來源

編輯 `parser.py`，添加白名單檢查:

```python
ALLOWED_DOMAINS = [
    'example.com',
    'cdn.example.com'
]

def is_allowed_url(url):
    from urllib.parse import urlparse
    domain = urlparse(url).netloc
    return any(domain.endswith(allowed) for allowed in ALLOWED_DOMAINS)
```

### 2. 限制檔案大小

編輯 `segment_downloader.py`:

```python
MAX_SEGMENT_SIZE = 100 * 1024 * 1024  # 100 MB

def _download_segment(self, segment, output_dir):
    # 檢查檔案大小
    response = requests.head(url)
    content_length = int(response.headers.get('Content-Length', 0))

    if content_length > MAX_SEGMENT_SIZE:
        raise ValueError("Segment 太大")
```

## 📝 配置檔案範例

創建 `hls_config.json`:

```json
{
  "downloader": {
    "default_threads": 8,
    "max_threads": 32,
    "max_retries": 3,
    "timeout": 30,
    "retry_delay": 2
  },
  "converter": {
    "method": "concat_demuxer",
    "fallback": true
  },
  "cleanup": {
    "auto_cleanup": true,
    "keep_temp_files": false
  }
}
```

## 🚀 生產環境部署

### 1. 使用 systemd 服務（Linux）

創建 `/etc/systemd/system/hls-downloader.service`:

```ini
[Unit]
Description=HLS Downloader MCP Server
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/DownloadVideoPythonProject
ExecStart=/path/to/.venv/bin/python server.py
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

啟動服務:
```bash
sudo systemctl daemon-reload
sudo systemctl enable hls-downloader
sudo systemctl start hls-downloader
```

### 2. 使用 Docker（跨平台）

創建 `Dockerfile`:

```dockerfile
FROM python:3.11-slim

# 安裝 FFmpeg
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

# 設置工作目錄
WORKDIR /app

# 複製檔案
COPY ../requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY .. .

# 運行服務
CMD ["python", "server.py"]
```

建立和運行:
```bash
docker build -t hls-downloader .
docker run -v $(pwd)/downloads:/app/downloads hls-downloader
```

## 📚 進階設定

### 自訂進度顯示

編輯 `downloader.py`:

```python
def custom_progress_callback(completed, total):
    percentage = (completed / total) * 100
    bar_length = 50
    filled = int(bar_length * completed / total)
    bar = '█' * filled + '░' * (bar_length - filled)
    print(f'\r下載進度: [{bar}] {percentage:.1f}% ({completed}/{total})', end='')
```

### 啟用詳細日誌

```python
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('hls_downloader.log'),
        logging.StreamHandler()
    ]
)
```

## ✅ 驗證清單

安裝完成後，請確認以下項目:

- [ ] Python 3.7+ 已安裝
- [ ] FFmpeg 和 FFprobe 可用
- [ ] 虛擬環境已創建並啟動
- [ ] 所有 Python 依賴已安裝
- [ ] m3u8 模組可正常導入
- [ ] MCP Server 可以啟動
- [ ] 測試下載成功

## 🎉 完成！

恭喜！HLS 下載器已成功安裝並設定完成。

### 下一步
1. 閱讀 [使用範例](spec/hls_usage_examples.md)
2. 查看 [模組說明](tools/hls_downloader/README.md)
3. 開始使用 Claude Desktop 下載視頻

### 獲取幫助
- 查看 [常見問題](README.md#-常見問題)
- 閱讀 [更新日誌](CHANGELOG_HLS.md)
- 提交 Issue 到 GitHub

祝使用愉快！
