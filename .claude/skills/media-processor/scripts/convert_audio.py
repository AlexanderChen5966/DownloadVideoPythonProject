#!/usr/bin/env python3
"""
音訊格式轉換工具
取代 MCP 的 convert_to_mp3 功能
"""

import subprocess
import sys
from pathlib import Path


def convert_to_mp3(input_file, output_file, quality=2):
    """
    使用 FFmpeg 轉換音訊為 MP3

    Args:
        input_file: 輸入檔案路徑
        output_file: 輸出 MP3 檔案路徑
        quality: 品質等級 0-9 (0=最高, 9=最低)

    Returns:
        str: 輸出檔案路徑

    Raises:
        SystemExit: 轉換失敗時
    """
    # 驗證輸入檔案
    input_path = Path(input_file)
    if not input_path.exists():
        print(f"❌ 錯誤: 找不到輸入檔案 {input_file}")
        sys.exit(1)

    # 建立輸出目錄
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 構建 FFmpeg 命令
    cmd = [
        'ffmpeg',
        '-i', str(input_path),
        '-vn',              # 無視訊
        '-ar', '44100',     # 取樣率 44.1kHz
        '-ac', '2',         # 雙聲道
        '-b:a', '192k',     # 位元率 192kbps
        '-q:a', str(quality),  # 品質參數
        '-y',               # 覆蓋輸出檔案
        str(output_path)
    ]

    print(f"🔄 轉換中: {input_path.name} → {output_path.name}")

    # 執行轉換
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding='utf-8'
    )

    # 檢查結果
    if result.returncode == 0:
        output_size = output_path.stat().st_size / 1024 / 1024
        print(f"✅ 轉換成功")
        print(f"   輸出: {output_path}")
        print(f"   大小: {output_size:.2f} MB")
        print(f"   品質: {quality} (0=最高, 9=最低)")
        return str(output_path)
    else:
        print(f"❌ 轉換失敗")
        print(f"   錯誤訊息:")
        print(result.stderr)
        sys.exit(1)


def main():
    """主函數"""
    if len(sys.argv) < 3:
        print("用法: python convert_audio.py <input> <output> [quality]")
        print()
        print("參數:")
        print("  input    - 輸入音訊檔案路徑")
        print("  output   - 輸出 MP3 檔案路徑")
        print("  quality  - 品質等級 0-9 (選填, 預設: 2)")
        print()
        print("範例:")
        print("  python convert_audio.py input.wav output.mp3")
        print("  python convert_audio.py input.flac output.mp3 0")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]
    quality = int(sys.argv[3]) if len(sys.argv) > 3 else 2

    # 驗證品質參數
    if not 0 <= quality <= 9:
        print(f"❌ 錯誤: 品質參數必須在 0-9 之間")
        sys.exit(1)

    convert_to_mp3(input_file, output_file, quality)


if __name__ == "__main__":
    main()
