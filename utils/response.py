"""
統一回傳結構工具

error_code 對照表：
  WHITELIST_DENIED    - 白名單驗證失敗，提示使用者加入白名單
  YTDLP_NOT_FOUND     - 找不到 yt-dlp，提示安裝
  YTDLP_FAILED        - yt-dlp 執行失敗，可嘗試更新後重試
  DOWNLOAD_FAILED     - HTTP 下載失敗，可重試
  DOWNLOAD_TIMEOUT    - 下載逾時，可重試
  FILE_NOT_FOUND      - 輸入檔案不存在，請確認路徑
  CONVERSION_FAILED   - FFmpeg 轉換失敗，檢查輸入格式
  INVALID_CONTENT_TYPE - Content-Type 非預期，不應重試
  EMPTY_FILE          - 下載檔案為空，可重試
  SSL_ERROR           - SSL 憑證錯誤（已自動 fallback）
  INVALID_URL         - URL 格式錯誤，不應重試
  MISSING_PARAM       - 缺少必要參數
  UNKNOWN_ERROR       - 未預期的錯誤
"""


def success_response(**kwargs) -> dict:
    """建立成功回傳結構"""
    return {"success": True, **kwargs}


def error_response(code: str, message: str, **kwargs) -> dict:
    """建立失敗回傳結構，含結構化 error_code"""
    return {
        "success": False,
        "error_code": code,
        "error": message,
        **kwargs
    }
