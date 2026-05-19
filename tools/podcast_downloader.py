"""
Podcast 下載器 MCP 工具
用於下載 Podcast 音檔（支援 RSS Feed 和直接 MP3 URL）
"""

from typing import Dict, Any

from utils.audio_downloader import download_audio_direct
from utils.sanitizer import sanitize_filename
from utils.rss_parser import is_rss_url, parse_rss_feed
from utils.whitelist_validator import get_validator
from utils.response import error_response


async def download_podcast(url: str, target_dir: str = "./downloads", episode_index: int = 0) -> Dict[str, Any]:
    """
    下載 Podcast 音檔

    Args:
        url: Podcast RSS Feed URL 或直接 MP3 URL
        target_dir: 下載目標目錄
        episode_index: RSS Feed 時指定集數（0 = 最新）
    """
    try:
        validator = get_validator()
        is_allowed, message = validator.validate(url)
        if not is_allowed:
            return error_response("WHITELIST_DENIED", message, url=url)

        if is_rss_url(url):
            return await _download_from_rss(url, target_dir, episode_index)
        else:
            return await download_audio_direct(url=url, output_dir=target_dir, skip_whitelist=True)

    except Exception as e:
        return error_response("UNKNOWN_ERROR", f"下載失敗: {e}", url=url)


async def _download_from_rss(rss_url: str, target_dir: str, episode_index: int) -> Dict[str, Any]:
    """從 RSS Feed 解析並下載指定集數"""
    rss_result = parse_rss_feed(rss_url, episode_index)

    if not rss_result.get("success"):
        return error_response(
            "DOWNLOAD_FAILED",
            rss_result.get("error", "RSS 解析失敗"),
            url=rss_url, source_type="rss"
        )

    audio_url = rss_result["audio_url"]
    episode_title = rss_result["episode_title"]
    podcast_title = rss_result["podcast_title"]

    validator = get_validator()
    is_allowed, message = validator.validate(audio_url)
    if not is_allowed:
        return error_response(
            "WHITELIST_DENIED", message,
            url=audio_url, source_type="rss"
        )

    result = await download_audio_direct(
        url=audio_url,
        output_dir=target_dir,
        filename=sanitize_filename(episode_title),
        skip_whitelist=True
    )

    if result.get("success"):
        result.update({
            "source_type": "rss",
            "episode_title": episode_title,
            "podcast_title": podcast_title,
            "episode_index": episode_index,
            "total_episodes": rss_result.get("total_episodes"),
        })

    return result
