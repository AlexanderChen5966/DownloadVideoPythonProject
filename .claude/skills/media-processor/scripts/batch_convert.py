#!/usr/bin/env python3
"""
批量轉換音訊/視訊檔案
支援目錄遞迴處理、並行處理加速轉換
"""

import argparse
import subprocess
import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed


def convert_file(input_file, output_dir, format='mp3', quality=2):
    """
    轉換單個檔案

    Args:
        input_file: 輸入檔案路徑
        output_dir: 輸出目錄
        format: 輸出格式
        quality: 品質等級

    Returns:
        tuple: (success, input_file, output_file, error)
    """
    input_path = Path(input_file)
    output_path = Path(output_dir) / f"{input_path.stem}.{format}"

    # 確保輸出目錄存在
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 構建 FFmpeg 命令
    cmd = [
        'ffmpeg',
        '-i', str(input_path),
        '-vn',
        '-ar', '44100',
        '-ac', '2',
        '-b:a', '192k',
        '-q:a', str(quality),
        '-y',
        str(output_path)
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )
        return (True, str(input_path), str(output_path), None)
    except subprocess.CalledProcessError as e:
        return (False, str(input_path), None, str(e))


def find_audio_files(input_dir, extensions=None):
    """
    查找目錄中的所有音訊檔案

    Args:
        input_dir: 輸入目錄
        extensions: 檔案副檔名列表

    Returns:
        list: 檔案路徑列表
    """
    if extensions is None:
        extensions = ['.mp3', '.wav', '.m4a', '.flac', '.ogg', '.aac', '.wma', '.mp4', '.webm']

    input_path = Path(input_dir)
    files = []

    for ext in extensions:
        files.extend(input_path.glob(f'**/*{ext}'))

    return files


def main():
    """主函數"""
    parser = argparse.ArgumentParser(description='批量轉換音訊/視訊檔案')
    parser.add_argument('--input-dir', required=True, help='輸入目錄路徑')
    parser.add_argument('--output-dir', required=True, help='輸出目錄路徑')
    parser.add_argument('--format', default='mp3', help='輸出格式 (預設: mp3)')
    parser.add_argument('--quality', type=int, default=2, help='品質等級 0-9 (預設: 2)')
    parser.add_argument('--workers', type=int, default=4, help='並行處理數量 (預設: 4)')

    args = parser.parse_args()

    # 驗證輸入目錄
    if not Path(args.input_dir).exists():
        print(f"❌ 錯誤: 輸入目錄不存在: {args.input_dir}")
        sys.exit(1)

    # 查找所有音訊檔案
    print(f"🔍 搜尋音訊檔案: {args.input_dir}")
    files = find_audio_files(args.input_dir)

    if not files:
        print(f"⚠️  未找到任何音訊檔案")
        sys.exit(0)

    print(f"📁 找到 {len(files)} 個檔案")
    print(f"🔄 開始批量轉換...")
    print(f"   輸出格式: {args.format}")
    print(f"   品質: {args.quality}")
    print(f"   並行數: {args.workers}")
    print()

    # 並行處理
    success_count = 0
    failed_count = 0

    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        # 提交所有任務
        futures = {
            executor.submit(
                convert_file,
                file,
                args.output_dir,
                args.format,
                args.quality
            ): file for file in files
        }

        # 處理完成的任務
        for future in as_completed(futures):
            success, input_file, output_file, error = future.result()

            if success:
                success_count += 1
                print(f"✅ [{success_count}/{len(files)}] {Path(input_file).name} → {Path(output_file).name}")
            else:
                failed_count += 1
                print(f"❌ [{success_count + failed_count}/{len(files)}] {Path(input_file).name} - {error}")

    # 輸出統計
    print()
    print(f"📊 轉換完成")
    print(f"   成功: {success_count}")
    print(f"   失敗: {failed_count}")
    print(f"   總計: {len(files)}")

    if failed_count > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
