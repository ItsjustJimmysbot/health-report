#!/usr/bin/env python3
"""
Health Agent V5.0 环境验证脚本
新session启动时运行，确保环境配置正确
"""
import json
from pathlib import Path
from datetime import datetime

def check_environment():
    """检查V5.0环境配置"""
    print("=" * 60)
    print("Health Agent V5.0 环境验证")
    print("=" * 60)
    
    errors = []
    warnings = []
    
    # 1. 检查必需文件
    print("\n📄 检查必需文件...")
    required_files = [
        ('AGENTS.md', '全局规则'),
        ('BOOTSTRAP.md', 'V5.0启动配置'),
        ('docs/REPORT_STANDARD_V5_REVISED.md', '标准化流程'),
        ('docs/PERSONALIZED_AI_GUIDE.md', 'AI分析规范'),
    ]
    
    for filename, desc in required_files:
        path = Path(filename)
        if path.exists():
            print(f"  ✅ {desc}: {filename}")
        else:
            errors.append(f"缺失文件: {filename} ({desc})")
            print(f"  ❌ {desc}: {filename} (缺失)")
    
    # 2. 检查模板
    print("\n🎨 检查V2模板...")
    templates = [
        ('templates/DAILY_TEMPLATE_V2.html', '667eea', '日报'),
        ('templates/WEEKLY_TEMPLATE_V2.html', '3b82f6', '周报'),
        ('templates/MONTHLY_TEMPLATE_V2.html', '7c3aed', '月报'),
    ]
    
    for filename, color, desc in templates:
        path = Path(filename)
        if not path.exists():
            errors.append(f"缺失模板: {filename}")
            print(f"  ❌ {desc}: {filename} (缺失)")
        else:
            content = path.read_text()
            if color not in content:
                errors.append(f"模板错误: {filename} 不是V2模板")
                print(f"  ❌ {desc}: {filename} (版本错误)")
            else:
                print(f"  ✅ {desc}: {filename}")
    
    # 3. 检查数据目录
    print("\n📊 检查数据目录...")
    home = Path.home()
    data_dirs = [
        (home / '我的云端硬盘' / 'Health Auto Export' / 'Health Data', 'Health Data'),
        (home / '我的云端硬盘' / 'Health Auto Export' / 'Workout Data', 'Workout Data'),
    ]
    
    for path, desc in data_dirs:
        if path.exists():
            files = list(path.glob('*.json'))
            print(f"  ✅ {desc}: {len(files)}个文件")
        else:
            warnings.append(f"数据目录不存在: {path}")
            print(f"  ⚠️ {desc}: 目录不存在")
    
    # 4. 检查缓存目录
    print("\n💾 检查缓存目录...")
    cache_dir = Path('cache/daily')
    if not cache_dir.exists():
        cache_dir.mkdir(parents=True, exist_ok=True)
        print(f"  ✅ 已创建: {cache_dir}")
    else:
        cache_files = list(cache_dir.glob('*.json'))
        print(f"  ✅ 缓存目录: {len(cache_files)}个缓存文件")
    
    # 5. 检查输出目录
    print("\n📤 检查输出目录...")
    output_dir = home / '.openclaw' / 'workspace' / 'shared' / 'health-reports' / 'upload'
    if not output_dir.exists():
        output_dir.mkdir(parents=True, exist_ok=True)
        print(f"  ✅ 已创建: {output_dir}")
    else:
        print(f"  ✅ 输出目录: 已就绪")
    
    # 6. 加载关键常量
    print("\n🔧 加载V5.0常量...")
    constants = {
        'RECOVERY_BASE': 70,
        'HRV_ANALYSIS_LENGTH': (150, 200),
        'SLEEP_ANALYSIS_LENGTH': (150, 200),
        'WORKOUT_ANALYSIS_LENGTH': (150, 200),
        'PRIORITY_RECOMMENDATION_LENGTH': (250, 300),
    }
    for name, value in constants.items():
        print(f"  ✅ {name}: {value}")
    
    # 7. 检查最近数据
    print("\n📅 检查最近数据...")
    today = datetime.now().strftime('%Y-%m-%d')
    recent_dates = [
        (datetime.now() - __import__('datetime').timedelta(days=i)).strftime('%Y-%m-%d')
        for i in range(7)
    ]
    
    health_dir = home / '我的云端硬盘' / 'Health Auto Export' / 'Health Data'
    if health_dir.exists():
        found_dates = []
        for date in recent_dates:
            filepath = health_dir / f'HealthAutoExport-{date}.json'
            if filepath.exists():
                found_dates.append(date)
        
        if found_dates:
            print(f"  ✅ 最近数据: {', '.join(found_dates[:3])}...")
        else:
            warnings.append("未找到最近7天的健康数据")
            print(f"  ⚠️ 未找到最近7天的健康数据")
    
    # 总结
    print("\n" + "=" * 60)
    if errors:
        print(f"❌ 验证失败: 发现 {len(errors)} 个错误")
        for error in errors:
            print(f"   - {error}")
        return False
    elif warnings:
        print(f"⚠️ 验证通过: 发现 {len(warnings)} 个警告")
        for warning in warnings:
            print(f"   - {warning}")
        return True
    else:
        print("✅ 验证通过: 环境配置正确")
        return True

def show_quick_start():
    """显示快速入门"""
    print("\n" + "=" * 60)
    print("🚀 Health Agent V5.0 快速入门")
    print("=" * 60)
    print("""
生成日报：
  python3 scripts/generate_v5_ai_report.py

生成周报/月报：
  python3 scripts/generate_weekly_monthly_v5_ai.py

查看标准化流程：
  cat docs/REPORT_STANDARD_V5_REVISED.md

验证环境：
  python3 scripts/verify_v5_environment.py
""")

if __name__ == '__main__':
    success = check_environment()
    show_quick_start()
    
    if not success:
        exit(1)
