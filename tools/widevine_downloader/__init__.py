"""
tools.widevine_downloader — Widevine DRM 解密模組（研究用途）

主要匯出：
  - WidevineDecryptor    核心解密類別
  - KeyExtractor         金鑰提取輔助
  - DrmInfo / DrmType    DRM 偵測結果資料類別
  - detect_from_url      快速偵測 Manifest DRM
  - parse_manifest_mpd   解析 MPD 字串
  - parse_manifest_m3u8  解析 M3U8 字串

注意事項：
  - 需自備 WVD device file（本專案不提供）
  - 需安裝 mp4decrypt 或 shaka-packager 才能解密檔案
  - 僅供研究用途，使用者自行承擔法律責任
"""

from .decryptor import (
    WidevineDecryptor,
    WvdNotFoundError,
    LicenseServerError,
    DecryptToolNotFoundError,
)
from .drm_detector import (
    DrmInfo,
    DrmType,
    DrmLevel,
    detect_from_url,
    parse_manifest_mpd,
    parse_manifest_m3u8,
)
from .key_extractor import KeyExtractor

__all__ = [
    # decryptor
    "WidevineDecryptor",
    "WvdNotFoundError",
    "LicenseServerError",
    "DecryptToolNotFoundError",
    # drm_detector
    "DrmInfo",
    "DrmType",
    "DrmLevel",
    "detect_from_url",
    "parse_manifest_mpd",
    "parse_manifest_m3u8",
    # key_extractor
    "KeyExtractor",
]
