#!/usr/bin/env python3
"""配置验证脚本 - 执行 JSON Schema + 业务规则 双重校验"""
import sys
import json
from pathlib import Path

# 添加 scripts 目录到路径
sys.path.insert(0, str(Path(__file__).parent))
from utils import load_config, validate_config_schema, ConfigError, handle_error


def _find_config_path() -> Path | None:
    """定位实际使用的 config.json 路径"""
    candidates = [
        Path(__file__).parent.parent / "config.json",
        Path.home() / '.openclaw' / 'workspace-health' / 'config.json',
    ]
    for p in candidates:
        if p.exists():
            return p
    return None


def _load_schema() -> dict:
    schema_path = Path(__file__).parent.parent / "config.schema.json"
    if not schema_path.exists():
        raise ConfigError(f"找不到 schema 文件: {schema_path}")
    with open(schema_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def _validate_with_jsonschema(config: dict, schema: dict) -> list[str]:
    """使用 jsonschema 校验（结构约束）"""
    try:
        import jsonschema
    except ImportError:
        return ["未安装 jsonschema，请先执行: pip3 install jsonschema"]

    errors = []
    validator = jsonschema.Draft7Validator(schema)
    for e in sorted(validator.iter_errors(config), key=lambda x: list(x.path)):
        path = '.'.join(str(i) for i in e.path) if e.path else 'root'
        errors.append(f"schema[{path}]: {e.message}")
    return errors


def main():
    """验证 config.json 配置"""
    try:
        config = load_config()
        if not config:
            handle_error(ConfigError("无法加载配置文件"), "配置验证")
            return 1

        config_path = _find_config_path()
        schema = _load_schema()

        schema_errors = _validate_with_jsonschema(config, schema)
        business_errors = validate_config_schema(config)

        # 去重并保持顺序
        all_errors = []
        for err in schema_errors + business_errors:
            if err not in all_errors:
                all_errors.append(err)

        if all_errors:
            print("\n❌ 配置验证失败:")
            if config_path:
                print(f"   配置文件: {config_path}")
            print("   发现以下问题:")
            for error in all_errors:
                print(f"  - {error}")
            return 1

        print("\n✅ 配置验证通过")
        if config_path:
            print(f"   配置文件: {config_path}")
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
