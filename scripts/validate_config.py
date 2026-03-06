#!/usr/bin/env python3
"""配置验证脚本 - 执行 JSON Schema + 业务规则 双重校验"""
import argparse
import sys
import json
from pathlib import Path
from typing import Optional

# 添加 scripts 目录到路径
sys.path.insert(0, str(Path(__file__).parent))
from utils import load_config, validate_config_schema, ConfigError, handle_error


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="验证 Health Report 配置文件")
    parser.add_argument(
        "--config",
        dest="config_path",
        help="指定要校验的配置文件路径（默认按内置搜索路径查找）",
    )
    parser.add_argument(
        "--schema",
        dest="schema_path",
        help="指定 schema 文件路径（默认使用仓库根目录 config.schema.json）",
    )
    return parser.parse_args()


def _find_config_path(explicit_path: Optional[str] = None) -> Optional[Path]:
    """定位实际使用的 config.json 路径"""
    if explicit_path:
        p = Path(explicit_path).expanduser()
        return p if p.exists() else None

    candidates = [
        Path(__file__).parent.parent / "config.json",
        Path.home() / '.openclaw' / 'workspace-health' / 'config.json',
    ]
    for p in candidates:
        if p.exists():
            return p
    return None


def _load_config_from_path(config_path: Path) -> dict:
    """从指定路径加载配置"""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise ConfigError(f"配置文件 JSON 解析失败: {config_path} ({e})")
    except Exception as e:
        raise ConfigError(f"读取配置文件失败: {config_path} ({e})")


def _load_schema(schema_path: Optional[str] = None) -> dict:
    if schema_path:
        path = Path(schema_path).expanduser()
    else:
        path = Path(__file__).parent.parent / "config.schema.json"

    if not path.exists():
        raise ConfigError(f"找不到 schema 文件: {path}")

    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise ConfigError(f"schema JSON 解析失败: {path} ({e})")


def _validate_with_jsonschema(config: dict, schema: dict) -> list[str]:
    """使用 jsonschema 校验（结构约束）"""
    try:
        import jsonschema
    except ImportError:
        return ["未安装 jsonschema，请先执行: pip3 install jsonschema"]

    errors = []
    validator = jsonschema.Draft7Validator(schema, format_checker=jsonschema.FormatChecker())
    for e in sorted(validator.iter_errors(config), key=lambda x: list(x.path)):
        path = '.'.join(str(i) for i in e.path) if e.path else 'root'
        errors.append(f"schema[{path}]: {e.message}")
    return errors


def main():
    """验证 config.json 配置"""
    args = _parse_args()

    try:
        # 显式路径优先；否则沿用默认搜索
        if args.config_path:
            config_path = _find_config_path(args.config_path)
            if not config_path:
                handle_error(ConfigError(f"找不到指定配置文件: {Path(args.config_path).expanduser()}"), "配置验证", exit_on_fatal=False)
                return 1
            config = _load_config_from_path(config_path)
        else:
            config_path = _find_config_path()
            config = load_config()
            if not config:
                handle_error(ConfigError("无法加载配置文件"), "配置验证", exit_on_fatal=False)
                return 1
            if not config_path:
                handle_error(ConfigError("未找到配置文件路径"), "配置验证", exit_on_fatal=False)
                return 1

        schema = _load_schema(args.schema_path)

        schema_errors = _validate_with_jsonschema(config, schema)
        business_errors = validate_config_schema(config)

        # 去重并保持顺序
        all_errors = []
        for err in schema_errors + business_errors:
            if err not in all_errors:
                all_errors.append(err)

        if all_errors:
            print("\n❌ 配置验证失败:")
            print(f"   配置文件: {config_path}")
            print("   发现以下问题:")
            for error in all_errors:
                print(f"  - {error}")
            return 1

        print("\n✅ 配置验证通过")
        print(f"   配置文件: {config_path}")
        members = config.get('members', [])
        print(f"   版本: {config.get('version', 'unknown')}")
        print(f"   成员数: {len(members)}")
        print(f"   语言: {config.get('language', 'CN')}")
        for i, m in enumerate(members):
            print(f"   成员{i+1}: {m.get('name', '未命名')}")
        return 0

    except Exception as e:
        handle_error(e, "配置验证", exit_on_fatal=False)
        return 1


if __name__ == '__main__':
    sys.exit(main())
