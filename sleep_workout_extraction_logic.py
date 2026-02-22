#!/usr/bin/env python3
"""
正确的睡眠数据提取逻辑 - 标准化流程
适用于 Apple Health Auto Export 的睡眠数据结构
"""
import json
from datetime import datetime, timedelta

def extract_sleep_data_correct(date_str, data_dir):
    """
    提取指定日期的睡眠数据（时间窗口：当日20:00 - 次日12:00）
    
    Apple Health 睡眠数据结构：
    {
      "name": "sleep_analysis",
      "units": "hr",
      "data": [{
        "date": "2026-02-19 00:00:00 +0800",
        "asleep": 2.8169228286213346,      # 总睡眠时长（小时）
        "totalSleep": 2.8169228286213346,  # 同上
        "sleepStart": "2026-02-19 06:28:03 +0800",  # 入睡时间
        "sleepEnd": "2026-02-19 09:17:04 +0800",    # 醒来时间
        "deep": 0,     # 深睡时长（小时）
        "core": 0,     # 核心睡眠时长（小时）
        "rem": 0,      # REM睡眠时长（小时）
        "awake": 0,    # 清醒时长（小时）
        "inBed": 0,
        "inBedStart": "...",
        "inBedEnd": "...",
        "source": "Siegfried's Apple Watch"
      }]
    }
    """
    
    target_date = datetime.strptime(date_str, "%Y-%m-%d")
    window_start = target_date.replace(hour=20, minute=0)  # 当日20:00
    window_end = (target_date + timedelta(days=1)).replace(hour=12, minute=0)  # 次日12:00
    
    # 需要检查的文件：当日文件 + 次日文件
    files_to_check = [
        f"{data_dir}/HealthAutoExport-{date_str}.json",
        f"{data_dir}/HealthAutoExport-{(target_date + timedelta(days=1)).strftime('%Y-%m-%d')}.json"
    ]
    
    sleep_sessions = []
    
    for filepath in files_to_check:
        if not os.path.exists(filepath):
            continue
            
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        metrics = data.get('data', {}).get('metrics', [])
        
        for metric in metrics:
            if metric.get('name') == 'sleep_analysis':
                for sleep in metric.get('data', []):
                    sleep_start_str = sleep.get('sleepStart')
                    sleep_end_str = sleep.get('sleepEnd')
                    
                    if not sleep_start_str or not sleep_end_str:
                        continue
                    
                    try:
                        sleep_start = datetime.strptime(sleep_start_str[:19], "%Y-%m-%d %H:%M:%S")
                        sleep_end = datetime.strptime(sleep_end_str[:19], "%Y-%m-%d %H:%M:%S")
                    except:
                        continue
                    
                    # 检查是否在时间窗口内（入睡时间在20:00后，醒来时间在次日12:00前）
                    if sleep_start >= window_start and sleep_end <= window_end:
                        sleep_sessions.append({
                            'start': sleep_start,
                            'end': sleep_end,
                            'total_hours': sleep.get('totalSleep') or sleep.get('asleep') or 0,
                            'deep_hours': sleep.get('deep', 0),
                            'core_hours': sleep.get('core', 0),
                            'rem_hours': sleep.get('rem', 0),
                            'awake_hours': sleep.get('awake', 0),
                            'in_bed_start': sleep.get('inBedStart'),
                            'in_bed_end': sleep.get('inBedEnd'),
                            'source': sleep.get('source', 'Apple Watch'),
                            'source_file': filepath.split('/')[-1]
                        })
    
    if not sleep_sessions:
        return None
    
    # 合并睡眠时段
    total_sleep = sum(s['total_hours'] for s in sleep_sessions)
    total_deep = sum(s['deep_hours'] for s in sleep_sessions)
    total_core = sum(s['core_hours'] for s in sleep_sessions)
    total_rem = sum(s['rem_hours'] for s in sleep_sessions)
    total_awake = sum(s['awake_hours'] for s in sleep_sessions)
    
    bed_time = min(s['start'] for s in sleep_sessions)
    wake_time = max(s['end'] for s in sleep_sessions)
    
    return {
        'total_hours': total_sleep,
        'deep_hours': total_deep,
        'core_hours': total_core,
        'rem_hours': total_rem,
        'awake_hours': total_awake,
        'bed_time': bed_time,
        'wake_time': wake_time,
        'sessions': sleep_sessions,
        'num_sessions': len(sleep_sessions)
    }

def extract_workout_data(date_str, workout_dir):
    """
    提取锻炼数据
    
    Workout 数据结构：
    {
      "name": "楼梯",
      "start": "2026-02-18 20:25:19 +0800",
      "duration": 2001.5222681760788,  # 秒
      "energy": null,  # 千卡（可能为null）
      "heart_rate_avg": null,  # 可能为null
      "heart_rate_max": null,  # 可能为null
      "distance": null  # 米
    }
    """
    filepath = f"{workout_dir}/HealthAutoExport-{date_str}.json"
    
    if not os.path.exists(filepath):
        return []
    
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    workouts = data.get('data', {}).get('workouts', [])
    
    result = []
    for w in workouts:
        result.append({
            'name': w.get('name', '未知运动'),
            'start': w.get('start', ''),
            'duration_min': (w.get('duration', 0) or 0) / 60,
            'energy_kcal': w.get('energy'),  # 可能为null
            'avg_hr': w.get('heart_rate_avg'),  # 可能为null
            'max_hr': w.get('heart_rate_max'),  # 可能为null
            'distance_m': w.get('distance')  # 可能为null
        })
    
    return result

import os

if __name__ == '__main__':
    # 测试提取2026-02-18的数据
    DATA_DIR = "/Users/jimmylu/我的云端硬盘/Health Auto Export/Health Data"
    WORKOUT_DIR = "/Users/jimmylu/我的云端硬盘/Health Auto Export/Workout Data"
    
    print("=" * 60)
    print("2026-02-18 睡眠数据提取测试")
    print("=" * 60)
    
    sleep = extract_sleep_data_correct("2026-02-18", DATA_DIR)
    if sleep:
        print(f"✅ 找到睡眠数据:")
        print(f"   入睡时间: {sleep['bed_time']}")
        print(f"   醒来时间: {sleep['wake_time']}")
        print(f"   总睡眠: {sleep['total_hours']:.2f}小时")
        print(f"   睡眠段数: {sleep['num_sessions']}")
        if sleep['deep_hours'] > 0 or sleep['core_hours'] > 0 or sleep['rem_hours'] > 0:
            print(f"   睡眠结构:")
            print(f"     - 深睡: {sleep['deep_hours']:.2f}h ({sleep['deep_hours']/sleep['total_hours']*100:.1f}%)")
            print(f"     - 核心: {sleep['core_hours']:.2f}h ({sleep['core_hours']/sleep['total_hours']*100:.1f}%)")
            print(f"     - REM: {sleep['rem_hours']:.2f}h ({sleep['rem_hours']/sleep['total_hours']*100:.1f}%)")
            print(f"     - 清醒: {sleep['awake_hours']:.2f}h ({sleep['awake_hours']/sleep['total_hours']*100:.1f}%)")
        else:
            print(f"   ⚠️ 睡眠结构未分类（显示为0）")
    else:
        print("❌ 未找到睡眠数据")
    
    print("\n" + "=" * 60)
    print("2026-02-18 锻炼数据提取测试")
    print("=" * 60)
    
    workouts = extract_workout_data("2026-02-18", WORKOUT_DIR)
    if workouts:
        for i, w in enumerate(workouts):
            print(f"\n锻炼 {i+1}: {w['name']}")
            print(f"   开始: {w['start']}")
            print(f"   时长: {w['duration_min']:.1f}分钟")
            if w['energy_kcal']:
                print(f"   能量: {w['energy_kcal']:.0f}千卡")
            else:
                print(f"   能量: 未记录")
            if w['avg_hr']:
                print(f"   平均心率: {w['avg_hr']:.0f}bpm")
                print(f"   最高心率: {w['max_hr']:.0f}bpm")
            else:
                print(f"   心率: 未记录")
    else:
        print("❌ 未找到锻炼数据")
