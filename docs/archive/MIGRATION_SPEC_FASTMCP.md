# FastMCP 2.0 遷移規格書

## 📋 文件資訊
- **專案名稱**: 多媒體下載與轉檔 MCP 伺服器
- **遷移類型**: 官方 MCP Python SDK → FastMCP 2.0
- **文件版本**: 1.0
- **建立日期**: 2025-12-11
- **預估修改範圍**: 中等（主要在 server.py 和 requirements.txt）

---

## 🎯 遷移目標與預期效益

### 遷移目標
將現有基於官方 MCP Python SDK 的專案遷移至 FastMCP 2.0，以獲得更好的開發體驗和生產級功能。

### 預期效益
1. **減少程式碼量**: 預計減少 30-40% 的樣板代碼
2. **自動 Schema 生成**: 從函數簽名和 docstring 自動生成工具 schema
3. **更好的類型安全**: 利用 Python 類型提示自動驗證
4. **簡化工具定義**: 使用單一 `@mcp.tool()` 裝飾器取代複雜的手動定義
5. **生產就緒功能**: 獲得企業級認證、測試框架等進階功能

---

## 📊 影響範圍評估

### 需要修改的檔案
| 檔案路徑 | 修改程度 | 說明 |
|---------|---------|------|
| `requirements.txt` | ⭐ 低 | 更新依賴套件 |
| `server.py` | ⭐⭐⭐ 高 | 核心邏輯重構 |
| `claude_desktop_config.example.json` | ⭐ 低 | 可能需要更新啟動指令（若有變更） |

### 不需修改的檔案
- `tools/` 目錄下的所有模組（保持不變）
- `utils/` 目錄下的所有工具函數（保持不變）
- `download_cli.py`（獨立的 CLI 工具）
- 所有配置文件和文檔

### 修改範圍總結
- **總檔案數**: 2-3 個主要檔案
- **預估工作量**: 2-4 小時
- **風險等級**: 🟢 低（主要是 API 替換，業務邏輯不變）

---

## 🔄 詳細修改規格

### 1. requirements.txt 修改

#### 現有內容
```text
mcp>=1.0.0
yt-dlp>=2024.0.0
Pillow>=10.0.0
requests>=2.31.0
feedparser>=6.0.0
m3u8>=3.5.0
tqdm>=4.65.0
```

#### 修改後內容
```text
# FastMCP 2.0 - 主要 MCP 框架
fastmcp>=2.0.0

# 媒體下載與處理
yt-dlp>=2024.0.0
Pillow>=10.0.0
requests>=2.31.0
feedparser>=6.0.0
m3u8>=3.5.0
tqdm>=4.65.0
```

#### 變更說明
- 移除 `mcp>=1.0.0`
- 新增 `fastmcp>=2.0.0`
- 保留所有其他依賴不變

---

### 2. server.py 核心重構

#### 2.1 Import 語句變更

**現有程式碼**（第 18-20 行）:
```python
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
```

**修改後**:
```python
from fastmcp import FastMCP
```

**變更說明**:
- FastMCP 提供統一的 API，不需要分別 import Server、stdio_server、Tool、TextContent
- 大幅簡化 import 語句

---

#### 2.2 伺服器初始化變更

**現有程式碼**（第 31 行）:
```python
app = Server("media-downloader")
```

**修改後**:
```python
mcp = FastMCP("media-downloader")
```

**變更說明**:
- 使用 `FastMCP` 類別取代 `Server`
- 慣例上使用 `mcp` 作為實例名稱（而非 `app`）

---

#### 2.3 工具定義方式重構

這是最大的變更點。FastMCP 使用裝飾器直接在函數上定義工具，而不需要手動編寫 inputSchema。

**現有模式**（約 250 行程式碼）:
```python
@app.list_tools()
async def list_tools() -> list[Tool]:
    """列出所有可用的工具"""
    return [
        Tool(
            name="download_media",
            description="使用 yt-dlp 下載 YouTube 影片或音檔...",
            inputSchema={
                "type": "object",
                "properties": {
                    "urls": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "要下載的媒體 URL 列表..."
                    },
                    # ... 更多手動定義
                },
                "required": ["urls"]
            }
        ),
        # ... 重複 10 次，共 11 個工具
    ]

@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """處理工具呼叫"""
    if name == "download_media":
        result = await download_media(...)
        return [TextContent(type="text", text=json.dumps(result, ...))]
    elif name == "convert_to_mp3":
        # ... 重複 11 次
```

**修改後的模式**（每個工具僅需裝飾器 + docstring）:
```python
@mcp.tool()
async def download_media(
    urls: list[str],
    output_dir: str = "./downloads",
    format: str = "audio"
) -> dict:
    """
    使用 yt-dlp 下載 YouTube 影片或音檔，支援批量下載多個 URL

    Args:
        urls: 要下載的媒體 URL 列表（支援 YouTube、Podcast 等）
        output_dir: 下載檔案的輸出目錄路徑
        format: 下載格式，可選 'audio'（僅音檔）、'video'（影片）、'best'（最佳品質）

    Returns:
        包含下載結果的字典，含成功/失敗數量、檔案列表和錯誤資訊
    """
    # 確保輸出目錄存在
    os.makedirs(output_dir, exist_ok=True)
    # ... 原有的業務邏輯保持不變
    return {
        "success": len(saved_files),
        "failed": len(errors),
        "saved_files": saved_files,
        "errors": errors,
        "output_dir": output_dir
    }
```

**關鍵優勢**:
1. ✅ FastMCP 自動從函數簽名生成 inputSchema
2. ✅ 類型提示（`urls: list[str]`）自動轉換為 JSON Schema
3. ✅ Docstring 自動解析為工具描述
4. ✅ 不需要手動處理 `call_tool()` 路由
5. ✅ 自動處理結果序列化，直接返回 dict/str 即可

---

#### 2.4 所有 11 個工具的重構對照表

| 工具名稱 | 現有行數 | 修改後行數 | 減少百分比 |
|---------|---------|-----------|-----------|
| `download_media` | ~50 行 | ~25 行 | 50% |
| `convert_to_mp3` | ~40 行 | ~20 行 | 50% |
| `ensure_directory` | ~20 行 | ~10 行 | 50% |
| `list_files` | ~35 行 | ~18 行 | 48% |
| `open_file` | ~25 行 | ~12 行 | 52% |
| `download_and_convert_image` | ~40 行 | ~20 行 | 50% |
| `podcast_downloader` | ~30 行 | ~15 行 | 50% |
| `download_hls` | ~45 行 | ~22 行 | 51% |
| `whitelist_add_rule` | ~15 行 | ~8 行 | 46% |
| `whitelist_remove_rule` | ~15 行 | ~8 行 | 46% |
| `whitelist_list_rules` | ~12 行 | ~6 行 | 50% |
| `whitelist_set_enabled` | ~15 行 | ~8 行 | 46% |
| `direct_download_audio` | ~20 行 | ~10 行 | 50% |
| **總計** | **~362 行** | **~182 行** | **約 50%** |

---

#### 2.5 主函數修改

**現有程式碼**（第 788-800 行）:
```python
async def main():
    """啟動 MCP 伺服器"""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

**修改後**:
```python
if __name__ == "__main__":
    mcp.run()
```

**變更說明**:
- FastMCP 內建簡化的啟動方法
- 自動處理 stdio transport 和事件循環
- 從 8 行簡化為 2 行

---

### 3. 類型提示增強建議（選用）

FastMCP 支援更豐富的類型提示，可以進一步改善開發體驗：

**現有**:
```python
async def download_media(urls: list[str], output_dir: str, format: str) -> dict:
```

**增強版**（使用 Literal 限制選項）:
```python
from typing import Literal

async def download_media(
    urls: list[str],
    output_dir: str = "./downloads",
    format: Literal["audio", "video", "best"] = "audio"
) -> dict:
```

**好處**:
- IDE 自動完成提示
- FastMCP 自動生成 enum 限制的 schema
- 類型檢查更嚴格

---

### 4. 錯誤處理變更

**現有模式**:
```python
@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    try:
        if name == "download_media":
            result = await download_media(...)
            return [TextContent(type="text", text=json.dumps(result, ...))]
    except Exception as e:
        return [TextContent(type="text", text=f"錯誤: {str(e)}")]
```

**FastMCP 模式**:
```python
@mcp.tool()
async def download_media(...) -> dict:
    # FastMCP 自動捕獲異常並格式化錯誤訊息
    # 可以直接拋出異常，或返回包含 error 的 dict
    if error_condition:
        raise ValueError("清晰的錯誤訊息")
    return {"success": True, ...}
```

**變更說明**:
- FastMCP 自動處理異常格式化
- 可以使用標準 Python 異常
- 不需要手動包裝為 TextContent

---

## 🔧 遷移步驟（實施計畫）

### Phase 1: 環境準備
1. ✅ **備份現有專案**
   ```bash
   git commit -am "Backup before FastMCP migration"
   ```

2. ✅ **更新依賴**
   ```bash
   pip uninstall mcp
   pip install fastmcp>=2.0.0
   ```

3. ✅ **驗證安裝**
   ```bash
   python -c "import fastmcp; print(fastmcp.__version__)"
   ```

### Phase 2: 程式碼重構
1. ✅ **修改 server.py - Import 區塊**
   - 更新第 18-20 行的 import 語句

2. ✅ **修改 server.py - 伺服器初始化**
   - 更新第 31 行的實例化

3. ✅ **重構工具定義**（建議逐個遷移，每次測試）
   - 將 `@app.list_tools()` 和 `@app.call_tool()` 替換為 `@mcp.tool()`
   - 為每個工具函數添加類型提示和詳細 docstring
   - 移除手動 schema 定義

4. ✅ **簡化主函數**
   - 替換第 788-800 行為 `mcp.run()`

### Phase 3: 測試驗證
1. ✅ **單元測試**
   - 測試每個工具的基本功能
   - 驗證參數驗證是否正常

2. ✅ **整合測試**
   - 在 Claude Desktop 中測試所有 11 個工具
   - 驗證白名單功能正常運作

3. ✅ **效能測試**
   - 對比遷移前後的回應時間
   - 確保無效能退化

### Phase 4: 文檔更新
1. ✅ 更新 README.md 中的安裝指令
2. ✅ 更新 claude_desktop_config.example.json（如需要）
3. ✅ 記錄遷移日期和版本於 CHANGELOG

---

## 🧪 測試檢查清單

### 功能測試
- [ ] `download_media` - 下載單個和多個 URL
- [ ] `convert_to_mp3` - 轉換各種格式
- [ ] `ensure_directory` - 建立目錄
- [ ] `list_files` - 列出檔案和過濾
- [ ] `open_file` - 開啟檔案/資料夾
- [ ] `download_and_convert_image` - 圖片下載與轉換
- [ ] `podcast_downloader` - Podcast 下載
- [ ] `download_hls` - HLS 串流下載
- [ ] `whitelist_add_rule` - 新增白名單規則
- [ ] `whitelist_remove_rule` - 移除白名單規則
- [ ] `whitelist_list_rules` - 列出白名單
- [ ] `whitelist_set_enabled` - 啟用/停用白名單
- [ ] `direct_download_audio` - 直接音檔下載

### 錯誤處理測試
- [ ] 無效 URL 測試
- [ ] 白名單阻擋測試
- [ ] 檔案不存在測試
- [ ] 權限錯誤測試
- [ ] 網路錯誤測試

### 整合測試
- [ ] Claude Desktop 連接正常
- [ ] 所有工具在 Claude 中可見
- [ ] 參數提示正確顯示
- [ ] 錯誤訊息清晰易懂

---

## ⚠️ 風險評估與應對

### 可能的風險
1. **API 不相容性**
   - **風險**: FastMCP 2.0 某些行為與官方 SDK 不同
   - **應對**: 充分測試每個工具，參考官方遷移指南

2. **類型提示問題**
   - **風險**: 某些複雜類型可能無法正確轉換為 JSON Schema
   - **應對**: 使用 `from typing import Any` 作為備選方案

3. **依賴衝突**
   - **風險**: FastMCP 可能與現有套件版本衝突
   - **應對**: 使用虛擬環境隔離，逐步更新相關依賴

### 回滾計畫
如果遷移失敗，可以快速回滾：
```bash
git reset --hard HEAD~1
pip uninstall fastmcp
pip install mcp>=1.0.0
```

---

## 📈 預期成果

### 程式碼品質改善
- ✅ 程式碼行數減少約 **180 行**（從 801 行 → 約 620 行）
- ✅ 複雜度降低（去除手動路由邏輯）
- ✅ 可讀性提升（裝飾器模式更直觀）
- ✅ 維護性增強（schema 由類型提示自動生成）

### 開發效率提升
- ✅ 新增工具時間減少 **50%**（不需手動編寫 schema）
- ✅ 調試更容易（類型提示支援 IDE 自動完成）
- ✅ 錯誤更少（自動驗證減少手動錯誤）

### 功能增強（未來可選）
FastMCP 2.0 提供額外功能，可在未來考慮使用：
- 企業級認證（Google、GitHub、Azure 等）
- 伺服器組合（將多個 MCP 伺服器組合）
- 從 OpenAPI 自動生成工具
- 內建測試框架
- 可觀測性和日誌記錄

---

## 📚 參考資源

### 官方文檔
- [FastMCP 2.0 官方文檔](https://gofastmcp.com/)
- [FastMCP GitHub](https://github.com/jlowin/fastmcp)
- [遷移指南](https://github.com/modelcontextprotocol/python-sdk/issues/1068)

### 範例專案
- [FastMCP 範例](https://github.com/jlowin/fastmcp/tree/main/examples)
- [社群最佳實踐](https://medium.com/@shmilysyg/fastmcp-the-fastway-to-build-mcp-servers-aa14f88536d2)

---

## ✅ 結論

### 是否建議遷移？
**✅ 強烈建議遷移**

### 理由
1. **程式碼品質顯著提升**：減少約 50% 的樣板代碼
2. **風險可控**：主要是 API 替換，業務邏輯不變
3. **未來擴展性**：FastMCP 2.0 提供更多生產級功能
4. **社群趨勢**：FastMCP 是 2025 年的主流推薦

### 預估完成時間
- **準備與規劃**: 30 分鐘
- **程式碼重構**: 2-3 小時
- **測試驗證**: 1 小時
- **文檔更新**: 30 分鐘
- **總計**: 約 4-5 小時

### 建議執行時機
建議在以下情況執行遷移：
- ✅ 沒有緊急功能開發
- ✅ 有完整時間進行測試
- ✅ 已做好程式碼備份

---

**文件結束**

如有任何問題或需要協助，請參考上述「參考資源」或聯繫 FastMCP 社群。
