#!/usr/bin/env python3
"""提取Apple Health数据用于V5.0报告生成"""

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

HEALTH_DIR = Path.home() / "我的云端硬盘" / "Health Auto Export" / "Health Data"
WORKOUT_DIR = Path.home() / "我的云端硬盘" / "Health Auto Export" / "Workout Data"

def extract_metric_avg(metrics, metric_name):
    """提取平均值和数据点数"""
    metric = metrics.get(metric_name, {})
    data = metric.get('data', [])
    if not data:
        return None, 0
    values = [d.get('qty', 0) for d in data if d.get('qty') is not None]
    if not values:
        return None, 0
    return sum(values) / len(values), len(values)

def extract_metric_sum(metrics, metric_name):
    """提取总和"""
    metric = metrics.get(metric_name, {})
    data = metric.get('data', [])
    if not data:
        return 0
    return sum(d.get('qty', 0) for d in data if d.get('qty') is not None)

def parse_sleep_data_v5(date_str):
    """V5.0: 使用sleepStart字段，严格时间窗口筛选"""
    date = datetime.strptime(date_str, '%Y-%m-%d')
    next_date = (date + timedelta(days=1)).strftime('%Y-%m-%d')
    
    filepath = HEALTH_DIR / f'HealthAutoExport-{next_date}.json'
    if not filepath.exists():
        return None
    
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    metrics = {m['name']: m for m in data.get('data', {}).get('metrics', [])}
    sleep_metric = metrics.get('sleep_analysis', {})
    
    units = sleep_metric.get('units', '')
    if units != 'hr':
        print(f"⚠️ 警告: 睡眠数据单位是 {units}", file=sys.stderr)
    
    window_start = date.replace(hour=20, minute=0)
    window_end = (date + timedelta(days=1)).replace(hour=12, minute=0)
    
    sleep_records = []
    for sleep in sleep_metric.get('data', []):
        sleep_start_str = sleep.get('sleepStart', '')
        if not sleep_start_str:
            continue
        
        try:
            sleep_start = datetime.strptime(sleep_start_str[:19], '%Y-%m-%d %H:%M:%S')
            
            if window_start <= sleep_start <= window_end:
                sleep_records.append({
                    'total': sleep.get('asleep', 0) or sleep.get('totalSleep', 0),
                    'deep': sleep.get('deep', 0),
                    'core': sleep.get('core', 0),
                    'rem': sleep.get('rem', 0),
                    'awake': sleep.get('awake', 0),
                })
        except Exception as e:
            continue
    
    return sleep_records

def extract_workout_data(date_str):
    """提取运动数据 - V5.1.1-fix: 从当日文件读取"""
    date = datetime.strptime(date_str, '%Y-%m-%d')
    
    # V5.1.1-fix: 运动数据从当日文件读取
    # 先检查workout目录
    workout_file = WORKOUT_DIR / f'HealthAutoExport-{date_str}.json'
    if not workout_file.exists():
        workout_file = HEALTH_DIR / f'HealthAutoExport-{date_str}.json'
    
    if not workout_file.exists():
        return []
    
    with open(workout_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    workouts = data.get('data', {}).get('workouts', [])
    result = []
    
    for w in workouts:
        # 提取心率数据
        hr_field = w.get('heartRate', {})
        avg_hr = None
        max_hr = None
        
        if isinstance(hr_field, dict):
            avg_hr = hr_field.get('avg', {}).get('qty') if hr_field.get('avg') else None
            max_hr = hr_field.get('max', {}).get('qty') if hr_field.get('max') else None
        
        # 如果为null，从heartRateData计算
        if avg_hr is None or max_hr is None:
            hr_data = w.get('heartRateData', [])
            if hr_data:
                avg_values = [hr.get('Avg', 0) for hr in hr_data if hr.get('Avg')]
                max_values = [hr.get('Max', 0) for hr in hr_data if hr.get('Max')]
                
                if avg_values and avg_hr is None:
                    avg_hr = sum(avg_values) / len(avg_values)
                if max_values and max_hr is None:
                    max_hr = max(max_values)
        
        result.append({
            'name': w.get('name', '未知运动'),
            'duration_min': w.get('duration', 0) / 60 if w.get('duration') else 0,
            'avg_hr': round(avg_hr) if avg_hr else None,
            'max_hr': round(max_hr) if max_hr else None,
            'energy_kcal': (w.get('activeEnergyBurned', {}).get('qty', 0) if isinstance(w.get('activeEnergyBurned'), dict) else w.get('activeEnergyBurned', 0)) / 4.184,
            'hr_data': w.get('heartRateData', [])
        })
    
    return result

def extract_daily_data(date_str):
    """提取完整的一天数据"""
    date = datetime.strptime(date_str, '%Y-%m-%d')
    next_date = (date + timedelta(days=1)).strftime('%Y-%m-%d')
    
    # V5.1.1-fix: 活动数据从当日文件读取，睡眠数据从次日文件读取
    # 当日文件（用于活动数据）
    today_filepath = HEALTH_DIR / f'HealthAutoExport-{date_str}.json'
    # 次日文件（用于睡眠数据）
    next_filepath = HEALTH_DIR / f'HealthAutoExport-{next_date}.json'
    
    # 读取当日文件（活动数据）
    if today_filepath.exists():
        with open(today_filepath, 'r', encoding='utf-8') as f:
            today_data = json.load(f)
        today_metrics = {m['name']: m for m in today_data.get('data', {}).get('metrics', [])}
    else:
        print(f"⚠️ 当日文件不存在: {today_filepath}", file=sys.stderr)
        today_metrics = {}
    
    # 读取次日文件（睡眠数据）
    if next_filepath.exists():
        with open(next_filepath, 'r', encoding='utf-8') as f:
            next_data = json.load(f)
        next_metrics = {m['name']: m for m in next_data.get('data', {}).get('metrics', [])}
    else:
        print(f"⚠️ 次日文件不存在: {next_filepath}", file=sys.stderr)
        next_metrics = {}
    
    # 提取日间活动指标（从当日文件）
    hrv_raw, hrv_points = extract_metric_avg(today_metrics, 'heart_rate_variability')
    resting_hr_raw, _ = extract_metric_avg(today_metrics, 'resting_heart_rate')
    steps = extract_metric_sum(today_metrics, 'step_count')
    distance = extract_metric_sum(today_metrics, 'walking_running_distance')  # km
    active_energy = extract_metric_sum(today_metrics, 'active_energy_burned')  # kJ
    flights = extract_metric_sum(today_metrics, 'flights_climbed')  # V5.1.1-fix: 使用累加而非平均
    stand_time = extract_metric_sum(today_metrics, 'apple_stand_time')  # min
    
    # 血氧 - 智能单位判断（从当日文件）
    spo2_raw, _ = extract_metric_avg(today_metrics, 'blood_oxygen_saturation')
    if spo2_raw and spo2_raw > 1:
        spo2 = spo2_raw
    elif spo2_raw:
        spo2 = spo2_raw * 100
    else:
        spo2 = None
    
    basal_energy = extract_metric_sum(today_metrics, 'basal_energy_burned')  # kJ
    respiratory, _ = extract_metric_avg(today_metrics, 'respiratory_rate')
    
    # 睡眠数据
    sleep_records = parse_sleep_data_v5(date_str)
    sleep_total = sum(r['total'] for r in sleep_records) if sleep_records else 0
    sleep_deep = sum(r['deep'] for r in sleep_records) if sleep_records else 0
    sleep_core = sum(r['core'] for r in sleep_records) if sleep_records else 0
    sleep_rem = sum(r['rem'] for r in sleep_records) if sleep_records else 0
    sleep_awake = sum(r['awake'] for r in sleep_records) if sleep_records else 0
    
    # 运动数据
    workouts = extract_workout_data(date_str)
    
    # 活动能量合并 (kJ to kcal)
    workout_energy = sum(w.get('energy_kcal', 0) * 4.184 for w in workouts)  # back to kJ for calc
    total_energy_kJ = active_energy + workout_energy
    total_energy_kcal = total_energy_kJ / 4.184
    
    result = {
        'date': date_str,
        'data_source': 'Apple Health',
        'hrv': {
            'value': round(hrv_raw, 1) if hrv_raw else None,
            'points': hrv_points
        },
        'resting_hr': {
            'value': round(resting_hr_raw) if resting_hr_raw else None
        },
        'steps': int(steps),
        'distance_km': round(distance, 2),
        'active_energy_kcal': round(total_energy_kcal, 1),
        'flights_climbed': round(flights, 1) if flights else 0,
        'stand_time_min': int(stand_time),
        'spo2': round(spo2, 1) if spo2 else None,
        'basal_energy_kcal': round(basal_energy / 4.184, 1) if basal_energy else 0,
        'respiratory_rate': round(respiratory, 1) if respiratory else None,
        'sleep': {
            'total_hours': round(sleep_total, 2),
            'deep_hours': round(sleep_deep, 2) if sleep_deep else 0,
            'core_hours': round(sleep_core, 2) if sleep_core else 0,
            'rem_hours': round(sleep_rem, 2) if sleep_rem else 0,
            'awake_hours': round(sleep_awake, 2) if sleep_awake else 0,
            'records': len(sleep_records) if sleep_records else 0
        },
        'workouts': workouts
    }
    
    return result

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python extract_data_v5.py YYYY-MM-DD", file=sys.stderr)
        sys.exit(1)
    
    date_str = sys.argv[1]
    data = extract_daily_data(date_str)
    
    if data:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        sys.exit(1)
