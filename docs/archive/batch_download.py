#!/usr/bin/env python3
"""
批量下载 JSON 中的视频和图片
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
    """加载 JSON 数据并返回视频列表"""
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data.get('ymSubmenu', {}).get('dvd', {}).get('submenu', [])


async def download_video_ytdlp(url: str, output_dir: str, filename: str, format: str = "mp4") -> dict:
    """使用 yt-dlp 下载视频"""
    try:
        os.makedirs(output_dir, exist_ok=True)

        # 清理文件名（移除不允许的字符）
        safe_filename = "".join(c for c in filename if c.isalnum() or c in (' ', '-', '_', '！', '？'))
        output_path = os.path.join(output_dir, safe_filename)

        cmd = [
            ".venv/bin/yt-dlp",
            "-o", f"{output_path}.%(ext)s"
        ]

        # 根据格式添加参数
        if format == "mp3":
            cmd.extend(["--extract-audio", "--audio-format", "mp3", "--audio-quality", "0"])
        elif format == "mp4":
            cmd.extend(["-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best", "--merge-output-format", "mp4"])
        elif format == "webm":
            cmd.extend(["-f", "bestvideo[ext=webm]+bestaudio[ext=webm]/best[ext=webm]/best", "--merge-output-format", "webm"])
        else:
            cmd.extend(["-f", "best"])

        cmd.append(url)

        # 执行下载
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
            "error": f"下载失败: {e.stderr}"
        }
    except Exception as e:
        return {
            "success": False,
            "filename": filename,
            "url": url,
            "error": str(e)
        }


def download_image(url: str, output_dir: str, filename: str) -> dict:
    """下载图片"""
    try:
        os.makedirs(output_dir, exist_ok=True)

        # 清理文件名
        safe_filename = "".join(c for c in filename if c.isalnum() or c in (' ', '-', '_', '！', '？'))

        # 获取文件扩展名
        ext = os.path.splitext(url)[1].split('?')[0]
        if not ext:
            ext = '.jpg'

        output_path = os.path.join(output_dir, f"{safe_filename}{ext}")

        # 下载图片
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
    """批量下载视频"""
    print(f"\n开始下载 {len(videos)} 个视频...")
    print(f"输出目录: {os.path.abspath(output_dir)}")
    print(f"格式: {format}")
    print("=" * 80)

    results = []
    for idx, video in enumerate(videos, 1):
        name = video.get('name', f'video_{idx}')
        url = video.get('url', '')

        if not url:
            print(f"[{idx}/{len(videos)}] 跳过 (无 URL): {name}")
            continue

        print(f"\n[{idx}/{len(videos)}] 下载中: {name}")
        print(f"  URL: {url[:80]}...")

        result = await download_video_ytdlp(url, output_dir, name, format)
        results.append(result)

        if result.get("success"):
            print(f"  ✓ 成功")
        else:
            print(f"  ✗ 失败: {result.get('error', '未知错误')}")

    return results


def batch_download_images(videos: List[dict], output_dir: str):
    """批量下载图片"""
    print(f"\n开始下载 {len(videos)} 张图片...")
    print(f"输出目录: {os.path.abspath(output_dir)}")
    print("=" * 80)

    results = []
    for idx, video in enumerate(videos, 1):
        name = video.get('name', f'image_{idx}')
        url = video.get('imgurl', '')

        if not url:
            print(f"[{idx}/{len(videos)}] 跳过 (无图片 URL): {name}")
            continue

        print(f"\n[{idx}/{len(videos)}] 下载中: {name}")
        print(f"  URL: {url[:80]}...")

        result = download_image(url, output_dir, name)
        results.append(result)

        if result.get("success"):
            size_kb = result.get('size', 0) / 1024
            print(f"  ✓ 成功 ({size_kb:.1f} KB)")
        else:
            print(f"  ✗ 失败: {result.get('error', '未知错误')}")

    return results


def print_summary(video_results: List[dict], image_results: List[dict]):
    """打印下载总结"""
    print("\n" + "=" * 80)
    print("下载总结")
    print("=" * 80)

    if video_results:
        video_success = sum(1 for r in video_results if r.get("success"))
        video_failed = len(video_results) - video_success
        print(f"\n视频:")
        print(f"  总计: {len(video_results)}")
        print(f"  成功: {video_success}")
        print(f"  失败: {video_failed}")

        if video_failed > 0:
            print("\n  失败的视频:")
            for r in video_results:
                if not r.get("success"):
                    print(f"    - {r.get('filename')}: {r.get('error', '未知错误')}")

    if image_results:
        image_success = sum(1 for r in image_results if r.get("success"))
        image_failed = len(image_results) - image_success
        print(f"\n图片:")
        print(f"  总计: {len(image_results)}")
        print(f"  成功: {image_success}")
        print(f"  失败: {image_failed}")

        if image_failed > 0:
            print("\n  失败的图片:")
            for r in image_results:
                if not r.get("success"):
                    print(f"    - {r.get('filename')}: {r.get('error', '未知错误')}")

    print("=" * 80)


async def main():
    parser = argparse.ArgumentParser(
        description="批量下载 JSON 中的视频和图片",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 下载所有视频 (MP4 格式)
  %(prog)s data.json --type video --format mp4

  # 下载所有图片
  %(prog)s data.json --type image

  # 同时下载视频和图片
  %(prog)s data.json --type all --format mp4

  # 指定输出目录
  %(prog)s data.json --type all --video-dir ./videos --image-dir ./images
        """
    )

    parser.add_argument(
        "json_file",
        help="JSON 数据文件路径"
    )

    parser.add_argument(
        "--type",
        choices=["video", "image", "all"],
        default="all",
        help="下载类型 (video=仅视频, image=仅图片, all=全部)"
    )

    parser.add_argument(
        "--format",
        choices=["mp3", "mp4", "webm", "best"],
        default="mp4",
        help="视频格式 (默认: mp4)"
    )

    parser.add_argument(
        "--video-dir",
        default="./downloads/videos",
        help="视频输出目录 (默认: ./downloads/videos)"
    )

    parser.add_argument(
        "--image-dir",
        default="./downloads/images",
        help="图片输出目录 (默认: ./downloads/images)"
    )

    args = parser.parse_args()

    # 加载数据
    videos = load_json_data(args.json_file)

    if not videos:
        print("错误: JSON 文件中没有找到视频数据")
        sys.exit(1)

    print(f"从 {args.json_file} 加载了 {len(videos)} 个项目")

    # 执行下载
    video_results = []
    image_results = []

    if args.type in ["video", "all"]:
        video_results = await batch_download_videos(videos, args.video_dir, args.format)

    if args.type in ["image", "all"]:
        image_results = batch_download_images(videos, args.image_dir)

    # 打印总结
    print_summary(video_results, image_results)

    # 设置退出码
    total_failed = sum(1 for r in video_results + image_results if not r.get("success"))
    sys.exit(0 if total_failed == 0 else 1)


if __name__ == "__main__":
    asyncio.run(main())
