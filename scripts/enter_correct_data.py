#!/usr/bin/env python3
"""
Apple Health 数据录入 + 报告生成
运行后输入正确数据，自动生成修正报告
"""

import json
import os
from datetime import datetime

print("=" * 70)
print("📱 Apple Health 数据录入 + 报告生成 - 2026-02-19")
print("=" * 70)
print()
print("请从 iPhone Apple Health App 查看 2月19日 数据：")
print()

# 默认值（当前报告中的错误数据）
defaults = {
    'hrv': 52,
    'resting_hr': 46,
    'active_energy': 380
}

data = {}

# 交互式输入
print("💓 HRV (心率变异性)")
print("   Apple Health → 浏览 → 心脏 → 心率变异性")
val = input(f"   输入数值 (ms) [当前: {defaults['hrv']}]: ").strip()
data['hrv'] = float(val) if val else defaults['hrv']

print()
print("❤️  静息心率")
print("   Apple Health → 浏览 → 心脏 → 静息心率")
val = input(f"   输入数值 (bpm) [当前: {defaults['resting_hr']}]: ").strip()
data['resting_hr'] = float(val) if val else defaults['resting_hr']

print()
print("🔥 活动能量 (Active Energy)")
print("   Apple Health → 浏览 → 活动记录 → 活动能量")
val = input(f"   输入数值 (千卡) [当前: {defaults['active_energy']}]: ").strip()
data['active_energy'] = float(val) if val else defaults['active_energy']

# 其他数据保持不变
print()
print("✅ 其他数据保持不变：")
print(f"   步数: 6156")
print(f"   睡眠: 6.54h (03:02→09:34 UTC+8)")
print(f"   平均心率: 73 bpm")

# 保存数据
output_file = '/Users/jimmylu/.openclaw/workspace-health/data/apple_health_corrected_2026-02-19.json'
os.makedirs(os.path.dirname(output_file), exist_ok=True)

with open(output_file, 'w') as f:
    json.dump(data, f, indent=2)

print()
print("=" * 70)
print("📊 修正后的数据：")
print("=" * 70)
print(f"  HRV: {data['hrv']} ms (来源: Apple Health)")
print(f"  静息心率: {data['resting_hr']} bpm (来源: Apple Health)")
print(f"  活动能量: {data['active_energy']} kcal (来源: Apple Health)")
print()
print(f"💾 数据已保存: {output_file}")
print()
print("⚠️  现在运行报告生成脚本生成修正版 PDF")
