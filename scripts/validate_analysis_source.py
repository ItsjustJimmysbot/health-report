#!/usr/bin/env python3
"""
AI Analysis Source Validator
阻止非 AI 对话生成的分析文本
"""
import sys
import os
import json
import re

def validate_analysis_file(filepath):
    """验证 AI 分析文件是否符合规范"""
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    errors = []
    
    # 检查1: 禁止 f-string 痕迹
    fstring_patterns = [
        r'f["\'][^"\']*\{[^}]+\}[^"\']*["\']',  # f"...{var}..."
        r'["\'][^"\']*["\']\s*\.format\(',       # "...".format(...)
        r'["\'][^"\']*["\']\s*%\s*\w+',          # "..." % var
    ]
    for pattern in fstring_patterns:
        if re.search(pattern, content):
            errors.append(f"检测到 f-string 模板痕迹: {pattern}")
    
    # 检查2: 分析文本必须有足够长度 (AI 分析至少 100 字)
    try:
        data = json.loads(content)
        for key in ['hrv', 'resting_hr', 'steps', 'distance', 'sleep', 'workout', 'respiratory']:
            if key in data and len(str(data[key])) < 50:
                errors.append(f"{key} 分析过短，疑似模板生成")
    except:
        pass
    
    # 检查3: 必须有数据引用 (具体的数字)
    if not re.search(r'\d+\.?\d*\s*(ms|bpm|步|km|kcal|小时|分|%)', content):
        errors.append("分析中未引用具体数据点")
    
    return errors

def validate_environment():
    """验证环境变量标记"""
    if not os.environ.get('AI_ANALYSIS_VALIDATED'):
        return ["缺少 AI_ANALYSIS_VALIDATED 环境变量，必须通过 AI 对话分析后才能生成报告"]
    return []

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: validate_analysis_source.py <analysis.json>")
        sys.exit(1)
    
    filepath = sys.argv[1]
    
    errors = validate_environment() + validate_analysis_file(filepath)
    
    if errors:
        print("❌ 验证失败:")
        for e in errors:
            print(f"  - {e}")
        print("\n正确流程:")
        print("  1. AI 读取数据并在对话中分析")
        print("  2. 保存分析为 JSON")
        print("  3. export AI_ANALYSIS_VALIDATED=1")
        print("  4. 生成报告")
        sys.exit(1)
    else:
        print("✅ AI 分析来源验证通过")
        sys.exit(0)
