"""
EBU R128 響度正規化（兩趟式 loudnorm）

第一趟只量測整檔響度，第二趟帶著量測值套用。
單趟 loudnorm 是為串流設計的動態模式，無法預看全檔，成品響度會飄、
與目標值可能差數 dB，因此不適合用於離線轉檔。
"""

import json
import subprocess

# EBU R128 廣播標準。改這裡即可調整全專案的正規化目標：
# -23 LUFS 為廣播標準；Podcast / 串流平台慣用 -16（Apple）或 -14（Spotify）
TARGET_I = -23.0    # 整體響度 (LUFS)
TARGET_LRA = 7.0    # 響度範圍 (LU)
TARGET_TP = -2.0    # 真實峰值上限 (dBTP)

# loudnorm 內部以 192kHz 運算，輸出取樣率會被改寫成 192000，
# 而 libmp3lame 最高只支援 48kHz，故第二趟必須明確指定取樣率
OUTPUT_SAMPLE_RATE = 44100

_MEASURED_KEYS = ("input_i", "input_lra", "input_tp", "input_thresh", "target_offset")


class LoudnormError(Exception):
    """量測失敗；呼叫端應回報錯誤，不可默默產出未正規化的檔案"""


def _filter_arg(**params) -> str:
    body = ":".join(f"{k}={v}" for k, v in params.items())
    return f"loudnorm={body}"


def measure_loudness(input_file: str) -> dict:
    """
    第一趟：只量測不編碼

    Returns:
        loudnorm 的量測值 dict（input_i / input_lra / input_tp / input_thresh / target_offset）

    Raises:
        LoudnormError: ffmpeg 執行失敗、輸出無法解析，或音訊為靜音
    """
    cmd = [
        "ffmpeg", "-i", input_file,
        "-af", _filter_arg(I=TARGET_I, LRA=TARGET_LRA, TP=TARGET_TP, print_format="json"),
        "-f", "null", "-",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise LoudnormError(f"響度量測失敗: {result.stderr.strip()[-500:]}")

    # loudnorm 的 JSON 區塊印在 stderr 最末，且內部沒有巢狀大括號
    stderr = result.stderr
    start, end = stderr.rfind("{"), stderr.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise LoudnormError("找不到 loudnorm 量測結果，請確認 FFmpeg 版本支援 print_format=json")

    try:
        measured = json.loads(stderr[start:end + 1])
    except json.JSONDecodeError as e:
        raise LoudnormError(f"無法解析響度量測結果: {e}")

    missing = [k for k in _MEASURED_KEYS if k not in measured]
    if missing:
        raise LoudnormError(f"響度量測結果缺少欄位: {', '.join(missing)}")

    # 全靜音或近乎無聲的音軌量不到響度，強行套用會得到無意義的增益
    if any(str(measured[k]).lstrip("-").lower() in ("inf", "nan") for k in _MEASURED_KEYS):
        raise LoudnormError("音訊為靜音或響度過低，無法正規化")

    return measured


def build_loudnorm_filter(measured: dict) -> str:
    """
    第二趟：把量測值組成 loudnorm 濾鏡參數

    linear=true 要求以線性增益達成目標（音質較佳）；
    若目標無法在不破壞動態的前提下達成，FFmpeg 會自動退回動態模式。
    """
    return _filter_arg(
        I=TARGET_I,
        LRA=TARGET_LRA,
        TP=TARGET_TP,
        measured_I=measured["input_i"],
        measured_LRA=measured["input_lra"],
        measured_TP=measured["input_tp"],
        measured_thresh=measured["input_thresh"],
        offset=measured["target_offset"],
        linear="true",
    )
