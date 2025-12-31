
名稱：DownloadImageMCP
語言：Python
用途：提供 Claude 能依據網址下載圖片並轉成 JPG。

Tool 1：download_and_convert_image
參數：
  - url (string, required)：圖片網址
  - filename (string, optional)：自訂輸出檔名（不含副檔名）

流程：
  1. 檢查 URL 是否為 HTTP/HTTPS。
  2. 下載圖片 headers。
  3. 若 Content-Type 非 image/* → 回傳錯誤。
  4. 下載圖片內容。
  5. 使用 Pillow 開啟圖片。
  6. 自動轉成 RGB → 儲存成 JPG。
  7. 檔名格式：若未指定 filename → timestamp 自動產生。
  8. 儲存至：`<project_root>/images/xxx.jpg`
  9. 回傳：
     - success
     - saved_path
     - original_format

錯誤處理：
  - 下載失敗：回傳錯誤
  - 非圖片檔案：拒絕
  - Pillow 無法解析：回報錯誤

依賴套件：
  - Pillow
  - requests
  - mcp
