"""
檔名清洗工具
用於處理不合法的檔案名稱字元，確保跨平台相容性
"""

import re


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
    - 前後空白
    """
    # 移除或替換不合法字元
    # Windows: \ / : * ? " < > |
    # macOS: : (但 Finder 會顯示為 /)
    # Linux: /
    illegal_chars = r'[\\/:*?"<>|]'
    cleaned = re.sub(illegal_chars, replacement, filename)

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