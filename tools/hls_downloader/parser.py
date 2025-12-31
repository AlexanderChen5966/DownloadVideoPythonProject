"""
M3U8 Playlist Parser
解析 HLS m3u8 文件並選擇最高品質
"""

import m3u8
from typing import Dict, List, Any
from urllib.parse import urljoin


def parse_m3u8(m3u8_url: str, select_highest_quality: bool = True) -> Dict[str, Any]:
    """
    解析 m3u8 playlist

    Args:
        m3u8_url: m3u8 playlist URL
        select_highest_quality: 是否自動選擇最高畫質

    Returns:
        包含解析結果的字典
    """
    try:
        # 載入 m3u8 playlist
        playlist = m3u8.load(m3u8_url)

        # 檢查是否為 master playlist (包含多個解析度)
        if playlist.is_variant:
            return _parse_master_playlist(playlist, m3u8_url, select_highest_quality)
        else:
            return _parse_media_playlist(playlist, m3u8_url)

    except Exception as e:
        return {
            "success": False,
            "error": f"解析 m3u8 失敗: {str(e)}"
        }


def _parse_master_playlist(playlist: m3u8.M3U8, base_url: str, select_highest: bool) -> Dict[str, Any]:
    """
    解析 master playlist (包含多個品質選項)

    Args:
        playlist: m3u8 playlist 物件
        base_url: 基礎 URL
        select_highest: 是否選擇最高品質

    Returns:
        解析結果字典
    """
    if not playlist.playlists:
        return {
            "success": False,
            "error": "Master playlist 中沒有可用的變體"
        }

    # 收集所有可用的品質選項
    variants = []
    for p in playlist.playlists:
        variant_info = {
            "uri": p.uri,
            "absolute_uri": p.absolute_uri or urljoin(base_url, p.uri),
            "bandwidth": p.stream_info.bandwidth if p.stream_info else 0,
            "resolution": (
                f"{p.stream_info.resolution[0]}x{p.stream_info.resolution[1]}"
                if p.stream_info and p.stream_info.resolution
                else "unknown"
            ),
            "codecs": p.stream_info.codecs if p.stream_info else None
        }
        variants.append(variant_info)

    # 依照頻寬排序，選擇最高品質
    variants.sort(key=lambda x: x["bandwidth"], reverse=True)

    if select_highest:
        selected_variant = variants[0]
        # 載入選定的媒體 playlist
        media_playlist = m3u8.load(selected_variant["absolute_uri"])

        return {
            "success": True,
            "is_master": True,
            "selected_variant": selected_variant,
            "available_variants": variants,
            "segments": _extract_segments(media_playlist, selected_variant["absolute_uri"])
        }
    else:
        return {
            "success": True,
            "is_master": True,
            "available_variants": variants
        }


def _parse_media_playlist(playlist: m3u8.M3U8, base_url: str) -> Dict[str, Any]:
    """
    解析媒體 playlist (包含 TS segments)

    Args:
        playlist: m3u8 playlist 物件
        base_url: 基礎 URL

    Returns:
        解析結果字典
    """
    return {
        "success": True,
        "is_master": False,
        "segments": _extract_segments(playlist, base_url)
    }


def _extract_segments(playlist: m3u8.M3U8, base_url: str) -> List[Dict[str, Any]]:
    """
    從 playlist 提取所有 TS segments

    Args:
        playlist: m3u8 playlist 物件
        base_url: 基礎 URL

    Returns:
        segment 列表
    """
    segments = []

    for idx, segment in enumerate(playlist.segments):
        absolute_uri = segment.absolute_uri or urljoin(base_url, segment.uri)

        segment_info = {
            "index": idx,
            "uri": segment.uri,
            "absolute_uri": absolute_uri,
            "duration": segment.duration,
            "title": segment.title
        }
        segments.append(segment_info)

    return segments
