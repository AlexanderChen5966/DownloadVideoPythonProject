#!/usr/bin/env python3
"""
分析 JSON 数据并提取视频和图片链接
"""
import json
import sys

def analyze_json(json_file):
    """分析 JSON 文件并提取所有链接"""

    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 提取视频列表
    videos = data.get('ymSubmenu', {}).get('dvd', {}).get('submenu', [])

    print("=" * 80)
    print(f"找到 {len(videos)} 個視頻")
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
        print(f"   視頻: {video_url}")
        print(f"   圖片: {img_url}")
        print()

        if video_url:
            video_urls.append((name, video_url))
        if img_url:
            image_urls.append((name, img_url))

    print("=" * 80)
    print(f"總計: {len(video_urls)} 個視頻, {len(image_urls)} 張圖片")
    print("=" * 80)
    print()

    # 生成下载脚本
    print("\n如果要批量下载，可以使用以下命令：")
    print("\n# 下载所有视频 (MP4 格式):")
    print("python batch_download.py temp_data.json --type video --format mp4\n")
    print("# 下载所有图片:")
    print("python batch_download.py temp_data.json --type image\n")
    print("# 同时下载视频和图片:")
    print("python batch_download.py temp_data.json --type all --format mp4\n")

    return video_urls, image_urls

if __name__ == "__main__":
    json_file = sys.argv[1] if len(sys.argv) > 1 else "temp_data.json"
    analyze_json(json_file)
