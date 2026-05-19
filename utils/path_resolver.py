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
