#!/usr/bin/env python3
"""邮件发送Provider实现 - V5.9.0"""

import os
import sys
import time
import base64
import subprocess
from abc import ABC, abstractmethod
from pathlib import Path
from uuid import uuid4
from typing import List


class EmailProvider(ABC):
    """邮件发送Provider基类"""
    
    def __init__(self, config: dict):
        self.config = config
        self.max_retries = config.get('max_retries', 3)
        self.retry_delay = config.get('retry_delay', 5)
    
    @abstractmethod
    def is_available(self) -> bool:
        """检查Provider是否可用"""
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        """返回Provider名称"""
        pass
    
    @abstractmethod
    def send(self, receiver: str, attachments: List[str], subject: str, body: str) -> bool:
        """发送邮件，返回是否成功"""
        pass
    
    def send_with_retry(self, receiver: str, attachments: List[str], subject: str, body: str) -> bool:
        """带重试机制的发送"""
        for attempt in range(self.max_retries):
            try:
                if self.send(receiver, attachments, subject, body):
                    return True
            except Exception as e:
                print(f"  发送失败: {e}")
            
            if attempt < self.max_retries - 1:
                print(f"  第{attempt + 1}次失败，{self.retry_delay}秒后重试...")
                time.sleep(self.retry_delay)
        
        return False


class OAuth2Provider(EmailProvider):
    """Gmail OAuth2 邮件发送"""
    
    def is_available(self) -> bool:
        enabled = self.config.get('enabled', False)
        client_id = self.config.get('client_id', '')
        client_secret = self.config.get('client_secret', '')
        refresh_token = self.config.get('refresh_token', '')
        sender = self.config.get('sender_email', '')
        
        if not enabled:
            return False
        
        # 检查是否所有必需字段都已配置
        if not all([client_id, client_secret, refresh_token, sender]):
            print(f"  OAuth2配置不完整，跳过")
            return False
        
        # 检查google-auth库
        try:
            import google.auth
            import google.auth.transport.requests
            from google.oauth2.credentials import Credentials
            return True
        except ImportError:
            print(f"  未安装google-auth库，跳过OAuth2")
            return False
    
    def get_name(self) -> str:
        return "Gmail OAuth2"
    
    def send(self, receiver: str, attachments: List[str], subject: str, body: str) -> bool:
        try:
            from google.oauth2.credentials import Credentials
            from google.auth.transport.requests import Request
            import smtplib
            from email.mime.multipart import MIMEMultipart
            from email.mime.base import MIMEBase
            from email.mime.text import MIMEText
            from email import encoders
        except ImportError as e:
            print(f"  缺少依赖: {e}")
            return False
        
        try:
            # 使用refresh token获取access token
            creds = Credentials(
                None,
                refresh_token=self.config['refresh_token'],
                token_uri="https://oauth2.googleapis.com/token",
                client_id=self.config['client_id'],
                client_secret=self.config['client_secret'],
            )
            creds.refresh(Request())
            
            # 连接Gmail SMTP 使用 XOAUTH2
            server = smtplib.SMTP('smtp.gmail.com', 587, timeout=30)
            server.ehlo()
            server.starttls()
            server.ehlo()

            sender = self.config['sender_email']
            auth_string = f"user={sender}\x01auth=Bearer {creds.token}\x01\x01"
            auth_b64 = base64.b64encode(auth_string.encode('utf-8')).decode('utf-8')
            code, resp = server.docmd('AUTH', 'XOAUTH2 ' + auth_b64)
            if code != 235:
                resp_text = resp.decode('utf-8', errors='ignore') if isinstance(resp, bytes) else str(resp)
                raise Exception(f"XOAUTH2认证失败: {code} {resp_text}")
            
            # 构建邮件
            msg = MIMEMultipart()
            msg['From'] = sender
            msg['To'] = receiver
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain', 'utf-8'))
            
            # 添加附件
            for attachment_path in attachments:
                with open(attachment_path, 'rb') as f:
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(f.read())
                    encoders.encode_base64(part)
                    filename = os.path.basename(attachment_path)
                    part.add_header(
                        'Content-Disposition',
                        f'attachment; filename="{filename}"'
                    )
                    msg.attach(part)
            
            server.send_message(msg)
            server.quit()
            print(f"  ✅ 通过OAuth2发送成功")
            return True
            
        except Exception as e:
            print(f"  ❌ OAuth2发送失败: {e}")
            return False


class SMTPProvider(EmailProvider):
    """SMTP 邮件发送"""
    
    def is_available(self) -> bool:
        enabled = self.config.get('enabled', False)
        server = self.config.get('server', '')
        sender = self.config.get('sender_email', '')
        password = self.config.get('password', '')
        
        if not enabled:
            return False
        
        if not all([server, sender]):
            print(f"  SMTP配置不完整(缺少server或sender_email)")
            return False
        
        return True
    
    def get_name(self) -> str:
        return f"SMTP ({self.config.get('server', 'unknown')})"
    
    def send(self, receiver: str, attachments: List[str], subject: str, body: str) -> bool:
        try:
            import smtplib
            from email.mime.multipart import MIMEMultipart
            from email.mime.base import MIMEBase
            from email.mime.text import MIMEText
            from email import encoders
        except ImportError as e:
            print(f"  缺少依赖: {e}")
            return False
        
        try:
            server_addr = self.config['server']
            port = self.config.get('port', 587)
            use_tls = self.config.get('use_tls', True)
            sender = self.config['sender_email']
            password = self.config.get('password', '')
            
            # 连接服务器
            if use_tls:
                server = smtplib.SMTP(server_addr, port)
                server.starttls()
            else:
                server = smtplib.SMTP_SSL(server_addr, port)
            
            # 登录
            if password:
                server.login(sender, password)
            
            # 构建邮件
            msg = MIMEMultipart()
            msg['From'] = sender
            msg['To'] = receiver
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain', 'utf-8'))
            
            # 添加附件
            for attachment_path in attachments:
                with open(attachment_path, 'rb') as f:
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(f.read())
                    encoders.encode_base64(part)
                    filename = os.path.basename(attachment_path)
                    part.add_header(
                        'Content-Disposition',
                        f'attachment; filename="{filename}"'
                    )
                    msg.attach(part)
            
            server.send_message(msg)
            server.quit()
            print(f"  ✅ 通过SMTP发送成功")
            return True
            
        except Exception as e:
            print(f"  ❌ SMTP发送失败: {e}")
            return False


class MailAppProvider(EmailProvider):
    """macOS Mail.app 邮件发送"""
    
    def is_available(self) -> bool:
        enabled = self.config.get('enabled', False)
        
        if not enabled:
            return False
        
        # 检查是否为macOS
        if sys.platform != 'darwin':
            print(f"  非macOS系统，跳过Mail.app")
            return False
        
        return True
    
    def get_name(self) -> str:
        return "macOS Mail.app"
    
    def send(self, receiver: str, attachments: List[str], subject: str, body: str) -> bool:
        try:
            # 构建AppleScript
            attachment_list = ', '.join([f'"{p}"' for p in attachments])
            
            applescript = f'''
            tell application "Mail"
                set newMessage to make new outgoing message with properties {{subject:"{subject}", content:"{body}"}}
                tell newMessage
                    make new to recipient at end of to recipients with properties {{address:"{receiver}"}}
                    {' '.join([f'make new attachment with properties {{file name:"{p}"}} at after last paragraph' for p in attachments])}
                    send newMessage
                end tell
            end tell
            '''
            
            # 执行AppleScript
            result = subprocess.run(
                ['osascript', '-e', applescript],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                print(f"  ✅ 通过Mail.app发送成功")
                return True
            else:
                print(f"  ❌ Mail.app发送失败: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            print(f"  ❌ Mail.app发送超时")
            return False
        except Exception as e:
            print(f"  ❌ Mail.app发送失败: {e}")
            return False


class LocalProvider(EmailProvider):
    """本地保存Provider（不发送邮件，只保存到目录）"""
    
    def is_available(self) -> bool:
        enabled = self.config.get('enabled', False)
        output_dir = self.config.get('output_dir', '')
        
        if not enabled:
            return False
        
        if not output_dir:
            print(f"  Local provider未配置output_dir")
            return False
        
        return True
    
    def get_name(self) -> str:
        return "Local Save"
    
    def send(self, receiver: str, attachments: List[str], subject: str, body: str) -> bool:
        try:
            output_dir = Path(self.config['output_dir']).expanduser()
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # 复制附件到输出目录
            for attachment_path in attachments:
                src = Path(attachment_path)
                if src.exists():
                    dst = output_dir / src.name
                    import shutil
                    shutil.copy2(src, dst)
                    print(f"  📄 已保存: {dst}")
            
            # 保存邮件正文为文本文件
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            suffix = f"{int(time.time() * 1000) % 1000:03d}_{uuid4().hex[:6]}"
            body_file = output_dir / f"email_{timestamp}_{suffix}.txt"
            with open(body_file, 'w', encoding='utf-8') as f:
                f.write(f"To: {receiver}\n")
                f.write(f"Subject: {subject}\n")
                f.write(f"\n{body}\n")
            
            print(f"  ✅ 本地保存完成")
            return True
            
        except Exception as e:
            print(f"  ❌ 本地保存失败: {e}")
            return False


# Provider映射表
PROVIDER_MAP = {
    'oauth2': OAuth2Provider,
    'smtp': SMTPProvider,
    'mail_app': MailAppProvider,
    'local': LocalProvider,
}