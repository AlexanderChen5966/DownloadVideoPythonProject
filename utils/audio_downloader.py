"""
音檔直接下載器
用於直接下載音檔 URL（MP3、M4A、WAV 等），不依賴 yt-dlp
支援白名單驗證、Content-Type 檢查、串流下載
"""

import os
import requests
import warnings
from pathlib import Path
from typing import Dict, Any, Optional
from urllib.parse import urlparse, unquote

from utils.sanitizer import sanitize_filename
from utils.whitelist_validator import get_validator

# 禁用 SSL 警告（因為某些網站的憑證有問題）
warnings.filterwarnings('ignore', message='Unverified HTTPS request')
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


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

    Returns:
        下載結果字典，包含：
        {
            "success": bool,           # 是否成功
            "file_path": str,          # 完整檔案路徑
            "file_name": str,          # 檔案名稱
            "file_size": int,          # 檔案大小（bytes）
            "content_type": str,       # Content-Type
            "url": str,                # 原始 URL
            "error": str               # 錯誤訊息（如果失敗）
        }
    """
    try:
        # 1. 白名單驗證
        if not skip_whitelist:
            validator = get_validator()
            is_allowed, message = validator.validate(url)
            if not is_allowed:
                return {
                    "success": False,
                    "url": url,
                    "error": "白名單驗證失敗",
                    "message": message,
                    "error_type": "whitelist_failed"
                }

        # 2. HEAD 請求檢查 Content-Type
        try:
            head_response = requests.head(url, timeout=10, allow_redirects=True, verify=False)
            head_response.raise_for_status()
            content_type = head_response.headers.get('Content-Type', '').lower()
            content_length = head_response.headers.get('Content-Length')

            # 檢查是否為音檔（允許一些例外情況）
            if content_type and not _is_audio_content_type(content_type):
                # 某些伺服器不提供正確的 Content-Type，記錄警告但繼續
                # 稍後會在 GET 請求時再次檢查
                pass

        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "url": url,
                "error": f"HEAD 請求失敗: {str(e)}",
                "error_type": "head_request_failed"
            }

        # 3. GET 請求下載音檔（串流模式）
        try:
            response = requests.get(url, timeout=60, stream=True, verify=False)
            response.raise_for_status()

            # 再次檢查 Content-Type（GET 請求）
            content_type = response.headers.get('Content-Type', '').lower()

            # 嚴格檢查：如果 Content-Type 明確不是音檔且不是通用類型，拒絕下載
            if content_type and _is_non_audio_content_type(content_type):
                return {
                    "success": False,
                    "url": url,
                    "error": f"URL 不是音檔，Content-Type: {content_type}",
                    "content_type": content_type,
                    "error_type": "invalid_content_type"
                }

        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code if hasattr(e, 'response') else None
            return {
                "success": False,
                "url": url,
                "error": f"HTTP 錯誤 {status_code}: {str(e)}",
                "status_code": status_code,
                "error_type": "http_error"
            }
        except requests.exceptions.Timeout:
            return {
                "success": False,
                "url": url,
                "error": "下載逾時（超過 60 秒）",
                "error_type": "timeout"
            }
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "url": url,
                "error": f"下載請求失敗: {str(e)}",
                "error_type": "request_failed"
            }

        # 4. 決定檔名和副檔名
        if filename:
            # 使用者指定檔名
            base_filename = sanitize_filename(filename)
        else:
            # 從 URL 提取檔名
            base_filename = _extract_filename_from_url(url)
            base_filename = sanitize_filename(base_filename)

        # 5. 偵測副檔名
        extension = _detect_extension(content_type, url)

        # 6. 建立目錄
        try:
            os.makedirs(output_dir, exist_ok=True)
        except OSError as e:
            return {
                "success": False,
                "url": url,
                "error": f"無法建立目錄 {output_dir}: {str(e)}",
                "error_type": "directory_creation_failed"
            }

        # 7. 完整檔案路徑
        file_name = f"{base_filename}{extension}"
        file_path = os.path.join(output_dir, file_name)

        # 8. 串流下載並寫入檔案
        try:
            total_size = 0
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        total_size += len(chunk)

            # 檢查檔案是否為空
            if total_size == 0:
                os.remove(file_path)  # 刪除空檔案
                return {
                    "success": False,
                    "url": url,
                    "error": "下載的檔案為空",
                    "error_type": "empty_file"
                }

        except IOError as e:
            return {
                "success": False,
                "url": url,
                "error": f"寫入檔案失敗: {str(e)}",
                "error_type": "file_write_failed"
            }

        # 9. 成功回傳結果
        return {
            "success": True,
            "file_path": os.path.abspath(file_path),
            "file_name": file_name,
            "file_size": total_size,
            "content_type": content_type,
            "url": url
        }

    except Exception as e:
        # 未預期的錯誤
        return {
            "success": False,
            "url": url,
            "error": f"未預期的錯誤: {str(e)}",
            "error_type": "unexpected_error"
        }


def _detect_extension(content_type: str, url: str) -> str:
    """
    根據 Content-Type 或 URL 推斷音檔副檔名

    Args:
        content_type: HTTP Content-Type header
        url: 音檔 URL

    Returns:
        副檔名（包含 .）
    """
    # 1. 優先根據 Content-Type 判斷
    if content_type:
        content_type_lower = content_type.lower()

        # 音檔 MIME types 對應
        mime_to_ext = {
            'audio/mpeg': '.mp3',
            'audio/mp3': '.mp3',
            'audio/mp4': '.m4a',
            'audio/m4a': '.m4a',
            'audio/x-m4a': '.m4a',
            'audio/wav': '.wav',
            'audio/wave': '.wav',
            'audio/x-wav': '.wav',
            'audio/ogg': '.ogg',
            'audio/vorbis': '.ogg',
            'audio/flac': '.flac',
            'audio/x-flac': '.flac',
            'audio/aac': '.aac',
            'audio/webm': '.webm',
            'audio/opus': '.opus',
        }

        for mime_type, ext in mime_to_ext.items():
            if mime_type in content_type_lower:
                return ext

        # 備用：從 content_type 中尋找常見關鍵字
        if 'mpeg' in content_type_lower or 'mp3' in content_type_lower:
            return '.mp3'
        elif 'mp4' in content_type_lower or 'm4a' in content_type_lower:
            return '.m4a'
        elif 'wav' in content_type_lower:
            return '.wav'
        elif 'ogg' in content_type_lower:
            return '.ogg'
        elif 'flac' in content_type_lower:
            return '.flac'
        elif 'aac' in content_type_lower:
            return '.aac'

    # 2. 從 URL 推斷副檔名
    url_lower = url.lower()

    # URL 解碼（處理 %20 等編碼）
    url_decoded = unquote(url_lower)

    # 常見音檔副檔名列表
    audio_extensions = ['.mp3', '.m4a', '.wav', '.ogg', '.flac', '.aac', '.opus', '.webm', '.wma']

    for ext in audio_extensions:
        if ext in url_decoded:
            return ext

    # 3. 嘗試從 URL path 提取副檔名
    parsed_url = urlparse(url)
    path = parsed_url.path
    if path:
        path_ext = os.path.splitext(path)[1].lower()
        if path_ext in audio_extensions:
            return path_ext

    # 4. 預設使用 .mp3
    return '.mp3'


def _extract_filename_from_url(url: str) -> str:
    """
    從 URL 中提取檔案名稱（不含副檔名）

    Args:
        url: 音檔 URL

    Returns:
        檔案名稱（不含副檔名）
    """
    # URL 解碼
    url_decoded = unquote(url)

    # 解析 URL
    parsed_url = urlparse(url_decoded)
    path = parsed_url.path

    if path:
        # 取得 path 的最後部分
        filename = os.path.basename(path)

        # 移除查詢參數
        filename = filename.split('?')[0]

        # 移除副檔名
        name_without_ext = os.path.splitext(filename)[0]

        if name_without_ext:
            return name_without_ext

    # 如果無法提取，使用預設名稱
    return "audio"


def _is_audio_content_type(content_type: str) -> bool:
    """
    檢查 Content-Type 是否為音檔

    Args:
        content_type: Content-Type header 值

    Returns:
        是否為音檔
    """
    content_type_lower = content_type.lower()

    # 音檔相關的 MIME types
    audio_types = [
        'audio/',                    # 所有 audio/* 類型
        'application/octet-stream',  # 通用二進位檔案（允許）
        'binary/octet-stream',       # 通用二進位檔案（允許）
    ]

    return any(audio_type in content_type_lower for audio_type in audio_types)


def _is_non_audio_content_type(content_type: str) -> bool:
    """
    檢查 Content-Type 是否明確不是音檔

    Args:
        content_type: Content-Type header 值

    Returns:
        是否明確不是音檔
    """
    content_type_lower = content_type.lower()

    # 明確不是音檔的類型
    non_audio_types = [
        'text/html',
        'text/plain',
        'application/json',
        'application/xml',
        'text/xml',
        'image/',
        'video/',  # 視訊檔案（雖然可能包含音軌，但不是純音檔）
    ]

    return any(non_audio in content_type_lower for non_audio in non_audio_types)
