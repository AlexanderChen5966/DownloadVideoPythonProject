"""
Podcast 下載器 MCP 工具
用於下載 Podcast 音檔（支援 RSS Feed 和直接 MP3 URL）
"""

import os
import requests
from pathlib import Path
from typing import Dict, Any

from utils.sanitizer import sanitize_filename
from utils.rss_parser import is_rss_url, parse_rss_feed
from utils.whitelist_validator import get_validator


async def download_podcast(url: str, target_dir: str = "./downloads", episode_index: int = 0) -> Dict[str, Any]:
    """
    下載 Podcast 音檔

    Args:
        url: Podcast RSS Feed URL 或直接 MP3 URL
        target_dir: 下載目標目錄（預設為 ./downloads）
        episode_index: 如果是 RSS Feed，指定要下載第幾集（0 = 最新）

    Returns:
        下載結果字典，包含成功狀態、檔案路徑等資訊
    """
    try:
        # 白名單檢查
        validator = get_validator()
        is_allowed, message = validator.validate(url)
        if not is_allowed:
            return {
                "success": False,
                "error": "白名單驗證失敗",
                "message": message
            }

        # 判斷 URL 類型
        if is_rss_url(url):
            return await _download_from_rss(url, target_dir, episode_index)
        else:
            return await _download_direct_audio(url, target_dir)

    except Exception as e:
        return {
            "success": False,
            "error": f"下載失敗: {str(e)}"
        }


async def _download_from_rss(rss_url: str, target_dir: str, episode_index: int) -> Dict[str, Any]:
    """
    從 RSS Feed 下載 Podcast

    Args:
        rss_url: RSS Feed URL
        target_dir: 下載目標目錄
        episode_index: 要下載的集數索引

    Returns:
        下載結果字典
    """
    # 解析 RSS Feed
    rss_result = parse_rss_feed(rss_url, episode_index)

    if not rss_result.get("success"):
        return {
            "success": False,
            "error": rss_result.get("error", "RSS 解析失敗"),
            "source_type": "rss"
        }

    audio_url = rss_result["audio_url"]
    episode_title = rss_result["episode_title"]
    podcast_title = rss_result["podcast_title"]

    # 白名單檢查 (檢查音檔 URL)
    validator = get_validator()
    is_allowed, message = validator.validate(audio_url)
    if not is_allowed:
        return {
            "success": False,
            "error": "音檔 URL 白名單驗證失敗",
            "message": message,
            "source_type": "rss",
            "audio_url": audio_url
        }

    # 清洗檔名
    safe_filename = sanitize_filename(episode_title)

    # 下載音檔
    download_result = await _download_audio_file(
        audio_url,
        target_dir,
        safe_filename
    )

    if download_result["success"]:
        download_result.update({
            "source_type": "rss",
            "episode_title": episode_title,
            "podcast_title": podcast_title,
            "episode_index": episode_index,
            "total_episodes": rss_result.get("total_episodes")
        })

    return download_result


async def _download_direct_audio(audio_url: str, target_dir: str) -> Dict[str, Any]:
    """
    直接下載音檔 URL

    Args:
        audio_url: 音檔的直接 URL
        target_dir: 下載目標目錄

    Returns:
        下載結果字典
    """
    # 使用 URL 最後部分作為檔名
    filename = audio_url.split('/')[-1].split('?')[0]

    # 如果檔名沒有副檔名，使用預設名稱
    if '.' not in filename:
        filename = "podcast"

    # 移除副檔名
    name_without_ext = os.path.splitext(filename)[0]
    safe_filename = sanitize_filename(name_without_ext)

    # 下載音檔
    download_result = await _download_audio_file(
        audio_url,
        target_dir,
        safe_filename
    )

    if download_result["success"]:
        download_result["source_type"] = "mp3"

    return download_result


async def _download_audio_file(audio_url: str, target_dir: str, filename: str) -> Dict[str, Any]:
    """
    下載音檔檔案

    Args:
        audio_url: 音檔 URL
        target_dir: 目標目錄
        filename: 檔案名稱（不含副檔名）

    Returns:
        下載結果字典
    """
    try:
        # 先用 HEAD 請求檢查檔案
        head_response = requests.head(audio_url, timeout=10, allow_redirects=True)
        content_type = head_response.headers.get('Content-Type', '').lower()

        # 檢查是否為音檔
        if content_type and not content_type.startswith('audio/'):
            # 某些伺服器不提供正確的 Content-Type，嘗試下載
            # 但給予警告
            pass

        # 下載音檔
        response = requests.get(audio_url, timeout=60, stream=True)
        response.raise_for_status()

        # 再次檢查 Content-Type（GET 請求）
        content_type = response.headers.get('Content-Type', '').lower()

        # 確定副檔名
        extension = _get_audio_extension(content_type, audio_url)

        # 建立目錄
        os.makedirs(target_dir, exist_ok=True)

        # 完整檔案路徑
        file_name = f"{filename}{extension}"
        file_path = os.path.join(target_dir, file_name)

        # 寫入檔案
        total_size = 0
        with open(file_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    total_size += len(chunk)

        return {
            "success": True,
            "file_path": os.path.abspath(file_path),
            "file_name": file_name,
            "file_size": total_size,
            "content_type": content_type
        }

    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "error": f"下載音檔失敗: {str(e)}"
        }
    except IOError as e:
        return {
            "success": False,
            "error": f"寫入檔案失敗: {str(e)}"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"未預期的錯誤: {str(e)}"
        }


def _get_audio_extension(content_type: str, url: str) -> str:
    """
    根據 Content-Type 或 URL 推斷音檔副檔名

    Args:
        content_type: HTTP Content-Type header
        url: 音檔 URL

    Returns:
        副檔名（包含 .）
    """
    # 根據 Content-Type 判斷
    if content_type:
        if 'mpeg' in content_type or 'mp3' in content_type:
            return '.mp3'
        elif 'mp4' in content_type or 'm4a' in content_type:
            return '.m4a'
        elif 'wav' in content_type:
            return '.wav'
        elif 'ogg' in content_type:
            return '.ogg'
        elif 'flac' in content_type:
            return '.flac'

    # 從 URL 推斷
    url_lower = url.lower()
    for ext in ['.mp3', '.m4a', '.wav', '.ogg', '.flac', '.aac']:
        if ext in url_lower:
            return ext

    # 預設使用 .mp3
    return '.mp3'
