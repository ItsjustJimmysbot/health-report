#!/usr/bin/env python3
"""
更新 2.19 Apple Health 数据并重新生成报告
"""

import json
import os
import sys

# 默认值（当前报告中的错误数据）
current_data = {
    'date': '2026-02-19',
    'hrv_ms': 52,
    'resting_hr_bpm': 46,
    'active_energy_kcal': 380,
    'steps': 6156,
    'avg_hr': 73,
    'sleep_hours': 6.54,
    'sleep_start': '2026-02-20 03:02',
    'sleep_end': '2026-02-20 09:34'
}

print("=" * 70)
print("📱 更新 2.19 Apple Health 数据")
print("=" * 70)
print()
print("当前报告数据（可能有误）：")
print(f"  HRV: {current_data['hrv_ms']} ms")
print(f"  静息心率: {current_data['resting_hr_bpm']} bpm")
print(f"  活动能量: {current_data['active_energy_kcal']} kcal")
print()

# 两种方式输入新数据
print("选择输入方式：")
print("1. 手动输入数值")
print("2. 提供 JSON 文件路径")
print()

choice = input("选择 (1/2): ").strip()

if choice == '1':
    print()
    print("请输入 Apple Health 实际数据：")
    
    val = input(f"HRV (ms) [当前 {current_data['hrv_ms']}]: ").strip()
    if val: current_data['hrv_ms'] = float(val)
    
    val = input(f"静息心率 (bpm) [当前 {current_data['resting_hr_bpm']}]: ").strip()
    if val: current_data['resting_hr_bpm'] = float(val)
    
    val = input(f"活动能量 (kcal) [当前 {current_data['active_energy_kcal']}]: ").strip()
    if val: current_data['active_energy_kcal'] = float(val)
    
elif choice == '2':
    file_path = input("请输入 JSON 文件路径: ").strip()
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            new_data = json.load(f)
            current_data.update(new_data)
        print(f"✅ 已从 {file_path} 读取数据")
    else:
        print(f"❌ 文件不存在: {file_path}")
        sys.exit(1)
else:
    print("❌ 无效选择")
    sys.exit(1)

# 保存修正数据
output_dir = '/Users/jimmylu/.openclaw/workspace-health/data'
os.makedirs(output_dir, exist_ok=True)

output_file = os.path.join(output_dir, 'apple_health_2026-02-19-corrected.json')
with open(output_file, 'w') as f:
    json.dump(current_data, f, indent=2)

print()
print("=" * 70)
print("✅ 数据已更新！")
print("=" * 70)
print()
print("📊 修正后的数据：")
print(f"  HRV: {current_data['hrv_ms']} ms")
print(f"  静息心率: {current_data['resting_hr_bpm']} bpm")
print(f"  活动能量: {current_data['active_energy_kcal']} kcal")
print()
print(f"💾 保存位置: {output_file}")
print()
print("⚠️  请运行报告生成脚本生成新版 PDF")
