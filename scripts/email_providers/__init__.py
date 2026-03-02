#!/usr/bin/env python3
"""邮件发送 Provider 包"""

from .base import EmailProvider
from .oauth2_gmail import GmailOAuth2Provider
from .smtp_sender import SMTPProvider
from .mail_app_sender import MailAppProvider
from .local_copy import LocalCopyProvider

__all__ = [
    'EmailProvider',
    'GmailOAuth2Provider',
    'SMTPProvider',
    'MailAppProvider',
    'LocalCopyProvider',
]

# Provider 映射表
PROVIDER_MAP = {
    'oauth2': GmailOAuth2Provider,
    'smtp': SMTPProvider,
    'mail_app': MailAppProvider,
    'local': LocalCopyProvider,
}