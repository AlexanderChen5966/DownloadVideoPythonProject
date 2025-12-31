"""
TS Merger and MP4 Converter
合併 TS segments 並轉換為 MP4
"""

import os
import subprocess
from typing import List, Dict, Any


class VideoConverter:
    """視頻轉換器"""

    @staticmethod
    def merge_ts_files(ts_files: List[str], merged_path: str) -> Dict[str, Any]:
        """
        合併多個 TS 檔案為一個檔案

        Args:
            ts_files: TS 檔案路徑列表（按順序）
            merged_path: 合併後的輸出路徑

        Returns:
            合併結果字典
        """
        try:
            total_size = 0

            with open(merged_path, 'wb') as merged:
                for ts_file in ts_files:
                    if not os.path.exists(ts_file):
                        return {
                            "success": False,
                            "error": f"TS 檔案不存在: {ts_file}"
                        }

                    with open(ts_file, 'rb') as segment:
                        data = segment.read()
                        merged.write(data)
                        total_size += len(data)

            return {
                "success": True,
                "merged_path": merged_path,
                "total_size": total_size,
                "segment_count": len(ts_files)
            }

        except IOError as e:
            return {
                "success": False,
                "error": f"合併 TS 檔案失敗: {str(e)}"
            }

    @staticmethod
    def convert_to_mp4_direct_copy(input_ts: str, output_mp4: str) -> Dict[str, Any]:
        """
        使用 FFmpeg direct copy 將 TS 轉換為 MP4（快速，不重新編碼）

        Args:
            input_ts: 輸入 TS 檔案路徑
            output_mp4: 輸出 MP4 檔案路徑

        Returns:
            轉換結果字典
        """
        try:
            cmd = [
                "ffmpeg",
                "-y",  # 覆蓋現有檔案
                "-i", input_ts,
                "-c", "copy",  # 直接複製，不重新編碼
                "-bsf:a", "aac_adtstoasc",  # AAC 位元流過濾器
                output_mp4
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )

            if os.path.exists(output_mp4):
                return {
                    "success": True,
                    "output_file": output_mp4,
                    "file_size": os.path.getsize(output_mp4),
                    "method": "direct_copy"
                }
            else:
                return {
                    "success": False,
                    "error": "轉換完成但找不到輸出檔案"
                }

        except subprocess.CalledProcessError as e:
            # direct copy 失敗，嘗試重新編碼
            return VideoConverter.convert_to_mp4_reencode(input_ts, output_mp4)

        except Exception as e:
            return {
                "success": False,
                "error": f"FFmpeg 執行失敗: {str(e)}"
            }

    @staticmethod
    def convert_to_mp4_reencode(input_ts: str, output_mp4: str) -> Dict[str, Any]:
        """
        使用 FFmpeg 重新編碼將 TS 轉換為 MP4（慢但相容性高）

        Args:
            input_ts: 輸入 TS 檔案路徑
            output_mp4: 輸出 MP4 檔案路徑

        Returns:
            轉換結果字典
        """
        try:
            cmd = [
                "ffmpeg",
                "-y",
                "-i", input_ts,
                "-c:v", "libx264",  # H.264 視頻編碼
                "-c:a", "aac",      # AAC 音頻編碼
                "-preset", "medium",
                "-crf", "23",
                output_mp4
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )

            if os.path.exists(output_mp4):
                return {
                    "success": True,
                    "output_file": output_mp4,
                    "file_size": os.path.getsize(output_mp4),
                    "method": "reencode"
                }
            else:
                return {
                    "success": False,
                    "error": "重新編碼完成但找不到輸出檔案"
                }

        except subprocess.CalledProcessError as e:
            return {
                "success": False,
                "error": f"FFmpeg 重新編碼失敗: {e.stderr}"
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"重新編碼執行失敗: {str(e)}"
            }

    @staticmethod
    def convert_using_concat_demuxer(ts_files: List[str], output_mp4: str, temp_dir: str) -> Dict[str, Any]:
        """
        使用 FFmpeg concat demuxer 直接從 TS 列表轉換為 MP4（推薦方法）

        Args:
            ts_files: TS 檔案路徑列表
            output_mp4: 輸出 MP4 檔案路徑
            temp_dir: 暫存目錄

        Returns:
            轉換結果字典
        """
        try:
            # 建立 concat 列表檔案
            concat_list_path = os.path.join(temp_dir, "concat_list.txt")

            with open(concat_list_path, 'w', encoding='utf-8') as f:
                for ts_file in ts_files:
                    # 使用絕對路徑
                    abs_path = os.path.abspath(ts_file)
                    # 轉義單引號
                    escaped_path = abs_path.replace("'", "'\\''")
                    f.write(f"file '{escaped_path}'\n")

            # 使用 FFmpeg concat demuxer
            cmd = [
                "ffmpeg",
                "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", concat_list_path,
                "-c", "copy",
                "-bsf:a", "aac_adtstoasc",
                output_mp4
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )

            if os.path.exists(output_mp4):
                return {
                    "success": True,
                    "output_file": output_mp4,
                    "file_size": os.path.getsize(output_mp4),
                    "method": "concat_demuxer"
                }
            else:
                return {
                    "success": False,
                    "error": "轉換完成但找不到輸出檔案"
                }

        except subprocess.CalledProcessError as e:
            # concat demuxer 失敗，回退到合併後重新編碼
            merged_ts = os.path.join(temp_dir, "merged.ts")
            merge_result = VideoConverter.merge_ts_files(ts_files, merged_ts)

            if not merge_result["success"]:
                return merge_result

            return VideoConverter.convert_to_mp4_reencode(merged_ts, output_mp4)

        except Exception as e:
            return {
                "success": False,
                "error": f"concat demuxer 執行失敗: {str(e)}"
            }
