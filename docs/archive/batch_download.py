#!/usr/bin/env python3
"""
批次下載 JSON 中的影片和圖片
"""
import json
import sys
import os
import argparse
import asyncio
import subprocess
from pathlib import Path
import requests
from typing import List, Tuple


def load_json_data(json_file: str) -> List[dict]:
    """載入 JSON 資料並返回影片列表"""
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data.get('ymSubmenu', {}).get('dvd', {}).get('submenu', [])


async def download_video_ytdlp(url: str, output_dir: str, filename: str, format: str = "mp4") -> dict:
    """使用 yt-dlp 下載影片"""
    try:
        os.makedirs(output_dir, exist_ok=True)

        # 清理檔名（移除不允許的字元）
        safe_filename = "".join(c for c in filename if c.isalnum() or c in (' ', '-', '_', '！', '？'))
        output_path = os.path.join(output_dir, safe_filename)

        cmd = [
            ".venv/bin/yt-dlp",
            "-o", f"{output_path}.%(ext)s"
        ]

        # 根據格式添加參數
        if format == "mp3":
            cmd.extend(["--extract-audio", "--audio-format", "mp3", "--audio-quality", "0"])
        elif format == "mp4":
            cmd.extend(["-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best", "--merge-output-format", "mp4"])
        elif format == "webm":
            cmd.extend(["-f", "bestvideo[ext=webm]+bestaudio[ext=webm]/best[ext=webm]/best", "--merge-output-format", "webm"])
        else:
            cmd.extend(["-f", "best"])

        cmd.append(url)

        # 執行下載
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )

        return {
            "success": True,
            "filename": safe_filename,
            "url": url,
            "output": result.stdout
        }

    except subprocess.CalledProcessError as e:
        return {
            "success": False,
            "filename": filename,
            "url": url,
            "error": f"下載失敗: {e.stderr}"
        }
    except Exception as e:
        return {
            "success": False,
            "filename": filename,
            "url": url,
            "error": str(e)
        }


def download_image(url: str, output_dir: str, filename: str) -> dict:
    """下載圖片"""
    try:
        os.makedirs(output_dir, exist_ok=True)

        # 清理檔名
        safe_filename = "".join(c for c in filename if c.isalnum() or c in (' ', '-', '_', '！', '？'))

        # 取得副檔名
        ext = os.path.splitext(url)[1].split('?')[0]
        if not ext:
            ext = '.jpg'

        output_path = os.path.join(output_dir, f"{safe_filename}{ext}")

        # 下載圖片
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        with open(output_path, 'wb') as f:
            f.write(response.content)

        return {
            "success": True,
            "filename": safe_filename,
            "url": url,
            "path": output_path,
            "size": len(response.content)
        }

    except Exception as e:
        return {
            "success": False,
            "filename": filename,
            "url": url,
            "error": str(e)
        }


async def batch_download_videos(videos: List[dict], output_dir: str, format: str = "mp4"):
    """批次下載影片"""
    print(f"\n開始下載 {len(videos)} 個影片...")
    print(f"輸出目錄: {os.path.abspath(output_dir)}")
    print(f"格式: {format}")
    print("=" * 80)

    results = []
    for idx, video in enumerate(videos, 1):
        name = video.get('name', f'video_{idx}')
        url = video.get('url', '')

        if not url:
            print(f"[{idx}/{len(videos)}] 跳過 (無 URL): {name}")
            continue

        print(f"\n[{idx}/{len(videos)}] 下載中: {name}")
        print(f"  URL: {url[:80]}...")

        result = await download_video_ytdlp(url, output_dir, name, format)
        results.append(result)

        if result.get("success"):
            print(f"  ✓ 成功")
        else:
            print(f"  ✗ 失敗: {result.get('error', '未知錯誤')}")

    return results


def batch_download_images(videos: List[dict], output_dir: str):
    """批次下載圖片"""
    print(f"\n開始下載 {len(videos)} 張圖片...")
    print(f"輸出目錄: {os.path.abspath(output_dir)}")
    print("=" * 80)

    results = []
    for idx, video in enumerate(videos, 1):
        name = video.get('name', f'image_{idx}')
        url = video.get('imgurl', '')

        if not url:
            print(f"[{idx}/{len(videos)}] 跳過 (無圖片 URL): {name}")
            continue

        print(f"\n[{idx}/{len(videos)}] 下載中: {name}")
        print(f"  URL: {url[:80]}...")

        result = download_image(url, output_dir, name)
        results.append(result)

        if result.get("success"):
            size_kb = result.get('size', 0) / 1024
            print(f"  ✓ 成功 ({size_kb:.1f} KB)")
        else:
            print(f"  ✗ 失敗: {result.get('error', '未知錯誤')}")

    return results


def print_summary(video_results: List[dict], image_results: List[dict]):
    """輸出下載總結"""
    print("\n" + "=" * 80)
    print("下載總結")
    print("=" * 80)

    if video_results:
        video_success = sum(1 for r in video_results if r.get("success"))
        video_failed = len(video_results) - video_success
        print(f"\n影片:")
        print(f"  總計: {len(video_results)}")
        print(f"  成功: {video_success}")
        print(f"  失敗: {video_failed}")

        if video_failed > 0:
            print("\n  失敗的影片:")
            for r in video_results:
                if not r.get("success"):
                    print(f"    - {r.get('filename')}: {r.get('error', '未知錯誤')}")

    if image_results:
        image_success = sum(1 for r in image_results if r.get("success"))
        image_failed = len(image_results) - image_success
        print(f"\n圖片:")
        print(f"  總計: {len(image_results)}")
        print(f"  成功: {image_success}")
        print(f"  失敗: {image_failed}")

        if image_failed > 0:
            print("\n  失敗的圖片:")
            for r in image_results:
                if not r.get("success"):
                    print(f"    - {r.get('filename')}: {r.get('error', '未知錯誤')}")

    print("=" * 80)


async def main():
    parser = argparse.ArgumentParser(
        description="批次下載 JSON 中的影片和圖片",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 下載所有影片 (MP4 格式)
  %(prog)s data.json --type video --format mp4

  # 下載所有圖片
  %(prog)s data.json --type image

  # 同時下載影片和圖片
  %(prog)s data.json --type all --format mp4

  # 指定輸出目錄
  %(prog)s data.json --type all --video-dir ./videos --image-dir ./images
        """
    )

    parser.add_argument(
        "json_file",
        help="JSON 資料檔案路徑"
    )

    parser.add_argument(
        "--type",
        choices=["video", "image", "all"],
        default="all",
        help="下載類型 (video=僅影片, image=僅圖片, all=全部)"
    )

    parser.add_argument(
        "--format",
        choices=["mp3", "mp4", "webm", "best"],
        default="mp4",
        help="影片格式 (預設: mp4)"
    )

    parser.add_argument(
        "--video-dir",
        default="./downloads/videos",
        help="影片輸出目錄 (預設: ./downloads/videos)"
    )

    parser.add_argument(
        "--image-dir",
        default="./downloads/images",
        help="圖片輸出目錄 (預設: ./downloads/images)"
    )

    args = parser.parse_args()

    # 載入資料
    videos = load_json_data(args.json_file)

    if not videos:
        print("錯誤: JSON 檔案中沒有找到影片資料")
        sys.exit(1)

    print(f"從 {args.json_file} 載入了 {len(videos)} 個項目")

    # 執行下載
    video_results = []
    image_results = []

    if args.type in ["video", "all"]:
        video_results = await batch_download_videos(videos, args.video_dir, args.format)

    if args.type in ["image", "all"]:
        image_results = batch_download_images(videos, args.image_dir)

    # 輸出總結
    print_summary(video_results, image_results)

    # 設定結束代碼
    total_failed = sum(1 for r in video_results + image_results if not r.get("success"))
    sys.exit(0 if total_failed == 0 else 1)


if __name__ == "__main__":
    asyncio.run(main())
