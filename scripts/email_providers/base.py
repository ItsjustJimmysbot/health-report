#!/usr/bin/env python3
"""邮件发送 Provider 抽象基类 - V5.8.1 增加重试机制"""

from abc import ABC, abstractmethod
from typing import List
import time


class EmailProvider(ABC):
    """邮件发送 Provider 抽象基类"""
    
    def __init__(self, config: dict):
        self.config = config
        self.enabled = config.get('enabled', False)
        self.max_retries = config.get('max_retries', 3)
        self.retry_delay = config.get('retry_delay', 2)  # 秒
    
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
    
    def send_with_retry(self, recipient: str, report_files: List[str], 
                        subject: str, body: str) -> bool:
        """带重试的发送
        
        参数:
            recipient: 收件人邮箱
            report_files: 报告文件路径列表
            subject: 邮件主题
            body: 邮件正文
        
        返回:
            bool: 发送成功返回 True
        """
        for attempt in range(1, self.max_retries + 1):
            print(f"   尝试 {attempt}/{self.max_retries}...")
            
            try:
                if self.send(recipient, report_files, subject, body):
                    return True
            except Exception as e:
                print(f"   ⚠️  发送异常: {e}")
            
            if attempt < self.max_retries:
                print(f"   ⏳ {self.retry_delay}秒后重试...")
                time.sleep(self.retry_delay)
        
        print(f"   ❌ {self.max_retries}次尝试均失败")
        return False