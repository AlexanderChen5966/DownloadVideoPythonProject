#!/usr/bin/env python3
"""
壓縮音訊/視訊檔案
支援指定目標檔案大小或位元率
"""

import argparse
import subprocess
import sys
from pathlib import Path


def parse_size(size_str):
    """
    解析檔案大小字串 (例如: 50MB, 100KB)

    Args:
        size_str: 大小字串

    Returns:
        int: 位元組數
    """
    size_str = size_str.upper()
    if size_str.endswith('GB'):
        return int(float(size_str[:-2]) * 1024 * 1024 * 1024)
    elif size_str.endswith('MB'):
        return int(float(size_str[:-2]) * 1024 * 1024)
    elif size_str.endswith('KB'):
        return int(float(size_str[:-2]) * 1024)
    else:
        return int(size_str)


def get_duration(file_path):
    """
    取得媒體檔案的時長 (秒)

    Args:
        file_path: 檔案路徑

    Returns:
        float: 時長 (秒)
    """
    cmd = [
        'ffprobe',
        '-v', 'error',
        '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1',
        str(file_path)
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        return float(result.stdout.strip())
    return 0


def compress_media(input_file, output_file, target_size=None, bitrate=None):
    """
    壓縮媒體檔案

    Args:
        input_file: 輸入檔案路徑
        output_file: 輸出檔案路徑
        target_size: 目標檔案大小 (位元組)
        bitrate: 位元率 (例如: 128k)

    Returns:
        str: 輸出檔案路徑

    Raises:
        SystemExit: 壓縮失敗時
    """
    # 驗證輸入檔案
    input_path = Path(input_file)
    if not input_path.exists():
        print(f"❌ 錯誤: 找不到輸入檔案 {input_file}")
        sys.exit(1)

    # 建立輸出目錄
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 如果指定目標大小，計算所需位元率
    if target_size:
        duration = get_duration(input_path)
        if duration == 0:
            print(f"❌ 錯誤: 無法取得檔案時長")
            sys.exit(1)

        # 計算位元率 (位元/秒)
        # 留一些空間給音訊和容器格式
        target_bitrate = int((target_size * 8) / duration * 0.95)
        bitrate = f"{target_bitrate}"

    # 構建 FFmpeg 命令
    cmd = [
        'ffmpeg',
        '-i', str(input_path),
        '-b:v', str(bitrate),
        '-b:a', '128k',  # 音訊位元率固定為 128k
        '-y',
        str(output_path)
    ]

    print(f"🔄 壓縮中: {input_path.name} → {output_path.name}")
    if target_size:
        print(f"   目標大小: {target_size / 1024 / 1024:.2f} MB")
    print(f"   位元率: {bitrate}")

    # 執行壓縮
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True
    )

    # 檢查結果
    if result.returncode == 0:
        input_size = input_path.stat().st_size / 1024 / 1024
        output_size = output_path.stat().st_size / 1024 / 1024
        compression_ratio = (1 - output_size / input_size) * 100

        print(f"✅ 壓縮成功")
        print(f"   輸出: {output_path}")
        print(f"   原始大小: {input_size:.2f} MB")
        print(f"   壓縮後: {output_size:.2f} MB")
        print(f"   壓縮率: {compression_ratio:.1f}%")
        return str(output_path)
    else:
        print(f"❌ 壓縮失敗")
        print(f"   錯誤訊息:")
        print(result.stderr)
        sys.exit(1)


def main():
    """主函數"""
    parser = argparse.ArgumentParser(description='壓縮音訊/視訊檔案')
    parser.add_argument('input', help='輸入檔案路徑')
    parser.add_argument('output', help='輸出檔案路徑')

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--target-size', help='目標檔案大小 (例如: 50MB, 100KB)')
    group.add_argument('--bitrate', help='目標位元率 (例如: 128k, 1M)')

    args = parser.parse_args()

    target_size = None
    bitrate = None

    if args.target_size:
        target_size = parse_size(args.target_size)
    else:
        bitrate = args.bitrate

    compress_media(args.input, args.output, target_size, bitrate)


if __name__ == "__main__":
    main()
