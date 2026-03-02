#!/usr/bin/env python3
"""
健康报告邮件发送脚本 V5.7 - 自动 fallback (Mail.app -> Gmail -> 通用SMTP -> 复制到本地)
支持多成员：可通过参数指定发送给哪个成员
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

def get_member_email(member_idx=0):
    """获取指定成员的邮箱，优先使用成员自己的邮箱，其次使用全局 receiver_email"""
    members = CONFIG.get("members", [])
    
    # 边界检查
    if members and len(members) > member_idx:
        member = members[member_idx]
        # 优先使用成员自己的邮箱
        return member.get("email") or CONFIG.get("receiver_email") or EMAIL_CONFIG.get("receiver_email", EMAIL_CONFIG.get("sender_email", ""))
    elif members and len(members) > 0:
        # fallback 到第一个成员
        return members[0].get("email") or CONFIG.get("receiver_email") or EMAIL_CONFIG.get("receiver_email", EMAIL_CONFIG.get("sender_email", ""))
    else:
        # 没有成员配置，使用全局配置
        return CONFIG.get("receiver_email") or EMAIL_CONFIG.get("receiver_email", EMAIL_CONFIG.get("sender_email", ""))

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

def find_reports_for_member(date_str, upload_dir, member_name):
    """查找指定成员的报告文件"""
    from datetime import datetime, timedelta
    
    upload_path = Path(upload_dir).expanduser()
    if not upload_path.exists():
        return []
    
    safe_name = member_name.replace(' ', '_').replace('/', '_').replace('\\', '_')
    
    # 查找日报
    daily_reports = list(upload_path.glob(f"{date_str}-daily-v5-medical-{safe_name}.pdf"))
    if not daily_reports:
        # 尝试模糊匹配
        daily_reports = list(upload_path.glob(f"{date_str}-daily-v5-medical-*.pdf"))
    
    # 查找周报（在当前周内）
    date = datetime.strptime(date_str, '%Y-%m-%d')
    # 找到本周一
    monday = date - timedelta(days=date.weekday())
    sunday = monday + timedelta(days=6)
    weekly_pattern = f"{monday.strftime('%Y-%m-%d')}_to_{sunday.strftime('%Y-%m-%d')}-weekly-medical-{safe_name}.pdf"
    weekly_reports = list(upload_path.glob(weekly_pattern))
    if not weekly_reports:
        weekly_reports = list(upload_path.glob(f"*_to_*-weekly-medical-{safe_name}.pdf"))
    
    # 查找月报
    year_month = date_str[:7]
    monthly_reports = list(upload_path.glob(f"{year_month}-monthly-medical-{safe_name}.pdf"))
    if not monthly_reports:
        monthly_reports = list(upload_path.glob(f"*-monthly-medical-{safe_name}.pdf"))
    
    return [str(r) for r in daily_reports + weekly_reports + monthly_reports]

def send_email_to_all(date_str, report_files_pattern=None):
    """发送健康报告邮件给所有成员"""
    members = CONFIG.get("members", [])
    if not members:
        print("❌ 错误: 未配置任何成员")
        return False
    
    upload_dir = CONFIG.get("output_dir", "~/.openclaw/workspace/shared/health-reports/upload")
    
    success_count = 0
    for idx, member in enumerate(members):
        member_name = member.get("name", f"成员{idx+1}")
        print(f"\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print(f"📧 正在为成员 {idx+1}/{len(members)} 发送邮件: {member_name}")
        
        # 查找该成员的报告文件
        if report_files_pattern:
            # 使用指定的文件模式
            member_files = [f for f in report_files_pattern if member_name.replace(' ', '_') in f or f"-{member_name}-" in f or f"_{member_name}_" in f]
            if not member_files:
                # 如果没有找到特定成员的文件，尝试使用通配模式
                member_files = report_files_pattern
        else:
            # 自动查找该成员的报告
            member_files = find_reports_for_member(date_str, upload_dir, member_name)
        
        if not member_files:
            print(f"⚠️  未找到 {member_name} 的报告文件，跳过")
            continue
        
        print(f"📊 找到 {len(member_files)} 个报告文件:")
        for f in member_files:
            print(f"  - {f}")
        
        if send_email(date_str, member_files, idx):
            success_count += 1
    
    print(f"\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"✅ 邮件发送完成: {success_count}/{len(members)} 成功")
    return success_count == len(members)

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

def send_email(date_str, report_files, member_idx=0):
    """发送健康报告邮件给指定成员"""
    
    if not report_files:
        print("❌ 错误: 没有报告文件需要发送")
        return False
    
    existing_files = [f for f in report_files if Path(f).exists()]
    if not existing_files:
        print("❌ 错误: 指定的报告文件都不存在")
        return False
    
    # 获取指定成员的邮箱
    receiver_email = get_member_email(member_idx)
    upload_dir = CONFIG.get("output_dir", "~/.openclaw/workspace/shared/health-reports/upload")
    
    subject = f"健康报告 - {date_str}"
    body = f"您好，\n您的健康报告 ({date_str}) 已生成。\n\n"
    
    print(f"📧 准备发送邮件至 {receiver_email}")
    
    # 1. 尝试 Mail.app
    print("📋 方式1: 使用 macOS Mail.app...")
    if send_with_mail_app(receiver_email, existing_files, subject, body):
        return True
        
    # 获取 SMTP 配置
    sender = EMAIL_CONFIG.get("sender_email")
    password = EMAIL_CONFIG.get("password")
    
    if sender and password:
        if "gmail.com" in sender:
            # 2. Gmail 专用
            print("\n📋 方式2: 使用 Gmail SMTP...")
            if send_with_gmail(sender, password, receiver_email, existing_files, subject, body):
                return True
        else:
            # 3. 通用 SMTP
            print("\n📋 方式3: 使用通用 SMTP...")
            if send_with_smtp(sender, password, receiver_email, existing_files, subject, body):
                return True
    else:
        print("\n⚠️ 未配置 email_config.sender_email/password，跳过 SMTP。")
        
    # 4. Fallback: 复制到本地
    print("\n📋 方式4: 保存到本地 (Fallback)...")
    return send_with_copy(date_str, existing_files, upload_dir)

def main():
    if len(sys.argv) < 2:
        print("用法: python3 send_health_report_email.py <日期> [member_index] [报告文件...]")
        print("示例:")
        print("  python3 send_health_report_email.py 2026-03-01         # 发送给第一个成员")
        print("  python3 send_health_report_email.py 2026-03-01 1       # 发送给第二个成员")
        print("  python3 send_health_report_email.py 2026-03-01 0 file1.pdf file2.pdf")
        sys.exit(1)
        
    date_str = sys.argv[1]
    
    # 解析参数：检查第二个参数是否为成员索引（数字）
    member_idx = 0
    report_files_start = 2
    
    if len(sys.argv) > 2:
        try:
            # 尝试解析为成员索引
            member_idx = int(sys.argv[2])
            report_files_start = 3
        except ValueError:
            # 不是数字，视为报告文件
            member_idx = 0
            report_files_start = 2
    
    # 确定输出目录
    upload_dir = CONFIG.get("output_dir", "~/.openclaw/workspace/shared/health-reports/upload")
    
    if len(sys.argv) > report_files_start:
        report_files = sys.argv[report_files_start:]
    else:
        report_files = find_reports(date_str, upload_dir)
        
    if not report_files:
        print(f"❌ 未找到 {date_str} 的报告文件")
        sys.exit(1)
    
    print(f"📊 找到 {len(report_files)} 个报告文件:")
    for f in report_files:
        print(f"  - {f}")
    print()
        
    success = send_email(date_str, report_files, member_idx)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
