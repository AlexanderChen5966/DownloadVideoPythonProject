#!/usr/bin/env python3
"""
音檔下載 CLI 工具
支援直接下載音檔 URL 或使用 yt-dlp 下載 YouTube、Apple Podcasts 等平台
"""

import sys
import os
import argparse
import asyncio
from typing import List
from urllib.parse import urlparse

# 確保可以導入專案模組
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.audio_downloader import download_audio_direct
from utils.path_resolver import find_ytdlp, find_node


def needs_ytdlp(url: str) -> bool:
    """
    判斷是否需要使用 yt-dlp 下載（而非直接 HTTP 下載）

    支援的平台：
    - YouTube
    - Apple Podcasts
    - Spotify (需要特殊處理)
    - SoundCloud
    - 其他需要網頁解析的平台

    Args:
        url: 要檢查的 URL

    Returns:
        是否需要使用 yt-dlp
    """
    # 需要 yt-dlp 的網域列表
    ytdlp_domains = [
        # YouTube
        'youtube.com',
        'www.youtube.com',
        'm.youtube.com',
        'youtu.be',
        'music.youtube.com',
        # Apple Podcasts
        'podcasts.apple.com',
        # Spotify
        'open.spotify.com',
        'spotify.com',
        # SoundCloud
        'soundcloud.com',
        'm.soundcloud.com',
        # Vimeo
        'vimeo.com',
        # Twitch
        'twitch.tv',
        'www.twitch.tv',
    ]

    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        return any(ytdlp_domain in domain for ytdlp_domain in ytdlp_domains)
    except:
        return False


async def download_with_ytdlp(url: str, output_dir: str, format: str = "mp3") -> dict:
    """
    使用 yt-dlp 下載（用於 YouTube 等）

    Args:
        url: YouTube URL
        output_dir: 輸出目錄
        format: 下載格式 (mp3, mp4, webm, audio, video, best)

    Returns:
        下載結果字典
    """
    import subprocess

    try:
        # 確保目錄存在
        os.makedirs(output_dir, exist_ok=True)

        # 建立 yt-dlp 指令（動態偵測路徑）
        yt_dlp_path = find_ytdlp()
        node_path = find_node()
        cmd = [
            yt_dlp_path,
            "-o", f"{output_dir}/%(title)s.%(ext)s"
        ]
        if node_path:
            cmd[1:1] = ["--js-runtimes", f"node:{node_path}"]

        # 根據格式添加參數
        if format == "mp3":
            cmd.extend(["--extract-audio", "--audio-format", "mp3", "--audio-quality", "0"])
        elif format == "audio":
            cmd.extend(["--extract-audio", "--audio-format", "best", "--audio-quality", "0"])
        elif format == "mp4":
            cmd.extend(["-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best", "--merge-output-format", "mp4"])
        elif format == "webm":
            cmd.extend(["-f", "bestvideo[ext=webm]+bestaudio[ext=webm]/best[ext=webm]/best", "--merge-output-format", "webm"])
        elif format == "video":
            cmd.extend(["-f", "bestvideo+bestaudio/best"])
        else:  # best
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
            "url": url,
            "method": "yt-dlp",
            "format": format,
            "output": result.stdout
        }

    except subprocess.CalledProcessError as e:
        return {
            "success": False,
            "url": url,
            "method": "yt-dlp",
            "error": str(e),
            "stderr": e.stderr
        }
    except FileNotFoundError:
        return {
            "success": False,
            "url": url,
            "method": "yt-dlp",
            "error": "找不到 yt-dlp，請先安裝：pip install yt-dlp"
        }
    except Exception as e:
        return {
            "success": False,
            "url": url,
            "method": "yt-dlp",
            "error": str(e)
        }


async def download_single_url(
    url: str,
    output_dir: str,
    filename: str = None,
    skip_whitelist: bool = False,
    force_ytdlp: bool = False,
    format: str = "mp3"
) -> dict:
    """
    下載單一 URL

    Args:
        url: 要下載的 URL
        output_dir: 輸出目錄
        filename: 自訂檔名
        skip_whitelist: 是否跳過白名單
        force_ytdlp: 是否強制使用 yt-dlp
        format: 下載格式 (mp3, mp4, webm, audio, video, best)

    Returns:
        下載結果字典
    """
    # 判斷下載方式
    if force_ytdlp or needs_ytdlp(url):
        # 使用 yt-dlp（用於 YouTube、Apple Podcasts 等需要網頁解析的平台）
        print(f"      檢測到需要 yt-dlp 的平台，使用 yt-dlp 下載（格式: {format}）...")
        return await download_with_ytdlp(url, output_dir, format)
    else:
        # 使用直接下載
        return await download_audio_direct(
            url=url,
            output_dir=output_dir,
            filename=filename,
            skip_whitelist=skip_whitelist
        )


async def download_multiple_urls(
    urls: List[str],
    output_dir: str,
    filename: str = None,
    skip_whitelist: bool = False,
    force_ytdlp: bool = False,
    format: str = "mp3"
) -> List[dict]:
    """
    批量下載多個 URL

    Args:
        urls: URL 列表
        output_dir: 輸出目錄
        filename: 自訂檔名（僅適用於單一 URL）
        skip_whitelist: 是否跳過白名單
        force_ytdlp: 是否強制使用 yt-dlp
        format: 下載格式 (mp3, mp4, webm, audio, video, best)

    Returns:
        下載結果列表
    """
    results = []

    for i, url in enumerate(urls):
        # 如果是批量下載，忽略自訂檔名
        current_filename = filename if len(urls) == 1 else None

        print(f"\n[{i+1}/{len(urls)}] 下載中: {url}")

        result = await download_single_url(
            url=url,
            output_dir=output_dir,
            filename=current_filename,
            skip_whitelist=skip_whitelist,
            force_ytdlp=force_ytdlp,
            format=format
        )

        results.append(result)

        # 顯示結果
        if result.get("success"):
            print(f"  成功 {result.get('file_name', 'OK')}")
            if result.get('file_size'):
                size_mb = result['file_size'] / (1024 * 1024)
                print(f"      檔案大小: {size_mb:.2f} MB")
            if result.get('file_path'):
                print(f"      儲存位置: {result['file_path']}")
        else:
            print(f"  失敗 {result.get('error', '未知錯誤')}")

    return results


def print_summary(results: List[dict]):
    """
    顯示下載總結

    Args:
        results: 下載結果列表
    """
    total = len(results)
    success = sum(1 for r in results if r.get("success"))
    failed = total - success

    print("\n" + "=" * 60)
    print(f"下載總結")
    print("=" * 60)
    print(f"總計: {total} 個")
    print(f"成功: {success} 個")
    print(f"失敗: {failed} 個")

    if failed > 0:
        print("\n失敗的下載:")
        for i, result in enumerate(results):
            if not result.get("success"):
                print(f"  {i+1}. {result.get('url')}")
                print(f"     錯誤: {result.get('error', '未知錯誤')}")

    print("=" * 60)


def main():
    """主程式"""
    parser = argparse.ArgumentParser(
        description="多媒體下載 CLI 工具 - 支援直接下載或使用 yt-dlp (YouTube、Apple Podcasts 等)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
範例:
  # 下載單一音檔（MP3）
  %(prog)s "https://example.com/audio.mp3"

  # 下載 YouTube 影片為 MP4 格式
  %(prog)s "https://www.youtube.com/watch?v=xxxxx" -f mp4

  # 下載 YouTube 音訊為 MP3 格式
  %(prog)s "https://www.youtube.com/watch?v=xxxxx" -f mp3

  # 下載為 WebM 格式
  %(prog)s "https://www.youtube.com/watch?v=xxxxx" -f webm

  # 下載並指定輸出目錄
  %(prog)s "https://example.com/audio.mp3" -o ./my_downloads

  # 下載並自訂檔名
  %(prog)s "https://example.com/audio.mp3" -n "my_song"

  # 批量下載多個音檔
  %(prog)s "url1" "url2" "url3" -o ./downloads

  # 下載 Apple Podcasts（自動偵測使用 yt-dlp）
  %(prog)s "https://podcasts.apple.com/podcast/xxxxx"

  # 強制使用 yt-dlp
  %(prog)s "https://example.com/video" --youtube

  # 跳過白名單驗證
  %(prog)s "https://example.com/audio.mp3" --no-whitelist
        """
    )

    parser.add_argument(
        "urls",
        nargs="+",
        help="要下載的媒體 URL（可指定多個）"
    )

    parser.add_argument(
        "-o", "--output",
        dest="output_dir",
        default="./downloads",
        help="輸出目錄（預設: ./downloads）"
    )

    parser.add_argument(
        "-n", "--name",
        dest="filename",
        help="自訂檔名（不含副檔名，僅適用於單一 URL）"
    )

    parser.add_argument(
        "-f", "--format",
        dest="format",
        default="mp3",
        choices=["mp3", "mp4", "webm", "audio", "video", "best"],
        help="下載格式（預設: mp3）。mp3/audio=音訊, mp4/webm/video=影片, best=最佳品質"
    )

    parser.add_argument(
        "--no-whitelist",
        dest="skip_whitelist",
        action="store_true",
        help="跳過白名單驗證"
    )

    parser.add_argument(
        "--youtube",
        dest="force_ytdlp",
        action="store_true",
        help="強制使用 yt-dlp（用於 YouTube 等平台）"
    )

    args = parser.parse_args()

    # 執行下載
    print(f"開始下載 {len(args.urls)} 個媒體檔案...")
    print(f"輸出目錄: {os.path.abspath(args.output_dir)}")
    print(f"下載格式: {args.format}")

    if args.skip_whitelist:
        print("注意: 已跳過白名單驗證")

    if args.force_ytdlp:
        print("使用 yt-dlp 下載")

    # 執行非同步下載
    results = asyncio.run(
        download_multiple_urls(
            urls=args.urls,
            output_dir=args.output_dir,
            filename=args.filename,
            skip_whitelist=args.skip_whitelist,
            force_ytdlp=args.force_ytdlp,
            format=args.format
        )
    )

    # 顯示總結
    print_summary(results)

    # 根據結果設定退出碼
    failed_count = sum(1 for r in results if not r.get("success"))
    sys.exit(0 if failed_count == 0 else 1)


if __name__ == "__main__":
    main()