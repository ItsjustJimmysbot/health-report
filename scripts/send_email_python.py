#!/usr/bin/env python3
"""
使用 smtplib 发送健康报告邮件
无需额外安装依赖
"""

import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import os
import sys
from pathlib import Path

def send_health_report(pdf_file=None, to_email="itestmolt@outlook.com"):
    """发送健康报告邮件"""
    
    # 配置
    smtp_server = "smtp.office365.com"
    smtp_port = 587  # 或尝试 465
    sender_email = "itestmolt@outlook.com"
    sender_password = "zrxykblntwxrgrks"  # 应用密码
    
    # 如果没有指定 PDF，使用最新的
    if not pdf_file:
        reports_dir = Path.home() / ".openclaw/workspace/shared/health-reports/pdf"
        pdf_files = sorted(reports_dir.glob("*.pdf"), key=lambda x: x.stat().st_mtime, reverse=True)
        if pdf_files:
            pdf_file = str(pdf_files[0])
        else:
            print("❌ 没有找到 PDF 报告")
            return False
    
    # 创建邮件
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = to_email
    msg['Subject'] = f"每日健康报告 - {Path(pdf_file).stem}"
    
    # 邮件正文
    body = """你好，

这是你的每日健康报告。

报告包含以下内容：
- 心血管指标 (心率、HRV、血氧等)
- 运动数据分析  
- 睡眠质量评估
- 恢复度评分
- 个性化建议

详细的 PDF 报告请查看附件。

祝健康！

---
由 Health Agent 自动生成
"""
    
    msg.attach(MIMEText(body, 'plain', 'utf-8'))
    
    # 添加附件
    try:
        with open(pdf_file, "rb") as attachment:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(attachment.read())
        
        encoders.encode_base64(part)
        part.add_header(
            "Content-Disposition",
            f"attachment; filename= {Path(pdf_file).name}",
        )
        msg.attach(part)
        print(f"✅ 附件已添加: {pdf_file}")
    except Exception as e:
        print(f"❌ 添加附件失败: {e}")
        return False
    
    # 发送邮件
    try:
        print(f"🔄 连接到 {smtp_server}:{smtp_port}...")
        
        # 尝试 STARTTLS (端口 587)
        try:
            context = ssl.create_default_context()
            with smtplib.SMTP(smtp_server, smtp_port, timeout=30) as server:
                server.ehlo()
                server.starttls(context=context)
                server.ehlo()
                server.login(sender_email, sender_password)
                server.sendmail(sender_email, to_email, msg.as_string())
                print("✅ 邮件发送成功 (STARTTLS)")
                return True
        except Exception as e1:
            print(f"STARTTLS 失败: {e1}")
            
            # 尝试 SSL (端口 465)
            try:
                print("🔄 尝试 SSL 连接 (端口 465)...")
                context = ssl.create_default_context()
                with smtplib.SMTP_SSL(smtp_server, 465, context=context, timeout=30) as server:
                    server.login(sender_email, sender_password)
                    server.sendmail(sender_email, to_email, msg.as_string())
                    print("✅ 邮件发送成功 (SSL)")
                    return True
            except Exception as e2:
                print(f"SSL 也失败: {e2}")
                return False
                
    except Exception as e:
        print(f"❌ 发送失败: {e}")
        return False

if __name__ == "__main__":
    pdf_file = sys.argv[1] if len(sys.argv) > 1 else None
    to_email = sys.argv[2] if len(sys.argv) > 2 else "itestmolt@outlook.com"
    
    if send_health_report(pdf_file, to_email):
        print("\n✅ 完成!")
        sys.exit(0)
    else:
        print("\n❌ 发送失败")
        sys.exit(1)
