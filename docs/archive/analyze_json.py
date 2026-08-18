#!/usr/bin/env python3
"""
分析 JSON 資料並提取影片和圖片連結
"""
import json
import sys

def analyze_json(json_file):
    """分析 JSON 檔案並提取所有連結"""

    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 提取影片列表
    videos = data.get('ymSubmenu', {}).get('dvd', {}).get('submenu', [])

    print("=" * 80)
    print(f"找到 {len(videos)} 個影片")
    print("=" * 80)
    print()

    video_urls = []
    image_urls = []

    for idx, video in enumerate(videos, 1):
        name = video.get('name', '未命名')
        video_url = video.get('url', '')
        img_url = video.get('imgurl', '')
        dvd_id = video.get('DvdID', '')

        print(f"{idx}. {name}")
        print(f"   DVD ID: {dvd_id}")
        print(f"   影片: {video_url}")
        print(f"   圖片: {img_url}")
        print()

        if video_url:
            video_urls.append((name, video_url))
        if img_url:
            image_urls.append((name, img_url))

    print("=" * 80)
    print(f"總計: {len(video_urls)} 個影片, {len(image_urls)} 張圖片")
    print("=" * 80)
    print()

    # 產生下載腳本
    print("\n如果要批次下載，可以使用以下指令：")
    print("\n# 下載所有影片 (MP4 格式):")
    print("python batch_download.py temp_data.json --type video --format mp4\n")
    print("# 下載所有圖片:")
    print("python batch_download.py temp_data.json --type image\n")
    print("# 同時下載影片和圖片:")
    print("python batch_download.py temp_data.json --type all --format mp4\n")

    return video_urls, image_urls

if __name__ == "__main__":
    json_file = sys.argv[1] if len(sys.argv) > 1 else "temp_data.json"
    analyze_json(json_file)
