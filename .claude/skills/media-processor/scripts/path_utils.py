#!/usr/bin/env python3
"""
路徑解析工具
處理「看起來一樣但編碼不同」的檔名，避免誤判檔案不存在
"""

import re
import unicodedata
from pathlib import Path

# 與半形空格在畫面上無法區分的空白字元
LOOKALIKE_SPACES = "               "
# 完全不可見、複製貼上時會無聲帶入的零寬字元
INVISIBLE_CHARS = "​‌‍‎‏⁠﻿"

_LOOKALIKE_SPACE_RE = re.compile(f"[{LOOKALIKE_SPACES}]")
_INVISIBLE_RE = re.compile(f"[{INVISIBLE_CHARS}]")


def normalize_unicode_filename(filename: str) -> str:
    """將檔名中不可見或與半形空格難以區分的 Unicode 字元正規化"""
    cleaned = _LOOKALIKE_SPACE_RE.sub(" ", filename)
    cleaned = _INVISIBLE_RE.sub("", cleaned)
    cleaned = unicodedata.normalize("NFC", cleaned)
    return re.sub(r" {2,}", " ", cleaned)


def resolve_existing_path(path: str) -> str | None:
    """
    找出實際存在於磁碟上的路徑，容忍 Unicode 正規化差異

    影片標題常夾帶 NBSP（U+00A0），下載後的檔名看起來和半形空格一模一樣，
    照著螢幕打出來的路徑會對不上，直接用 exists() 會誤判為檔案不存在。

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
