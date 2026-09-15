"""
檔名清洗工具
用於處理不合法的檔案名稱字元，確保跨平台相容性
"""

import re
import unicodedata
from pathlib import Path

# 與半形空格在畫面上無法區分的空白字元，留在檔名裡會讓使用者照著螢幕打出來的路徑找不到檔案
LOOKALIKE_SPACES = "               "
# 完全不可見、複製貼上時會無聲帶入的零寬字元
INVISIBLE_CHARS = "​‌‍‎‏⁠﻿"

_LOOKALIKE_SPACE_RE = re.compile(f"[{LOOKALIKE_SPACES}]")
_INVISIBLE_RE = re.compile(f"[{INVISIBLE_CHARS}]")


def normalize_unicode_filename(filename: str) -> str:
    """
    將檔名中不可見或與半形空格難以區分的 Unicode 字元正規化

    處理項目：
    - 各式不可見空白（NBSP、窄空格、數字空格等）轉為半形空格
    - 零寬字元與 BOM 直接移除
    - 統一為 NFC 組合形式（macOS 可能產生 NFD）
    - 合併連續空格
    """
    cleaned = _LOOKALIKE_SPACE_RE.sub(" ", filename)
    cleaned = _INVISIBLE_RE.sub("", cleaned)
    cleaned = unicodedata.normalize("NFC", cleaned)
    cleaned = re.sub(r" {2,}", " ", cleaned)
    return cleaned


def resolve_existing_path(path: str) -> str | None:
    """
    找出實際存在於磁碟上的路徑，容忍 Unicode 正規化差異

    使用者或上游工具給的路徑可能是「看起來一樣但編碼不同」的版本
    （例：把檔名裡的 NBSP 打成半形空格、NFC/NFD 混用），
    直接用 os.path.exists 會誤判為檔案不存在。

    Returns:
        磁碟上真實的路徑字串；找不到時回傳 None
    """
    candidate = Path(path)
    if candidate.exists():
        return path

    for form in ("NFC", "NFD"):
        variant = unicodedata.normalize(form, path)
        if Path(variant).exists():
            return variant

    parent = candidate.parent
    if not parent.is_dir():
        return None

    target = normalize_unicode_filename(candidate.name)
    for entry in parent.iterdir():
        if normalize_unicode_filename(entry.name) == target:
            return str(entry)

    return None


def sanitize_filename(filename: str, replacement: str = "_") -> str:
    """
    清洗檔案名稱，移除或替換不合法字元

    Args:
        filename: 原始檔案名稱
        replacement: 用於替換不合法字元的字串（預設為底線）

    Returns:
        清洗後的合法檔案名稱

    移除的字元包括：
    - Windows/macOS/Linux 不允許的字元: \\ / : * ? " < > |
    - 控制字元 (ASCII 0-31)
    - 不可見空白與零寬字元
    - 前後空白
    """
    cleaned = normalize_unicode_filename(filename)

    # 移除或替換不合法字元
    # Windows: \ / : * ? " < > |
    # macOS: : (但 Finder 會顯示為 /)
    # Linux: /
    illegal_chars = r'[\\/:*?"<>|]'
    cleaned = re.sub(illegal_chars, replacement, cleaned)

    # 移除控制字元 (ASCII 0-31)
    cleaned = re.sub(r'[\x00-\x1f]', '', cleaned)

    # 移除前後空白
    cleaned = cleaned.strip()

    # 如果檔名變成空字串，使用預設值
    if not cleaned:
        cleaned = "untitled"

    # 限制檔名長度（避免過長，一般建議 < 255 字元）
    max_length = 200
    if len(cleaned) > max_length:
        cleaned = cleaned[:max_length].rstrip()

    return cleaned


def sanitize_path(path: str) -> str:
    """
    清洗完整路徑，僅處理檔案名稱部分

    Args:
        path: 完整路徑（可能包含目錄和檔名）

    Returns:
        清洗後的路徑
    """
    import os

    directory = os.path.dirname(path)
    filename = os.path.basename(path)

    # 分離檔名和副檔名
    name, ext = os.path.splitext(filename)

    # 清洗檔名部分
    clean_name = sanitize_filename(name)

    # 重新組合
    clean_filename = f"{clean_name}{ext}"

    if directory:
        return os.path.join(directory, clean_filename)
    else:
        return clean_filename