# DASH 串流下載與 DRM 判斷紀錄

> **類型：📝 技術知識紀錄（非待實作任務）**
> **建立日期：2026-06-29**
> **相關模組：`tools/hls_downloader/`**
> **結論：暫不實作 DASH 支援，僅留存判斷與手動處理流程**

---

## 背景

使用者提供博客來電子書（`vod-ebook.books.com.tw`）的串流連結，希望下載並轉成 mp3：

```
dash:         .../E070009570-4/master-dash/stream.mpd
hls:          .../E070009570-4/master-hls/master.m3u8
preview-dash: .../E070009570-4/preview-dash/stream.mpd
preview-hls:  .../E070009570-4/preview-hls/master.m3u8
```

用現有工具下載 `master` 連結失敗。經查失敗原因**不是 bug**，而是兩個獨立因素：

1. **`master` 內容有 Widevine DRM 加密** → 無法解密，下載下來也無法播放。
2. **現有下載器只支援 HLS（m3u8），不支援 DASH（.mpd）** → `.mpd` 本來就不在處理範圍。

---

## 重點一：先判斷串流能不能下載（DRM 偵測）

**動手抓之前，先看 manifest 有沒有 DRM 標記**，可省下大量試誤時間。

抓 manifest 檢查：

```bash
curl -s "<manifest_url>" | head -c 2000
```

判斷依據：

| manifest 內出現 | 意義 | 可否下載 |
|----------------|------|---------|
| `<ContentProtection ...>` | 有內容保護 | ❌ DRM，放棄 |
| `<cenc:pssh>...</cenc:pssh>` | CENC / Widevine 金鑰資訊 | ❌ DRM，放棄 |
| `schemeIdUri="urn:uuid:edef8ba9-79d6-4ace-a3c8-27dcd51d21ed"` | Widevine | ❌ DRM，放棄 |
| 以上皆無 | 未加密 | ✅ 可下載 |

本案實測：

- `master-dash/stream.mpd` → 含 `ContentProtection` + Widevine `pssh` → **DRM，不可下載**。
- `preview-dash/stream.mpd` → 無任何保護標記 → **未加密，可下載**（31 秒試聽段落）。

> ⚠️ 僅處理**未加密**內容。對 DRM 內容取得解密金鑰、繞過保護屬於規避存取控制，不在本專案範圍。

---

## 重點二：未加密 DASH 音訊 → mp3 的手動流程

`ffmpeg` 直接讀 `.mpd` 會失敗：

```
Error opening input: Invalid data found when processing input
```

因此改用「抓 init + 依序抓 segment → 串接 → ffmpeg 轉檔」流程。

片段命名規則來自 manifest 的 `<SegmentTemplate>`：

```xml
<SegmentTemplate initialization="$RepresentationID$/init.mp4"
                 media="$RepresentationID$/seg-$Number$.m4s"
                 startNumber="1" .../>
<Representation id="audio/und/mp4a" .../>
```

→ `$RepresentationID$` = `audio/und/mp4a`，所以：
- init：`audio/und/mp4a/init.mp4`
- 片段：`audio/und/mp4a/seg-1.m4s`、`seg-2.m4s`、…

實際指令（從 `seg-1` 抓到第一個非 200 回應為止）：

```bash
BASE="https://vod-ebook.books.com.tw/streaming/E070009570-4/preview-dash/audio/und/mp4a"

# 1. 抓 init 當合併檔起頭
curl -s "$BASE/init.mp4" -o merged.mp4

# 2. 依序串接所有片段
n=1
while true; do
  code=$(curl -s -w "%{http_code}" -o seg_tmp.m4s "$BASE/seg-$n.m4s")
  [ "$code" != "200" ] && break
  cat seg_tmp.m4s >> merged.mp4
  n=$((n+1))
done
rm -f seg_tmp.m4s

# 3. 轉 mp3
ffmpeg -y -i merged.mp4 -vn -c:a libmp3lame -q:a 2 output.mp3
```

本案結果：17 個片段，輸出 31 秒 / ~195 kbps mp3，正常播放。

---

## 重點三：現有工具範圍

| 格式 | 副檔名 | 現況 |
|------|--------|------|
| HLS | `.m3u8` | ✅ 支援（`tools/hls_downloader/`，輸出 MP4 影片） |
| DASH | `.mpd` | ❌ 不支援，無 parser |

`tools/hls_downloader/parser.py` 使用 `m3u8` 套件，整條流程針對 TS segments → MP4，**沒有任何 `.mpd` 解析邏輯**。

---

## 為何暫不實作 DASH 支援

1. **是完整 feature 而非補丁**：需新增 `.mpd` parser（解析 `SegmentTemplate` / `Representation`）、init+seg 下載流程、音訊轉 mp3 路徑，並接上 `whitelist_validator`，等於在 HLS 模組旁長出平行架構。
2. **可用場景窄**：實務上想抓的 `master` 多半有 DRM，本流程無效；能成功的只有 `preview` 類未加密內容。
3. **目前為一次性需求**：用上述 curl + ffmpeg 手動流程即可解決，無反覆需求。

### 何時該改為實作

若「未加密 DASH 下載」變成**反覆出現的需求**，再走 `requirements` skill 開正式任務文件，評估影響範圍後實作。屆時建議將「DRM 偵測（重點一）」直接做進 parser，遇到 `ContentProtection` 立即回傳明確錯誤而非嘗試下載。

---

## 重點四：Widevine L3 解密（研究用途，已實測可行）

針對 Widevine DRM 保護內容，本專案已在 P4 任務實作研究用途的解密流程，
詳見 `tools/widevine_downloader/`。

2026-06-30 已用 VideoHelp 下載的 Samsung SM-A125F L3 WVD 成功解密博客來音訊。
實測報告：`docs/issues/ISSUE-002-Widevine-WVD-Research.md`

### 前提條件

| 條件 | 說明 |
|------|------|
| WVD device file | `tools/widevine_downloader/samsung_l3.wvd`（VideoHelp 取得，Samsung SM-A125F L3） |
| pywidevine | `pip install pywidevine` |
| mp4decrypt 或 shaka-packager | `brew install bento4`（mp4decrypt） |
| yt-dlp | `yt-dlp --allow-unplayable-formats` 下載加密原始檔 |

### 使用 CLI

```bash
# 偵測 DRM
python download_cli.py --detect-drm "https://...stream.mpd"

# 完整解密下載（wvd-path 有預設值，可省略）
python download_cli.py "https://...stream.mpd" \
  --decrypt-widevine \
  --widevine-pssh "AAAA..." \
  --widevine-license-url "https://license.example.com/..." \
  --widevine-headers '{"customdata":"<瀏覽器取得的 fresh customdata>"}' \
  -f mp3

# 指定其它 WVD
python download_cli.py "https://..." --decrypt-widevine \
  --wvd-path /path/to/other.wvd \
  --widevine-pssh "AAAA..." \
  --widevine-license-url "..." \
  --widevine-headers '{"customdata":"..."}' \
  -f mp3
```

### 金鑰提取

```bash
# 互動式
python -m tools.widevine_downloader.key_extractor

# 或指定 WVD
python -m tools.widevine_downloader.key_extractor --wvd tools/widevine_downloader/samsung_l3.wvd
```

### 手動完整流程

```bash
# 1. 用 key_extractor 取得 Content Key
# 2. 下載加密音訊
yt-dlp --allow-unplayable-formats -f bestaudio \
  -o "./downloads/enc_audio.%(ext)s" \
  "https://vod-ebook.books.com.tw/streaming/E070009570-5/master-dash/stream.mpd"

# 3. 解密（kid:key 從步驟 1 取得）
mp4decrypt --key <kid>:<key> ./downloads/enc_audio.m4a ./downloads/decrypted.m4a

# 4. 轉 MP3
ffmpeg -i ./downloads/decrypted.m4a -vn -c:a libmp3lame -q:a 0 ./downloads/output.mp3
```

> ⚠️ 僅限研究用途。customdata 每次需從瀏覽器 Network 面板重新取得（1 小時有效）。