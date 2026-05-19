#!/usr/bin/env python3
"""
多媒體下載與轉檔 MCP 伺服器
提供 YouTube 下載、圖片下載與轉檔、格式轉換和應用程式啟動功能
"""

import json
import os
import subprocess
import time
from pathlib import Path
from typing import Literal

import requests
from PIL import Image
from fastmcp import FastMCP, Context

# 導入工具模組
from tools.podcast_downloader import download_podcast
from tools.hls_downloader import download_hls
from utils.audio_downloader import download_audio_direct

# 導入白名單驗證器
from utils.whitelist_validator import get_validator

# 導入路徑偵測工具
from utils.path_resolver import find_ytdlp, find_node

# 導入統一回傳結構
from utils.response import success_response, error_response

# 導入下載歷史紀錄
from utils.download_history import is_downloaded, add_record

# 初始化 FastMCP 伺服器
mcp = FastMCP("media-downloader")


# ── MCP Resources ────────────────────────────────────────────────────────────

@mcp.resource("config://whitelist")
async def whitelist_resource() -> str:
    """目前的白名單規則和啟用狀態"""
    validator = get_validator()
    rules = validator.list_rules()
    return json.dumps({
        "enabled": validator.enabled,
        "total_rules": len(rules),
        "rules": rules
    }, ensure_ascii=False, indent=2)


@mcp.resource("status://ytdlp-version")
async def ytdlp_version_resource() -> str:
    """yt-dlp 的目前版本與路徑"""
    from utils.path_resolver import get_ytdlp_version
    return json.dumps(get_ytdlp_version(), ensure_ascii=False, indent=2)


@mcp.resource("data://download-history")
async def download_history_resource() -> str:
    """最近 20 筆下載歷史紀錄"""
    from utils.download_history import load_history
    history = load_history()
    recent = history["downloads"][-20:]
    return json.dumps(recent, ensure_ascii=False, indent=2)


# ── MCP Prompts ───────────────────────────────────────────────────────────────

@mcp.prompt()
def batch_download_youtube() -> str:
    """批量下載 YouTube 影片的最佳操作流程"""
    return """
操作步驟：
1. 先用 whitelist_manage(action="list") 確認 youtube.com 在白名單中
2. 使用 download_media(urls=[...], format="audio") 批量下載
3. 若下載失敗且 error_code 為 YTDLP_FAILED，可能需要更新 yt-dlp（重啟 Claude Desktop 即可自動更新）
4. 下載完成後告知使用者檔案位置和大小
"""


@mcp.prompt()
def download_with_subtitles() -> str:
    """下載影片同時取得字幕的操作流程"""
    return """
操作步驟：
1. 使用 query_formats(url=...) 查詢可用格式和字幕語言
2. 確認 subtitle_languages 或 auto_subtitle_languages 中有 zh-TW 或 en
3. 使用 download_media(urls=[...], format="mp4", subtitles=True, sub_lang="zh-TW,en")
4. 字幕檔（.srt）會自動儲存在影片同目錄下
"""


@mcp.prompt()
def download_podcast_series() -> str:
    """下載 Podcast RSS Feed 整季的操作流程"""
    return """
操作步驟：
1. 先用 whitelist_manage(action="list") 確認 Podcast 網域在白名單中
   若不在，使用 whitelist_manage(action="add", rule="*.podcast-domain.com") 加入
2. 使用 podcast_downloader(url=RSS_URL, episode_index=0) 下載最新一集確認格式正確
3. 批量下載時，依序指定 episode_index=0,1,2,... 逐集下載
4. 若 URL 為直接 MP3 連結（非 RSS），改用 direct_download_audio(url=...)
"""


@mcp.prompt()
def download_hls_stream() -> str:
    """下載 HLS (.m3u8) 串流視頻的操作流程"""
    return """
操作步驟：
1. 確認手上有 .m3u8 的 URL（通常從瀏覽器開發者工具的 Network 面板取得）
2. 使用 download_hls_tool(m3u8_url=..., output_path="./downloads/video.mp4")
3. 大型影片建議加上 threads=32 加速下載
4. 注意：不支援加密的 HLS 流（AES-128 加密）
5. 下載完成後確認 MP4 可正常播放
"""


@mcp.prompt()
def manage_whitelist() -> str:
    """白名單完整設定流程"""
    return """
白名單管理操作：

查看目前規則：
  whitelist_manage(action="list")

新增網域（三種格式）：
  完整網域：whitelist_manage(action="add", rule="example.com")
  子網域：  whitelist_manage(action="add", rule="*.example.com")
  正則：    whitelist_manage(action="add", rule="^https?://.*\\.example\\.com/.*")

移除規則：
  whitelist_manage(action="remove", rule="example.com")

暫時停用白名單（測試用，不建議長期）：
  whitelist_manage(action="disable")

重新啟用：
  whitelist_manage(action="enable")

常用白名單規則建議：
  youtube.com, *.youtube.com, youtu.be — YouTube
  *.buzzsprout.com, *.libsyn.com       — Podcast 平台
  *.googlevideo.com                    — YouTube CDN（下載需要）
"""


@mcp.prompt()
def check_mcp_health() -> str:
    """診斷 MCP 狀態的操作流程"""
    return """
MCP 狀態診斷步驟：

1. 讀取 yt-dlp 版本：
   讀取 Resource status://ytdlp-version
   若版本超過 30 天未更新，建議重啟 Claude Desktop（start_mcp.sh 會自動更新）

2. 確認白名單狀態：
   讀取 Resource config://whitelist
   確認 enabled=true 且目標網域在規則中

3. 查看最近下載紀錄：
   讀取 Resource data://download-history
   確認最近下載是否成功

4. 若 yt-dlp 下載持續失敗：
   error_code=YTDLP_FAILED    → 重啟 Claude Desktop 強制更新
   error_code=NODE_NOT_FOUND  → 需安裝 Node.js（brew install node）
   error_code=WHITELIST_DENIED → 執行 manage_whitelist 流程
"""


@mcp.tool()
async def download_media(
    urls: list[str],
    output_dir: str = "./downloads",
    format: Literal["audio", "video", "best", "mp4", "mp3", "webm"] = "audio",
    subtitles: bool = False,
    sub_lang: str = "zh-TW,en",
    ctx: Context = None
) -> dict:
    """
    使用 yt-dlp 下載 YouTube 影片或音檔，支援批量下載多個 URL

    Args:
        urls: 要下載的媒體 URL 列表
              支援單一影片、播放清單（playlist）、頻道 URL
        output_dir: 下載檔案的輸出目錄路徑
        format: 下載格式
            - 'audio': 僅音檔（自動選擇最佳音頻格式）
            - 'video': 影片（自動選擇最佳視頻格式）
            - 'best': 最佳品質
            - 'mp4': MP4 視頻格式
            - 'mp3': MP3 音頻格式
            - 'webm': WebM 視頻格式
        subtitles: 是否同時下載字幕（預設 False）
        sub_lang: 字幕語言代碼，逗號分隔（預設 "zh-TW,en"）

    Returns:
        包含下載結果的字典，含成功/失敗/跳過數量、檔案列表和錯誤資訊
    """
    os.makedirs(output_dir, exist_ok=True)

    saved_files = []
    skipped_files = []
    errors = []
    total = len(urls)

    validator = get_validator()

    for i, url in enumerate(urls):
        if ctx:
            await ctx.report_progress(
                progress=i,
                total=total,
                message=f"下載中 ({i + 1}/{total}): {url[:60]}"
            )

        # 白名單檢查
        is_allowed, message = validator.validate(url)
        if not is_allowed:
            errors.append({"url": url, "error_code": "WHITELIST_DENIED", "error": message})
            continue

        # 歷史紀錄查詢：檔案存在則跳過
        existing = is_downloaded(url)
        if existing:
            skipped_files.append({
                "url": url,
                "status": "skipped",
                "reason": "already_downloaded",
                "file_path": existing["file_path"]
            })
            continue

        try:
            try:
                yt_dlp_path = find_ytdlp()
            except FileNotFoundError as e:
                errors.append({"url": url, "error_code": "YTDLP_NOT_FOUND", "error": str(e)})
                continue

            node_path = find_node()
            cmd = [
                yt_dlp_path,
                "--remote-components", "ejs:github",
                "--yes-playlist",
                "-o", f"{output_dir}/%(title)s.%(ext)s",
                "--print", "after_move:filepath"
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

            if subtitles:
                cmd.extend([
                    "--write-subs",
                    "--write-auto-subs",
                    "--sub-langs", sub_lang,
                    "--sub-format", "srt/best"
                ])

            cmd.append(url)

            result = subprocess.run(cmd, capture_output=True, text=True, check=True)

            # 從 --print after_move:filepath 取得實際儲存路徑
            file_paths = [p.strip() for p in result.stdout.strip().splitlines() if p.strip()]
            for file_path in file_paths:
                file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
                add_record(url, file_path, file_size, success=True)

            saved_files.append({
                "url": url,
                "status": "success",
                "files": file_paths
            })

        except subprocess.CalledProcessError as e:
            errors.append({"url": url, "error_code": "YTDLP_FAILED", "error": str(e), "stderr": e.stderr})
        except Exception as e:
            errors.append({"url": url, "error_code": "UNKNOWN_ERROR", "error": str(e)})

    if ctx:
        await ctx.report_progress(
            progress=total,
            total=total,
            message="全部下載完成"
        )

    return {
        "success": len(saved_files),
        "skipped": len(skipped_files),
        "failed": len(errors),
        "saved_files": saved_files,
        "skipped_files": skipped_files,
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
    if not os.path.exists(input_file):
        return error_response("FILE_NOT_FOUND", f"輸入檔案不存在: {input_file}", input_file=input_file)

    if output_file is None:
        output_file = str(Path(input_file).with_suffix('.mp3'))

    if input_file.lower().endswith('.mp3') and input_file == output_file:
        return success_response(message="檔案已經是 MP3 格式", input_file=input_file, output_file=output_file)

    try:
        cmd = [
            "ffmpeg", "-i", input_file,
            "-vn", "-codec:a", "libmp3lame",
            "-qscale:a", str(quality), "-y",
            output_file
        ]
        subprocess.run(cmd, capture_output=True, text=True, check=True)
        return success_response(
            input_file=input_file,
            output_file=output_file,
            quality=quality,
            file_size=os.path.getsize(output_file)
        )
    except subprocess.CalledProcessError as e:
        return error_response("CONVERSION_FAILED", str(e), stderr=e.stderr)
    except Exception as e:
        return error_response("UNKNOWN_ERROR", str(e))


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
        if not url.startswith(('http://', 'https://')):
            return error_response("INVALID_URL", "URL 必須是 HTTP 或 HTTPS 協議", url=url)

        validator = get_validator()
        is_allowed, message = validator.validate(url)
        if not is_allowed:
            return error_response("WHITELIST_DENIED", message, url=url)

        response = requests.head(url, timeout=10, allow_redirects=True)
        content_type = response.headers.get('Content-Type', '')
        if not content_type.startswith('image/'):
            return error_response(
                "INVALID_CONTENT_TYPE",
                f"URL 不是圖片檔案，Content-Type: {content_type}",
                url=url, content_type=content_type
            )

        original_format = content_type.split('/')[-1].split(';')[0]
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        from io import BytesIO
        img = Image.open(BytesIO(response.content))
        if img.mode != 'RGB':
            img = img.convert('RGB')

        if filename is None:
            filename = f"image_{int(time.time() * 1000)}"

        images_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "images")
        os.makedirs(images_dir, exist_ok=True)
        output_path = os.path.join(images_dir, f"{filename}.jpg")
        img.save(output_path, 'JPEG', quality=95)

        return success_response(
            saved_path=output_path,
            original_format=original_format,
            file_size=os.path.getsize(output_path),
            dimensions=f"{img.width}x{img.height}"
        )

    except requests.exceptions.RequestException as e:
        return error_response("DOWNLOAD_FAILED", f"下載失敗: {e}", url=url)
    except Exception as e:
        return error_response("UNKNOWN_ERROR", f"處理圖片時發生錯誤: {e}", url=url)


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
            return error_response("MISSING_PARAM", f"action='{action}' 時必須提供 rule 參數")

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

        return error_response("MISSING_PARAM", f"未知的 action: {action}")

    except Exception as e:
        return error_response("UNKNOWN_ERROR", str(e))


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


@mcp.tool()
async def query_formats(url: str) -> dict:
    """
    查詢 URL 可用的下載格式（影片畫質、音檔品質、字幕語言）

    Args:
        url: 媒體 URL（YouTube 等 yt-dlp 支援的平台）

    Returns:
        可用格式列表，包含解析度、字幕語言
    """
    validator = get_validator()
    is_allowed, message = validator.validate(url)
    if not is_allowed:
        return error_response("WHITELIST_DENIED", message, url=url)

    try:
        yt_dlp_path = find_ytdlp()
    except FileNotFoundError as e:
        return error_response("YTDLP_NOT_FOUND", str(e))

    try:
        result = subprocess.run(
            [yt_dlp_path, "-J", "--no-download", url],
            capture_output=True, text=True, timeout=30, check=True
        )
        info = json.loads(result.stdout)
    except subprocess.TimeoutExpired:
        return error_response("DOWNLOAD_TIMEOUT", "格式查詢逾時（超過 30 秒）", url=url)
    except subprocess.CalledProcessError as e:
        return error_response("YTDLP_FAILED", str(e), stderr=e.stderr, url=url)
    except json.JSONDecodeError as e:
        return error_response("YTDLP_FAILED", f"解析格式資訊失敗: {e}", url=url)

    formats = [
        {
            "format_id": f.get("format_id"),
            "ext": f.get("ext"),
            "resolution": f.get("resolution", "audio only"),
            "filesize": f.get("filesize"),
            "vcodec": f.get("vcodec"),
            "acodec": f.get("acodec"),
        }
        for f in info.get("formats", [])
    ]

    return success_response(
        title=info.get("title"),
        duration=info.get("duration"),
        formats=formats[-10:],
        subtitle_languages=list(info.get("subtitles", {}).keys()),
        auto_subtitle_languages=list(info.get("automatic_captions", {}).keys())[:10]
    )


if __name__ == "__main__":
    mcp.run()