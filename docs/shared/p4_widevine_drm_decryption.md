# P4：Widevine DRM 解密下載（研究用途）

**優先級：** Low（研究性功能）
**建立日期：** 2026-06-30
**完成日期：** 2026-06-30
**狀態：** ✅ 完整流程已驗證（VideoHelp WVD + 博客來實測成功）
**影響路徑：** `tools/widevine_downloader/`（新增模組）、`download_cli.py`、`docs/shared/dash_stream_download_notes.md`

---

## 背景

現有下載器遇到 Widevine DRM 保護的串流時，只能回報「DRM，放棄」（見 `dash_stream_download_notes.md`）。使用者希望為研究用途，在專案中新增一套可選用的 Widevine L3 解密下載流程，能對特定平台（如 Rakuten TV、部分 OTT）的音訊內容進行解密與下載。

此功能**不作為預設啟用**，需使用者自備 WVD device file 並明確指定啟用，以符合研究目的之定位。

---

## 實作完成項目

### 新增模組 `tools/widevine_downloader/`

| 檔案 | 功能 |
|------|------|
| `drm_detector.py` | 解析 MPD/M3U8，偵測 Widevine/PlayReady/FairPlay，提取 PSSH |
| `decryptor.py` | 封裝 pywidevine CDM，支援 `get_content_keys()` + `decrypt_file()` + `full_pipeline()` |
| `key_extractor.py` | 三種模式：自動/手動/偵測 Manifest，含互動式 CLI |
| `__init__.py` | 統一匯出所有公開 API |

### 修改既有檔案

| 檔案 | 修改內容 |
|------|---------|
| `download_cli.py` | 新增 `--decrypt-widevine`、`--wvd-path`、`--widevine-pssh`、`--widevine-license-url`、`--widevine-headers`、`--detect-drm` |
| `requirements.txt` | 新增 `pywidevine>=1.9.0` |

### CLI 使用方式

```bash
# 偵測 DRM 類型
python download_cli.py --detect-drm "https://...stream.mpd"

# 完整解密下載（需 WVD）
python download_cli.py "https://...stream.mpd" \
  --decrypt-widevine \
  --wvd-path /path/to/device.wvd \
  --widevine-pssh "AAAA..." \
  --widevine-license-url "https://license.example.com/..." \
  --widevine-headers '{"Authorization": "Bearer xxx"}' \
  -f mp3

# 互動式金鑰提取
python -m tools.widevine_downloader.key_extractor --wvd /path/to/device.wvd
```

---

## 實測紀錄：博客來電子書（vod-ebook.books.com.tw）

**測試日期：** 2026-06-30

### DRM 偵測結果

```
DASH (stream.mpd)
  DRM 類型   ：Widevine L3
  PSSH       ：AAAAa3Bzc2gAAAAA7e+LqXnWSs6jyCfc1R0h7QAAAEsSELscBnJbEyvs...
  License URL：https://widevine.keyos.com/api/v4/getLicense（KeyOS 平台）

HLS (master.m3u8)
  master 層  ：無 DRM 標記（偵測為 none）← 誤判
  子播放清單 ：EXT-X-KEY METHOD=SAMPLE-AES, URI="skd://..."（FairPlay）
```

> ⚠️ **DRM 偵測器漏洞**：`drm_detector.py` 的 M3U8 偵測只讀 master playlist，沒有追入子播放清單（media playlist），會漏掉 `EXT-X-KEY`。待修。

### License Server 測試

```python
# 送假 challenge（100 bytes random），測試 customdata 認證是否通過
POST https://widevine.keyos.com/api/v4/getLicense
headers: {customdata: "...", origin: "https://viewer-ebook.books.com.tw", ...}

# 結果
HTTP 403
{"errorcode": 371000005,
 "errormsg": "Widevine license generation failed (SIGNED_MESSAGE_PARSE_ERROR)",
 "errorid": "..."}
```

**結論：`customdata` 認證通過**（403 是 challenge 格式錯誤，不是 auth 錯誤）。
有效的 WVD challenge 理論上能正確取得 Content Key。

### customdata 特性

```xml
<WidevineContentKeySpec TrackType="HD">
    <SecurityLevel>1</SecurityLevel>  ← 要求 L1
</WidevineContentKeySpec>
<ExpirationTime>... 1 小時後過期 ...</ExpirationTime>
```

- Token **每次頁面載入重新產生**，有效期 1 小時
- SecurityLevel=1 要求 → **實測 L3 CDM 未被拒絕**（audio-only 軌道未強制執行）
- 從瀏覽器 Network 面板 → 搜尋 `widevine.keyos.com` → Request Headers → `customdata` 欄位取得

---

## WVD 取得方式研究紀錄

### 方式 A：Android 模擬器 + Frida dumper ❌ 失敗

**嘗試工具：** [wvdumper/dumper](https://github.com/wvdumper/dumper)

**環境：**
- Android Studio AVD：Pixel 3a, API 28 (arm64-v8a)
- frida-server 17.15.3

**發現的問題與修正：**

| 問題 | 原因 | 修正 |
|------|------|------|
| `TypeError: not a function` | Frida 17.x 移除 `Module.enumerateExportsSync` | 改為 `Process.getModuleByName(name).enumerateExports()` |
| `Script.exports` 棄用警告 | Frida 17.x 新 API | 改為 `script.exports_sync` |
| protobuf 版本衝突 | dumper 使用舊版 protobuf 生成碼 | 加環境變數 `PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python` |
| 鉤錯進程 | 以為是 `@1.0-service`（pid=315）| 實際為 `@1.3-service.widevine`（pid=317）|
| 動態函式名稱不符 | dumper 硬編碼舊版名稱（`polorucp` 等） | 此版本 CDM 名稱完全不同（`vyxlkkyb` 等） |

**最終失敗原因：**
Chrome 瀏覽器有自己內建的 Widevine CDM，**不經過** Android 系統的 `libwvdrmengine.so` / `libwvhidl.so`。Frida 掛的 hook 完全不會被觸發。`wvdumper/dumper` 只對**原生 Android App**（Netflix App、YouTube App）有效，不適用於模擬器內的 Chrome。

**進程與模組對應關係（已確認）：**

| 進程 | PID | Widevine 模組 | `_lcc*` 函式 |
|------|-----|--------------|-------------|
| `android.hardware.drm@1.0-service` | 315 | `libwvdrmengine.so` | 139 個 |
| `android.hardware.drm@1.3-service.widevine` | 317 | `libwvhidl.so` | 139 個 |
| `android.hardware.drm@1.3-service.clearkey` | 316 | — | — |

---

### 方式 B：WidevineProxy2 + Remote CDM（已不需要）

**工具：** [DevLARLEY/WidevineProxy2](https://github.com/DevLARLEY/WidevineProxy2)

WidevineProxy2 是金鑰攔截器，Remote CDM 模式可不需自備 WVD。
實測 Remote CDM 無反應，且方式 C 已成功，不再嘗試。

---

### 方式 C：videohelp.com 現成 WVD ✅ 成功

下載自 [VideoHelp Real Device L3 CDMs](https://forum.videohelp.com/threads/417425-Real-Device-L3-Cdms)

**WVD 檔案：** `tools/widevine_downloader/samsung_l3.wvd`
**來源裝置：** Samsung SM-A125F, Android 16, L3 (22589)

**博客來實測結果（2026-06-30）：**

| 步驟 | 結果 |
|------|------|
| License Server | `https://widevine.keyos.com/api/v4/getLicense` → ✅ 接受 L3 CDM |
| Content Key | `bb1c06725b132bec4a3b74a1fe8495b4:f49790e9cdba77de9139c2299df0c809` |
| 解密 + 轉 MP3 | 5 分 13 秒音訊，244 kbps，播放正常 |

**SecurityLevel=1 驗證：** KeyOS 雖標示 L1 要求，但 L3 CDM 仍成功取得 Content Key（audio-only 未強制執行）。

---

### 方式 D：實體 Android 裝置 + Frida（備用）

若方式 C 的 WVD 日後被 KeyOS 列入黑名單，再用此方式自行提取。
完整步驟見 `docs/issues/ISSUE-002-Widevine-WVD-Research.md`。

---

## 已知限制與注意事項

1. **M3U8 偵測器漏洞**：只讀 master playlist，不追子播放清單。博客來 HLS 的 FairPlay 被誤判為 none。
2. ~~SecurityLevel=1 風險~~ → **已驗證 L3 CDM 可用**（audio-only 未強制執行）
3. **customdata 1 小時過期**：每次下載前需重新從瀏覽器取得。
4. **FairPlay 無法解密**：`skd://` 協定為 Apple 硬體安全，軟體無解。
5. **WVD**：`tools/widevine_downloader/samsung_l3.wvd`（VideoHelp 下載），若遭 KeyOS 封鎖需更換。

---

## 後續行動

- [x] 修正 `drm_detector.py` 的 M3U8 偵測：追入子播放清單讀取 `EXT-X-KEY`（`drm_detector.py:199-240`）
- [x] 從 VideoHelp 取得現成 L3 WVD（方式 C ✅ 成功）
- [x] 用 CLI 工具完整測試 `--decrypt-widevine` 流程（博客來實測通過）
- [ ] 若 `samsung_l3.wvd` 日後被 KeyOS 封鎖，改用其他 VideoHelp WVD 或方式 D 自行提取

---

## 相關檔案

| 檔案 | 說明 |
|------|------|
| `tools/widevine_downloader/__init__.py` | 模組匯出 |
| `tools/widevine_downloader/drm_detector.py` | DRM 偵測（含已知 M3U8 漏洞） |
| `tools/widevine_downloader/decryptor.py` | pywidevine 封裝 |
| `tools/widevine_downloader/key_extractor.py` | 金鑰提取互動介面 |
| `download_cli.py` | CLI 整合（`--decrypt-widevine` 等參數） |
| `requirements.txt` | 新增 `pywidevine>=1.9.0` |
| `tools/widevine_downloader/samsung_l3.wvd` | VideoHelp 下載的 L3 WVD（Samsung SM-A125F） |
| `docs/issues/ISSUE-002-Widevine-WVD-Research.md` | WVD 取得方式完整研究紀錄 |
| `/tmp/opencode/dumper/` | wvdumper 修正版（含 Frida 17.x 相容修正） |
