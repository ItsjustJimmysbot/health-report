#!/usr/bin/env python3
"""Gmail OAuth2 邮件发送 Provider"""

import base64
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path
from typing import List, Optional

import requests

from .base import EmailProvider


class GmailOAuth2Provider(EmailProvider):
    """Gmail OAuth2 邮件发送 Provider"""
    
    TOKEN_URL = "https://oauth2.googleapis.com/token"
    GMAIL_API_URL = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"
    
    def get_name(self) -> str:
        return "Gmail OAuth2"
    
    def _check_credentials(self) -> bool:
        required = ['client_id', 'client_secret', 'refresh_token', 'sender_email']
        return all(self.config.get(k) for k in required)
    
    def _get_access_token(self) -> Optional[str]:
        """使用 refresh_token 获取 access_token"""
        data = {
            'client_id': self.config['client_id'],
            'client_secret': self.config['client_secret'],
            'refresh_token': self.config['refresh_token'],
            'grant_type': 'refresh_token'
        }
        
        try:
            response = requests.post(self.TOKEN_URL, data=data, timeout=30)
            response.raise_for_status()
            token_data = response.json()
            return token_data.get('access_token')
        except Exception as e:
            print(f"❌ 获取 OAuth2 access_token 失败: {e}")
            return None
    
    def _create_message(self, sender: str, recipient: str, subject: str, 
                        body: str, report_files: List[str]) -> dict:
        """创建 MIME 消息并转为 base64url 格式"""
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
        
        # 转为 base64url
        raw_message = base64.urlsafe_b64encode(msg.as_bytes()).decode('utf-8')
        return {'raw': raw_message}
    
    def send(self, recipient: str, report_files: List[str], subject: str, body: str) -> bool:
        """使用 Gmail API 发送邮件"""
        print(f"📧 使用 Gmail OAuth2 发送...")
        
        access_token = self._get_access_token()
        if not access_token:
            return False
        
        sender = self.config['sender_email']
        message = self._create_message(sender, recipient, subject, body, report_files)
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        try:
            response = requests.post(
                self.GMAIL_API_URL,
                headers=headers,
                json=message,
                timeout=60
            )
            response.raise_for_status()
            print("✅ Gmail OAuth2 发送成功")
            return True
        except Exception as e:
            print(f"❌ Gmail OAuth2 发送失败: {e}")
            if hasattr(e, 'response') and e.response:
                print(f"   错误详情: {e.response.text}")
            return False