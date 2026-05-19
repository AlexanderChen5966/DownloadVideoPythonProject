"""
音檔直接下載器
用於直接下載音檔 URL（MP3、M4A、WAV 等），不依賴 yt-dlp
支援白名單驗證、Content-Type 檢查、串流下載、SSL fallback
"""

import os
import requests
from pathlib import Path
from typing import Dict, Any, Optional
from urllib.parse import urlparse, unquote

from utils.sanitizer import sanitize_filename
from utils.whitelist_validator import get_validator
from utils.response import success_response, error_response


def _safe_request(method: str, url: str, **kwargs):
    """先嘗試 SSL 驗證，失敗後自動 fallback 為不驗證"""
    try:
        return requests.request(method, url, verify=True, **kwargs)
    except requests.exceptions.SSLError:
        return requests.request(method, url, verify=False, **kwargs)


async def download_audio_direct(
    url: str,
    output_dir: str = "./downloads",
    filename: Optional[str] = None,
    skip_whitelist: bool = False
) -> Dict[str, Any]:
    """
    直接下載音檔 URL

    Args:
        url: 音檔的直接 URL
        output_dir: 下載目標目錄（預設為 ./downloads）
        filename: 自訂檔名（不含副檔名，選填）
        skip_whitelist: 是否跳過白名單驗證（預設 False）
    """
    try:
        # 1. 白名單驗證
        if not skip_whitelist:
            validator = get_validator()
            is_allowed, message = validator.validate(url)
            if not is_allowed:
                return error_response("WHITELIST_DENIED", message, url=url)

        # 2. HEAD 請求確認 Content-Type
        try:
            head_resp = _safe_request("HEAD", url, timeout=10, allow_redirects=True)
            head_resp.raise_for_status()
            content_type = head_resp.headers.get("Content-Type", "").lower()
        except requests.exceptions.RequestException as e:
            return error_response("DOWNLOAD_FAILED", f"HEAD 請求失敗: {e}", url=url)

        # 3. GET 串流下載
        try:
            response = _safe_request("GET", url, timeout=60, stream=True)
            response.raise_for_status()
            content_type = response.headers.get("Content-Type", "").lower()

            if content_type and _is_non_audio_content_type(content_type):
                return error_response(
                    "INVALID_CONTENT_TYPE",
                    f"URL 不是音檔，Content-Type: {content_type}",
                    url=url, content_type=content_type
                )
        except requests.exceptions.Timeout:
            return error_response("DOWNLOAD_TIMEOUT", "下載逾時（超過 60 秒）", url=url)
        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code if hasattr(e, "response") else None
            return error_response("DOWNLOAD_FAILED", f"HTTP 錯誤 {status_code}", url=url, status_code=status_code)
        except requests.exceptions.RequestException as e:
            return error_response("DOWNLOAD_FAILED", f"下載請求失敗: {e}", url=url)

        # 4. 決定檔名與副檔名
        base_filename = sanitize_filename(filename) if filename else sanitize_filename(_extract_filename_from_url(url))
        extension = _detect_extension(content_type, url)

        # 5. 建立目錄
        try:
            os.makedirs(output_dir, exist_ok=True)
        except OSError as e:
            return error_response("DOWNLOAD_FAILED", f"無法建立目錄 {output_dir}: {e}", url=url)

        # 6. 寫入檔案
        file_path = os.path.join(output_dir, f"{base_filename}{extension}")
        try:
            total_size = 0
            with open(file_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        total_size += len(chunk)

            if total_size == 0:
                os.remove(file_path)
                return error_response("EMPTY_FILE", "下載的檔案為空", url=url)

        except IOError as e:
            return error_response("DOWNLOAD_FAILED", f"寫入檔案失敗: {e}", url=url)

        return success_response(
            file_path=os.path.abspath(file_path),
            file_name=f"{base_filename}{extension}",
            file_size=total_size,
            content_type=content_type,
            url=url
        )

    except Exception as e:
        return error_response("UNKNOWN_ERROR", f"未預期的錯誤: {e}", url=url)


def _detect_extension(content_type: str, url: str) -> str:
    """根據 Content-Type 或 URL 推斷音檔副檔名"""
    mime_to_ext = {
        "audio/mpeg": ".mp3", "audio/mp3": ".mp3",
        "audio/mp4": ".m4a", "audio/m4a": ".m4a", "audio/x-m4a": ".m4a",
        "audio/wav": ".wav", "audio/wave": ".wav", "audio/x-wav": ".wav",
        "audio/ogg": ".ogg", "audio/vorbis": ".ogg",
        "audio/flac": ".flac", "audio/x-flac": ".flac",
        "audio/aac": ".aac",
        "audio/webm": ".webm",
        "audio/opus": ".opus",
    }
    ct = content_type.lower()
    for mime, ext in mime_to_ext.items():
        if mime in ct:
            return ext
    if "mpeg" in ct or "mp3" in ct:
        return ".mp3"
    if "mp4" in ct or "m4a" in ct:
        return ".m4a"

    audio_extensions = [".mp3", ".m4a", ".wav", ".ogg", ".flac", ".aac", ".opus", ".webm", ".wma"]
    url_decoded = unquote(url.lower())
    for ext in audio_extensions:
        if ext in url_decoded:
            return ext
    path_ext = os.path.splitext(urlparse(url).path)[1].lower()
    if path_ext in audio_extensions:
        return path_ext

    return ".mp3"


def _extract_filename_from_url(url: str) -> str:
    """從 URL 中提取檔案名稱（不含副檔名）"""
    path = urlparse(unquote(url)).path
    if path:
        name = os.path.splitext(os.path.basename(path.split("?")[0]))[0]
        if name:
            return name
    return "audio"


def _is_audio_content_type(content_type: str) -> bool:
    ct = content_type.lower()
    return any(t in ct for t in ["audio/", "application/octet-stream", "binary/octet-stream"])


def _is_non_audio_content_type(content_type: str) -> bool:
    ct = content_type.lower()
    return any(t in ct for t in ["text/html", "text/plain", "application/json", "application/xml", "text/xml", "image/"])
