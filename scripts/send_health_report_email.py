#!/usr/bin/env python3
"""
健康报告邮件发送脚本 V5.0 - 使用 macOS Mail.app
用法: python3 scripts/send_health_report_email.py <日期> [报告文件列表...]

配置:
- 使用系统 Mail.app (已配置 Outlook)
- Outlook 邮箱: revolutionljk@gmail.com (或其他已配置账户)
"""

import sys
import subprocess
import shutil
from pathlib import Path
from datetime import datetime

def send_with_mail_app(date_str, report_files, subject, body):
    """使用 macOS Mail.app 发送邮件"""
    
    recipient = "revolutionljk@gmail.com"
    
    # 构建 AppleScript
    # 转义特殊字符
    escaped_subject = subject.replace('"', '\\"')
    escaped_body = body.replace('"', '\\"').replace("'", "\\'")
    
    # 构建附件列表
    attachment_list = ", ".join([f'"{f}"' for f in report_files])
    
    applescript = f'''
tell application "Mail"
    set newMessage to make new outgoing message with properties {{subject:"{escaped_subject}", content:"{escaped_body}"}}
    tell newMessage
        make new to recipient with properties {{address:"{recipient}"}}
        '''
    
    # 添加附件
    for f in report_files:
        applescript += f'        make new attachment with properties {{file name:"{f}"}} at after last paragraph\n'
    
    applescript += '''        send
    end tell
end tell
'''
    
    print(f"   使用 Mail.app 发送...")
    print(f"   收件人: {recipient}")
    print(f"   主题: {subject}")
    print(f"   附件: {len(report_files)} 个")
    
    try:
        result = subprocess.run(
            ["osascript", "-e", applescript],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            print("   ✅ Mail.app 发送成功")
            return True
        else:
            print(f"   ❌ Mail.app 失败: {result.stderr}")
            return False
    except Exception as e:
        print(f"   ❌ Mail.app 异常: {e}")
        return False

def send_with_outlook_smtp(date_str, report_files, subject, body):
    """使用 Outlook SMTP 直接发送"""
    
    # Outlook SMTP 配置
    smtp_server = "smtp.office365.com"
    smtp_port = 587
    sender_email = "revolutionljk@gmail.com"  # 或其他Outlook邮箱
    receiver_email = "revolutionljk@gmail.com"
    password = "fkvkbrttcrzkgnjw"  # Outlook 应用密码
    
    print(f"   使用 Outlook SMTP: {smtp_server}:{smtp_port}")
    
    try:
        import smtplib
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText
        from email.mime.base import MIMEBase
        from email import encoders
        
        # 创建邮件
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = receiver_email
        msg['Subject'] = subject
        
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        
        # 添加附件
        for f in report_files:
            p = Path(f)
            if p.exists():
                print(f"   附加: {p.name}")
                with open(f, 'rb') as fp:
                    attachment = MIMEBase('application', 'pdf')
                    attachment.set_payload(fp.read())
                    encoders.encode_base64(attachment)
                    attachment.add_header(
                        'Content-Disposition',
                        f'attachment; filename="{p.name}"'
                    )
                    msg.attach(attachment)
        
        # 连接SMTP
        print("   连接 SMTP...")
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        print("   登录...")
        server.login(sender_email, password)
        print("   发送...")
        server.send_message(msg)
        server.quit()
        
        print("   ✅ Outlook SMTP 发送成功")
        return True
        
    except Exception as e:
        print(f"   ❌ SMTP 失败: {e}")
        return False

def send_with_copy(date_str, report_files, target_dir):
    """保存到本地作为 fallback"""
    target = Path(target_dir)
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

def send_email(date_str, report_files):
    """发送健康报告邮件"""
    
    if not report_files:
        print("❌ 错误: 没有报告文件需要发送")
        return False
    
    existing_files = [f for f in report_files if Path(f).exists()]
    if not existing_files:
        print("❌ 错误: 指定的报告文件都不存在")
        return False
    
    subject = f"健康日报 - {date_str}"
    
    body_lines = [
        "您好，",
        "",
        "您的健康报告已生成完成。",
        "",
        f"报告日期: {date_str}",
        f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "附件包含以下报告:"
    ]
    
    for f in existing_files:
        p = Path(f)
        size_kb = p.stat().st_size / 1024
        body_lines.append(f"  • {p.name} ({size_kb:.0f} KB)")
    
    body_lines.extend([
        "",
        "报告说明:",
        "• 日报: 单日详细健康数据分析",
        "• 周报: 本周数据趋势汇总（周日发送）",
        "• 月报: 整月数据统计分析（月末发送）",
        "",
        "数据来源: Apple Health",
        "分析方法: V5.0 AI分析标准化流程"
    ])
    
    body = "\n".join(body_lines)
    
    print(f"📧 准备发送邮件")
    print(f"   收件人: revolutionljk@gmail.com")
    print(f"   主题: {subject}")
    print(f"   附件: {len(existing_files)} 个文件")
    print()
    
    # 方式1: 使用 Outlook SMTP (已配置应用密码)
    print("📋 方式1: 使用 Outlook SMTP...")
    if send_with_outlook_smtp(date_str, existing_files, subject, body):
        return True
    print()
    
    # 方式2: 尝试使用 Mail.app
    print("📋 方式2: 使用 macOS Mail.app...")
    if send_with_mail_app(date_str, existing_files, subject, body):
        return True
    print()
    
    # 方式3: 保存到本地
    upload_dir = Path.home() / ".openclaw" / "workspace" / "shared" / "health-reports" / "upload"
    print("📋 方式3: 保存到本地...")
    return send_with_copy(date_str, existing_files, upload_dir)

def find_reports(date_str, upload_dir):
    """查找指定日期的报告文件（每种类型只取一份）"""
    upload_path = Path(upload_dir)
    
    if not upload_path.exists():
        return []
    
    # 查找日报: 优先使用带成员名的版本，排除-dashboard旧版本
    daily_reports = list(upload_path.glob(f"{date_str}-daily-v5-medical-*.pdf"))
    # 过滤掉包含 -dashboard 的旧版本
    daily_filtered = [r for r in daily_reports if "-dashboard" not in r.name]
    # 如果有过滤后的版本，使用第一个；否则使用原始列表的第一个
    selected_daily = [daily_filtered[0]] if daily_filtered else ([daily_reports[0]] if daily_reports else [])
    
    # 周报: 只取一份
    weekly_reports = list(upload_path.glob(f"weekly-report-*-to-{date_str}-V5.pdf"))
    selected_weekly = [weekly_reports[0]] if weekly_reports else []
    
    # 月报: 只取一份
    year_month = date_str[:7]
    monthly_reports = list(upload_path.glob(f"monthly-report-{year_month}-V5.pdf"))
    selected_monthly = [monthly_reports[0]] if monthly_reports else []
    
    all_reports = selected_daily + selected_weekly + selected_monthly
    return [str(r) for r in all_reports]

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python3 scripts/send_health_report_email.py <日期> [报告文件1] [报告文件2] ...")
        print("示例: python3 scripts/send_health_report_email.py 2026-02-24")
        print()
        print("邮件发送方式（按优先级）:")
        print("  1. Outlook SMTP (smtp.office365.com)")
        print("  2. macOS Mail.app (osascript)")
        print("  3. 保存到本地目录")
        sys.exit(1)
    
    date_str = sys.argv[1]
    
    if len(sys.argv) > 2:
        report_files = sys.argv[2:]
    else:
        upload_dir = Path.home() / ".openclaw" / "workspace" / "shared" / "health-reports" / "upload"
        report_files = find_reports(date_str, upload_dir)
    
    if not report_files:
        print(f"❌ 未找到 {date_str} 的报告文件")
        sys.exit(1)
    
    print(f"📊 找到 {len(report_files)} 个报告文件:")
    for f in report_files:
        print(f"  - {f}")
    print()
    
    success = send_email(date_str, report_files)
    sys.exit(0 if success else 1)
