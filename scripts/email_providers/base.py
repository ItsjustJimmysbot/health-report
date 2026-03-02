#!/usr/bin/env python3
"""邮件发送 Provider 抽象基类"""

from abc import ABC, abstractmethod
from typing import List


class EmailProvider(ABC):
    """邮件发送 Provider 抽象基类"""
    
    def __init__(self, config: dict):
        self.config = config
        self.enabled = config.get('enabled', False)
    
    @abstractmethod
    def send(self, recipient: str, report_files: List[str], subject: str, body: str) -> bool:
        """发送邮件，返回是否成功"""
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        """返回 Provider 名称"""
        pass
    
    def is_available(self) -> bool:
        """检查是否可用（配置正确且启用）"""
        return self.enabled and self._check_credentials()
    
    @abstractmethod
    def _check_credentials(self) -> bool:
        """检查凭证是否有效"""
        pass