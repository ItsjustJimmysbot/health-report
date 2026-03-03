#!/usr/bin/env python3
"""配置验证脚本 - V5.8.1"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from utils import load_config, validate_config_schema, MAX_MEMBERS


def main():
    config = load_config()
    
    if not config:
        print("错误: 无法加载 config.json")
        sys.exit(1)
    
    errors = validate_config_schema(config)
    
    if errors:
        print(f"发现 {len(errors)} 个错误:")
        for error in errors:
            print(f"  - {error}")
        sys.exit(1)
    else:
        print("配置验证通过！")
        sys.exit(0)


if __name__ == '__main__':
    main()
