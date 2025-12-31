"""
HLS Video Downloader
主下載器模組，整合所有功能
"""

import os
import shutil
import tempfile
from typing import Dict, Any
from pathlib import Path

from .parser import parse_m3u8
from .segment_downloader import SegmentDownloader
from .converter import VideoConverter
from .metadata import MetadataExtractor
from utils.whitelist_validator import get_validator


async def download_hls(
    m3u8_url: str,
    output_path: str,
    threads: int = 8,
    select_highest_quality: bool = True,
    cleanup_temp: bool = True
) -> Dict[str, Any]:
    """
    下載 HLS 視頻並轉換為 MP4

    Args:
        m3u8_url: m3u8 playlist URL
        output_path: 輸出 MP4 檔案路徑
        threads: 並行下載線程數
        select_highest_quality: 是否自動選擇最高畫質
        cleanup_temp: 是否清理暫存檔案

    Returns:
        下載結果字典
    """
    temp_dir = None

    try:
        # 1. 白名單檢查
        validator = get_validator()
        is_allowed, message = validator.validate(m3u8_url)
        if not is_allowed:
            return {
                "success": False,
                "error": "白名單驗證失敗",
                "message": message
            }

        # 2. 解析 m3u8 playlist
        parse_result = parse_m3u8(m3u8_url, select_highest_quality)

        if not parse_result.get("success"):
            return parse_result

        # 3. 取得 segments
        segments = parse_result.get("segments", [])

        if not segments:
            return {
                "success": False,
                "error": "沒有找到可下載的 segments"
            }

        # 4. 建立暫存目錄
        temp_dir = tempfile.mkdtemp(prefix="hls_download_")

        # 5. 下載所有 TS segments
        downloader = SegmentDownloader(max_workers=threads)

        download_result = downloader.download_segments(
            segments,
            temp_dir,
            progress_callback=_progress_callback
        )

        if not download_result.get("success"):
            return {
                "success": False,
                "error": "部分 segments 下載失敗",
                "download_result": download_result
            }

        # 6. 準備 TS 檔案列表（按順序）
        ts_files = [
            item["path"]
            for item in download_result["downloaded_files"]
        ]

        # 7. 確保輸出目錄存在
        output_dir = os.path.dirname(output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        # 8. 使用 concat demuxer 轉換為 MP4（推薦方法）
        converter = VideoConverter()
        convert_result = converter.convert_using_concat_demuxer(
            ts_files,
            output_path,
            temp_dir
        )

        if not convert_result.get("success"):
            return {
                "success": False,
                "error": "轉換為 MP4 失敗",
                "convert_result": convert_result
            }

        # 9. 提取視頻元數據
        metadata = MetadataExtractor.extract_metadata(output_path)

        # 10. 清理暫存檔案
        if cleanup_temp and temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

        # 11. 組合最終結果
        return {
            "success": True,
            "output_file": os.path.abspath(output_path),
            "duration": metadata.get("duration", "unknown"),
            "resolution": metadata.get("resolution", "unknown"),
            "bitrate": metadata.get("bitrate", "unknown"),
            "video_codec": metadata.get("video_codec"),
            "audio_codec": metadata.get("audio_codec"),
            "file_size": os.path.getsize(output_path),
            "total_segments": download_result["total_segments"],
            "conversion_method": convert_result.get("method", "unknown"),
            "is_master_playlist": parse_result.get("is_master", False),
            "selected_variant": parse_result.get("selected_variant")
        }

    except Exception as e:
        # 清理暫存目錄
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

        return {
            "success": False,
            "error": f"下載過程發生錯誤: {str(e)}"
        }


def _progress_callback(completed: int, total: int):
    """
    下載進度回調函數

    Args:
        completed: 已完成數
        total: 總數
    """
    percentage = (completed / total) * 100
    print(f"下載進度: {completed}/{total} ({percentage:.1f}%)")
