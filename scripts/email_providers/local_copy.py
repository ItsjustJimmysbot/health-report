#!/usr/bin/env python3
"""本地保存 Fallback Provider"""

import shutil
from pathlib import Path
from typing import List

from .base import EmailProvider


class LocalCopyProvider(EmailProvider):
    """本地保存作为 Fallback"""
    
    def __init__(self, config: dict):
        super().__init__(config)
        # 默认启用
        if 'enabled' not in config:
            self.enabled = True
    
    def get_name(self) -> str:
        return "Local Copy"
    
    def _check_credentials(self) -> bool:
        return True  # 总是可用
    
    def send(self, recipient: str, report_files: List[str], subject: str, body: str) -> bool:
        """复制报告到本地目录"""
        output_dir = self.config.get('output_dir', 
                                     '~/.openclaw/workspace/shared/health-reports/upload')
        target = Path(output_dir).expanduser()
        target.mkdir(parents=True, exist_ok=True)
        
        # 从 subject 中提取日期
        date_str = subject.split(' - ')[-1] if ' - ' in subject else 'unknown'
        
        copied = []
        for f in report_files:
            src = Path(f)
            if src.exists():
                dst = target / f"{date_str}_{src.name}"
                shutil.copy2(src, dst)
                copied.append(dst)
        
        if copied:
            print(f"📁 报告已保存到本地 (Fallback): {target}")
            for c in copied:
                print(f"   - {c.name}")
            return True
        return False