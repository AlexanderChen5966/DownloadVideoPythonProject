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
