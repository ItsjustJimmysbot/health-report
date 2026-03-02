#!/usr/bin/env python3
"""提取Apple Health数据用于V5.7.1报告生成 - 支持多成员"""

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

# V5.7.1: 从 config.json 读取路径配置，支持多语言和多成员
def load_config():
    """加载配置文件 - 尝试多个可能的路径"""
    config_paths = [
        Path(__file__).parent.parent / "config.json",  # skill目录
        Path.home() / ".openclaw" / "workspace-health" / "config.json",  # 兼容旧路径
    ]
    
    for config_path in config_paths:
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
    return {}

def get_member_config(member_idx=0):
    """获取指定成员的配置，优先从config.json读取"""
    config = load_config()
    members = config.get('members', [])
    
    # 添加边界检查：如果索引超出范围则使用第一个成员
    if members and len(members) > member_idx:
        member = members[member_idx]
    elif members and len(members) > 0:
        member = members[0]  # fallback 到第一个成员
    else:
        # 默认配置
        return {
            'health_dir': '~/我的云端硬盘/Health Auto Export/Health Data',
            'workout_dir': '~/我的云端硬盘/Health Auto Export/Workout Data',
            'profile': {'name': '', 'age': None, 'gender': None, 'height_cm': None, 'weight_kg': None}
        }
    
    return {
        'health_dir': member.get('health_dir', '~/我的云端硬盘/Health Auto Export/Health Data'),
        'workout_dir': member.get('workout_dir', '~/我的云端硬盘/Health Auto Export/Workout Data'),
        'profile': {
            'name': member.get('name', ''),
            'age': member.get('age'),
            'gender': member.get('gender'),
            'height_cm': member.get('height_cm'),
            'weight_kg': member.get('weight_kg')
        }
    }

def get_all_members_count():
    """获取配置的成员总数"""
    config = load_config()
    return len(config.get('members', []))

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

def parse_sleep_data_v5(date_str, health_dir=None):
    """V5.0: 使用sleepStart字段，严格时间窗口筛选 - V5.7.0: 支持路径传入"""
    date = datetime.strptime(date_str, '%Y-%m-%d')
    next_date = date + timedelta(days=1)
    
    # V5.7.0: 使用传入的路径或全局默认路径
    if health_dir is None:
        health_dir = Path('~/我的云端硬盘/Health Auto Export/Health Data').expanduser()
    else:
        health_dir = Path(health_dir).expanduser()
    
    # 尝试读取次日文件（睡眠数据存储在次日）
    next_date_file = health_dir / f'HealthAutoExport-{next_date.strftime("%Y-%m-%d")}.json'
    
    if not next_date_file.exists():
        return []
    
    try:
        with open(next_date_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except:
        return []
    
    sleep_records = []
    
    # Try getting sleep_analysis from data directly
    sleep_data = data.get('data', {}).get('sleep_analysis')
    
    # If not there, try getting it from metrics array
    if not sleep_data:
        metrics_list = data.get('data', {}).get('metrics', [])
        metrics_dict = {m.get('name'): m for m in metrics_list if 'name' in m}
        sleep_data = metrics_dict.get('sleep_analysis', {})
    
    if not sleep_data:
        return []
    
    for record in sleep_data.get('data', []):
        # V5.0: 使用 sleepStart 字段（UTC时间戳，毫秒）
        start_ts = record.get('sleepStart')
        end_ts = record.get('sleepEnd')
        
        if not start_ts or not end_ts:
            continue
        
        # 转换为本地时间（UTC+8）
        start_dt = datetime.fromtimestamp(start_ts / 1000)
        end_dt = datetime.fromtimestamp(end_ts / 1000)
        
        # 严格筛选：只保留属于目标日期的睡眠（当天20:00到次日12:00）
        sleep_date = start_dt.strftime('%Y-%m-%d')
        sleep_hour = start_dt.hour
        
        # 归属逻辑：如果是当天20:00之后开始，属于当天
        # 如果是次日12:00之前结束，也属于当天
        belongs_to_date = False
        
        if sleep_date == date_str and sleep_hour >= 20:
            # 当天20:00之后开始
            belongs_to_date = True
        elif sleep_date == next_date.strftime('%Y-%m-%d') and sleep_hour < 12:
            # 次日12:00之前开始（跨夜睡眠）
            belongs_to_date = True
        
        if belongs_to_date:
            # 转换毫秒到小时
            duration_hours = (end_ts - start_ts) / 1000 / 3600
            
            sleep_records.append({
                'start': start_dt.strftime('%H:%M'),
                'end': end_dt.strftime('%H-%M'),
                'total': duration_hours,
                'deep': record.get('sleep_deep', 0) / 3600 if record.get('sleep_deep') else 0,
                'core': record.get('sleep_core', 0) / 3600 if record.get('sleep_core') else 0,
                'rem': record.get('sleep_rem', 0) / 3600 if record.get('sleep_rem') else 0,
                'awake': record.get('sleep_awake', 0) / 3600 if record.get('sleep_awake') else 0
            })
    
    return sleep_records

def extract_workout_data(date_str, workout_dir=None):
    """提取运动数据 - V5.7.0: 支持路径传入"""
    date = datetime.strptime(date_str, '%Y-%m-%d')
    
    # V5.7.0: 使用传入的路径或全局默认路径
    if workout_dir is None:
        workout_dir = Path('~/我的云端硬盘/Health Auto Export/Workout Data').expanduser()
    else:
        workout_dir = Path(workout_dir).expanduser()
    
    workout_file = workout_dir / f'{date_str}.json'
    
    if not workout_file.exists():
        return []
    
    try:
        with open(workout_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except:
        return []
    
    workouts = []
    workout_data = data.get('data', {}).get('workouts', {})
    
    if not workout_data:
        return []
    
    for workout in workout_data.get('data', []):
        # 解析开始时间
        start_ts = workout.get('start')
        if not start_ts:
            continue
        
        start_dt = datetime.fromtimestamp(start_ts)
        
        workouts.append({
            'type': workout.get('name', 'Unknown'),
            'start_time': start_dt.strftime('%H:%M'),
            'duration_min': workout.get('duration', 0) / 60,
            'energy_kcal': workout.get('energy', 0) / 4.184 if workout.get('energy') else 0,
            'avg_hr': workout.get('avg_hr'),
            'max_hr': workout.get('max_hr')
        })
    
    return workouts

def extract_daily_data(date_str, health_dir=None, workout_dir=None, user_profile=None):
    """提取完整的一天数据 - V5.7.0: 支持多成员路径传入"""
    date = datetime.strptime(date_str, '%Y-%m-%d')
    
    # V5.7.0: 使用传入的路径或全局默认路径
    if health_dir is None:
        health_dir = Path('~/我的云端硬盘/Health Auto Export/Health Data').expanduser()
    else:
        health_dir = Path(health_dir).expanduser()
    
    if workout_dir is None:
        workout_dir = Path('~/我的云端硬盘/Health Auto Export/Workout Data').expanduser()
    else:
        workout_dir = Path(workout_dir).expanduser()
    
    if user_profile is None:
        user_profile = {'name': '', 'age': None, 'gender': None, 'height_cm': None, 'weight_kg': None}
    
    # 读取当日数据文件
    data_file = health_dir / f'HealthAutoExport-{date_str}.json'
    
    if not data_file.exists():
        print(f"Warning: Data file not found: {data_file}", file=sys.stderr)
        return None
    
    try:
        with open(data_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error reading data file: {e}", file=sys.stderr)
        return None
    
    # 提取指标
    metrics_list = data.get('data', {}).get('metrics', [])
    metrics = {m['name']: m for m in metrics_list if 'name' in m}
    
    # HRV (心率变异性)
    hrv_raw, hrv_points = extract_metric_avg(metrics, 'heart_rate_variability')
    
    # 静息心率 - V5.5.0: 使用 resting_heart_rate 而不是 heart_rate
    resting_hr_raw, _ = extract_metric_avg(metrics, 'resting_heart_rate')
    
    # 步数
    steps = extract_metric_sum(metrics, 'step_count')
    
    # 距离 (km)
    distance = extract_metric_sum(metrics, 'walking_running_distance') / 1000
    
    # 活动能量 (kJ)
    active_energy = extract_metric_sum(metrics, 'active_energy')
    
    # 爬楼层数
    flights = extract_metric_sum(metrics, 'flights_climbed')
    
    # 站立时间 (分钟)
    stand_time = extract_metric_sum(metrics, 'apple_stand_time') / 60
    
    # 血氧 - V5.5.0: 修复百分比单位问题
    spo2_raw, _ = extract_metric_avg(metrics, 'blood_oxygen_saturation')
    if spo2_raw and spo2_raw <= 1.0:
        spo2 = spo2_raw * 100
    elif spo2_raw:
        spo2 = spo2_raw
    else:
        spo2 = None
    
    basal_energy = extract_metric_sum(metrics, 'basal_energy_burned')  # kJ
    respiratory, _ = extract_metric_avg(metrics, 'respiratory_rate')
    
    # 睡眠数据 - V5.5.0: 传递健康数据路径
    sleep_records = parse_sleep_data_v5(date_str, health_dir)
    sleep_total = sum(r['total'] for r in sleep_records) if sleep_records else 0
    sleep_deep = sum(r['deep'] for r in sleep_records) if sleep_records else 0
    sleep_core = sum(r['core'] for r in sleep_records) if sleep_records else 0
    sleep_rem = sum(r['rem'] for r in sleep_records) if sleep_records else 0
    sleep_awake = sum(r['awake'] for r in sleep_records) if sleep_records else 0
    
    # 运动数据
    workouts = extract_workout_data(date_str, workout_dir)
    
    # 活动能量合并 (kJ to kcal)
    workout_energy = sum(w.get('energy_kcal', 0) * 4.184 for w in workouts)  # back to kJ for calc
    total_energy_kJ = active_energy + workout_energy
    total_energy_kcal = total_energy_kJ / 4.184
    
    result = {
        'date': date_str,
        'data_source': 'Apple Health',
        'profile': user_profile,
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

def extract_all_members_data(date_str):
    """V5.7.0: 提取所有成员的数据"""
    config = load_config()
    members = config.get('members', [])
    
    if not members:
        print("Error: No members configured in config.json", file=sys.stderr)
        return None
    
    all_members_data = []
    
    for idx, _ in enumerate(members):
        member_config = get_member_config(idx)
        health_dir = member_config['health_dir']
        workout_dir = member_config['workout_dir']
        profile = member_config['profile']
        
        print(f"Extracting data for member {idx}: {profile.get('name', 'Unknown')}...", file=sys.stderr)
        
        data = extract_daily_data(date_str, health_dir, workout_dir, profile)
        if data:
            all_members_data.append(data)
        else:
            print(f"Warning: No data found for member {idx}", file=sys.stderr)
    
    if not all_members_data:
        return None
    
    # 返回包含所有成员数据的结构
    return {
        'date': date_str,
        'members_count': len(all_members_data),
        'members': all_members_data
    }

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python extract_data_v5.py YYYY-MM-DD [member_index|all]", file=sys.stderr)
        print("Examples:", file=sys.stderr)
        print("  python extract_data_v5.py 2026-03-01       # 提取第一个成员数据（默认）", file=sys.stderr)
        print("  python extract_data_v5.py 2026-03-01 1     # 提取第二个成员数据", file=sys.stderr)
        print("  python extract_data_v5.py 2026-03-01 2     # 提取第三个成员数据", file=sys.stderr)
        print("  python extract_data_v5.py 2026-03-01 all   # 提取所有成员数据（V5.7.0+）", file=sys.stderr)
        sys.exit(1)
    
    date_str = sys.argv[1]
    
    # 检查是否使用 'all' 参数
    if len(sys.argv) > 2 and sys.argv[2].lower() == 'all':
        # 提取所有成员数据
        data = extract_all_members_data(date_str)
    else:
        # 提取单个成员数据
        member_idx = int(sys.argv[2]) if len(sys.argv) > 2 else 0
        member_config = get_member_config(member_idx)
        
        data = extract_daily_data(
            date_str, 
            member_config['health_dir'], 
            member_config['workout_dir'], 
            member_config['profile']
        )
    
    if data:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        sys.exit(1)
