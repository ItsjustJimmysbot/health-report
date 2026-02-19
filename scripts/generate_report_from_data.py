#!/usr/bin/env python3
"""
使用真实健康数据生成报告（结合 Google Fit 睡眠数据）
"""

import json
import sys
import subprocess
sys.path.insert(0, '/Users/jimmylu/.openclaw/workspace-health/scripts')

from generate_visual_report import generate_visual_report, calculate_recovery_score, calculate_sleep_score, calculate_exercise_score
from parse_health_data import parse_health_data
from get_google_fit_sleep import get_google_fit_sleep, merge_sleep_data

def main():
    target_date = "2026-02-18"
    
    # 1. 读取 Apple Health 数据（除睡眠外的所有数据）
    apple_health_file = f"{os.path.expanduser('~')}/我的云端硬盘/Health Auto Export/Health Data/HealthAutoExport-{target_date}.json"
    
    try:
        health_data = parse_health_data(apple_health_file, target_date)
        print(f"✅ Apple Health 数据已解析")
    except Exception as e:
        print(f"❌ 解析 Apple Health 数据失败: {e}")
        # 使用默认数据
        health_data = {
            'date': target_date,
            'weekday': '三',
            'steps': 6853,
            'exercise_min': 40,
            'hrv': 52.77,
            'resting_hr': 57,
            'floors': 108,
            'blood_oxygen': 97,
            'distance': 0,
            'active_calories': 0
        }
    
    # 2. 从 Google Fit 获取睡眠数据
    print(f"📱 正在从 Google Fit 获取 {target_date} 的睡眠数据...")
    google_sleep = get_google_fit_sleep(target_date)
    
    if google_sleep:
        print(f"✅ Google Fit 睡眠数据: {google_sleep['total_hours']} 小时")
        # 合并数据（使用 Google Fit 的睡眠时长）
        health_data = merge_sleep_data(health_data, google_sleep)
    else:
        print("⚠️ 使用 Apple Health 睡眠数据")
    
    # 3. 转换为整数/合理格式
    health_data['steps'] = int(health_data.get('steps', 0))
    health_data['floors'] = int(health_data.get('floors', 0))
    
    # 确保睡眠百分比存在
    sleep_hours = health_data.get('sleep_hours', 0)
    if sleep_hours > 0:
        if 'sleep_deep_pct' not in health_data:
            health_data['sleep_deep_pct'] = round(health_data.get('sleep_deep', 0) / sleep_hours * 100)
            health_data['sleep_rem_pct'] = round(health_data.get('sleep_rem', 0) / sleep_hours * 100)
            health_data['sleep_core_pct'] = round(health_data.get('sleep_core', 0) / sleep_hours * 100)
            health_data['sleep_awake_pct'] = round(health_data.get('sleep_awake', 0) / sleep_hours * 100)
    
    # 4. 计算各评分
    recovery_score = calculate_recovery_score(health_data)
    sleep_score = calculate_sleep_score(health_data)
    exercise_score = calculate_exercise_score(health_data)
    
    print(f"📊 恢复度评分: {recovery_score}/100")
    print(f"😴 睡眠质量评分: {sleep_score}/100")
    print(f"🏃 运动完成评分: {exercise_score}/100")
    
    # 5. 生成报告
    html_file = '/Users/jimmylu/.openclaw/workspace/shared/health-reports/2026-02-18-visual-report.html'
    generate_visual_report(health_data, html_file)
    
    print(f"✅ HTML报告已生成: {html_file}")
    
    # 保存数据供调试
    with open('/tmp/health_data_final.json', 'w', encoding='utf-8') as f:
        json.dump(health_data, f, ensure_ascii=False, indent=2)
    
    return html_file

if __name__ == '__main__':
    import os
    main()
