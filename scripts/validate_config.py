#!/usr/bin/env python3
"""配置验证脚本 - 使用 utils.py 中的验证逻辑"""
import sys
from pathlib import Path

# 添加 scripts 目录到路径
sys.path.insert(0, str(Path(__file__).parent))
from utils import load_config, validate_config_schema, ConfigError, handle_error

def main():
    """验证 config.json 配置"""
    try:
        config = load_config()
        if not config:
            handle_error(ConfigError("无法加载配置文件"), "配置验证")
            return 1
        
        errors = validate_config_schema(config)
        
        if errors:
            print("\n❌ 配置验证失败:")
            for error in errors:
                print(f"  - {error}")
            return 1
        else:
            print("\n✅ 配置验证通过")
            members = config.get('members', [])
            print(f"   版本: {config.get('version', 'unknown')}")
            print(f"   成员数: {len(members)}")
            print(f"   语言: {config.get('language', 'CN')}")
            for i, m in enumerate(members):
                print(f"   成员{i+1}: {m.get('name', '未命名')}")
            return 0
            
    except Exception as e:
        handle_error(e, "配置验证")
        return 1

if __name__ == '__main__':
    sys.exit(main())
