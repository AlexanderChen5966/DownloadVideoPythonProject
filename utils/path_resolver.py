import shutil
import subprocess
import sys
from pathlib import Path


def find_ytdlp() -> str:
    """
    動態偵測 yt-dlp 路徑
    優先順序：同 venv → 系統 PATH → 報錯
    """
    venv_path = Path(sys.executable).parent / "yt-dlp"
    if venv_path.exists():
        return str(venv_path)

    system_path = shutil.which("yt-dlp")
    if system_path:
        return system_path

    raise FileNotFoundError(
        "找不到 yt-dlp。請執行: pip install yt-dlp"
    )


def find_node() -> str | None:
    """
    偵測 Node.js 路徑（用於 YouTube n-challenge 解密）
    找不到時回傳 None，不阻斷下載
    """
    return shutil.which("node")


def get_ytdlp_version() -> dict:
    """取得 yt-dlp 版本資訊（供 P3 MCP Resource 使用）"""
    try:
        path = find_ytdlp()
        result = subprocess.run(
            [path, "--version"],
            capture_output=True, text=True, timeout=5
        )
        return {"version": result.stdout.strip(), "path": path}
    except FileNotFoundError as e:
        return {"version": "unknown", "error": str(e)}
    except Exception as e:
        return {"version": "unknown", "error": str(e)}


# YouTube player client 優先序。
# 預設的 android_vr client 取得的媒體網址會被 YouTube 擋下（HTTP 403），
# 且 ios/mweb 的高畫質 DASH 格式需要 GVS PO Token 才能下載。
# web_embedded 目前可在無 PO Token、無 cookies 的情況下取得完整格式，
# 後面兩個作為 fallback，由 yt-dlp 依序嘗試。
YOUTUBE_PLAYER_CLIENTS = "web_embedded,mweb,default"


def is_youtube_url(url: str) -> bool:
    """判斷是否為 YouTube 網址（含 youtu.be 短網址）"""
    lowered = url.lower()
    return "youtube.com" in lowered or "youtu.be" in lowered


def youtube_extractor_args(url: str) -> list[str]:
    """
    YouTube 網址回傳指定 player client 的 yt-dlp 參數，其他網站回傳空清單。
    用於繞過 android_vr client 造成的 HTTP 403 Forbidden。
    """
    if not is_youtube_url(url):
        return []
    return ["--extractor-args", f"youtube:player_client={YOUTUBE_PLAYER_CLIENTS}"]
