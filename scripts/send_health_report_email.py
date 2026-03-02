#!/usr/bin/env python3
"""健康报告邮件发送脚本 V5.8.0

功能:
    - 支持可配置的 Provider 优先级 (OAuth2/SMTP/Mail.app/Local)
    - 支持多成员邮件发送
    - 自动 fallback 机制
"""

import sys
import json
from pathlib import Path
from datetime import datetime, timedelta

# 导入 Provider
from email_providers import PROVIDER_MAP


def load_config():
    """加载配置文件"""
    config_paths = [
        Path(__file__).parent.parent / "config.json",
        Path.home() / '.openclaw' / 'workspace-health' / 'config.json',
    ]
    for config_path in config_paths:
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
    return {}


def get_email_providers(config: dict) -> list:
    """根据配置返回启用的 Provider 列表（按优先级排序）"""
    email_config = config.get('email_config', {})
    
    # 默认优先级
    default_priority = ['oauth2', 'smtp', 'mail_app', 'local']
    priority = email_config.get('provider_priority', default_priority)
    
    providers = []
    for provider_name in priority:
        provider_class = PROVIDER_MAP.get(provider_name)
        if not provider_class:
            print(f"⚠️  未知 Provider: {provider_name}")
            continue
        
        # 获取 Provider 配置
        provider_config = email_config.get(provider_name, {})
        
        # 兼容旧配置：如果 smtp 没有独立配置，使用 email_config 顶层
        if provider_name == 'smtp' and not provider_config.get('sender_email'):
            legacy_config = {
                'enabled': bool(email_config.get('sender_email') or 
                              email_config.get('smtp_server')),
                'sender_email': email_config.get('sender_email', ''),
                'password': email_config.get('password', ''),
                'server': email_config.get('smtp_server', ''),
                'port': email_config.get('smtp_port', 587),
                'use_tls': True,
            }
            if legacy_config['enabled']:
                provider_config = legacy_config
        
        # 兼容旧配置：如果 oauth2 有配置但未设置 enabled
        if provider_name == 'oauth2' and provider_config.get('client_id'):
            provider_config['enabled'] = True
        
        # 默认启用 local
        if provider_name == 'local' and 'enabled' not in provider_config:
            provider_config['enabled'] = True
            provider_config['output_dir'] = config.get('output_dir', 
                '~/.openclaw/workspace/shared/health-reports/upload')
        
        provider = provider_class(provider_config)
        
        if provider.is_available():
            providers.append(provider)
            print(f"✅ {provider.get_name()} 已启用")
        else:
            print(f"⏭️  {provider.get_name()} 未启用或配置不完整")
    
    return providers


def get_member_email(config: dict, member_idx: int = 0) -> str:
    """获取指定成员的邮箱 - V5.8.0: 索引越界时返回空字符串，不静默 fallback"""
    members = config.get('members', [])
    email_config = config.get('email_config', {})
    
    # 边界检查 - 越界时返回空字符串并报错
    if members and len(members) > member_idx:
        member = members[member_idx]
        return (member.get('email') or 
                config.get('receiver_email') or 
                email_config.get('receiver_email', ''))
    else:
        print(f"❌ 错误: 成员索引 {member_idx} 超出范围 (总成员数: {len(members)})")
        return ''


def find_reports_for_member(date_str: str, upload_dir: str, member_name: str) -> list:
    """查找指定成员的报告文件"""
    upload_path = Path(upload_dir).expanduser()
    if not upload_path.exists():
        return []
    
    # 处理特殊字符
    safe_name = member_name.replace(' ', '_').replace('/', '_').replace('\\', '_')
    
    # 查找日报 - V5.8.0: 严格匹配 safe_name，不匹配他人文件
    daily_reports = list(upload_path.glob(f"{date_str}-daily-v5-medical-{safe_name}.pdf"))
    # 旧格式兼容（无成员名后缀）
    if not daily_reports:
        daily_reports = list(upload_path.glob(f"{date_str}-daily-v5-medical.pdf"))
    
    # 查找周报（在当前周内）
    date = datetime.strptime(date_str, '%Y-%m-%d')
    monday = date - timedelta(days=date.weekday())
    sunday = monday + timedelta(days=6)
    weekly_pattern = f"{monday.strftime('%Y-%m-%d')}_to_{sunday.strftime('%Y-%m-%d')}-weekly-medical-{safe_name}.pdf"
    weekly_reports = list(upload_path.glob(weekly_pattern))
    
    # 查找月报
    year_month = date_str[:7]
    monthly_reports = list(upload_path.glob(f"{year_month}-monthly-medical-{safe_name}.pdf"))
    
    return [str(r) for r in daily_reports + weekly_reports + monthly_reports]


def send_email(date_str: str, report_files: list, member_idx: int = 0) -> bool:
    """发送邮件给指定成员"""
    config = load_config()
    
    # 获取成员邮箱
    receiver = get_member_email(config, member_idx)
    if not receiver:
        print("❌ 错误: 未配置接收邮箱")
        return False
    
    # 验证报告文件
    existing_files = [f for f in report_files if Path(f).exists()]
    if not existing_files:
        print("❌ 错误: 指定的报告文件都不存在")
        return False
    
    # 获取所有可用的 Provider
    providers = get_email_providers(config)
    if not providers:
        print("❌ 错误: 没有可用的邮件发送方式")
        print("   请检查 config.json 中的 email_config 配置")
        return False
    
    members = config.get('members', [])
    member_name = (members[member_idx].get('name', f'成员{member_idx+1}') 
                   if members and len(members) > member_idx else '用户')
    
    subject = f"健康报告 - {date_str}"
    body = f"您好 {member_name}，\n\n您的健康报告 ({date_str}) 已生成，请查收附件。\n\n祝您健康！"
    
    print(f"\n📧 准备发送邮件至: {receiver}")
    print(f"📎 附件数量: {len(existing_files)}")
    
    # 按优先级尝试
    for i, provider in enumerate(providers, 1):
        print(f"\n{'─' * 50}")
        print(f"📋 尝试方式 {i}/{len(providers)}: {provider.get_name()}")
        print('─' * 50)
        
        if provider.send(receiver, existing_files, subject, body):
            print(f"\n✅ 邮件发送成功！")
            return True
        
        if i < len(providers):
            print(f"⏭️  尝试下一个方式...")
    
    print(f"\n❌ 所有发送方式均失败")
    return False


def send_email_to_all(date_str: str, report_files_pattern: list = None) -> bool:
    """发送邮件给所有成员"""
    config = load_config()
    members = config.get('members', [])
    
    if not members:
        print("❌ 错误: 未配置任何成员")
        return False
    
    upload_dir = config.get('output_dir', 
                            '~/.openclaw/workspace/shared/health-reports/upload')
    
    success_count = 0
    
    print(f"\n{'=' * 60}")
    print(f"📧 批量发送模式: 共 {len(members)} 个成员")
    print('=' * 60)
    
    for idx, member in enumerate(members):
        member_name = member.get('name', f'成员{idx+1}')
        
        print(f"\n{'━' * 60}")
        print(f"👤 成员 {idx+1}/{len(members)}: {member_name}")
        print('━' * 60)
        
        # 确定该成员的报告文件 - V5.8.0: 删除 fallback，不匹配时不发送
        if report_files_pattern:
            # 从指定文件列表中筛选
            safe_name = member_name.replace(' ', '_').replace('/', '_').replace('\\', '_')
            member_files = []
            for f in report_files_pattern:
                if (safe_name in f or member_name in f or 
                    f"-{safe_name}-" in f or f"_{safe_name}_" in f):
                    member_files.append(f)
            # 删除：不再 fallback 到全部文件
        else:
            # 自动查找
            member_files = find_reports_for_member(date_str, upload_dir, member_name)
        
        if not member_files:
            print(f"⚠️  未找到 {member_name} 的报告文件，跳过")
            continue
        
        print(f"📊 找到 {len(member_files)} 个报告文件:")
        for f in member_files:
            print(f"   - {Path(f).name}")
        
        if send_email(date_str, member_files, idx):
            success_count += 1
    
    print(f"\n{'=' * 60}")
    print(f"📊 发送完成: {success_count}/{len(members)} 成功")
    print('=' * 60)
    
    return success_count == len(members)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    date_str = sys.argv[1]
    
    # 解析参数
    member_idx = 0
    report_files_start = 2
    send_to_all = False
    
    if len(sys.argv) > 2:
        second_arg = sys.argv[2]
        if second_arg.lower() == 'all':
            send_to_all = True
            report_files_start = 3
        else:
            try:
                member_idx = int(second_arg)
                report_files_start = 3
            except ValueError:
                # 不是数字，视为报告文件
                member_idx = 0
                report_files_start = 2
    
    # 确定报告文件
    if len(sys.argv) > report_files_start:
        report_files = sys.argv[report_files_start:]
    else:
        # 自动查找
        config = load_config()
        upload_dir = config.get('output_dir', 
                                '~/.openclaw/workspace/shared/health-reports/upload')
        
        if send_to_all:
            report_files = None  # 会在 send_email_to_all 中按成员查找
        else:
            members = config.get('members', [])
            if members and len(members) > member_idx:
                member_name = members[member_idx].get('name', '')
            else:
                member_name = ''
            report_files = find_reports_for_member(date_str, upload_dir, member_name)
    
    # 执行发送
    if send_to_all:
        success = send_email_to_all(date_str, report_files)
    else:
        if not report_files:
            print(f"❌ 未找到 {date_str} 的报告文件")
            sys.exit(1)
        
        print(f"📊 找到 {len(report_files)} 个报告文件:")
        for f in report_files:
            print(f"   - {f}")
        print()
        
        success = send_email(date_str, report_files, member_idx)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
