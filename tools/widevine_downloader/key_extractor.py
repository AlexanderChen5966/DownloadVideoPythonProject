"""
金鑰提取輔助：三種模式協助使用者從瀏覽器資訊取得 Widevine Content Key。

模式說明：
  1. 自動（auto）：提供 PSSH + License URL + Headers → 自動 POST 取得金鑰
  2. 手動（manual）：僅產生 License Challenge bytes → 使用者自行 POST
  3. 查詢（detect）：提供 Manifest URL → 自動偵測 DRM 並提取 PSSH

使用前提：需有效的 WVD device file。
"""
from __future__ import annotations

import base64
import json
import os
import sys
from typing import TextIO

from .decryptor import WidevineDecryptor, WvdNotFoundError
from .drm_detector import DrmInfo, DrmType, detect_from_url


class KeyExtractor:
    """
    多模式金鑰提取器。

    使用範例：
        extractor = KeyExtractor("/path/to/device.wvd")

        # 自動模式
        keys = extractor.auto(
            pssh="AAAA...",
            license_url="https://license.example.com/...",
            headers={"Authorization": "Bearer xxx"}
        )

        # 手動模式（取得 challenge 後自行 POST）
        challenge_b64 = extractor.get_challenge_b64(pssh="AAAA...")
        # 使用者自行 POST challenge_b64 至 license_url
        # 取得回應後：
        keys = extractor.parse_license_response(session_pssh, response_bytes)

        # 從 Manifest URL 偵測並提示後續步驟
        info = extractor.detect_manifest("https://...stream.mpd")
    """

    def __init__(self, wvd_path: str) -> None:
        """
        Args:
            wvd_path: Widevine Device (.wvd) 路徑

        Raises:
            WvdNotFoundError: 檔案不存在
        """
        self._decryptor = WidevineDecryptor(wvd_path)
        self._wvd_path  = wvd_path

    # ── 模式 1：自動 ──────────────────────────────────────────────────────────

    def auto(
        self,
        pssh: str,
        license_url: str,
        headers: dict[str, str] | None = None,
        privacy: bool = False,
        timeout: int = 30,
        verbose: bool = True,
        out: TextIO = sys.stdout,
    ) -> list[dict[str, str]]:
        """
        自動模式：直接送出 License 請求並回傳 Content Key。

        Args:
            pssh:        Base64 PSSH data
            license_url: License Server URL
            headers:     HTTP Request Headers（Authorization、Referer 等）
            privacy:     是否啟用隱私模式
            timeout:     HTTP 逾時秒數
            verbose:     是否印出金鑰資訊
            out:         輸出 stream（預設 stdout）

        Returns:
            [{"type": str, "kid": str, "key": str}, ...]
        """
        if verbose:
            print(f"[KeyExtractor] 正在向 License Server 請求金鑰...", file=out)
            print(f"  License URL : {license_url}", file=out)

        keys = self._decryptor.get_content_keys(
            pssh=pssh,
            license_url=license_url,
            headers=headers,
            privacy=privacy,
            timeout=timeout,
        )

        if verbose:
            content_keys = [k for k in keys if k["type"] == "CONTENT"]
            print(f"\n[KeyExtractor] 取得 {len(content_keys)} 個 Content Key：", file=out)
            for k in content_keys:
                print(f"  {k['kid']}:{k['key']}", file=out)
            if len(keys) > len(content_keys):
                print(f"  （另有 {len(keys) - len(content_keys)} 個非 CONTENT 類型金鑰）", file=out)

        return keys

    # ── 模式 2：手動（僅產生 Challenge）─────────────────────────────────────

    def get_challenge_bytes(self, pssh: str) -> bytes:
        """
        手動模式：僅產生 License Challenge bytes，不送出網路請求。

        Args:
            pssh: Base64 PSSH data

        Returns:
            Challenge bytes，可手動 POST 至 License Server
        """
        return self._decryptor.get_license_challenge_only(pssh)

    def get_challenge_b64(self, pssh: str) -> str:
        """
        取得 Base64 編碼的 License Challenge（方便顯示或複製）。

        Args:
            pssh: Base64 PSSH data

        Returns:
            Base64 License Challenge 字串
        """
        return base64.b64encode(self.get_challenge_bytes(pssh)).decode()

    def get_challenge_hex(self, pssh: str) -> str:
        """取得 Hex 格式的 License Challenge"""
        return self.get_challenge_bytes(pssh).hex()

    # ── 模式 3：Manifest 偵測 ─────────────────────────────────────────────────

    def detect_manifest(
        self,
        manifest_url: str,
        headers: dict[str, str] | None = None,
        verbose: bool = True,
        out: TextIO = sys.stdout,
    ) -> DrmInfo:
        """
        從 Manifest URL 偵測 DRM 類型，並在 verbose 模式下印出後續操作提示。

        Args:
            manifest_url: MPD 或 M3U8 URL
            headers:      可選 HTTP Headers
            verbose:      是否印出分析結果和操作提示
            out:          輸出 stream

        Returns:
            DrmInfo 物件
        """
        if verbose:
            print(f"[KeyExtractor] 正在分析 Manifest：{manifest_url}", file=out)

        info = detect_from_url(manifest_url, headers)

        if verbose:
            print(f"  DRM 類型：{info.drm_type.value}", file=out)
            print(f"  結論：{info.summary()}", file=out)

            if info.drm_type == DrmType.WIDEVINE:
                if info.pssh:
                    print(f"  PSSH（已自動提取）：{info.pssh}", file=out)
                else:
                    print(
                        "  ⚠ 未在 Manifest 中找到 PSSH。\n"
                        "     請改用瀏覽器 EME Logger Userscript 取得 PSSH：\n"
                        "     https://greasyfork.org/en/scripts/373903-eme-logger",
                        file=out
                    )
                if info.license_url:
                    print(f"  License URL（已自動提取）：{info.license_url}", file=out)
                else:
                    print(
                        "  ⚠ 未在 Manifest 中找到 License URL。\n"
                        "     請從瀏覽器 Network 面板搜尋 'Widevine' 請求取得。",
                        file=out
                    )

        return info

    # ── 工具方法 ──────────────────────────────────────────────────────────────

    @property
    def device_info(self) -> dict[str, str]:
        """回傳 WVD 裝置資訊"""
        return {
            "wvd_path":       self._wvd_path,
            "device_type":    self._decryptor.device_type,
            "security_level": f"L{self._decryptor.security_level}",
        }


# ── 互動式 CLI 輔助 ────────────────────────────────────────────────────────────

def interactive_key_extraction(wvd_path: str | None = None) -> None:
    """
    互動式 CLI：引導使用者逐步完成金鑰提取。

    用法：python -m tools.widevine_downloader.key_extractor
    """
    print("=" * 60)
    print(" Widevine Key Extractor（研究用途）")
    print("=" * 60)

    # Step 1：WVD 路徑
    if not wvd_path:
        wvd_path = input("\n請輸入 WVD device 檔案路徑：").strip().strip('"')
    if not os.path.exists(wvd_path):
        print(f"錯誤：找不到 WVD 檔案：{wvd_path}")
        print("請自行準備 Widevine L3 Device 檔案（本專案不提供）。")
        sys.exit(1)

    try:
        extractor = KeyExtractor(wvd_path)
        info = extractor.device_info
        print(f"\n裝置資訊：type={info['device_type']}, 安全等級={info['security_level']}")
    except Exception as e:
        print(f"錯誤：載入 WVD 失敗：{e}")
        sys.exit(1)

    # Step 2：選擇模式
    print("\n操作模式：")
    print("  1. 自動（提供 PSSH + License URL + Headers → 自動取得金鑰）")
    print("  2. 手動（僅產生 License Challenge，自行 POST）")
    print("  3. 偵測 Manifest（輸入 MPD/M3U8 URL 自動分析 DRM）")
    mode = input("\n請選擇模式 [1/2/3]：").strip()

    if mode == "1":
        _interactive_auto(extractor)
    elif mode == "2":
        _interactive_manual(extractor)
    elif mode == "3":
        _interactive_detect(extractor)
    else:
        print("無效的選擇，結束。")


def _interactive_auto(extractor: KeyExtractor) -> None:
    print("\n--- 自動模式 ---")
    pssh        = input("PSSH（Base64）：").strip()
    license_url = input("License URL：").strip()
    headers_str = input("Headers（JSON，可留空）：").strip()
    privacy     = input("啟用隱私模式？[y/N]：").strip().lower() == "y"

    headers: dict[str, str] | None = None
    if headers_str:
        try:
            headers = json.loads(headers_str)
        except json.JSONDecodeError:
            print("⚠ Headers JSON 格式不正確，將使用空 Headers")

    try:
        keys = extractor.auto(pssh, license_url, headers, privacy)
        content_keys = [k for k in keys if k["type"] == "CONTENT"]
        print(f"\n✓ 成功取得 {len(content_keys)} 個 Content Key")
        print("\n解密指令（mp4decrypt 格式）：")
        for k in content_keys:
            print(f"  mp4decrypt --key {k['kid']}:{k['key']} encrypted.mp4 decrypted.mp4")
    except Exception as e:
        print(f"\n✗ 失敗：{e}")


def _interactive_manual(extractor: KeyExtractor) -> None:
    print("\n--- 手動模式 ---")
    pssh = input("PSSH（Base64）：").strip()
    fmt  = input("輸出格式 [b64/hex]（預設 b64）：").strip().lower() or "b64"

    try:
        if fmt == "hex":
            challenge = extractor.get_challenge_hex(pssh)
        else:
            challenge = extractor.get_challenge_b64(pssh)
        print(f"\nLicense Challenge（{fmt.upper()}）：")
        print(challenge)
        print("\n請將此 Challenge POST 至 License Server，取得 License Response 後手動解析。")
    except Exception as e:
        print(f"\n✗ 失敗：{e}")


def _interactive_detect(extractor: KeyExtractor) -> None:
    print("\n--- Manifest 偵測模式 ---")
    url         = input("Manifest URL（.mpd 或 .m3u8）：").strip()
    headers_str = input("Headers（JSON，可留空）：").strip()

    headers: dict[str, str] | None = None
    if headers_str:
        try:
            headers = json.loads(headers_str)
        except json.JSONDecodeError:
            print("⚠ Headers JSON 格式不正確，將使用空 Headers")

    extractor.detect_manifest(url, headers)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Widevine Key Extractor 互動式模式")
    parser.add_argument("--wvd", dest="wvd_path", default=None, help="WVD 檔案路徑")
    args = parser.parse_args()
    interactive_key_extraction(args.wvd_path)
