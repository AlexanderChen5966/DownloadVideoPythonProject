"""
網路白名單驗證器
用於驗證 URL 是否在允許的白名單中
支援完整網域、萬用字元和正則表達式比對
"""

import os
import json
import re
from urllib.parse import urlparse
from fnmatch import fnmatch
from pathlib import Path
from typing import Optional, List, Tuple


class WhitelistValidator:
    """白名單驗證器"""

    def __init__(self, config_path: Optional[str] = None):
        """
        初始化白名單驗證器

        Args:
            config_path: whitelist.json 的路徑，若為 None 則使用預設路徑
        """
        if config_path is None:
            # 使用專案根目錄的 whitelist.json
            project_root = Path(__file__).parent.parent
            config_path = project_root / "whitelist.json"

        self.config_path = Path(config_path)
        self._load_config()

    def _load_config(self) -> None:
        """載入白名單設定檔"""
        if not self.config_path.exists():
            # 如果設定檔不存在，建立預設設定
            self.enabled = False
            self.rules = []
            return

        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                self.enabled = config.get('enabled', False)
                self.rules = config.get('rules', [])
        except Exception as e:
            print(f"警告: 無法載入白名單設定檔: {e}")
            self.enabled = False
            self.rules = []

    def reload(self) -> None:
        """重新載入設定檔"""
        self._load_config()

    def _extract_domain(self, url: str) -> str:
        """
        從 URL 中提取網域名稱

        Args:
            url: 完整的 URL

        Returns:
            網域名稱 (例如: youtube.com)
        """
        try:
            parsed = urlparse(url)
            # 如果沒有 scheme，可能是純網域名稱
            if not parsed.scheme:
                parsed = urlparse(f"http://{url}")
            return parsed.netloc.lower()
        except Exception:
            return ""

    def _match_exact(self, domain: str, rule: str) -> bool:
        """
        完整網域比對

        Args:
            domain: 要檢查的網域
            rule: 白名單規則

        Returns:
            是否符合
        """
        return domain == rule.lower()

    def _match_wildcard(self, domain: str, rule: str) -> bool:
        """
        萬用字元比對 (例如: *.youtube.com)

        Args:
            domain: 要檢查的網域
            rule: 白名單規則

        Returns:
            是否符合
        """
        if '*' not in rule:
            return False
        return fnmatch(domain, rule.lower())

    def _match_regex(self, url: str, rule: str) -> bool:
        """
        正則表達式比對

        Args:
            url: 完整的 URL
            rule: 白名單規則 (正則表達式)

        Returns:
            是否符合
        """
        # 如果規則包含正則表達式特殊字元 (但不是萬用字元 *)
        regex_chars = ['^', '$', '\\', '(', ')', '[', ']', '{', '}', '+', '?', '.']
        if any(char in rule for char in regex_chars):
            try:
                return bool(re.match(rule, url, re.IGNORECASE))
            except re.error:
                return False
        return False

    def validate(self, url: str) -> Tuple[bool, str]:
        """
        驗證 URL 是否在白名單中

        Args:
            url: 要驗證的 URL

        Returns:
            (是否允許, 訊息)
        """
        # 如果白名單未啟用，允許所有 URL
        if not self.enabled:
            return True, "白名單未啟用，允許所有網址"

        # 如果沒有任何規則，拒絕所有 URL
        if not self.rules:
            return False, "白名單已啟用但沒有任何規則，拒絕所有網址"

        domain = self._extract_domain(url)
        if not domain:
            return False, f"無法從 URL 中提取網域: {url}"

        # 依序檢查規則
        for rule in self.rules:
            # 1. 完整網域比對
            if self._match_exact(domain, rule):
                return True, f"符合白名單規則 (完整比對): {rule}"

            # 2. 萬用字元比對
            if self._match_wildcard(domain, rule):
                return True, f"符合白名單規則 (萬用字元): {rule}"

            # 3. 正則表達式比對
            if self._match_regex(url, rule):
                return True, f"符合白名單規則 (正則表達式): {rule}"

        return False, f"網域 '{domain}' 不在白名單中，請聯絡管理員新增"

    def add_rule(self, rule: str) -> Tuple[bool, str]:
        """
        新增規則到白名單

        Args:
            rule: 要新增的規則

        Returns:
            (是否成功, 訊息)
        """
        if rule in self.rules:
            return False, f"規則 '{rule}' 已存在於白名單中"

        self.rules.append(rule)
        self._save_config()
        return True, f"已成功新增規則: {rule}"

    def remove_rule(self, rule: str) -> Tuple[bool, str]:
        """
        從白名單移除規則

        Args:
            rule: 要移除的規則

        Returns:
            (是否成功, 訊息)
        """
        if rule not in self.rules:
            return False, f"規則 '{rule}' 不存在於白名單中"

        self.rules.remove(rule)
        self._save_config()
        return True, f"已成功移除規則: {rule}"

    def list_rules(self) -> List[str]:
        """
        列出所有白名單規則

        Returns:
            規則列表
        """
        return self.rules.copy()

    def set_enabled(self, enabled: bool) -> Tuple[bool, str]:
        """
        啟用或停用白名單

        Args:
            enabled: True 啟用, False 停用

        Returns:
            (是否成功, 訊息)
        """
        self.enabled = enabled
        self._save_config()
        status = "已啟用" if enabled else "已停用"
        return True, f"白名單{status}"

    def _save_config(self) -> None:
        """儲存設定到檔案"""
        config = {
            "enabled": self.enabled,
            "rules": self.rules
        }

        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"錯誤: 無法儲存白名單設定檔: {e}")


# 建立全域驗證器實例
_global_validator = None


def get_validator() -> WhitelistValidator:
    """取得全域白名單驗證器實例"""
    global _global_validator
    if _global_validator is None:
        _global_validator = WhitelistValidator()
    return _global_validator
