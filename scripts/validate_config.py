#!/usr/bin/env python3
"""配置验证脚本 - V5.8.1: 同时执行 JSON Schema + 业务校验"""

import sys
import json
from pathlib import Path

# 添加脚本目录到路径
sys.path.insert(0, str(Path(__file__).parent))
from utils import load_config, validate_config_schema

def validate_with_jsonschema(config: dict) -> list:
    """使用 jsonschema 校验配置"""
    errors = []
    
    try:
        from jsonschema import Draft7Validator
    except ImportError:
        print("❌ 缺少 jsonschema，无法执行 schema 校验")
        print("   请安装: pip3 install jsonschema>=4.0.0")
        sys.exit(1)
    
    # 读取 schema 文件
    schema_path = Path(__file__).parent.parent / 'config.schema.json'
    if not schema_path.exists():
        errors.append(f"[schema] 找不到 schema 文件: {schema_path}")
        return errors
    
    try:
        with open(schema_path, 'r', encoding='utf-8') as f:
            schema = json.load(f)
    except Exception as e:
        errors.append(f"[schema] 读取 schema 文件失败: {e}")
        return errors
    
    # 执行校验
    validator = Draft7Validator(schema)
    for error in validator.iter_errors(config):
        path = '/'.join(str(p) for p in error.path) if error.path else 'root'
        errors.append(f"[schema] {path}: {error.message}")
    
    return errors


def main():
    config = load_config()
    
    if not config:
        print("错误: 无法加载 config.json")
        sys.exit(1)
    
    # 合并两种校验的错误
    all_errors = []
    
    # 1. JSON Schema 校验
    schema_errors = validate_with_jsonschema(config)
    all_errors.extend(schema_errors)
    
    # 2. 业务逻辑校验
    logic_errors = validate_config_schema(config)
    for err in logic_errors:
        all_errors.append(f"[logic] {err}")
    
    # 输出结果
    if all_errors:
        print(f"发现 {len(all_errors)} 个错误:")
        for error in all_errors:
            print(f"  - {error}")
        sys.exit(1)
    else:
        print("配置验证通过！")
        sys.exit(0)


if __name__ == '__main__':
    main()
