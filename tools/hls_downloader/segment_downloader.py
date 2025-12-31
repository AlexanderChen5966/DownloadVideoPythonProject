"""
TS Segment Downloader
並行下載 HLS TS segments，支援重試和錯誤處理
"""

import os
import time
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Callable


class SegmentDownloader:
    """TS Segment 下載器"""

    def __init__(
        self,
        max_workers: int = 8,
        max_retries: int = 3,
        timeout: int = 30,
        retry_delay: int = 2
    ):
        """
        初始化下載器

        Args:
            max_workers: 最大並行下載數
            max_retries: 最大重試次數
            timeout: 請求超時時間（秒）
            retry_delay: 重試延遲時間（秒）
        """
        self.max_workers = max_workers
        self.max_retries = max_retries
        self.timeout = timeout
        self.retry_delay = retry_delay

    def download_segments(
        self,
        segments: List[Dict[str, Any]],
        output_dir: str,
        progress_callback: Callable[[int, int], None] = None
    ) -> Dict[str, Any]:
        """
        並行下載所有 TS segments

        Args:
            segments: segment 資訊列表
            output_dir: 輸出目錄
            progress_callback: 進度回調函數 (完成數, 總數)

        Returns:
            下載結果字典
        """
        # 確保輸出目錄存在
        os.makedirs(output_dir, exist_ok=True)

        total_segments = len(segments)
        downloaded_files = []
        failed_segments = []
        completed = 0

        # 使用線程池並行下載
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交所有下載任務
            future_to_segment = {
                executor.submit(
                    self._download_segment,
                    segment,
                    output_dir
                ): segment
                for segment in segments
            }

            # 等待完成
            for future in as_completed(future_to_segment):
                segment = future_to_segment[future]

                try:
                    result = future.result()

                    if result["success"]:
                        downloaded_files.append(result)
                    else:
                        failed_segments.append({
                            "segment": segment,
                            "error": result.get("error", "未知錯誤")
                        })

                except Exception as e:
                    failed_segments.append({
                        "segment": segment,
                        "error": str(e)
                    })

                # 更新進度
                completed += 1
                if progress_callback:
                    progress_callback(completed, total_segments)

        # 按索引排序下載的檔案
        downloaded_files.sort(key=lambda x: x["index"])

        return {
            "success": len(failed_segments) == 0,
            "total_segments": total_segments,
            "downloaded": len(downloaded_files),
            "failed": len(failed_segments),
            "downloaded_files": downloaded_files,
            "failed_segments": failed_segments
        }

    def _download_segment(self, segment: Dict[str, Any], output_dir: str) -> Dict[str, Any]:
        """
        下載單一 TS segment，支援重試

        Args:
            segment: segment 資訊
            output_dir: 輸出目錄

        Returns:
            下載結果
        """
        url = segment["absolute_uri"]
        index = segment["index"]
        output_path = os.path.join(output_dir, f"seg_{index:05d}.ts")

        # 重試機制
        for attempt in range(self.max_retries):
            try:
                response = requests.get(url, timeout=self.timeout, stream=True)
                response.raise_for_status()

                # 寫入檔案
                total_size = 0
                with open(output_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            total_size += len(chunk)

                return {
                    "success": True,
                    "index": index,
                    "path": output_path,
                    "size": total_size
                }

            except requests.exceptions.RequestException as e:
                # 如果還有重試機會，等待後重試
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                    continue
                else:
                    return {
                        "success": False,
                        "index": index,
                        "error": f"下載失敗（已重試 {self.max_retries} 次）: {str(e)}"
                    }

            except IOError as e:
                return {
                    "success": False,
                    "index": index,
                    "error": f"寫入檔案失敗: {str(e)}"
                }

        return {
            "success": False,
            "index": index,
            "error": "未知錯誤"
        }
