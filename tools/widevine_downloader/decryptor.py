"""
Widevine 解密核心：封裝 pywidevine CDM 操作 + 檔案解密（mp4decrypt / shaka-packager）。

使用前提：
  1. 需有效的 Widevine Device (.wvd) 檔案（L3 provision）
  2. 需安裝 mp4decrypt（Bento4）或 shaka-packager
     - Bento4:          https://www.bento4.com/downloads/
     - shaka-packager:  https://github.com/shaka-project/shaka-packager

研究用途 disclaimer：本模組僅供研究分析 DRM 技術使用。
"""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import requests
from pywidevine.cdm import Cdm
from pywidevine.device import Device
from pywidevine.pssh import PSSH


class WvdNotFoundError(FileNotFoundError):
    """WVD 裝置檔案不存在"""


class LicenseServerError(RuntimeError):
    """License Server 回傳錯誤"""


class DecryptToolNotFoundError(FileNotFoundError):
    """mp4decrypt / shaka-packager 均未安裝"""


# ── 工具偵測 ──────────────────────────────────────────────────────────────────

def _find_decrypt_tool() -> tuple[str, str]:
    """
    偵測系統是否安裝 mp4decrypt 或 shaka-packager。

    Returns:
        (tool_name, tool_path)  tool_name: 'mp4decrypt' | 'shaka-packager'

    Raises:
        DecryptToolNotFoundError: 兩者均未找到
    """
    # shaka-packager 優先（跨平台解密音訊較可靠）
    for name in ("packager", "shaka-packager", "packager-linux-x64",
                 "packager-osx-x64", "packager-win-x64.exe"):
        path = shutil.which(name)
        if path:
            return "shaka-packager", path

    path = shutil.which("mp4decrypt")
    if path:
        return "mp4decrypt", path

    raise DecryptToolNotFoundError(
        "找不到解密工具。請安裝以下其中一項：\n"
        "  - Bento4 mp4decrypt: https://www.bento4.com/downloads/\n"
        "  - shaka-packager:    https://github.com/shaka-project/shaka-packager"
    )


# ── WidevineDecryptor ─────────────────────────────────────────────────────────

class WidevineDecryptor:
    """
    封裝 pywidevine CDM 的完整解密流程。

    使用範例：
        decryptor = WidevineDecryptor("/path/to/device.wvd")
        keys = decryptor.get_content_keys(
            pssh="AAAAW3Bzc2gAAAAA...",
            license_url="https://...",
            headers={"Authorization": "Bearer ..."}
        )
        # keys = [{"type": "CONTENT", "kid": "abc123", "key": "def456"}, ...]

        decryptor.decrypt_file("encrypted.mp4", "decrypted.mp4", keys[0]["kid"], keys[0]["key"])
    """

    def __init__(self, wvd_path: str) -> None:
        """
        Args:
            wvd_path: Widevine Device (.wvd) 檔案路徑

        Raises:
            WvdNotFoundError: 檔案不存在
            Exception: pywidevine 載入失敗（格式不符等）
        """
        if not os.path.exists(wvd_path):
            raise WvdNotFoundError(
                f"找不到 WVD 檔案：{wvd_path}\n"
                "請自行準備 Widevine L3 Device 檔案（本專案不提供）。\n"
                "可參考：https://github.com/devine-dl/pywidevine"
            )
        self._wvd_path = wvd_path
        self._device   = Device.load(wvd_path)
        self._cdm      = Cdm.from_device(self._device)

    @property
    def device_type(self) -> str:
        return str(self._device.type)

    @property
    def security_level(self) -> int:
        return self._device.security_level

    def get_content_keys(
        self,
        pssh: str,
        license_url: str,
        headers: dict[str, str] | None = None,
        privacy: bool = False,
        timeout: int = 30,
    ) -> list[dict[str, str]]:
        """
        向 License Server 請求 Content Key。

        Args:
            pssh:        Base64 PSSH data（從 MPD / 瀏覽器 EME Logger 取得）
            license_url: Widevine License Server URL
            headers:     HTTP 請求 Headers（Authorization、Referer 等）
            privacy:     是否啟用隱私模式（需先取得 Service Certificate）
            timeout:     HTTP 請求逾時秒數

        Returns:
            List of {"type": str, "kid": str, "key": str}
            type 通常為 "CONTENT"（內容金鑰）或 "SIGNING"

        Raises:
            LicenseServerError: License Server 回傳非 200 或解析失敗
        """
        pssh_obj     = PSSH(pssh)
        session_id   = self._cdm.open()

        try:
            # 隱私模式：先取得 service certificate
            if privacy:
                cert_challenge = self._cdm.service_certificate_challenge
                cert_resp = requests.post(
                    license_url,
                    data=cert_challenge,
                    headers=headers or {},
                    timeout=timeout
                )
                if cert_resp.status_code != 200:
                    raise LicenseServerError(
                        f"Service Certificate 請求失敗 HTTP {cert_resp.status_code}：{cert_resp.text[:200]}"
                    )
                self._cdm.set_service_certificate(session_id, cert_resp.content)

            # 產生 License Challenge
            challenge = self._cdm.get_license_challenge(session_id, pssh_obj)

            # 送出 Challenge 至 License Server
            resp = requests.post(
                license_url,
                data=challenge,
                headers=headers or {},
                timeout=timeout
            )
            if resp.status_code != 200:
                raise LicenseServerError(
                    f"License Server 回傳 HTTP {resp.status_code}：{resp.text[:300]}\n"
                    "可能原因：provision 被封鎖、Authorization header 不正確、或此平台封鎖 L3 CDM。"
                )

            # 解析 License Response
            self._cdm.parse_license(session_id, resp.content)

            # 取得所有金鑰
            keys = [
                {
                    "type": str(key.type),
                    "kid":  key.kid.hex,
                    "key":  key.key.hex(),
                }
                for key in self._cdm.get_keys(session_id)
            ]
            return keys

        finally:
            self._cdm.close(session_id)

    def get_license_challenge_only(self, pssh: str) -> bytes:
        """
        僅產生 License Challenge，不送出請求（供手動模式使用）。

        Args:
            pssh: Base64 PSSH data

        Returns:
            License Challenge bytes（可手動 POST 至 License Server）
        """
        pssh_obj   = PSSH(pssh)
        session_id = self._cdm.open()
        try:
            challenge = self._cdm.get_license_challenge(session_id, pssh_obj)
            return bytes(challenge)
        finally:
            self._cdm.close(session_id)

    # ── 檔案解密 ──────────────────────────────────────────────────────────────

    def decrypt_file(
        self,
        input_path: str,
        output_path: str,
        kid: str,
        key: str,
        keep_encrypted: bool = True,
    ) -> str:
        """
        使用解密工具（mp4decrypt 或 shaka-packager）解密檔案。

        Args:
            input_path:      加密的輸入檔案路徑（mp4 / m4a）
            output_path:     解密後的輸出路徑
            kid:             Key ID（16 bytes hex）
            key:             Content Key（16 bytes hex）
            keep_encrypted:  是否保留加密原始檔（預設保留供除錯）

        Returns:
            output_path

        Raises:
            FileNotFoundError: 輸入檔案不存在
            DecryptToolNotFoundError: 解密工具未安裝
            subprocess.CalledProcessError: 解密失敗
        """
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"輸入檔案不存在：{input_path}")

        tool_name, tool_path = _find_decrypt_tool()
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        if tool_name == "shaka-packager":
            self._decrypt_with_shaka(tool_path, input_path, output_path, kid, key)
        else:
            self._decrypt_with_mp4decrypt(tool_path, input_path, output_path, kid, key)

        if not keep_encrypted and os.path.exists(output_path):
            os.remove(input_path)

        return output_path

    @staticmethod
    def _decrypt_with_mp4decrypt(
        tool_path: str,
        input_path: str,
        output_path: str,
        kid: str,
        key: str,
    ) -> None:
        """
        執行 Bento4 mp4decrypt。

        命令：mp4decrypt --key <kid>:<key> input.mp4 output.mp4
        """
        cmd = [tool_path, "--key", f"{kid}:{key}", input_path, output_path]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise subprocess.CalledProcessError(
                result.returncode, cmd, output=result.stdout, stderr=result.stderr
            )

    @staticmethod
    def _decrypt_with_shaka(
        tool_path: str,
        input_path: str,
        output_path: str,
        kid: str,
        key: str,
    ) -> None:
        """
        執行 shaka-packager 解密。

        命令：packager --enable_raw_key_decryption
               input=<in>,stream=0,output=<out>
               --keys key_id=<kid>:key=<key>
        """
        cmd = [
            tool_path,
            "--enable_raw_key_decryption",
            f"input={input_path},stream=0,output={output_path}",
            "--keys", f"key_id={kid}:key={key}",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise subprocess.CalledProcessError(
                result.returncode, cmd, output=result.stdout, stderr=result.stderr
            )

    # ── 完整下載 + 解密流程 ────────────────────────────────────────────────────

    def download_encrypted_with_ytdlp(
        self,
        url: str,
        output_dir: str,
        ytdlp_path: str = "yt-dlp",
    ) -> dict[str, str]:
        """
        使用 yt-dlp --allow-unplayable 下載加密檔案。

        Args:
            url:         媒體 URL（MPD 或 原始媒體 URL）
            output_dir:  輸出目錄
            ytdlp_path:  yt-dlp 執行檔路徑

        Returns:
            {"video": str | None, "audio": str | None}  各自的下載路徑
        """
        import glob as glob_mod

        os.makedirs(output_dir, exist_ok=True)
        tmp_prefix = os.path.join(output_dir, "enc_%(title)s.%(ext)s")

        cmd = [
            ytdlp_path,
            "--allow-unplayable-formats",
            "-f", "bestvideo+bestaudio/best",
            "-o", tmp_prefix,
            url,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise subprocess.CalledProcessError(
                result.returncode, cmd, output=result.stdout, stderr=result.stderr
            )

        # 找出新產生的 enc_ 開頭檔案
        enc_files = glob_mod.glob(os.path.join(output_dir, "enc_*"))
        video_file = next((f for f in enc_files if f.endswith(".mp4")), None)
        audio_file = next((f for f in enc_files if f.endswith((".m4a", ".aac", ".opus"))), None)

        return {"video": video_file, "audio": audio_file}

    def full_pipeline(
        self,
        url: str,
        pssh: str,
        license_url: str,
        output_dir: str,
        output_name: str = "output",
        headers: dict[str, str] | None = None,
        format: str = "mp3",
        ytdlp_path: str = "yt-dlp",
        ffmpeg_path: str = "ffmpeg",
        privacy: bool = False,
        keep_encrypted: bool = False,
    ) -> dict:
        """
        完整流程：取得金鑰 → 下載加密檔 → 解密 → ffmpeg 轉檔。

        Args:
            url:            媒體 URL
            pssh:           Base64 PSSH
            license_url:    License Server URL
            output_dir:     輸出目錄
            output_name:    輸出檔名（不含副檔名）
            headers:        License request headers
            format:         最終輸出格式 "mp3" | "m4a"
            ytdlp_path:     yt-dlp 路徑
            ffmpeg_path:    ffmpeg 路徑
            privacy:        是否啟用隱私模式
            keep_encrypted: 是否保留加密中間檔

        Returns:
            {"success": bool, "output_file": str, "keys": list, "error": str}
        """
        os.makedirs(output_dir, exist_ok=True)
        result: dict = {"success": False, "output_file": None, "keys": [], "error": None}

        # 1. 取得 Content Keys
        try:
            keys = self.get_content_keys(pssh, license_url, headers, privacy)
            result["keys"] = keys
        except Exception as e:
            result["error"] = f"取得 Content Key 失敗：{e}"
            return result

        content_keys = [k for k in keys if k["type"] == "CONTENT"]
        if not content_keys:
            result["error"] = f"License Server 回傳的金鑰中沒有 CONTENT 類型：{keys}"
            return result

        primary_key = content_keys[0]

        # 2. 下載加密檔案
        try:
            enc_files = self.download_encrypted_with_ytdlp(url, output_dir, ytdlp_path)
        except subprocess.CalledProcessError as e:
            result["error"] = f"yt-dlp 下載失敗：{e.stderr}"
            return result

        audio_enc = enc_files.get("audio")
        video_enc = enc_files.get("video")

        if not audio_enc and not video_enc:
            result["error"] = "yt-dlp 未產生任何加密檔案"
            return result

        # 3. 解密
        decrypted: dict[str, str] = {}
        try:
            if audio_enc:
                audio_dec = os.path.join(output_dir, f"dec_audio{Path(audio_enc).suffix}")
                self.decrypt_file(audio_enc, audio_dec, primary_key["kid"], primary_key["key"], keep_encrypted)
                decrypted["audio"] = audio_dec
            if video_enc:
                video_dec = os.path.join(output_dir, f"dec_video{Path(video_enc).suffix}")
                self.decrypt_file(video_enc, video_dec, primary_key["kid"], primary_key["key"], keep_encrypted)
                decrypted["video"] = video_dec
        except Exception as e:
            result["error"] = f"解密失敗：{e}"
            return result

        # 4. ffmpeg 轉檔 / 合併
        final_path = os.path.join(output_dir, f"{output_name}.{format}")
        try:
            self._merge_with_ffmpeg(
                ffmpeg_path=ffmpeg_path,
                video_path=decrypted.get("video"),
                audio_path=decrypted.get("audio"),
                output_path=final_path,
                format=format,
            )
        except Exception as e:
            result["error"] = f"ffmpeg 轉檔失敗：{e}"
            return result

        # 清理解密中間檔
        for f in decrypted.values():
            try:
                os.remove(f)
            except OSError:
                pass

        result["success"]     = True
        result["output_file"] = final_path
        return result

    @staticmethod
    def _merge_with_ffmpeg(
        ffmpeg_path: str,
        video_path: str | None,
        audio_path: str | None,
        output_path: str,
        format: str = "mp3",
    ) -> None:
        """使用 ffmpeg 合併影音或轉換格式"""
        if video_path and audio_path:
            # 影片 + 音訊 合併
            cmd = [
                ffmpeg_path, "-y",
                "-i", video_path,
                "-i", audio_path,
                "-c:v", "copy",
                "-c:a", "copy" if format not in ("mp3",) else "libmp3lame",
                output_path,
            ]
        elif audio_path:
            # 僅音訊轉檔
            if format == "mp3":
                cmd = [ffmpeg_path, "-y", "-i", audio_path,
                       "-vn", "-c:a", "libmp3lame", "-q:a", "0", output_path]
            else:  # m4a / 直接 copy
                cmd = [ffmpeg_path, "-y", "-i", audio_path,
                       "-vn", "-c:a", "copy", output_path]
        elif video_path:
            cmd = [ffmpeg_path, "-y", "-i", video_path, "-c:v", "copy", output_path]
        else:
            raise ValueError("video_path 與 audio_path 不能同時為 None")

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise subprocess.CalledProcessError(
                result.returncode, cmd, output=result.stdout, stderr=result.stderr
            )
