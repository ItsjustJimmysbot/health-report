#!/usr/bin/env python3
"""统一更新项目版本号 - V5.8.1"""
import re
from pathlib import Path

# 配置
OLD_VERSIONS = ["5.7.1", "5.7.0", "5.8.0"]
NEW_VERSION = "5.8.1"

# 需要更新的文件
FILES_TO_UPDATE = [
    "README.md",
    "SKILL.md",
    "config.json.example",
    "scripts/extract_data_v5.py",
    "scripts/generate_v5_medical_dashboard.py",
    "scripts/generate_weekly_monthly_medical.py",
    "scripts/send_health_report_email.py",
    "scripts/verify_v5_environment.py",
    "scripts/utils.py",
]

def update_version_in_file(filepath: Path) -> int:
    """更新文件中的版本号，返回替换次数"""
    if not filepath.exists():
        print(f"⚠️  文件不存在: {filepath}")
        return 0
    
    content = filepath.read_text(encoding='utf-8')
    original_content = content
    
    # 替换各种格式的版本号
    for old_ver in OLD_VERSIONS:
        # "version": "X.Y.Z"
        content = re.sub(
            rf'"version"\s*:\s*"{old_ver}"',
            f'"version": "{NEW_VERSION}"',
            content
        )
        
        # VX.Y.Z 格式
        content = re.sub(
            rf'V{old_ver}',
            f'V{NEW_VERSION}',
            content
        )
        
        # 文件头注释
        content = re.sub(
            rf'V{old_ver} ',
            f'V{NEW_VERSION} ',
            content
        )
    
    if content != original_content:
        filepath.write_text(content, encoding='utf-8')
        count = original_content.count(OLD_VERSIONS[0])
        print(f"✅ 已更新: {filepath} (约 {count} 处)")
        return count
    else:
        print(f"⏭️  无需更新: {filepath}")
        return 0

# 执行更新
total_replacements = 0
for file_path in FILES_TO_UPDATE:
    total_replacements += update_version_in_file(Path(file_path))

print(f"\n{'='*60}")
print(f"版本更新完成: -> V{NEW_VERSION}")
print(f"总替换次数: {total_replacements}")
print(f"{'='*60}")