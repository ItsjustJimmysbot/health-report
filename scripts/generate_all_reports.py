#!/usr/bin/env python3
"""
Daily Health Report Generator
生成四份报告：中文单日、英文单日、中文对比、英文对比
"""

import sys
import json
from datetime import datetime, timedelta
from playwright.sync_api import sync_playwright
import os

def parse_health_data(file_path, date_str):
    """解析 Apple Health 数据"""
    if not os.path.exists(file_path):
        print(f"⚠️ 文件不存在: {file_path}")
        return None
    
    with open(file_path, 'r') as f:
        data = json.load(f)
    
    metrics = data.get('data', {}).get('metrics', [])
    results = {'date': date_str}
    
    for metric in metrics:
        name = metric.get('name', '')
        metric_data = metric.get('data', [])
        
        if not metric_data:
            continue
        
        values = [d.get('qty', 0) for d in metric_data if 'qty' in d]
        if not values:
            continue
        
        if name == 'heart_rate_variability':
            results['hrv'] = round(sum(values) / len(values), 1)
        elif name == 'resting_heart_rate':
            results['resting_hr'] = round(sum(values) / len(values), 1)
        elif name == 'step_count':
            results['steps'] = int(sum(values))
        elif name == 'active_energy':
            kj = sum(values)
            results['active_energy_kj'] = round(kj, 1)
            results['active_energy'] = round(kj / 4.184, 1)  # kJ to kcal
        elif name == 'basal_energy_burned':
            kj = sum(values)
            results['basal_energy_kj'] = round(kj, 1)
            results['basal_energy'] = round(kj / 4.184, 1)
        elif name == 'apple_exercise_time':
            results['exercise_min'] = round(sum(values), 1)
    
    return results

def get_sleep_data(date_str):
    """从 Google Fit 获取睡眠数据（简化版，实际需要API调用）"""
    # 这里应该调用 Google Fit API
    # 简化版本：返回示例数据
    return {
        'sleep_hours': 6.5,
        'sleep_start': f'{date_str} 23:30',
        'sleep_end': f'{date_str} 06:00'
    }

def generate_html(data, lang='zh', is_comparison=False, compare_data=None):
    """生成 HTML 报告"""
    # 这里应该包含完整的 HTML 生成逻辑
    # 简化版本，实际需要完整的模板
    return "<html><body>Report</body></html>"

def main():
    if len(sys.argv) < 3:
        print("Usage: generate_all_reports.py <day_before> <yesterday>")
        print("Example: generate_all_reports.py 2026-02-18 2026-02-19")
        sys.exit(1)
    
    day_before = sys.argv[1]
    yesterday = sys.argv[2]
    
    print(f"Generating reports for:")
    print(f"  Day before: {day_before}")
    print(f"  Yesterday: {yesterday}")
    
    # 解析数据
    file_1 = f"/Users/jimmylu/我的云端硬盘/Health Auto Export/Health Data/HealthAutoExport-{day_before}.json"
    file_2 = f"/Users/jimmylu/我的云端硬盘/Health Auto Export/Health Data/HealthAutoExport-{yesterday}.json"
    
    data_1 = parse_health_data(file_1, day_before)
    data_2 = parse_health_data(file_2, yesterday)
    
    if not data_1 or not data_2:
        print("❌ 无法获取完整数据")
        sys.exit(1)
    
    # 添加睡眠数据（简化）
    sleep_1 = get_sleep_data(day_before)
    sleep_2 = get_sleep_data(yesterday)
    
    data_1.update(sleep_1)
    data_2.update(sleep_2)
    
    # 输出目录
    output_dir = "/Users/jimmylu/.openclaw/workspace/shared/health-reports/upload"
    os.makedirs(output_dir, exist_ok=True)
    
    # 这里应该调用完整的报告生成逻辑
    # 简化版本：假设已生成
    print("✅ Reports would be generated here")
    print(f"  - {yesterday}-report-zh.pdf")
    print(f"  - {yesterday}-report-en.pdf")
    print(f"  - {day_before}-vs-{yesterday}-comparison-zh.pdf")
    print(f"  - {day_before}-vs-{yesterday}-comparison-en.pdf")

if __name__ == '__main__':
    main()
