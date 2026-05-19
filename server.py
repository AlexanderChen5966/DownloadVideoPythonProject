#!/usr/bin/env python3
"""
多媒體下載與轉檔 MCP 伺服器
提供 YouTube 下載、圖片下載與轉檔、格式轉換和應用程式啟動功能
"""

import os
import subprocess
import time
from pathlib import Path
from typing import Literal

import requests
from PIL import Image
from fastmcp import FastMCP

# 導入工具模組
from tools.podcast_downloader import download_podcast
from tools.hls_downloader import download_hls
from utils.audio_downloader import download_audio_direct

# 導入白名單驗證器
from utils.whitelist_validator import get_validator

# 導入路徑偵測工具
from utils.path_resolver import find_ytdlp, find_node

# 初始化 FastMCP 伺服器
mcp = FastMCP("media-downloader")


@mcp.tool()
async def download_media(
    urls: list[str],
    output_dir: str = "./downloads",
    format: Literal["audio", "video", "best", "mp4", "mp3", "webm"] = "audio"
) -> dict:
    """
    使用 yt-dlp 下載 YouTube 影片或音檔，支援批量下載多個 URL

    Args:
        urls: 要下載的媒體 URL 列表（支援 YouTube、Podcast 等）
        output_dir: 下載檔案的輸出目錄路徑
        format: 下載格式
            - 'audio': 僅音檔（自動選擇最佳音頻格式）
            - 'video': 影片（自動選擇最佳視頻格式）
            - 'best': 最佳品質
            - 'mp4': MP4 視頻格式
            - 'mp3': MP3 音頻格式
            - 'webm': WebM 視頻格式

    Returns:
        包含下載結果的字典，含成功/失敗數量、檔案列表和錯誤資訊
    """
    # 確保輸出目錄存在
    os.makedirs(output_dir, exist_ok=True)

    saved_files = []
    errors = []

    # 取得白名單驗證器
    validator = get_validator()

    for url in urls:
        # 白名單檢查
        is_allowed, message = validator.validate(url)
        if not is_allowed:
            errors.append({
                "url": url,
                "error": "白名單驗證失敗",
                "message": message
            })
            continue

        try:
            # 建立 yt-dlp 指令（動態偵測路徑）
            yt_dlp_path = find_ytdlp()
            node_path = find_node()
            cmd = [
                yt_dlp_path,
                "--remote-components", "ejs:github",
                "-o", f"{output_dir}/%(title)s.%(ext)s"
            ]
            if node_path:
                cmd[1:1] = ["--js-runtimes", f"node:{node_path}"]

            if format == "audio":
                cmd.extend(["--extract-audio", "--audio-format", "best", "--audio-quality", "0"])
            elif format == "mp3":
                cmd.extend(["--extract-audio", "--audio-format", "mp3", "--audio-quality", "0"])
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

            # 取得下載的檔案資訊
            saved_files.append({
                "url": url,
                "status": "success",
                "output": result.stdout
            })

        except subprocess.CalledProcessError as e:
            errors.append({
                "url": url,
                "error": str(e),
                "stderr": e.stderr
            })
        except Exception as e:
            errors.append({
                "url": url,
                "error": str(e)
            })

    return {
        "success": len(saved_files),
        "failed": len(errors),
        "saved_files": saved_files,
        "errors": errors,
        "output_dir": output_dir
    }


@mcp.tool()
async def convert_to_mp3(
    input_file: str,
    output_file: str = None,
    quality: int = 2
) -> dict:
    """
    使用 FFmpeg 將音視頻檔案轉換為 MP3 格式

    Args:
        input_file: 要轉換的輸入檔案路徑（支援 mp4, wav, m4a, webm 等）
        output_file: 輸出的 MP3 檔案路徑（選填，預設為輸入檔名改 .mp3）
        quality: 音質等級 0-9，0 最高品質，9 最低品質

    Returns:
        轉換結果字典，包含成功狀態、檔案路徑和檔案大小
    """
    # 檢查輸入檔案是否存在
    if not os.path.exists(input_file):
        return {"success": False, "error": f"輸入檔案不存在: {input_file}"}

    # 如果沒有指定輸出檔案，自動生成
    if output_file is None:
        input_path = Path(input_file)
        output_file = str(input_path.with_suffix('.mp3'))

    # 如果輸入已經是 MP3，可以選擇跳過或重新編碼
    if input_file.lower().endswith('.mp3') and input_file == output_file:
        return {
            "success": True,
            "message": "檔案已經是 MP3 格式",
            "input_file": input_file,
            "output_file": output_file
        }

    try:
        # 建立 ffmpeg 指令
        cmd = [
            "ffmpeg",
            "-i", input_file,
            "-vn",  # 不處理視訊
            "-codec:a", "libmp3lame",
            "-qscale:a", str(quality),
            "-y",  # 覆蓋現有檔案
            output_file
        ]

        # 執行轉換
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )

        return {
            "success": True,
            "input_file": input_file,
            "output_file": output_file,
            "quality": quality,
            "file_size": os.path.getsize(output_file)
        }

    except subprocess.CalledProcessError as e:
        return {
            "success": False,
            "error": str(e),
            "stderr": e.stderr
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@mcp.tool()
async def download_and_convert_image(url: str, filename: str = None) -> dict:
    """
    依據網址下載圖片並轉換成 JPG 格式，儲存至 images 目錄

    Args:
        url: 圖片的 HTTP/HTTPS 網址
        filename: 自訂輸出檔名（不含副檔名，選填）

    Returns:
        下載結果字典，包含儲存路徑、原始格式、檔案大小和尺寸
    """
    try:
        # 1. 檢查 URL 是否為 HTTP/HTTPS
        if not url.startswith(('http://', 'https://')):
            return {
                "success": False,
                "error": "URL 必須是 HTTP 或 HTTPS 協議"
            }

        # 2. 白名單檢查
        validator = get_validator()
        is_allowed, message = validator.validate(url)
        if not is_allowed:
            return {
                "success": False,
                "error": "白名單驗證失敗",
                "message": message
            }

        # 3. 下載圖片 headers 檢查 Content-Type
        response = requests.head(url, timeout=10, allow_redirects=True)
        content_type = response.headers.get('Content-Type', '')

        # 3. 檢查 Content-Type 是否為 image/*
        if not content_type.startswith('image/'):
            return {
                "success": False,
                "error": f"URL 不是圖片檔案，Content-Type: {content_type}"
            }

        # 記錄原始格式
        original_format = content_type.split('/')[-1].split(';')[0]

        # 4. 下載圖片內容
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        # 5. 使用 Pillow 開啟圖片
        from io import BytesIO
        image_data = BytesIO(response.content)
        img = Image.open(image_data)

        # 6. 轉換為 RGB（處理 RGBA、灰階等格式）
        if img.mode != 'RGB':
            img = img.convert('RGB')

        # 7. 生成檔名
        if filename is None:
            # 使用 timestamp 自動產生檔名
            timestamp = int(time.time() * 1000)
            filename = f"image_{timestamp}"

        # 8. 確保 images 目錄存在並儲存
        project_root = os.path.dirname(os.path.abspath(__file__))
        images_dir = os.path.join(project_root, "images")
        os.makedirs(images_dir, exist_ok=True)

        output_path = os.path.join(images_dir, f"{filename}.jpg")

        # 儲存為 JPG
        img.save(output_path, 'JPEG', quality=95)

        # 9. 回傳結果
        return {
            "success": True,
            "saved_path": output_path,
            "original_format": original_format,
            "file_size": os.path.getsize(output_path),
            "dimensions": f"{img.width}x{img.height}"
        }

    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "error": f"下載失敗: {str(e)}"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"處理圖片時發生錯誤: {str(e)}"
        }


@mcp.tool()
async def podcast_downloader(
    url: str,
    target_dir: str = "./downloads",
    episode_index: int = 0
) -> dict:
    """
    下載 Podcast 音檔（支援 RSS Feed 或 MP3 直接連結）

    Args:
        url: Podcast RSS Feed URL 或 MP3 直接連結
        target_dir: 下載後的存放資料夾路徑
        episode_index: 若來源為 RSS，指定要下載第幾集（0 = 最新）

    Returns:
        下載結果字典
    """
    return await download_podcast(url, target_dir, episode_index)


@mcp.tool()
async def download_hls_tool(
    m3u8_url: str,
    output_path: str,
    threads: int = 8,
    select_highest_quality: bool = True
) -> dict:
    """
    下載 HLS (.m3u8) 串流視頻並轉換為 MP4 格式，支援自動選擇最高畫質、並行下載、錯誤重試

    Args:
        m3u8_url: HLS m3u8 playlist URL
        output_path: 輸出 MP4 檔案路徑
        threads: 並行下載線程數（預設 8）
        select_highest_quality: 是否自動選擇最高畫質（預設 true）

    Returns:
        下載結果字典
    """
    return await download_hls(m3u8_url, output_path, threads, select_highest_quality)


@mcp.tool()
async def whitelist_manage(
    action: Literal["list", "add", "remove", "enable", "disable"],
    rule: str | None = None
) -> dict:
    """
    管理網路白名單（查詢、新增、移除規則，啟用/停用）

    Args:
        action: 操作類型
            - 'list': 列出所有規則和狀態
            - 'add': 新增規則（需提供 rule），支援完整網域、萬用字元、正則
            - 'remove': 移除規則（需提供 rule）
            - 'enable': 啟用白名單
            - 'disable': 停用白名單
        rule: 白名單規則（action 為 add/remove 時必填）
              範例：'example.com', '*.example.com', '^https?://.*\\.example\\.com/.*'
    """
    try:
        validator = get_validator()

        if action == "list":
            rules = validator.list_rules()
            return {
                "success": True,
                "enabled": validator.enabled,
                "total_rules": len(rules),
                "rules": rules
            }

        if action in ("add", "remove") and not rule:
            return {
                "success": False,
                "error": f"action='{action}' 時必須提供 rule 參數"
            }

        if action == "add":
            success, message = validator.add_rule(rule)
            return {"success": success, "message": message, "rule": rule}

        if action == "remove":
            success, message = validator.remove_rule(rule)
            return {"success": success, "message": message, "rule": rule}

        if action == "enable":
            success, message = validator.set_enabled(True)
            return {"success": success, "message": message, "enabled": True}

        if action == "disable":
            success, message = validator.set_enabled(False)
            return {"success": success, "message": message, "enabled": False}

        return {"success": False, "error": f"未知的 action: {action}"}

    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool()
async def direct_download_audio(
    url: str,
    output_dir: str = "./downloads",
    filename: str = None
) -> dict:
    """
    直接下載音檔 URL（MP3、M4A、WAV 等），使用純 HTTP 下載，不依賴 yt-dlp。適用於直接音檔連結，不適用於 YouTube 等需要解析的平台。

    Args:
        url: 音檔的直接 URL（必須是可直接下載的音檔連結）
        output_dir: 下載檔案的輸出目錄路徑
        filename: 自訂檔名（不含副檔名，選填）

    Returns:
        下載結果字典
    """
    return await download_audio_direct(
        url=url,
        output_dir=output_dir,
        filename=filename,
        skip_whitelist=False  # MCP 工具永遠使用白名單
    )


if __name__ == "__main__":
    mcp.run()