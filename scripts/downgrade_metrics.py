#!/usr/bin/env python3
"""当AI无法生成某项指标分析时，自动从selected中移除该指标"""
import json
import sys
from pathlib import Path

def load_config():
    config_paths = [
        Path("config.json"),
        Path.home() / '.openclaw/workspace-health/config.json',
    ]
    for p in config_paths:
        if p.exists():
            with open(p, 'r', encoding='utf-8') as f:
                return json.load(f), p
    return {}, None

def save_config(config, path):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

def remove_metric_from_selected(metric_key):
    config, path = load_config()
    if not config:
        print("❌ 找不到config.json")
        return False
    
    rm = config.get('report_metrics', {})
    selected = rm.get('selected', [])
    
    if metric_key in selected:
        selected.remove(metric_key)
        rm['selected'] = selected
        config['report_metrics'] = rm
        save_config(config, path)
        print(f"✅ 已从selected中移除: {metric_key}")
        return True
    else:
        print(f"⚠️ {metric_key} 不在selected中")
        return False

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("用法: python3 scripts/downgrade_metrics.py <metric_key>")
        print("示例: python3 scripts/downgrade_metrics.py running_power")
        sys.exit(1)
    
    metric_key = sys.argv[1]
    remove_metric_from_selected(metric_key)
