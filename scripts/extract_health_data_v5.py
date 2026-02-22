#!/usr/bin/env python3
"""
V5.0 Health Data Extraction Script
提取指定日期的健康数据
"""
import json
from pathlib import Path
from datetime import datetime, timedelta
import sys

def extract_metric_avg(metrics, name):
    """提取指标平均值"""
    metric = metrics.get(name, {})
    data = metric.get('data', [])
    if not data:
        return None, 0
    values = [d.get('qty', 0) for d in data if d.get('qty') is not None]
    return (sum(values) / len(values), len(values)) if values else (None, 0)

def extract_metric_sum(metrics, name):
    """提取指标总和"""
    metric = metrics.get(name, {})
    data = metric.get('data', [])
    values = [d.get('qty', 0) for d in data if d.get('qty') is not None]
    return (sum(values), len(values)) if values else (None, 0)

def extract_spo2(metrics):
    """提取血氧，智能判断单位"""
    spo2_raw, points = extract_metric_avg(metrics, 'blood_oxygen_saturation')
    if spo2_raw and spo2_raw > 1:
        spo2 = spo2_raw
    elif spo2_raw:
        spo2 = spo2_raw * 100
    else:
        spo2 = None
    return {'value': round(spo2, 1) if spo2 else None, 'points': points}

def parse_sleep_data(date_str, health_dir):
    """V5.0: 使用sleepStart字段，严格时间窗口筛选"""
    date = datetime.strptime(date_str, '%Y-%m-%d')
    next_date = (date + timedelta(days=1)).strftime('%Y-%m-%d')
    
    filepath = Path(health_dir) / f'HealthAutoExport-{next_date}.json'
    if not filepath.exists():
        return None
    
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    metrics = {m['name']: m for m in data.get('data', {}).get('metrics', [])}
    sleep_metric = metrics.get('sleep_analysis', {})
    
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
                    'total': (sleep.get('asleep', 0) or sleep.get('totalSleep', 0)) / 3600,  # 转换为小时
                    'deep': sleep.get('deep', 0) / 3600 if sleep.get('deep') else 0,
                    'core': sleep.get('core', 0) / 3600 if sleep.get('core') else 0,
                    'rem': sleep.get('rem', 0) / 3600 if sleep.get('rem') else 0,
                    'awake': sleep.get('awake', 0) / 3600 if sleep.get('awake') else 0,
                })
        except:
            continue
    
    return sleep_records

def extract_workout_data(date_str, workout_dir):
    """提取运动数据"""
    filepath = Path(workout_dir) / f'HealthAutoExport-{date_str}.json'
    if not filepath.exists():
        return []
    
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    workouts = []
    for w in data.get('data', {}).get('workouts', []):
        hr_field = w.get('heartRate', {})
        avg_hr = hr_field.get('avg', {}).get('qty') if isinstance(hr_field, dict) else None
        max_hr = hr_field.get('max', {}).get('qty') if isinstance(hr_field, dict) else None
        
        # V5.0: 如果为null，从heartRateData计算
        if avg_hr is None or max_hr is None:
            hr_data = w.get('heartRateData', [])
            if hr_data:
                avg_values = [hr.get('Avg', 0) for hr in hr_data if hr.get('Avg')]
                max_values = [hr.get('Max', 0) for hr in hr_data if hr.get('Max')]
                
                if avg_values and avg_hr is None:
                    avg_hr = sum(avg_values) / len(avg_values)
                if max_values and max_hr is None:
                    max_hr = max(max_values)
        
        # 计算能量（kJ转kcal）
        energy_kj = w.get('activeEnergyBurned', {}).get('qty', 0)
        energy_kcal = energy_kj / 4.184 if energy_kj else 0
        
        # 计算步数
        step_data = w.get('stepCount', [])
        steps = sum(d.get('qty', 0) for d in step_data) if step_data else 0
        
        workouts.append({
            'name': w.get('name', ''),
            'start': w.get('start', ''),
            'end': w.get('end', ''),
            'duration_min': w.get('duration', 0) / 60,
            'avg_hr': round(avg_hr) if avg_hr else None,
            'max_hr': round(max_hr) if max_hr else None,
            'energy_kcal': round(energy_kcal, 1),
            'steps': round(steps),
            'hr_data': w.get('heartRateData', [])
        })
    
    return workouts

def main():
    date_str = sys.argv[1] if len(sys.argv) > 1 else '2026-02-18'
    
    health_dir = Path.home() / '我的云端硬盘/Health Auto Export/Health Data'
    workout_dir = Path.home() / '我的云端硬盘/Health Auto Export/Workout Data'
    
    # 读取健康数据
    filepath = health_dir / f'HealthAutoExport-{date_str}.json'
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    metrics = {m['name']: m for m in data.get('data', {}).get('metrics', [])}
    
    # 提取各项指标
    hrv_val, hrv_points = extract_metric_avg(metrics, 'heart_rate_variability')
    resting_hr_val, resting_points = extract_metric_avg(metrics, 'resting_heart_rate')
    steps_val, steps_points = extract_metric_sum(metrics, 'step_count')
    active_energy_val, energy_points = extract_metric_sum(metrics, 'active_energy_burned')
    spo2_data = extract_spo2(metrics)
    
    # 转换单位
    active_energy_kcal = active_energy_val / 4.184 if active_energy_val else 0
    
    # 提取睡眠数据
    sleep_records = parse_sleep_data(date_str, health_dir)
    sleep_data = None
    if sleep_records:
        total_sleep = sum(r['total'] for r in sleep_records)
        sleep_data = {
            'total_hours': round(total_sleep, 2),
            'deep_hours': round(sum(r['deep'] for r in sleep_records), 2),
            'core_hours': round(sum(r['core'] for r in sleep_records), 2),
            'rem_hours': round(sum(r['rem'] for r in sleep_records), 2),
            'awake_hours': round(sum(r['awake'] for r in sleep_records), 2),
            'records': len(sleep_records)
        }
    
    # 提取运动数据
    workouts = extract_workout_data(date_str, workout_dir)
    
    result = {
        'date': date_str,
        'hrv': {
            'value': round(hrv_val, 1) if hrv_val else None,
            'points': hrv_points
        },
        'resting_hr': {
            'value': round(resting_hr_val) if resting_hr_val else None,
            'points': resting_points
        },
        'steps': {
            'value': round(steps_val) if steps_val else 0,
            'points': steps_points
        },
        'active_energy': {
            'value': round(active_energy_kcal, 1) if active_energy_kcal else 0,
            'kJ': round(active_energy_val, 1) if active_energy_val else 0,
            'points': energy_points
        },
        'spo2': spo2_data,
        'sleep': sleep_data,
        'workouts': workouts
    }
    
    print(json.dumps(result, indent=2, ensure_ascii=False))

if __name__ == '__main__':
    main()
