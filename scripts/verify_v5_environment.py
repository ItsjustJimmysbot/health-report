#!/usr/bin/env python3
import sys
import os
import json
from pathlib import Path

def verify():
    print("🔍 开始 Health Agent V5.1 环境检查...\n")
    
    home = Path.home()
    workspace = Path(__file__).parent.parent
    
    # 1. 检查核心脚本
    scripts = ['extract_data_v5.py', 'generate_v5_medical_dashboard.py', 'generate_weekly_monthly_medical.py', 'send_health_report_email.py']
    for s in scripts:
        p = workspace / 'scripts' / s
        if p.exists():
            print(f"✅ 脚本检测: {s} 存在")
        else:
            print(f"❌ 脚本缺失: {s}")

    # 2. 检查模板
    templates = ['DAILY_TEMPLATE_MEDICAL_V2.html', 'WEEKLY_TEMPLATE_MEDICAL.html', 'MONTHLY_TEMPLATE_MEDICAL.html']
    for t in templates:
        p = workspace / 'templates' / t
        if p.exists():
            print(f"✅ 模板检测: {t} 存在")
        else:
            print(f"❌ 模板缺失: {t}")

    # 3. 检查数据目录 (根据脚本默认路径)
    health_dir = home / "我的云端硬盘" / "Health Auto Export" / "Health Data"
    if health_dir.exists():
        print(f"✅ 数据目录: {health_dir} 可访问")
        files = list(health_dir.glob("HealthAutoExport-*.json"))
        print(f"   找到 {len(files)} 个健康数据文件")
    else:
        print(f"⚠️ 数据目录: {health_dir} 未找到。请确保 Health Auto Export 已同步到该路径，或在脚本中修改 DEFAULT_HEALTH_DIR")

    # 4. 检查渲染依赖
    try:
        from playwright.sync_api import sync_playwright
        print("✅ 依赖检测: Playwright 已安装")
    except ImportError:
        print("❌ 依赖检测: Playwright 未安装，请运行 pip3 install playwright")

    # 5. 检查缓存目录
    cache_dir = workspace / 'cache' / 'daily'
    cache_dir.mkdir(parents=True, exist_ok=True)
    print(f"✅ 缓存目录: {cache_dir} 已就绪")

    print("\n🚀 检查完成！如果看到 ❌ 请先修复再运行报告生成。")

if __name__ == "__main__":
    verify()
