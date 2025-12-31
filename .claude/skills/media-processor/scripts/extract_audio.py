#!/usr/bin/env python3
"""
從視訊檔案提取音訊
支援多種音訊格式輸出、保留最高音質
"""

import argparse
import subprocess
import sys
from pathlib import Path


def extract_audio(input_video, output_audio, format='mp3', quality=2):
    """
    從視訊檔案提取音訊

    Args:
        input_video: 輸入視訊檔案路徑
        output_audio: 輸出音訊檔案路徑
        format: 輸出格式 (mp3, flac, aac, wav)
        quality: 品質等級 0-9

    Returns:
        str: 輸出檔案路徑

    Raises:
        SystemExit: 提取失敗時
    """
    # 驗證輸入檔案
    input_path = Path(input_video)
    if not input_path.exists():
        print(f"❌ 錯誤: 找不到輸入檔案 {input_video}")
        sys.exit(1)

    # 建立輸出目錄
    output_path = Path(output_audio)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 構建 FFmpeg 命令
    cmd = ['ffmpeg', '-i', str(input_path), '-vn']

    # 根據格式設置參數
    if format == 'mp3':
        cmd.extend([
            '-codec:a', 'libmp3lame',
            '-qscale:a', str(quality),
            '-ar', '44100',
            '-ac', '2'
        ])
    elif format == 'flac':
        cmd.extend([
            '-codec:a', 'flac',
            '-compression_level', str(quality)
        ])
    elif format == 'aac':
        cmd.extend([
            '-codec:a', 'aac',
            '-b:a', '192k'
        ])
    elif format == 'wav':
        cmd.extend([
            '-codec:a', 'pcm_s16le',
            '-ar', '44100',
            '-ac', '2'
        ])
    else:
        # 預設使用原始音訊編碼
        cmd.extend(['-codec:a', 'copy'])

    cmd.extend(['-y', str(output_path)])

    print(f"🔄 提取音訊: {input_path.name} → {output_path.name}")
    print(f"   格式: {format}")
    print(f"   品質: {quality}")

    # 執行提取
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True
    )

    # 檢查結果
    if result.returncode == 0:
        output_size = output_path.stat().st_size / 1024 / 1024
        print(f"✅ 提取成功")
        print(f"   輸出: {output_path}")
        print(f"   大小: {output_size:.2f} MB")
        return str(output_path)
    else:
        print(f"❌ 提取失敗")
        print(f"   錯誤訊息:")
        print(result.stderr)
        sys.exit(1)


def main():
    """主函數"""
    parser = argparse.ArgumentParser(description='從視訊檔案提取音訊')
    parser.add_argument('input', help='輸入視訊檔案路徑')
    parser.add_argument('output', help='輸出音訊檔案路徑')
    parser.add_argument('--format', default='mp3',
                       choices=['mp3', 'flac', 'aac', 'wav', 'copy'],
                       help='輸出音訊格式 (預設: mp3)')
    parser.add_argument('--quality', type=int, default=2,
                       help='品質等級 0-9 (預設: 2, 0=最高)')

    args = parser.parse_args()

    # 驗證品質參數
    if not 0 <= args.quality <= 9:
        print(f"❌ 錯誤: 品質參數必須在 0-9 之間")
        sys.exit(1)

    extract_audio(args.input, args.output, args.format, args.quality)


if __name__ == "__main__":
    main()
