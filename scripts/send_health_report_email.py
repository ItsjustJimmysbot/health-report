#!/usr/bin/env python3
"""
健康报告邮件发送脚本 V5.6 - 自动 fallback (Mail.app -> Gmail -> 通用SMTP -> 复制到本地)
"""

import sys
import os
import subprocess
import shutil
import json
from pathlib import Path
from datetime import datetime

def load_config():
    config_paths = [
        Path(__file__).parent.parent / "config.json",
        Path.home() / '.openclaw' / 'workspace-health' / 'config.json',
    ]
    for config_path in config_paths:
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
    return {}

CONFIG = load_config()
EMAIL_CONFIG = CONFIG.get("email_config", {})
# 优先使用配置中的接收邮箱，没有则使用全局接收邮箱，没有则使用发件邮箱
RECEIVER_EMAIL = CONFIG.get("receiver_email") or (CONFIG.get("members", [{}])[0].get("email") if CONFIG.get("members") else EMAIL_CONFIG.get("receiver_email", EMAIL_CONFIG.get("sender_email", "")))

def send_with_mail_app(recipient, report_files, subject, body):
    """使用 macOS Mail.app 发送邮件"""
    escaped_subject = subject.replace('"', '\\"')
    escaped_body = body.replace('"', '\\"').replace("'", "\\'")
    
    applescript = f'''
tell application "Mail"
    set newMessage to make new outgoing message with properties {{subject:"{escaped_subject}", content:"{escaped_body}"}}
    tell newMessage
        make new to recipient with properties {{address:"{recipient}"}}
        '''
    
    for f in report_files:
        applescript += f'        make new attachment with properties {{file name:"{f}"}} at after last paragraph\n'
    
    applescript += '''        send
    end tell
end tell
'''
    print(f"   使用 Mail.app 发送...")
    try:
        result = subprocess.run(["osascript", "-e", applescript], capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            print("   ✅ Mail.app 发送成功")
            return True
        else:
            print(f"   ❌ Mail.app 失败: {result.stderr.strip()}")
            return False
    except Exception as e:
        print(f"   ❌ Mail.app 异常: {e}")
        return False

def send_with_gmail(sender, password, receiver, report_files, subject, body):
    """使用 Gmail SMTP 发送 (需应用专用密码)"""
    smtp_server = "smtp.gmail.com"
    smtp_port = 587
    print(f"   使用 Gmail SMTP: {smtp_server}:{smtp_port}")
    return _send_smtp(smtp_server, smtp_port, sender, password, receiver, report_files, subject, body)

def send_with_smtp(sender, password, receiver, report_files, subject, body):
    """使用通用 SMTP 发送 (根据后缀自动猜测或默认)"""
    smtp_server = EMAIL_CONFIG.get("smtp_server", "smtp.office365.com")
    smtp_port = int(EMAIL_CONFIG.get("smtp_port", 587))
    
    if not EMAIL_CONFIG.get("smtp_server"):
        if "qq.com" in sender:
            smtp_server = "smtp.qq.com"
            smtp_port = 465
        elif "163.com" in sender:
            smtp_server = "smtp.163.com"
            smtp_port = 465
        elif "outlook.com" in sender or "hotmail.com" in sender:
            smtp_server = "smtp.office365.com"
            smtp_port = 587
    
    print(f"   使用通用 SMTP ({smtp_server}:{smtp_port})...")
    return _send_smtp(smtp_server, smtp_port, sender, password, receiver, report_files, subject, body)

def _send_smtp(smtp_server, smtp_port, sender, password, receiver, report_files, subject, body):
    try:
        import smtplib
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText
        from email.mime.base import MIMEBase
        from email import encoders
        
        msg = MIMEMultipart()
        msg['From'] = sender
        msg['To'] = receiver
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        
        for f in report_files:
            p = Path(f)
            if p.exists():
                with open(f, 'rb') as fp:
                    attachment = MIMEBase('application', 'pdf')
                    attachment.set_payload(fp.read())
                    encoders.encode_base64(attachment)
                    attachment.add_header('Content-Disposition', f'attachment; filename="{p.name}"')
                    msg.attach(attachment)
        
        if smtp_port == 465:
            server = smtplib.SMTP_SSL(smtp_server, smtp_port)
        else:
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            
        server.login(sender, password)
        server.send_message(msg)
        server.quit()
        print("   ✅ SMTP 发送成功")
        return True
    except Exception as e:
        print(f"   ❌ SMTP 失败: {e}")
        return False

def send_with_copy(date_str, report_files, target_dir):
    """保存到本地作为 fallback"""
    target = Path(target_dir).expanduser()
    target.mkdir(parents=True, exist_ok=True)
    
    copied = []
    for f in report_files:
        src = Path(f)
        if src.exists():
            dst = target / f"{date_str}_{src.name}"
            shutil.copy2(src, dst)
            copied.append(dst)
    
    print(f"📁 报告已保存到: {target}")
    for c in copied:
        print(f"  - {c.name}")
    return True

def find_reports(date_str, upload_dir):
    upload_path = Path(upload_dir).expanduser()
    if not upload_path.exists():
        return []
    
    daily_reports = list(upload_path.glob(f"{date_str}-daily-v5-medical-*.pdf"))
    daily_filtered = [r for r in daily_reports if "-dashboard" not in r.name]
    selected_daily = [daily_filtered[0]] if daily_filtered else ([daily_reports[0]] if daily_reports else [])
    
    weekly_reports = list(upload_path.glob(f"weekly-report-*-to-{date_str}-V5.pdf"))
    selected_weekly = [weekly_reports[0]] if weekly_reports else []
    
    year_month = date_str[:7]
    monthly_reports = list(upload_path.glob(f"monthly-report-{year_month}-V5.pdf"))
    selected_monthly = [monthly_reports[0]] if monthly_reports else []
    
    return [str(r) for r in selected_daily + selected_weekly + selected_monthly]

def main():
    if len(sys.argv) < 2:
        print("用法: python3 send_health_report_email.py <日期> [报告文件...]")
        sys.exit(1)
        
    date_str = sys.argv[1]
    
    # 确定输出目录
    upload_dir = CONFIG.get("output_dir", "~/.openclaw/workspace/shared/health-reports/upload")
    
    if len(sys.argv) > 2:
        report_files = sys.argv[2:]
    else:
        report_files = find_reports(date_str, upload_dir)
        
    if not report_files:
        print(f"❌ 未找到 {date_str} 的报告文件")
        sys.exit(1)
        
    existing_files = [f for f in report_files if Path(f).exists()]
    if not existing_files:
        print("❌ 错误: 指定的报告文件都不存在")
        sys.exit(1)

    subject = f"健康报告 - {date_str}"
    body = f"您好，\n您的健康报告 ({date_str}) 已生成。\n\n"
    
    print(f"📧 准备发送邮件至 {RECEIVER_EMAIL}")
    
    # 1. 尝试 Mail.app
    print("📋 方式1: 使用 macOS Mail.app...")
    if send_with_mail_app(RECEIVER_EMAIL, existing_files, subject, body):
        sys.exit(0)
        
    # 获取 SMTP 配置
    sender = EMAIL_CONFIG.get("sender_email")
    password = EMAIL_CONFIG.get("password")
    
    if sender and password:
        if "gmail.com" in sender:
            # 2. Gmail 专用
            print("\n📋 方式2: 使用 Gmail SMTP...")
            if send_with_gmail(sender, password, RECEIVER_EMAIL, existing_files, subject, body):
                sys.exit(0)
        else:
            # 3. 通用 SMTP
            print("\n📋 方式3: 使用通用 SMTP...")
            if send_with_smtp(sender, password, RECEIVER_EMAIL, existing_files, subject, body):
                sys.exit(0)
    else:
        print("\n⚠️ 未配置 email_config.sender_email/password，跳过 SMTP。")
        
    # 4. Fallback: 复制到本地
    print("\n📋 方式4: 保存到本地 (Fallback)...")
    send_with_copy(date_str, existing_files, upload_dir)
    sys.exit(0)

if __name__ == "__main__":
    main()
