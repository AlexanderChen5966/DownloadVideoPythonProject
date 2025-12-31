"""
RSS Feed 解析工具
用於解析 Podcast RSS Feed 並提取音檔資訊
"""

import feedparser
from typing import Optional, Dict, Any


def is_rss_url(url: str) -> bool:
    """
    判斷 URL 是否可能是 RSS Feed

    Args:
        url: 要檢查的 URL

    Returns:
        True 如果 URL 看起來像 RSS Feed
    """
    url_lower = url.lower()
    return (
        url_lower.endswith('.xml') or
        url_lower.endswith('.rss') or
        '/feed' in url_lower or
        '/rss' in url_lower or
        'feed' in url_lower
    )


def parse_rss_feed(url: str, episode_index: int = 0) -> Dict[str, Any]:
    """
    解析 RSS Feed 並取得指定集數的音檔資訊

    Args:
        url: RSS Feed URL
        episode_index: 要取得的集數索引（0 = 最新一集）

    Returns:
        包含音檔資訊的字典，格式如下：
        {
            "success": bool,
            "audio_url": str,           # 音檔下載 URL
            "episode_title": str,       # 集數標題
            "episode_description": str, # 集數描述
            "podcast_title": str,       # Podcast 名稱
            "error": str                # 錯誤訊息（如果失敗）
        }
    """
    try:
        # 解析 RSS Feed
        feed = feedparser.parse(url)

        # 檢查 Feed 是否有效
        if feed.bozo and not feed.entries:
            return {
                "success": False,
                "error": f"無法解析 RSS Feed: {feed.get('bozo_exception', '未知錯誤')}"
            }

        # 檢查是否有 episode
        if not feed.entries:
            return {
                "success": False,
                "error": "RSS Feed 中沒有找到任何 episode"
            }

        # 檢查 episode_index 是否有效
        if episode_index < 0 or episode_index >= len(feed.entries):
            return {
                "success": False,
                "error": f"Episode index {episode_index} 超出範圍（總共 {len(feed.entries)} 集）"
            }

        # 取得指定的 episode
        episode = feed.entries[episode_index]

        # 取得音檔 URL（從 enclosure）
        audio_url = None
        if hasattr(episode, 'enclosures') and episode.enclosures:
            # 尋找 audio/* 類型的 enclosure
            for enclosure in episode.enclosures:
                if hasattr(enclosure, 'type') and enclosure.type and 'audio' in enclosure.type.lower():
                    audio_url = enclosure.get('href') or enclosure.get('url')
                    break

            # 如果沒有找到 audio 類型，使用第一個 enclosure
            if not audio_url and episode.enclosures:
                audio_url = episode.enclosures[0].get('href') or episode.enclosures[0].get('url')

        # 如果還是沒有找到，嘗試從 links 中找
        if not audio_url and hasattr(episode, 'links'):
            for link in episode.links:
                if link.get('type', '').startswith('audio/'):
                    audio_url = link.get('href')
                    break

        if not audio_url:
            return {
                "success": False,
                "error": f"Episode #{episode_index} 沒有找到音檔 URL（可能沒有 enclosure）"
            }

        # 提取 episode 資訊
        episode_title = episode.get('title', f'Episode {episode_index}')
        episode_description = episode.get('summary', '') or episode.get('description', '')

        # 提取 Podcast 名稱
        podcast_title = feed.feed.get('title', 'Unknown Podcast')

        return {
            "success": True,
            "audio_url": audio_url,
            "episode_title": episode_title,
            "episode_description": episode_description,
            "podcast_title": podcast_title,
            "total_episodes": len(feed.entries),
            "episode_index": episode_index
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"解析 RSS Feed 時發生錯誤: {str(e)}"
        }


def get_feed_info(url: str) -> Dict[str, Any]:
    """
    取得 RSS Feed 的基本資訊（不下載音檔）

    Args:
        url: RSS Feed URL

    Returns:
        包含 Feed 資訊的字典
    """
    try:
        feed = feedparser.parse(url)

        if feed.bozo and not feed.entries:
            return {
                "success": False,
                "error": f"無法解析 RSS Feed: {feed.get('bozo_exception', '未知錯誤')}"
            }

        return {
            "success": True,
            "podcast_title": feed.feed.get('title', 'Unknown'),
            "podcast_description": feed.feed.get('description', ''),
            "total_episodes": len(feed.entries),
            "latest_episode": feed.entries[0].get('title', '') if feed.entries else None
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"取得 Feed 資訊時發生錯誤: {str(e)}"
        }
