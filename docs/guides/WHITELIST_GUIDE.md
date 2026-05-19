# 網路白名單功能指南

## 概述

網路白名單功能用於限制媒體下載工具只能從授權的網域下載內容,提高系統安全性。

## 功能特點

- ✅ **完整網域比對**: 精確匹配網域名稱 (例如: `youtube.com`)
- ✅ **萬用字元支援**: 使用 `*` 匹配子網域 (例如: `*.youtube.com`)
- ✅ **正則表達式**: 支援複雜的 URL 匹配規則
- ✅ **動態管理**: 透過 MCP 工具即時新增/移除規則
- ✅ **可開關**: 可隨時啟用或停用白名單功能

## 受保護的工具

白名單會檢查以下下載工具的 URL:

1. `download_media` - YouTube 影片/音檔下載
2. `download_and_convert_image` - 圖片下載
3. `podcast_downloader` - Podcast 下載
4. `download_hls` - HLS 串流下載

## 設定檔格式

白名單設定儲存在專案根目錄的 `whitelist.json`:

```json
{
  "enabled": true,
  "rules": [
    "youtube.com",
    "*.youtube.com",
    "youtu.be",
    "*.googlevideo.com",
    "podcasts.apple.com",
    "*.podbean.com"
  ]
}
```

### 設定欄位說明

- `enabled` (boolean): 是否啟用白名單功能
  - `true`: 啟用,只允許白名單中的網域
  - `false`: 停用,允許所有網域

- `rules` (array): 白名單規則列表,支援三種格式:
  1. **完整網域**: `youtube.com` - 僅匹配 youtube.com
  2. **萬用字元**: `*.youtube.com` - 匹配所有 youtube.com 的子網域
  3. **正則表達式**: `^https?://.*\.example\.com/.*` - 使用正則表達式匹配

## 管理工具

### 1. 列出白名單規則

查看目前的白名單狀態和所有規則:

```
請列出目前的白名單規則
```

回應範例:
```json
{
  "success": true,
  "enabled": true,
  "total_rules": 6,
  "rules": [
    "youtube.com",
    "*.youtube.com",
    "youtu.be",
    "*.googlevideo.com",
    "podcasts.apple.com",
    "*.podbean.com"
  ]
}
```

### 2. 新增白名單規則

新增一個網域到白名單:

```
請新增 twitch.tv 到白名單
```

或使用萬用字元:
```
請新增 *.twitch.tv 到白名單
```

或使用正則表達式:
```
請新增正則表達式 ^https?://.*\.trusteddomain\.com/.* 到白名單
```

回應範例:
```json
{
  "success": true,
  "message": "已成功新增規則: twitch.tv",
  "rule": "twitch.tv"
}
```

### 3. 移除白名單規則

從白名單中移除特定規則:

```
請從白名單移除 twitch.tv
```

回應範例:
```json
{
  "success": true,
  "message": "已成功移除規則: twitch.tv",
  "rule": "twitch.tv"
}
```

### 4. 啟用/停用白名單

啟用白名單:
```
請啟用白名單功能
```

停用白名單:
```
請停用白名單功能
```

回應範例:
```json
{
  "success": true,
  "message": "白名單已啟用",
  "enabled": true
}
```

## 使用範例

### 範例 1: 基本設定

1. 啟用白名單並新增常用網域:

```
請啟用白名單功能,並新增以下網域:
- youtube.com
- *.youtube.com
- youtu.be
```

2. 嘗試下載 YouTube 影片 (允許):

```
請下載這個 YouTube 影片:
https://www.youtube.com/watch?v=xxxxx
```

3. 嘗試下載非白名單網域 (拒絕):

```
請下載這個影片:
https://example.com/video.mp4
```

錯誤訊息:
```json
{
  "success": false,
  "error": "白名單驗證失敗",
  "message": "網域 'example.com' 不在白名單中，請聯絡管理員新增"
}
```

### 範例 2: Podcast 下載設定

為 Podcast 下載設定白名單:

```
請新增以下 Podcast 平台到白名單:
- *.podbean.com
- *.buzzsprout.com
- *.libsyn.com
- *.soundcloud.com
```

### 範例 3: 使用正則表達式

匹配特定 CDN 的所有子網域:

```
請新增正則表達式到白名單: ^https?://.*\.cdn\.example\.com/.*
```

這會允許:
- `https://video.cdn.example.com/file.mp4`
- `https://audio.cdn.example.com/podcast.mp3`

### 範例 4: 臨時停用白名單

在測試或特殊情況下臨時停用:

```
請臨時停用白名單,我需要下載一個測試檔案
```

下載完成後再啟用:

```
測試完成,請重新啟用白名單
```

## 規則匹配邏輯

白名單驗證器按以下順序檢查規則:

1. **完整網域比對**: 檢查網域是否完全相同
2. **萬用字元比對**: 使用 fnmatch 檢查萬用字元規則
3. **正則表達式比對**: 使用 re.match 檢查正則表達式規則

只要符合任一規則,即允許下載。

## 預設白名單

專案預設包含以下常用網域:

- YouTube: `youtube.com`, `*.youtube.com`, `youtu.be`, `*.googlevideo.com`
- Podcast 平台: `podcasts.apple.com`, `*.podbean.com`, `*.buzzsprout.com`, `*.libsyn.com`
- 音樂平台: `*.soundcloud.com`, `*.spotify.com`

## 錯誤處理

### 白名單驗證失敗

當 URL 不在白名單時:

```json
{
  "success": false,
  "error": "白名單驗證失敗",
  "message": "網域 'untrusted.com' 不在白名單中，請聯絡管理員新增"
}
```

### 規則已存在

嘗試新增重複規則時:

```json
{
  "success": false,
  "message": "規則 'youtube.com' 已存在於白名單中"
}
```

### 規則不存在

嘗試移除不存在的規則時:

```json
{
  "success": false,
  "message": "規則 'notfound.com' 不存在於白名單中"
}
```

## 安全建議

1. **最小權限原則**: 只新增必要的網域到白名單
2. **定期審查**: 定期檢查白名單規則,移除不再需要的網域
3. **避免過度寬鬆**: 謹慎使用萬用字元,避免 `*.*` 這類過於寬鬆的規則
4. **正則表達式測試**: 新增正則表達式規則前先測試確保正確性
5. **保持啟用**: 除非有特殊需求,建議保持白名單功能啟用

## 技術實作

### 檔案結構

```
DownloadVideoPythonProject/
├── whitelist.json                  # 白名單設定檔
├── utils/
│   └── whitelist_validator.py     # 白名單驗證模組
├── server.py                       # 整合白名單檢查的主伺服器
└── tools/
    ├── podcast_downloader.py       # 已整合白名單
    └── hls_downloader/
        └── downloader.py           # 已整合白名單
```

### API 參考

白名單驗證器類別 (`WhitelistValidator`):

- `validate(url: str) -> Tuple[bool, str]`: 驗證 URL 是否在白名單中
- `add_rule(rule: str) -> Tuple[bool, str]`: 新增規則
- `remove_rule(rule: str) -> Tuple[bool, str]`: 移除規則
- `list_rules() -> List[str]`: 列出所有規則
- `set_enabled(enabled: bool) -> Tuple[bool, str]`: 啟用/停用白名單

## 疑難排解

### Q: 為什麼下載失敗?

A: 檢查以下項目:
1. 確認白名單是否啟用 (`whitelist_list_rules`)
2. 確認目標網域是否在白名單中
3. 檢查萬用字元或正則表達式規則是否正確

### Q: 如何暫時繞過白名單?

A: 使用 `whitelist_set_enabled` 工具停用白名單:
```
請停用白名單功能
```

### Q: RSS Feed 下載失敗?

A: Podcast RSS Feed 可能重定向到不同的音檔 URL。需要同時將 RSS 來源和音檔 CDN 都加入白名單。

### Q: 正則表達式不起作用?

A: 確保正則表達式符合 Python `re` 模組語法,並且包含必要的轉義字元。例如 `.` 應寫為 `\\.`。

## 更新日誌

### 2024-11-27
- 初始實作網路白名單功能
- 支援完整網域、萬用字元、正則表達式三種匹配方式
- 整合到所有下載工具
- 新增 4 個 MCP 管理工具
