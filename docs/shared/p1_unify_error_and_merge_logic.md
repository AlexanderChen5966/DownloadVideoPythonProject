# P1：統一錯誤回傳結構、合併重複邏輯、修復 SSL

> **狀態：⏳ 待實作**
> **優先級：P1（重要）**
> **建立日期：2026-05-19**
> **預估影響檔案：4 個**
> **前置依賴：P0 完成後再做**

---

## 需求描述

目前各工具的錯誤回傳格式不一致，Agent 難以統一處理重試邏輯。同時有兩組重複的下載邏輯（`podcast_downloader` 和 `audio_downloader`），以及全域關閉 SSL 驗證的安全風險。

## 目標

1. 所有工具回傳結構統一，含結構化 error code
2. 合併重複的音檔下載邏輯
3. SSL 驗證預設開啟，僅在特定情況 fallback

---

## 影響範圍分析

| 檔案 | 修改原因 |
|------|---------|
| `server.py` | 所有工具的回傳結構統一 |
| `utils/audio_downloader.py` | 修復 SSL verify=False（第 66、87 行），作為共用下載器 |
| `tools/podcast_downloader.py` | 移除重複的 `_download_audio_file`，改用 `audio_downloader` |
| `utils/response.py`（新增） | 統一回傳結構工具 |

---

## 實作任務

### 任務 1：建立統一回傳結構

**新增 `utils/response.py`**

```python
from typing import Any


def success_response(data: dict | None = None, **kwargs) -> dict:
    result = {"success": True}
    if data:
        result.update(data)
    result.update(kwargs)
    return result


def error_response(
    code: str,
    message: str,
    **kwargs
) -> dict:
    result = {
        "success": False,
        "error_code": code,
        "error": message,
    }
    result.update(kwargs)
    return result
```

**標準 error code 清單：**

| error_code | 說明 | Agent 行為建議 |
|-----------|------|---------------|
| `WHITELIST_DENIED` | 白名單驗證失敗 | 提示使用者加入白名單 |
| `YTDLP_NOT_FOUND` | 找不到 yt-dlp | 提示安裝 |
| `YTDLP_FAILED` | yt-dlp 執行失敗 | 可嘗試更新 yt-dlp 後重試 |
| `NODE_NOT_FOUND` | 找不到 Node.js（warning） | 提示安裝，部分影片可能無法下載 |
| `DOWNLOAD_FAILED` | HTTP 下載失敗 | 可重試 |
| `DOWNLOAD_TIMEOUT` | 下載逾時 | 可重試 |
| `FILE_NOT_FOUND` | 輸入檔案不存在 | 請使用者確認路徑 |
| `CONVERSION_FAILED` | FFmpeg 轉換失敗 | 檢查輸入格式 |
| `INVALID_CONTENT_TYPE` | Content-Type 非預期 | 不應重試 |
| `EMPTY_FILE` | 下載檔案為空 | 可重試 |
| `SSL_ERROR` | SSL 憑證錯誤 | 自動 fallback 後重試 |

### 任務 2：修復 SSL 驗證

**修改 `utils/audio_downloader.py`**

**修改前（全域關閉 SSL）：**
```python
warnings.filterwarnings('ignore', message='Unverified HTTPS request')
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
# ...
head_response = requests.head(url, timeout=10, allow_redirects=True, verify=False)
response = requests.get(url, timeout=60, stream=True, verify=False)
```

**修改後（先嘗試 verify=True，失敗再 fallback）：**
```python
def _safe_request(method, url, **kwargs):
    """先嘗試 SSL 驗證，失敗後 fallback 為不驗證"""
    try:
        return requests.request(method, url, verify=True, **kwargs)
    except requests.exceptions.SSLError:
        return requests.request(method, url, verify=False, **kwargs)
```

移除全域的 `warnings.filterwarnings` 和 `urllib3.disable_warnings`。

### 任務 3：合併重複下載邏輯

**問題：** `tools/podcast_downloader.py` 的 `_download_audio_file()`（第 147-217 行）和 `utils/audio_downloader.py` 的 `download_audio_direct()` 做的事幾乎一樣。

**修改方式：**

`podcast_downloader.py` 中的 `_download_audio_file` 改為呼叫 `audio_downloader.download_audio_direct`：

```python
# podcast_downloader.py
from utils.audio_downloader import download_audio_direct

async def _download_from_rss(rss_url, target_dir, episode_index):
    # ... RSS 解析邏輯不變 ...

    # 改為呼叫共用下載器（skip_whitelist=True 因為已在上層驗證過）
    return await download_audio_direct(
        url=audio_url,
        output_dir=target_dir,
        filename=safe_filename,
        skip_whitelist=True
    )
```

刪除 `podcast_downloader.py` 中的 `_download_audio_file` 和 `_get_audio_extension` 函式。

### 任務 4：統一 server.py 所有工具的回傳格式

將所有工具改用 `success_response()` 和 `error_response()`。

**範例（convert_to_mp3 改寫前後）：**

```python
# 改寫前
return {"success": False, "error": f"輸入檔案不存在: {input_file}"}

# 改寫後
return error_response("FILE_NOT_FOUND", f"輸入檔案不存在: {input_file}", input_file=input_file)
```

---

## 驗證清單

- [ ] 所有工具的失敗回傳都包含 `error_code` 欄位
- [ ] `podcast_downloader.py` 中不再有 `_download_audio_file` 和 `_get_audio_extension`
- [ ] `audio_downloader.py` 無全域 SSL 警告抑制
- [ ] SSL 正常的網站：verify=True 通過
- [ ] SSL 異常的網站：自動 fallback 到 verify=False 並成功下載
- [ ] MCP 所有工具仍可正常呼叫
- [ ] CLI 工具仍可正常使用
