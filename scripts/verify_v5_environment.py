#!/usr/bin/env python3
"""Health Agent V6.0.5 环境检查脚本"""
import sys
import os
import json
from pathlib import Path

# 复用模板解析逻辑，确保环境检查与实际渲染逻辑一致
sys.path.insert(0, str(Path(__file__).parent))
from utils import get_template_path


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


def verify():
    print("🔍 开始 Health Agent V6.0.5 环境检查...\n")
    
    home = Path.home()
    workspace = Path(__file__).parent.parent
    
    # 加载配置获取路径
    config = load_config()
    members = config.get('members', [])
    
    # 检查所有成员（最多3位）
    print(f"📋 发现 {len(members)} 个成员配置（最多检查3位）")
    for idx, member in enumerate(members[:3]):
        member_name = member.get('name', f'成员{idx+1}')
        health_dir_str = member.get('health_dir', '~/我的云端硬盘/Health Auto Export/Health Data')
        workout_dir_str = member.get('workout_dir', '~/我的云端硬盘/Health Auto Export/Workout Data')
        
        health_dir = Path(health_dir_str).expanduser()
        workout_dir = Path(workout_dir_str).expanduser()
        
        print(f"  成员 {idx+1}: {member_name}")
        if health_dir.exists():
            print(f"    ✅ health_dir: {health_dir}")
        else:
            print(f"    ⚠️  health_dir: {health_dir} 不存在")
        
        if workout_dir.exists():
            print(f"    ✅ workout_dir: {workout_dir}")
        else:
            print(f"    ⚠️  workout_dir: {workout_dir} 不存在（如无需运动数据可忽略）")
        print()
    
    # 使用第一成员路径作为后续检查
    if members and len(members) > 0:
        first_member = members[0]
        health_dir_str = first_member.get('health_dir', '~/我的云端硬盘/Health Auto Export/Health Data')
    else:
        health_dir_str = '~/我的云端硬盘/Health Auto Export/Health Data'
        print("⚠️  未找到配置成员，使用默认路径")
    
    health_dir = Path(health_dir_str).expanduser()

    # 1. 检查核心脚本
    scripts = ['extract_data_v5.py', 'generate_v5_medical_dashboard.py', 'generate_weekly_monthly_medical.py', 'send_health_report_email.py']
    for s in scripts:
        p = workspace / 'scripts' / s
        if p.exists():
            print(f"✅ 脚本检测: {s} 存在")
        else:
            print(f"❌ 脚本缺失: {s}")

    # 2. 检查模板（按真实回退策略校验）
    language = str(config.get('language', 'CN')).strip().upper()
    template_dir = workspace / 'templates'

    for report_type in ['daily', 'weekly', 'monthly']:
        try:
            template_path = get_template_path(
                report_type,
                language,
                template_dir,
                version='V2'
            )
            print(f"✅ 模板检测: {report_type} -> {template_path.name}")
        except FileNotFoundError as e:
            print(f"❌ 模板缺失({report_type}): {e}")

    # 3. 检查数据目录 (从 config.json 读取)
    if health_dir.exists():
        print(f"✅ 数据目录: {health_dir} 可访问")
        files = list(health_dir.glob("HealthAutoExport-*.json"))
        print(f"   找到 {len(files)} 个健康数据文件")
    else:
        print(f"⚠️ 数据目录: {health_dir} 未找到。请确保 Health Auto Export 已同步到该路径，或在 config.json 中修改 health_dir")

    # 4. 检查渲染依赖
    try:
        from playwright.sync_api import sync_playwright
        print("✅ 依赖检测: Playwright 已安装")
    except ImportError:
        print("❌ 依赖检测: Playwright 未安装，请运行 pip3 install playwright")

    # 5. 检查缓存目录
    cache_dir_str = config.get('cache_dir', str(workspace / 'cache' / 'daily'))
    cache_dir = Path(cache_dir_str).expanduser()
    cache_dir.mkdir(parents=True, exist_ok=True)
    print(f"✅ 缓存目录: {cache_dir} 已就绪")
    
    # 6. 检查邮件配置
    email_config = config.get('email_config', {})
    if email_config:
        print("✅ 邮件配置: 已配置")
        providers = email_config.get('provider_priority', [])
        print(f"   Provider 优先级: {', '.join(providers)}")
    else:
        print("⚠️  邮件配置: 未配置，将使用本地保存模式")

    print("\n🚀 检查完成！如果看到 ❌ 请先修复再运行报告生成。")

if __name__ == "__main__":
    verify()
