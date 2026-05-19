📄 SPEC：多媒體下載與轉檔 AI Agent（Claude + MCP）
🎯 專案目標
建立一個可由 Claude AI Agent 透過 MCP（Model Context Protocol） 控制的自動化任務系統，具備以下能力：
批量下載 YouTube 影片 / Podcast 音檔 / 任意網址多媒體
自動辨識格式，若不是 MP3 → 轉成 MP3
支援影片轉音檔 (mp4 → mp3)
支援音檔轉音檔 (wav → mp3, m4a → mp3 …)
使用者可以一次給多個網址
AI Agent 可以呼叫本地工具完成：
下載（youtube-dl / yt-dlp）
轉檔（ffmpeg）
開啟資料夾或播放器（open / explorer）
所有功能皆由 MCP Tool 暴露 API 給 Claude Agent 使用。
🔧 系統架構
使用者 → Claude (AI Agent) → MCP Tools (你的本地工具)
                     ↳ download_tool        # yt-dlp 下載
                     ↳ convert_tool         # ffmpeg 轉檔
                     ↳ file_manager_tool    # 建立資料夾、列出檔案
                     ↳ app_launcher_tool    # 開啟音樂播放器/資料夾
📦 MCP Tools 規格
① download_tool（下載多媒體）
功能：
使用 yt-dlp 下載影片或音檔
輸入參數：
{
  "urls": ["https://youtube.com/xxx", "https://..."],
  "output_dir": "./downloads"
}
行為：
支援多個網址
自動下載最高可用音質
回傳下載後的檔案路徑
Python 範例（MCP 伺服器實作）
import subprocess
from mcp import tool

@tool
def download_media(urls: list[str], output_dir: str) -> list[str]:
    saved_files = []
    for url in urls:
        cmd = [
            "yt-dlp",
            "-o", f"{output_dir}/%(title)s.%(ext)s",
            "--extract-audio",
            "--audio-format", "best",
            url
        ]
        subprocess.run(cmd, check=True)
    return saved_files
② convert_tool（轉檔 MP3）
功能：
若來源不是 mp3 → 強制轉 mp3
mp4 → mp3
wav → mp3
m4a → mp3
輸入參數：
{
  "input_file": "xxx.mp4",
  "output_file": "xxx.mp3"
}
Python 範例（FFmpeg）
import subprocess
from mcp import tool

@tool
def convert_to_mp3(input_file: str, output_file: str) -> str:
    cmd = [
        "ffmpeg",
        "-i", input_file,
        "-vn",
        "-codec:a", "libmp3lame",
        "-qscale:a", "2",
        output_file
    ]
    subprocess.run(cmd, check=True)
    return output_file
③ file_manager_tool（檔案管理）
確保下載路徑存在
列出資料夾中的檔案
import os
from mcp import tool

@tool
def ensure_dir(path: str) -> bool:
    os.makedirs(path, exist_ok=True)
    return True

@tool
def list_files(path: str) -> list[str]:
    return os.listdir(path)
④ app_launcher_tool（開啟桌面 App）
macOS：open
Windows：start
Linux：xdg-open
import subprocess
import platform
from mcp import tool

@tool
def open_file(path: str):
    system = platform.system()

    if system == "Darwin":
        subprocess.run(["open", path])
    elif system == "Windows":
        subprocess.run(["start", path], shell=True)
    else:
        subprocess.run(["xdg-open", path])

    return True
