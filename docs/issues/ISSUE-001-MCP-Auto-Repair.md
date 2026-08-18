# ISSUE-001: MCP 啟動失敗不會自動修復

> 狀態: ✅ 已解決
> 日期: 2026-05-19
> 分類: MCP 穩定性

---

## 問題描述

`media-downloader` MCP 在 Claude Desktop 啟動時，若套件版本過舊（特別是 `yt-dlp`），會直接失敗且不會自動修復。使用者需要手動重新開啟 Claude Desktop 或手動更新套件才能恢復正常。

### 錯誤症狀

- MCP 工具無回應或顯示連線失敗
- 下載時出現 `TypeError: Cannot read properties of undefined (reading 'origin')` 錯誤
- 根本原因：`yt-dlp` JavaScript 挑戰解析器過時，YouTube 更新反爬蟲機制後失效

### 根本原因

YouTube 會定期更新反爬蟲機制，`yt-dlp` 需要跟進更新才能正常運作。Claude Desktop 設定直接指向 Python 執行檔，啟動時不會自動更新套件，導致版本過期後靜默失敗。

---

## 解決方案

建立啟動包裝腳本 `start_mcp.sh`，由 Claude Desktop 改呼叫此腳本，每次啟動 MCP 時自動完成修復流程。

### 新增檔案

**`start_mcp.sh`**（專案根目錄）

```bash
#!/bin/bash
# 每次啟動時自動更新 yt-dlp、補裝套件、清除快取，再啟動 server
```

修復流程：
1. 更新 `yt-dlp` 至最新版本
2. 靜默補裝 `requirements.txt` 所有依賴
3. 清除 `yt-dlp` 快取（`--rm-cache-dir`）
4. 用 `exec` 啟動 `server.py`（確保 STDIO 正確繼承）

啟動日誌寫入 `mcp_startup.log`，可用於排查問題。

### 設定變更

**`~/Library/Application Support/Claude/claude_desktop_config.json`**

```diff
 "media-downloader": {
-  "command": "/Users/alexander/PycharmProjects/DownloadVideoPythonProject/.venv/bin/python",
-  "args": ["...server.py"]
+  "command": "/bin/bash",
+  "args": ["/Users/alexander/PycharmProjects/DownloadVideoPythonProject/start_mcp.sh"]
 }
```

---

## 驗證

測試結果：
- `start_mcp.sh` 執行後 MCP server 正常啟動
- `mcp_startup.log` 正確記錄每次更新與啟動狀態
- `yt-dlp` 更新後下載功能恢復正常

---

## 注意事項

- 每次 Claude Desktop 啟動時都會執行一次 `pip install --upgrade yt-dlp`，約需 1-3 秒，屬正常現象
- 若日後需要禁用自動更新，可在 `start_mcp.sh` 中註解掉對應的 `pip install` 行
- `kyoto-assistant` MCP 無此問題，暫不套用相同方案

---

## 本方案的適用範圍（2026-08-18 補充）

`start_mcp.sh` 只能修復「**套件版本過舊**」這一類失敗。YouTube 反爬變更實際上有兩種形態：

| 形態 | 症狀 | 本方案能否修復 |
|------|------|----------------|
| yt-dlp 版本過舊 | 解析失敗、JS 挑戰失效 | ✅ 可以，自動更新即解決 |
| 需調整呼叫參數 | 版本已最新仍失敗（如 player client 被擋） | ❌ 不行，必須改程式碼 |

第二種形態的實例見 [ISSUE-003](ISSUE-003-YouTube-403-Player-Client.md)：yt-dlp 已是最新版，但預設 player client 遭 YouTube 回 403，自動更新完全無效。

> ⚠️ **重要**：修改 `server.py`、`utils/` 等 Python 程式碼後，**必須完全重啟 Claude Desktop** 才會生效。MCP server 是啟動時將程式碼載入記憶體的子進程，不會熱重載。`start_mcp.sh` 在這種情況下的作用只是「讓進程重新啟動」，與它的自動更新流程無關。
>
> 確認新程式碼已生效：
> ```bash
> ps -eo pid,lstart,command | grep "DownloadVideoPythonProject/server.py" | grep -v grep
> ```
> 啟動時間應晚於程式碼的修改時間。

---

## 腳本強化（2026-08-18）

針對長期運行下暴露的三個弱點修正 `start_mcp.sh`：

| 問題 | 修正 |
|------|------|
| 日誌無限增長，從不輪替 | 超過 1 MB 自動轉存為 `mcp_startup.log.1`，只保留一份舊檔 |
| 離線時 pip 反覆重試，拖住 MCP 啟動約 99 秒 | 加上 `--timeout 10 --retries 1`，離線啟動縮短至約 21 秒 |
| 每次啟動都清 yt-dlp 快取，反而拖慢首次下載 | 改為**僅在 yt-dlp 版本確實變動時**才清快取 |

其他調整：

- 加上 `--disable-pip-version-check`，消除日誌中的 "A new release of pip" 噪音
- 依賴安裝失敗（離線）時記錄警告並繼續啟動，不再靜默略過
- 補上註解說明：本腳本以 STDIO 溝通，所有輸出都必須導向日誌，不可寫入 stdout

> 保留「版本變動才清快取」而非完全移除，是因為 yt-dlp 升級後舊快取可能與新版不相容；平時保留快取則可避免每次啟動後首次下載都要重新解析 player JS。
