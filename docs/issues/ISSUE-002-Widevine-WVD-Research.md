# ISSUE-002: Widevine WVD 取得方式研究（進行中）

> **狀態：** ✅ 方式 C 成功（VideoHelp 現成 WVD 可解密博客來）
> **建立日期：** 2026-06-30
> **分類：** DRM 研究 / WVD 提取

---

## 問題描述

要使用 `tools/widevine_downloader/` 模組（P4）對博客來電子書音訊進行 Widevine 解密，需要一個有效的 **Widevine Device (.wvd) 檔案**（L3 provision）。本文件記錄取得 WVD 的各種嘗試過程、結果與待續行動。

---

## 目標平台分析

**平台：** 博客來電子書（`vod-ebook.books.com.tw`）

```
DASH：https://vod-ebook.books.com.tw/streaming/E070009570-5/master-dash/stream.mpd
HLS ：https://vod-ebook.books.com.tw/streaming/E070009570-5/master-hls/master.m3u8
```

### DRM 偵測結果（`python download_cli.py --detect-drm`）

| 格式 | DRM 類型 | 結論 |
|------|---------|------|
| DASH (.mpd) | **Widevine L3** | 理論上可解密，需 WVD |
| HLS (.m3u8) | **FairPlay** (`skd://`) | Apple 硬體安全，無法軟體解密 |

> ⚠️ HLS master playlist 無 DRM 標記，DRM 在子播放清單（media-1/stream.m3u8）的 `EXT-X-KEY` 中。已修正 `drm_detector.py`，現可正確偵測。

### License Server 資訊

```
URL    ：https://widevine.keyos.com/api/v4/getLicense
平台   ：KeyOS（多平台 DRM 服務商）
認證   ：HTTP Header customdata（Base64 XML）
```

### customdata 解碼內容

```xml
<KeyOSAuthenticationXML>
  <Data>
    <GenerationTime>2026-06-30 06:19:35</GenerationTime>
    <ExpirationTime>2026-06-30 07:19:35</ExpirationTime>  <!-- 1 小時有效 -->
    <UniqueId>1a69312e-45bf-4f30-a5e5-452f7e8cccdc</UniqueId>
    <RSAPubKeyId>20a04a8bb1fea9ec1608889377507842</RSAPubKeyId>
    <WidevinePolicy fl_CanPersist="true" fl_CanPlay="true">
      <LicenseDuration>157680000</LicenseDuration>
    </WidevinePolicy>
    <WidevineContentKeySpec TrackType="HD">
      <SecurityLevel>1</SecurityLevel>  <!-- L1 要求，可能拒絕 L3 CDM -->
    </WidevineContentKeySpec>
    <FairPlayPolicy persistent="true">...</FairPlayPolicy>
  </Data>
  <Signature>...</Signature>
</KeyOSAuthenticationXML>
```

### License Server 認證測試

送假 challenge（100 bytes random）測試 customdata 是否能通過認證：

```
HTTP 403
{
  "errorcode": 371000005,
  "errormsg": "Widevine license generation failed (SIGNED_MESSAGE_PARSE_ERROR)",
  "errorid": "..."
}
```

**結論：** `customdata` 認證**通過**（HTTP 403 是 challenge 格式錯誤，不是 auth 錯誤 401）。

⚠️ **SecurityLevel=1 實測結果：L3 CDM 並未被拒絕！** 使用 VideoHelp 下載的 Samsung SM-A125F L3 WVD 成功取得 Content Key（2026-06-30 實測）。推測博客來對 audio-only 軌道未強制執行 SecurityLevel 限制。

---

## 取得 WVD 嘗試紀錄

---

### 方式 A：Android 模擬器 + Frida dumper

**狀態：** ❌ 失敗（根本原因確認）

**工具：** [wvdumper/dumper](https://github.com/wvdumper/dumper)

**環境：**

| 項目 | 內容 |
|------|------|
| 模擬器 | Android Studio AVD，Pixel 3a，API 28，arm64-v8a |
| frida-server | 17.15.3（arm64） |
| 推送路徑 | `/data/local/tmp/frida-server` |

**過程與修正：**

#### 問題 1：protobuf 版本衝突

```
TypeError: Descriptors cannot be created directly.
```

修正：加環境變數

```bash
PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python python dump_keys.py
```

#### 問題 2：Frida 17.x API 不相容（`Module.enumerateExportsSync` 已移除）

`dumper/Helpers/script.js` 第 110 行：

```js
// 舊（Frida ≤ 15.x）
Module.enumerateExportsSync(name).forEach(...)

// 修正後（Frida 16+）
Process.getModuleByName(name).enumerateExports().forEach(...)
```

#### 問題 3：`Script.exports` 棄用

`dumper/Helpers/Scanner.py`：

```python
# 舊
script.exports.inject(library, process)
script.exports.widevinelibrary(lib)

# 修正後
script.exports_sync.inject(library, process)
script.exports_sync.widevinelibrary(lib)
```

#### 問題 4：鉤錯進程

以為 Widevine 在 `android.hardware.drm@1.0-service`（pid=315），實際是 `android.hardware.drm@1.3-service.widevine`（pid=317）。

**進程與模組對應：**

| 進程 | PID | Widevine 模組 | `_lcc*` 函式數 |
|------|-----|--------------|--------------|
| `android.hardware.drm@1.0-service` | 315 | `libwvdrmengine.so` | 139 個 |
| `android.hardware.drm@1.3-service.widevine` | 317 | `libwvhidl.so` | 139 個 |
| `android.hardware.drm@1.3-service.clearkey` | 316 | — | — |

#### 問題 5：動態函式名稱不符

wvdumper 硬編碼的舊版 CDM 動態函式名稱（如 `polorucp`、`ulns` 等）在此 CDM 版本完全不存在。

此版本 `libwvhidl.so` 實際的短名稱函式：

```
['vyxlkkyb', 'ifalijui', 'oamctmct', 'fyjkrifm', 'epdmnqaw', 'axxujrkt',
 'vngfjbek', 'cdzyglgq', 'vauxqowp', 'aghmjrzq', 'qshdnjvf', 'vlezovbp',
 'ydihlccg', 'fpntokux', 'gskvufzb', 'tfayzalk', 'pttbnsjd', 'umsygtib',
 'miwudsyh', 'iuifgddw']
```

即使以自訂 RSA key 掃描邏輯掛鉤以上所有函式（同時掃 `onEnter` / `onLeave` 的 arg pairs），仍未捕獲到私鑰。

#### 根本失敗原因

Android 模擬器上的 **Chrome 瀏覽器有自己內建的 Widevine CDM**，完全不走 Android 系統層的 `libwvhidl.so`，因此掛的 Frida hook 不會被觸發。

`wvdumper/dumper` 只對**原生 Android App**（Netflix App、YouTube App 等使用 `MediaDrm` API 的 App）有效，不適用於模擬器內的 Chrome。

---

### 方式 B：WidevineProxy2 + Remote CDM

**狀態：** ❌ 未測試（已不需要）

**工具：** [DevLARLEY/WidevineProxy2](https://github.com/DevLARLEY/WidevineProxy2)（已安裝）

**重要認知：** WidevineProxy2 **不是 WVD 提取工具**，而是金鑰攔截器。它在瀏覽器播放 DRM 內容時，用 WVD 或 Remote CDM 攔截 License 交換，直接輸出 `kid:key`。

**Remote CDM 模式（不需自備 WVD）：**

```
1. 下載 remote.json：
   https://github.com/user-attachments/files/21834836/remote.json

2. 打開 WidevineProxy2 擴充功能
   → 右上角選 Remote CDM（不是 WVD）
   → 點 Choose remote.json → 選剛才下載的檔案
   → 勾選 Enabled

3. 開啟博客來書本頁面並播放音訊

4. 擴充功能 Keys 欄位出現 kid:key
```

**成功後的解密流程（無需 WVD）：**

```bash
# 1. 下載加密音訊（yt-dlp）
yt-dlp --allow-unplayable-formats \
  -f bestaudio \
  -o "./downloads/enc_audio.%(ext)s" \
  "https://vod-ebook.books.com.tw/streaming/E070009570-5/master-dash/stream.mpd"

# 2. 解密（用 WidevineProxy2 取得的 kid:key）
mp4decrypt --key <kid>:<key> ./downloads/enc_audio.m4a ./downloads/decrypted.m4a

# 3. 轉 mp3
ffmpeg -i ./downloads/decrypted.m4a -vn -c:a libmp3lame -q:a 0 ./downloads/output.mp3
```

**風險：** Remote CDM 可能被 KeyOS License Server 拒絕（因 SecurityLevel=1 要求）。

---

### 方式 C：videohelp.com 現成 WVD（✅ 成功）

**狀態：** ✅ **成功 — 完整解密流程已驗證**

**來源：** [VideoHelp Real Device L3 CDMs](https://forum.videohelp.com/threads/417425-Real-Device-L3-Cdms)

**下載的 WVD：** `samsung_sm-a125f_16.0.0_e09f2dca_22589_l3.wvd`（Samsung SM-A125F，Android 16，L3）

**存放位置：** `tools/widevine_downloader/samsung_l3.wvd`

#### 驗證結果

```bash
# pywidevine test 通過（Bitmovin demo）
pywidevine test tools/widevine_downloader/samsung_l3.wvd
# → 成功解析 License，取得 Content Keys
```

#### 博客來實測

| 步驟 | 指令 / 結果 |
|------|------------|
| **取得 Content Key** | `KeyExtractor.auto()` → `bb1c06725b132bec4a3b74a1fe8495b4:f49790e9cdba77de9139c2299df0c809` |
| **下載加密音訊** | `yt-dlp --allow-unplayable-formats -f bestaudio -o "./downloads/enc_audio.%(ext)s" <mpd_url>` → `enc_audio.m4a`（8.2 MB） |
| **解密音訊** | `mp4decrypt --key <kid>:<key> enc_audio.m4a decrypted.m4a` |
| **轉 MP3** | `ffmpeg -i decrypted.m4a -vn -c:a libmp3lame -q:a 0 output.mp3` → 5 分 13 秒，244 kbps |

**關鍵發現：** KeyOS License Server 雖標示 `SecurityLevel=1`（L1 要求），但 **L3 CDM 仍成功取得 Content Key**（audio-only 軌道未強制執行）。

#### 完整指令

```bash
python download_cli.py \
  "https://vod-ebook.books.com.tw/streaming/E070009570-5/master-dash/stream.mpd" \
  --decrypt-widevine \
  --wvd-path tools/widevine_downloader/samsung_l3.wvd \
  --widevine-pssh "AAAAa3Bzc2gAAAAA7e+LqXnWSs6jyCfc1R0h7QAAAEsSELscBnJbEyvsSjt0of6ElbQaC2J1eWRybWtleW9zIiRlNGRhM2I3Zi1iYmNlLTIzNDUtZDc3Ny0yYjA2NzRhMzE4ZDVI49yVmwY=" \
  --widevine-license-url "https://widevine.keyos.com/api/v4/getLicense" \
  --widevine-headers '{"customdata":"<新的 customdata>","origin":"https://viewer-ebook.books.com.tw","referer":"https://viewer-ebook.books.com.tw/"}' \
  -f mp3
```
<新的 customdata>，<> 是多餘的，JSON 值不需要也不能包角括號。把 "<...>" 改成 "..." 即可
---

### 方式 D：實體 Android 裝置 + Frida

**狀態：** 🔲 不需要（方式 C 已成功）

使用真實 Android 手機，在**原生 App**（YouTube App、Netflix App）播放 DRM 內容時執行 dumper：

```bash
# 安裝修正後的 frida-server（對應手機 CPU 架構）
adb push frida-server /data/local/tmp/
adb shell chmod 755 /data/local/tmp/frida-server
adb shell nohup /data/local/tmp/frida-server &

# 執行修正後的 dumper
cd /path/to/dumper
PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python python dump_keys.py

# 在手機 YouTube App 播放任何有 Widevine 的影片
# dumper 輸出 key_dumps/ 目錄下的 private_key.pem + client_id.bin

# 打包成 WVD
pywidevine create-device \
  --type ANDROID \
  --security-level 3 \
  -k private_key.pem \
  -c client_id.bin \
  -o device.wvd
```

**注意事項：**
- 需 `adb root` 權限（rooted 手機或開發者模式的特定機型）
- 需在**原生 App** 播放，不能用 Chrome
- 小米手機需安裝 [liboemcrypto-disabler](https://github.com/umylive/liboemcrypto-disabler) Magisk 模組才能降級到 L3
- 使用修正後的 `script.js`（`Process.getModuleByName(name).enumerateExports()`）和 `Scanner.py`（`exports_sync`）

---

## 已知的 PSSH（可重複使用）

下次測試時直接使用，不需再偵測：

```
AAAAa3Bzc2gAAAAA7e+LqXnWSs6jyCfc1R0h7QAAAEsSELscBnJbEyvsSjt0of6ElbQaC2J1eWRybWtleW9zIiRlNGRhM2I3Zi1iYmNlLTIzNDUtZDc3Ny0yYjA2NzRhMzE4ZDVI49yVmwY=
```

> ⚠️ **customdata 每次需重新從瀏覽器取得**（1 小時有效），從 Network 面板 `widevine.keyos.com` 請求的 Request Headers 中複製。

---

## 後續行動

- [x] **C**：videohelp.com 搜尋現成 WVD，取得後用 CLI 工具測試完整流程（✅ 成功）
- [x] 確認 SecurityLevel=1 是否拒絕 L3 → **L3 CDM 可用，未拒絕**
- [x] 安裝 `mp4decrypt`（Bento4）→ 已透過 Homebrew 安裝
- [ ] 下次下載新書時需從瀏覽器 Network 面板取得新鮮的 `customdata`
- [ ] 若此 WVD 日後被 KeyOS 列入黑名單，可改用其他 VideoHelp WVD 或方式 D 自產

---

## 相關檔案

| 檔案 | 說明 |
|------|------|
| `docs/shared/p4_widevine_drm_decryption.md` | 主任務文件（程式碼實作） |
| `tools/widevine_downloader/drm_detector.py` | DRM 偵測（已修正 M3U8 子播放清單追蹤） |
| `tools/widevine_downloader/decryptor.py` | pywidevine 封裝（等待 WVD 測試） |
| `/tmp/opencode/dumper/` | wvdumper 修正版（Frida 17.x 相容，僅限原生 App） |


## 參考資料
https://www.reddit.com/r/software/comments/18hl3dp/is_there_really_a_drm_video_downloader_that_can/?tl=zh-hant
https://github.com/devine-dl/pywidevine
https://gist.github.com/frozenpandaman/a91f4dc7b999499761f798fdd6da6129