HLS Downloader MCP Tool - 完整規格書
1. 工具目的
提供 AI Agent（MCP）一個可直接下載 HLS (.m3u8) 串流、合併 .ts 段落並自動轉成 .mp4 的工具，包含下載、合併、格式轉換、錯誤處理等完整流程。
2. 工具功能清單
✅ 2.1 下載 m3u8 Playlist
支援 HTTP / HTTPS
支援 master playlist（多個解析度）
將最高畫質自動選取為下載目標（可覆寫選項）
✅ 2.2 下載所有 TS segments
自動解析 .m3u8 段落
逐段下載 .ts 檔
支援並行下載（可設定 thread 數）
支援 retry / timeout /錯誤續傳
✅ 2.3 合併 TS → MP4
自動串接所有 .ts segment
使用 FFmpeg 或 Pure Python（可切換）
產生最終的 .mp4 檔案
✅ 2.4 自動刪除暫存 TS 檔案
減少儲存空間浪費
✅ 2.5 回傳結果
影片完整輸出路徑
影片 metadata（duration、resolution、bitrate）
3. MCP Tool API 規格
tool name
hls_downloader
methods
(1) download_hls
下載並轉檔成 mp4。
Input Schema
{
  "type": "object",
  "properties": {
    "m3u8_url": { "type": "string" },
    "output_path": { "type": "string" },
    "threads": { "type": "number", "default": 8 },
    "select_highest_quality": { "type": "boolean", "default": true }
  },
  "required": ["m3u8_url", "output_path"]
}
Output Schema
{
  "type": "object",
  "properties": {
    "success": { "type": "boolean" },
    "output_file": { "type": "string" },
    "duration": { "type": "string" },
    "resolution": { "type": "string" },
    "bitrate": { "type": "string" }
  }
}
4. MCP Tool 實作架構（Python 範例）
主要流程 Pseudocode
def download_hls(m3u8_url, output_path, threads=8):
    playlist = parse_m3u8(m3u8_url)
    
    if playlist.is_master():
        playlist = playlist.select_highest_quality()

    ts_urls = playlist.ts_segments()
    
    temp_dir = create_temp_dir()

    parallel_download(ts_urls, temp_dir, threads)

    ts_file_list = sort_by_sequence(temp_dir)
    
    merged_ts_path = merge_ts(ts_file_list)
    
    output_mp4 = convert_to_mp4(merged_ts_path, output_path)

    cleanup(temp_dir)

    meta = extract_metadata(output_mp4)

    return meta
5. 完整 Python 工具範例程式碼（可直接嵌入 MCP 伺服器）
import os
import m3u8
import requests
from concurrent.futures import ThreadPoolExecutor
import subprocess

def download_segment(url, path):
    r = requests.get(url, timeout=10)
    with open(path, "wb") as f:
        f.write(r.content)

def merge_ts(ts_list, merged_path="merged.ts"):
    with open(merged_path, "wb") as merged:
        for ts in ts_list:
            with open(ts, "rb") as segment:
                merged.write(segment.read())
    return merged_path

def convert_to_mp4(input_ts, output_path):
    subprocess.run([
        "ffmpeg", "-y", "-i", input_ts, "-c", "copy", output_path
    ])
    return output_path

def hls_download(m3u8_url, output_mp4, threads=8):
    playlist = m3u8.load(m3u8_url)

    # 若為 master playlist，自動選最高畫質
    if playlist.is_variant:
        playlist = m3u8.load(playlist.playlists[-1].uri)

    ts_urls = [seg.absolute_uri for seg in playlist.segments]

    os.makedirs("temp", exist_ok=True)
    ts_paths = [f"temp/seg_{i}.ts" for i in range(len(ts_urls))]

    # 多執行緒下載 TS
    with ThreadPoolExecutor(max_workers=threads) as exe:
        for url, path in zip(ts_urls, ts_paths):
            exe.submit(download_segment, url, path)

    merged_ts = merge_ts(ts_paths)
    convert_to_mp4(merged_ts, output_mp4)

    return output_mp4
6. 使用案例
案例 1：下載 HLS 直播錄影
{
  "tool": "hls_downloader",
  "m3u8_url": "https://example.com/stream/playlist.m3u8",
  "output_path": "/Users/alex/video/output.mp4"
}
案例 2：使用 32 執行緒加速下載
{
  "tool": "hls_downloader",
  "m3u8_url": "https://cdn.site.com/video.m3u8",
  "output_path": "./movie.mp4",
  "threads": 32
}
7. 風險分析與優化建議
風險 1：TS 檔案大量 → 速度慢 + 容易斷線
問題點
HLS 通常包含數百到數千個 .ts 小檔案，逐段下載會：
網路斷線影響大
速度受限於 HTTP request 次數
推薦解法：分批並行下載 + retry
已在規格中加入 ThreadPoolExecutor 提升吞吐量。
風險 2：TS 合併後直接 copy 轉 MP4 可能不相容
某些 HLS 的 .ts 使用 AAC / H264，FFmpeg 可 direct copy
但若為 HEVC 或特殊封裝，可能需要重編碼。
推薦改善：加入 fallback re-encode
ffmpeg -i input.ts -c:v libx264 -c:a aac output.mp4
風險 3：Master playlist 解析錯誤
部分 CDN 的 m3u8 會包含相對路徑，需要處理 base URL。
推薦解決：自動補全 URL
8. 最佳化版本推薦
建議採用 FFmpeg concat demuxer
比自己 .ts 串接更穩定：
生成 concat 檔案：
file seg_0.ts
file seg_1.ts
...
轉成 mp4：
ffmpeg -f concat -safe 0 -i list.txt -c copy output.mp4
較不易出現破損、不同編碼切換問題。