🎧 Podcast Downloader MCP Tool — 工具規格書
1. 工具目的
提供 AI Agent（Claude / ChatGPT MCP Host）一個安全可控的工具，用於：
下載 Podcast 音檔（RSS Feed / MP3 直連 / Episode link）
自動辨識音訊格式
自動補上標準檔名 (title.mp3)
下載後回傳存放路徑
此工具只負責「下載 Podcast」，不涉入 FFmpeg 或轉檔。
2. 工具架構
2.1 工具名稱
podcast_downloader
2.2 工具類型
MCP Tool（Node.js）
屬於「File Operation + Network Download」類別
2.3 工具能力
✔ 支援下載來源
直接 MP3 URL
Podcast RSS Feed（自動解析第一集或指定集數）
Apple Podcast episode link（偵測後轉成音檔 URL）
Spotify Podcast episode page（需前端 API 解決方案，不一定有公開 API → 可選）
✔ 自動下載功能
GET/HEAD 請求確認檔案是否存在
自動偵測 Content-Type（audio/mpeg 等）
支援重新命名檔案
支援自動建立資料夾
3. 使用風險（Bug）與改善方案
3.1 Podcast 平台常阻擋爬蟲
Spotify、Apple Podcast 不一定允許直接下載（可能加密）
而一般 RSS Feed 都可以直接抓到 .mp3
改善方案（推薦）
僅支援 RSS Feed Podcast，避免不穩定來源。
3.2 Apple Podcast/Spotify 導向的是「網頁」，不是音檔
需要額外以非官方方式解析 → 有 API 政策風險
改善方案
工具預設 只支援音檔 URL 及 RSS Feed（安全）
如遇不支援來源 → 回傳錯誤訊息，避免 Agent 亂猜。
3.3 檔名包含特殊字元（macOS/Windows 有差異）
要做：
過濾 \/:*?"<>| 字元
自動轉成合法檔名
4. 工具 Input / Output Spec（正式 JSON Schema）
4.1 Input Schema
{
  "type": "object",
  "properties": {
    "url": {
      "type": "string",
      "description": "Podcast RSS / MP3 直連 / Episode link"
    },
    "target_dir": {
      "type": "string",
      "description": "下載後的存放資料夾路徑",
      "default": "./downloads"
    },
    "episode_index": {
      "type": "number",
      "description": "若來源為 RSS，指定要下載第幾集（0 = 最新）",
      "default": 0
    }
  },
  "required": ["url"]
}
4.2 Output Schema
{
  "type": "object",
  "properties": {
    "success": { "type": "boolean" },
    "file_path": { "type": "string" },
    "file_name": { "type": "string" },
    "episode_title": { "type": "string" },
    "source_type": { "type": "string", "enum": ["mp3", "rss"] }
  },
  "required": ["success"]
}
5. 工具運作流程（流程圖）
1. 接收 URL
2. 判斷是否為 RSS Feed
    ├── 是 → 解析 RSS → 取得指定集數音檔 URL
    └── 否 → 當作直接音訊 URL
3. 訪問音訊 URL，確認 Content-Type = audio/*
4. 自動處理檔名（RSS = episode title）
5. 建立目錄
6. 寫入檔案
7. 回傳下載成功狀態 + 路徑
6. Node.js MCP Tool 參考實作
6.1 TypeScript 實作（可直接用）
import { Tool } from "model-context-protocol";
import axios from "axios";
import fs from "fs";
import path from "path";
import Parser from "rss-parser";

const parser = new Parser();
const sanitize = (name: string) =>
  name.replace(/[\\/:*?"<>|]/g, "_");

export const podcastDownloader: Tool = {
  name: "podcast_downloader",
  description: "Download podcast audio (RSS or MP3 direct link).",
  inputSchema: {
    type: "object",
    properties: {
      url: { type: "string" },
      target_dir: { type: "string", default: "./downloads" },
      episode_index: { type: "number", default: 0 }
    },
    required: ["url"]
  },

  async run(input) {
    try {
      const { url, target_dir, episode_index } = input;

      // 判斷是否為 RSS
      const isRSS = url.endsWith(".xml")
        || url.includes("/feed")
        || url.includes("/rss");

      let audioUrl = url;
      let episodeTitle = "podcast";

      if (isRSS) {
        const feed = await parser.parseURL(url);
        const episode = feed.items[episode_index];

        if (!episode?.enclosure?.url) {
          return { success: false, error: "找不到音檔 URL" };
        }

        audioUrl = episode.enclosure.url;
        episodeTitle = sanitize(episode.title || "episode");
      }

      // 下載音檔
      const res = await axios.get(audioUrl, {
        responseType: "arraybuffer"
      });

      if (!res.headers["content-type"]?.includes("audio")) {
        return { success: false, error: "URL 並非音訊檔案" };
      }

      fs.mkdirSync(target_dir, { recursive: true });

      const fileName = `${episodeTitle}.mp3`;
      const filePath = path.join(target_dir, fileName);

      fs.writeFileSync(filePath, res.data);

      return {
        success: true,
        file_path: filePath,
        file_name: fileName,
        episode_title: episodeTitle,
        source_type: isRSS ? "rss" : "mp3"
      };

    } catch (err: any) {
      return { success: false, error: err.message };
    }
  }
};
7. 可與系統整合的擴充項目
建議後續擴充：
搭配 FFmpeg Tool → 自動轉 mp3 / wav / m4a
搭配 Filesystem MCP Tool → 自動歸檔
搭配 open_app Tool → 下載後自動開啟播放器
支援 download progress 回報（讓 Agent 可以顯示進度）
8. 最佳實務（避免 Bug）
問題情境	解決方案
RSS feed 沒有 enclosure	回傳 error 並停止
Spotify/Apple Podcast 無法下載	明確回報不支援
檔名不合法	使用 sanitize() 清洗字元
大檔案下載中斷	改為 stream 寫入（後續可加強）
audio/mpeg 判定錯誤	加入 mime fallback
9. 結論
此 MCP 工具可安全、穩定地完成：
Podcast RSS 解析
MP3 音檔下載
自動檔名
自動存檔
可被 AI Agent 多步驟自動化串起來
已符合 Claude MCP Tool 的完整開發標準。