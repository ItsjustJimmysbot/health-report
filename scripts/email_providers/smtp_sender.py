#!/usr/bin/env python3
"""SMTP 邮件发送 Provider"""

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path
from typing import List

from .base import EmailProvider


class SMTPProvider(EmailProvider):
    """SMTP 邮件发送 Provider"""
    
    def get_name(self) -> str:
        server = self.config.get('server', 'auto')
        return f"SMTP ({server})"
    
    def _check_credentials(self) -> bool:
        required = ['sender_email', 'password']
        return all(self.config.get(k) for k in required)
    
    def _get_server_config(self, sender: str) -> tuple:
        """获取 SMTP 服务器配置"""
        # 如果配置了具体服务器，直接使用
        if self.config.get('server') and self.config['server'] != 'auto':
            return (self.config['server'], self.config.get('port', 587))
        
        # 自动检测常见邮箱
        domain = sender.split('@')[-1].lower()
        configs = {
            'gmail.com': ('smtp.gmail.com', 587),
            'qq.com': ('smtp.qq.com', 465),
            '163.com': ('smtp.163.com', 465),
            '126.com': ('smtp.126.com', 465),
            'outlook.com': ('smtp.office365.com', 587),
            'hotmail.com': ('smtp.office365.com', 587),
            'live.com': ('smtp.office365.com', 587),
            'icloud.com': ('smtp.mail.me.com', 587),
            'me.com': ('smtp.mail.me.com', 587),
            'yahoo.com': ('smtp.mail.yahoo.com', 587),
            'foxmail.com': ('smtp.qq.com', 465),
        }
        
        return configs.get(domain, ('smtp.gmail.com', 587))
    
    def send(self, recipient: str, report_files: List[str], subject: str, body: str) -> bool:
        """使用 SMTP 发送邮件"""
        sender = self.config['sender_email']
        password = self.config['password']
        use_tls = self.config.get('use_tls', True)
        
        server, port = self._get_server_config(sender)
        print(f"📧 使用 SMTP ({server}:{port}) 发送...")
        
        try:
            msg = MIMEMultipart()
            msg['From'] = sender
            msg['To'] = recipient
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain', 'utf-8'))
            
            # 添加附件
            for f in report_files:
                p = Path(f)
                if p.exists():
                    with open(f, 'rb') as fp:
                        attachment = MIMEBase('application', 'pdf')
                        attachment.set_payload(fp.read())
                        encoders.encode_base64(attachment)
                        attachment.add_header('Content-Disposition', 
                                            f'attachment; filename="{p.name}"')
                        msg.attach(attachment)
            
            # 连接服务器
            if port == 465:
                conn = smtplib.SMTP_SSL(server, port, timeout=30)
            else:
                conn = smtplib.SMTP(server, port, timeout=30)
            
            if use_tls and port != 465:
                conn.starttls()
            
            conn.login(sender, password)
            conn.send_message(msg)
            conn.quit()
            
            print("✅ SMTP 发送成功")
            return True
            
        except Exception as e:
            print(f"❌ SMTP 发送失败: {e}")
            return False