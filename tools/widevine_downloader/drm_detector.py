"""
DRM 偵測器：解析 DASH MPD / HLS M3U8 manifest，判斷 DRM 類型與可解密性。

支援偵測：
- Widevine  (urn:uuid:edef8ba9-79d6-4ace-a3c8-27dcd51d21ed)
- PlayReady (urn:uuid:9a04f079-9840-4286-ab92-e65be0885f95)
- FairPlay  (skd:// protocol)
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from enum import Enum

import requests


# ── Widevine UUID ──────────────────────────────────────────────────────────────
_WIDEVINE_UUID   = "edef8ba9-79d6-4ace-a3c8-27dcd51d21ed"
_PLAYREADY_UUID  = "9a04f079-9840-4286-ab92-e65be0885f95"
_WIDEVINE_SCHEME = f"urn:uuid:{_WIDEVINE_UUID}"
_PLAYREADY_SCHEME = f"urn:uuid:{_PLAYREADY_UUID}"

# MPD 命名空間
_MPD_NS = {
    "mpd":  "urn:mpeg:dash:schema:mpd:2011",
    "cenc": "urn:mpeg:cenc:2013",
    "mspr": "urn:microsoft:playready",
}


class DrmType(Enum):
    WIDEVINE  = "widevine"
    PLAYREADY = "playready"
    FAIRPLAY  = "fairplay"
    NONE      = "none"
    UNKNOWN   = "unknown"


class DrmLevel(Enum):
    L1      = "L1"      # 硬體安全等級，無法軟體解密
    L3      = "L3"      # 軟體安全等級，可用 pywidevine 解密
    UNKNOWN = "unknown"


@dataclass
class DrmInfo:
    drm_type:    DrmType  = DrmType.NONE
    drm_level:   DrmLevel = DrmLevel.UNKNOWN
    pssh:        str | None = None   # Base64 PSSH data（Widevine 專用）
    license_url: str | None = None
    raw_schemes: list[str] = field(default_factory=list)  # 原始 schemeIdUri 清單

    @property
    def is_protected(self) -> bool:
        return self.drm_type != DrmType.NONE

    @property
    def can_decrypt_with_pywidevine(self) -> bool:
        """是否可以用 pywidevine（L3）解密"""
        return (
            self.drm_type == DrmType.WIDEVINE
            and self.drm_level in (DrmLevel.L3, DrmLevel.UNKNOWN)
        )

    def summary(self) -> str:
        if not self.is_protected:
            return "無 DRM 保護，可直接下載"
        if self.drm_type == DrmType.WIDEVINE:
            level = self.drm_level.value
            if self.can_decrypt_with_pywidevine:
                return f"Widevine {level}（可嘗試 pywidevine 解密）"
            return f"Widevine L1（硬體安全，無法軟體解密）"
        if self.drm_type == DrmType.PLAYREADY:
            return "PlayReady DRM（本工具不支援）"
        if self.drm_type == DrmType.FAIRPLAY:
            return "FairPlay DRM（Apple 裝置專用，本工具不支援）"
        return f"未知 DRM 類型：{self.raw_schemes}"


# ── 解析 MPD ──────────────────────────────────────────────────────────────────

def _find_widevine_pssh(root: ET.Element) -> str | None:
    """從 MPD XML 中找 Widevine 的 cenc:pssh Base64 值"""
    # 嘗試帶命名空間與不帶命名空間兩種搜尋方式
    for prefix, uri in _MPD_NS.items():
        for pssh_el in root.iter(f"{{{uri}}}pssh"):
            return (pssh_el.text or "").strip() or None
    # fallback：直接掃所有 pssh tag
    for pssh_el in root.iter("pssh"):
        return (pssh_el.text or "").strip() or None
    return None


def _find_license_url_from_mpd(root: ET.Element) -> str | None:
    """嘗試從 MPD ContentProtection 節點解析 license server URL"""
    # 部分平台把 License URL 放在 <ms:laurl> 或 Laurl 屬性裡
    for el in root.iter():
        tag_local = el.tag.split("}")[-1].lower() if "}" in el.tag else el.tag.lower()
        if tag_local in ("laurl", "licenseurl"):
            return (el.text or "").strip() or el.get("licenseUrl") or None
        # 部分 PlayReady WRMHEADER 解析略過
    return None


def parse_manifest_mpd(content: str) -> DrmInfo:
    """
    解析 DASH MPD 內容字串，回傳 DrmInfo。

    Args:
        content: MPD XML 字串

    Returns:
        DrmInfo 物件
    """
    info = DrmInfo()

    try:
        root = ET.fromstring(content)
    except ET.ParseError:
        # 若 XML 解析失敗，改用 regex 快速掃描
        return _fallback_regex_detect(content)

    # 收集所有 ContentProtection 的 schemeIdUri
    schemes: list[str] = []
    for el in root.iter():
        tag_local = el.tag.split("}")[-1] if "}" in el.tag else el.tag
        if tag_local.lower() == "contentprotection":
            scheme = (el.get("schemeIdUri") or "").lower()
            if scheme:
                schemes.append(scheme)

    info.raw_schemes = schemes

    if not schemes:
        info.drm_type = DrmType.NONE
        return info

    # 判斷 DRM 類型（Widevine 優先）
    for scheme in schemes:
        if _WIDEVINE_UUID in scheme:
            info.drm_type  = DrmType.WIDEVINE
            info.drm_level = DrmLevel.L3   # MPD 本身不標示 L1/L3，預設 L3
            info.pssh      = _find_widevine_pssh(root)
            info.license_url = _find_license_url_from_mpd(root)
            return info
        if _PLAYREADY_UUID in scheme:
            info.drm_type = DrmType.PLAYREADY
            # 繼續掃描是否同時有 Widevine（優先 Widevine）

    if info.drm_type == DrmType.NONE:
        info.drm_type = DrmType.UNKNOWN

    return info


def _fallback_regex_detect(content: str) -> DrmInfo:
    """XML 解析失敗時用 regex 快速偵測"""
    info = DrmInfo()
    if _WIDEVINE_UUID in content.lower():
        info.drm_type  = DrmType.WIDEVINE
        info.drm_level = DrmLevel.L3
        pssh_match = re.search(r"<[^>]*pssh[^>]*>([A-Za-z0-9+/=]+)</[^>]*pssh>", content, re.IGNORECASE)
        if pssh_match:
            info.pssh = pssh_match.group(1)
    elif _PLAYREADY_UUID in content.lower():
        info.drm_type = DrmType.PLAYREADY
    elif "contentprotection" in content.lower():
        info.drm_type = DrmType.UNKNOWN
    return info


# ── 解析 M3U8 ─────────────────────────────────────────────────────────────────

def parse_manifest_m3u8(content: str) -> DrmInfo:
    """
    解析 HLS M3U8 內容字串，回傳 DrmInfo。

    FairPlay 使用 `skd://` URI；Widevine 有時會出現在 EXT-X-KEY 的 URI 中。

    Args:
        content: M3U8 文字內容

    Returns:
        DrmInfo 物件
    """
    info = DrmInfo()

    # EXT-X-KEY 行解析
    key_lines = re.findall(r"#EXT-X-KEY:(.+)", content)
    if not key_lines:
        # 也嘗試 EXT-X-SESSION-KEY
        key_lines = re.findall(r"#EXT-X-SESSION-KEY:(.+)", content)

    if not key_lines:
        info.drm_type = DrmType.NONE
        return info

    for key_line in key_lines:
        method_match = re.search(r'METHOD=([^,\s]+)', key_line)
        uri_match    = re.search(r'URI="([^"]+)"', key_line)

        method = method_match.group(1).upper() if method_match else ""
        uri    = uri_match.group(1) if uri_match else ""

        if method == "NONE":
            continue

        if uri.startswith("skd://"):
            info.drm_type    = DrmType.FAIRPLAY
            info.license_url = uri
            return info

        if _WIDEVINE_UUID in uri.lower() or "widevine" in uri.lower():
            info.drm_type    = DrmType.WIDEVINE
            info.drm_level   = DrmLevel.L3
            info.license_url = uri
            return info

        if method in ("AES-128", "SAMPLE-AES"):
            # 標準 AES 加密但非 FairPlay/Widevine，視為 UNKNOWN
            info.drm_type = DrmType.UNKNOWN

    return info


# ── 從 URL 自動偵測 ───────────────────────────────────────────────────────────

def detect_from_url(
    manifest_url: str,
    headers: dict[str, str] | None = None,
    timeout: int = 15
) -> DrmInfo:
    """
    下載 manifest URL 並自動偵測 DRM。

    M3U8 會自動追入子播放清單（media playlist）以偵測 EXT-X-KEY，
    避免 master playlist 沒有 DRM 標記但子串流有加密的漏判（如博客來 FairPlay）。

    Args:
        manifest_url: MPD 或 M3U8 URL
        headers:      可選的請求 Headers（某些平台需要認證）
        timeout:      HTTP 請求逾時秒數

    Returns:
        DrmInfo 物件；網路失敗時回傳 drm_type=UNKNOWN
    """
    try:
        resp = requests.get(manifest_url, headers=headers or {}, timeout=timeout)
        resp.raise_for_status()
        content = resp.text
    except Exception as e:
        info = DrmInfo(drm_type=DrmType.UNKNOWN)
        info.raw_schemes = [f"fetch_error: {e}"]
        return info

    url_lower = manifest_url.lower()
    if url_lower.endswith(".mpd") or "mpd" in url_lower:
        return parse_manifest_mpd(content)
    if url_lower.endswith(".m3u8") or "m3u8" in url_lower:
        return _detect_m3u8_with_subplaylists(manifest_url, content, headers, timeout)

    # 自動猜測格式
    stripped = content.strip()
    if stripped.startswith("<?xml") or stripped.startswith("<MPD"):
        return parse_manifest_mpd(content)
    if stripped.startswith("#EXTM3U"):
        return _detect_m3u8_with_subplaylists(manifest_url, content, headers, timeout)

    info = DrmInfo(drm_type=DrmType.UNKNOWN)
    info.raw_schemes = ["unknown_format"]
    return info


def _detect_m3u8_with_subplaylists(
    master_url: str,
    master_content: str,
    headers: dict[str, str] | None,
    timeout: int,
) -> DrmInfo:
    """
    先解析 master M3U8；若 master 無 DRM 標記，
    追入第一個子播放清單（media playlist）再次偵測。
    修正：博客來等平台 master 無 EXT-X-KEY，DRM 標記在子串流。
    """
    info = parse_manifest_m3u8(master_content)
    if info.is_protected:
        return info

    # master 無 DRM，嘗試追入第一個 media playlist
    sub_url = _first_media_playlist_url(master_url, master_content)
    if not sub_url:
        return info

    try:
        resp = requests.get(sub_url, headers=headers or {}, timeout=timeout)
        resp.raise_for_status()
        sub_info = parse_manifest_m3u8(resp.text)
        if sub_info.is_protected:
            sub_info.raw_schemes = [f"(from sub-playlist: {sub_url})"] + sub_info.raw_schemes
            return sub_info
    except Exception:
        pass

    return info


def _first_media_playlist_url(master_url: str, master_content: str) -> str | None:
    """從 master M3U8 內容提取第一個 media playlist 的完整 URL"""
    from urllib.parse import urljoin
    for line in master_content.splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            # 相對路徑或絕對路徑都處理
            return urljoin(master_url, line)
    return None
