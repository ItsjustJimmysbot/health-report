#!/usr/bin/env python3
"""macOS Mail.app 发送 Provider"""

import subprocess
import platform
from typing import List

from .base import EmailProvider


class MailAppProvider(EmailProvider):
    """macOS Mail.app 发送 Provider"""
    
    def get_name(self) -> str:
        return "macOS Mail.app"
    
    def _check_credentials(self) -> bool:
        # Mail.app 不需要凭证，只需要 macOS
        return platform.system() == 'Darwin'
    
    def send(self, recipient: str, report_files: List[str], subject: str, body: str) -> bool:
        """使用 AppleScript 控制 Mail.app 发送"""
        print(f"📧 使用 macOS Mail.app 发送...")
        
        # 转义特殊字符
        escaped_subject = subject.replace('"', '\\"')
        escaped_body = body.replace('"', '\\"').replace("'", "\\'")
        
        applescript = f'''tell application "Mail"
    set newMessage to make new outgoing message with properties {{subject:"{escaped_subject}", content:"{escaped_body}"}}
    tell newMessage
        make new to recipient with properties {{address:"{recipient}"}}
'''
        for f in report_files:
            applescript += f'        make new attachment with properties {{file name:"{f}"}} at after last paragraph\n'
        
        applescript += '''        send
    end tell
end tell'''
        
        try:
            result = subprocess.run(
                ["osascript", "-e", applescript],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0:
                print("✅ Mail.app 发送成功")
                return True
            else:
                print(f"❌ Mail.app 失败: {result.stderr.strip()}")
                return False
        except Exception as e:
            print(f"❌ Mail.app 异常: {e}")
            return False