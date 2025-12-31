"""
Video Metadata Extractor
使用 FFprobe 提取視頻元數據
"""

import subprocess
import json
from typing import Dict, Any


class MetadataExtractor:
    """視頻元數據提取器"""

    @staticmethod
    def extract_metadata(video_path: str) -> Dict[str, Any]:
        """
        使用 FFprobe 提取視頻元數據

        Args:
            video_path: 視頻檔案路徑

        Returns:
            元數據字典
        """
        try:
            cmd = [
                "ffprobe",
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                "-show_streams",
                video_path
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )

            probe_data = json.loads(result.stdout)

            # 提取重要資訊
            metadata = {
                "success": True,
                "duration": None,
                "resolution": None,
                "bitrate": None,
                "video_codec": None,
                "audio_codec": None,
                "format": None
            }

            # 格式資訊
            if "format" in probe_data:
                format_info = probe_data["format"]

                if "duration" in format_info:
                    duration_seconds = float(format_info["duration"])
                    metadata["duration"] = MetadataExtractor._format_duration(duration_seconds)

                if "bit_rate" in format_info:
                    bitrate_bps = int(format_info["bit_rate"])
                    metadata["bitrate"] = MetadataExtractor._format_bitrate(bitrate_bps)

                if "format_name" in format_info:
                    metadata["format"] = format_info["format_name"]

            # 流資訊
            if "streams" in probe_data:
                for stream in probe_data["streams"]:
                    codec_type = stream.get("codec_type")

                    # 視頻流
                    if codec_type == "video":
                        if "codec_name" in stream:
                            metadata["video_codec"] = stream["codec_name"]

                        if "width" in stream and "height" in stream:
                            metadata["resolution"] = f"{stream['width']}x{stream['height']}"

                    # 音頻流
                    elif codec_type == "audio":
                        if "codec_name" in stream:
                            metadata["audio_codec"] = stream["codec_name"]

            return metadata

        except subprocess.CalledProcessError as e:
            return {
                "success": False,
                "error": f"FFprobe 執行失敗: {e.stderr}"
            }

        except json.JSONDecodeError as e:
            return {
                "success": False,
                "error": f"解析 FFprobe 輸出失敗: {str(e)}"
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"提取元數據失敗: {str(e)}"
            }

    @staticmethod
    def _format_duration(seconds: float) -> str:
        """
        格式化時長為 HH:MM:SS 格式

        Args:
            seconds: 秒數

        Returns:
            格式化的時長字串
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)

        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        else:
            return f"{minutes:02d}:{secs:02d}"

    @staticmethod
    def _format_bitrate(bitrate_bps: int) -> str:
        """
        格式化比特率

        Args:
            bitrate_bps: 比特率（bits per second）

        Returns:
            格式化的比特率字串
        """
        if bitrate_bps >= 1_000_000:
            return f"{bitrate_bps / 1_000_000:.2f} Mbps"
        elif bitrate_bps >= 1_000:
            return f"{bitrate_bps / 1_000:.2f} Kbps"
        else:
            return f"{bitrate_bps} bps"
