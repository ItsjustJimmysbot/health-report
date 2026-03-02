#!/usr/bin/env python3
"""提取Apple Health数据用于V5.8.1报告生成 - 支持多成员"""

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

MAX_MEMBERS = 3

# V5.8.1: 使用共用工具函数
sys.path.insert(0, str(Path(__file__).parent))
from utils import load_config

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

def get_sleep_config():
    """获取睡眠配置"""
    config = load_config()
    sleep_config = config.get('sleep_config', {})
    
    return {
        'read_mode': sleep_config.get('read_mode', 'next_day'),  # 'next_day' 或 'same_day'
        'start_hour': sleep_config.get('start_hour', 20),
        'end_hour': sleep_config.get('end_hour', 12)
    }


def get_all_members_count():
    """获取配置的成员总数（最多 MAX_MEMBERS）"""
    config = load_config()
    members = config.get('members', [])
    return min(len(members), MAX_MEMBERS)

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


def extract_workout_data(date_str, workout_dir=None, health_dir=None):
    """
    提取运动数据 - V5.8.0: 
    1. 支持双文件名: YYYY-MM-DD.json 和 HealthAutoExport-YYYY-MM-DD.json
    2. 兼容 workout 结构: data.workouts.data 和 data.workouts
    """
    date = datetime.strptime(date_str, '%Y-%m-%d')
    
    # V5.8.0: 使用传入的路径或全局默认路径
    if workout_dir is None:
        workout_dir = Path('~/我的云端硬盘/Health Auto Export/Workout Data').expanduser()
    else:
        workout_dir = Path(workout_dir).expanduser()
    
    if health_dir is None:
        health_dir = Path('~/我的云端硬盘/Health Auto Export/Health Data').expanduser()
    else:
        health_dir = Path(health_dir).expanduser()
    
    # 尝试两种文件名（按优先级）
    workout_paths = [
        workout_dir / f'{date_str}.json',
        workout_dir / f'HealthAutoExport-{date_str}.json',
        health_dir / f'HealthAutoExport-{date_str}.json',
    ]
    
    workout_file = None
    for p in workout_paths:
        if p.exists():
            workout_file = p
            break
    
    if not workout_file:
        return []
    
    try:
        with open(workout_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"⚠️  读取运动文件失败: {workout_file} - {e}", file=sys.stderr)
        return []
    
    # V5.8.0: 兼容两种 workout 结构
    workouts = []
    
    # 尝试结构1: data.workouts.data
    workout_data = data.get('data', {}).get('workouts', {})
    if workout_data and 'data' in workout_data:
        workout_list = workout_data.get('data', [])
    else:
        # 尝试结构2: data.workouts (直接是数组)
        workout_list = data.get('workouts', [])
        if not workout_list and 'data' in data:
            workout_list = data['data'].get('workouts', [])
    
    for workout in workout_list:
        # 解析开始时间
        start_ts = workout.get('start')
        if not start_ts:
            continue
        
        try:
            if isinstance(start_ts, (int, float)):
                start_dt = datetime.fromtimestamp(start_ts)
            else:
                # 字符串时间戳
                start_dt = datetime.fromtimestamp(float(start_ts))
        except (ValueError, TypeError):
            continue
        
        workouts.append({
            'type': workout.get('name', 'Unknown'),
            'start_time': start_dt.strftime('%H:%M'),
            'duration_min': workout.get('duration', 0) / 60 if workout.get('duration') else 0,
            'energy_kcal': workout.get('energy', 0) / 4.184 if workout.get('energy') else 0,
            'avg_hr': workout.get('avg_hr'),
            'max_hr': workout.get('max_hr')
        })
    
    return workouts

def extract_daily_data(date_str, health_dir=None, workout_dir=None, user_profile=None, sleep_config=None):
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
        from utils import DataError, handle_error
        handle_error(
            DataError(f"数据文件不存在: {data_file}"),
            f"提取成员数据"
        )
        return None
    
    try:
        with open(data_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        from utils import DataError, handle_error
        handle_error(
            DataError(f"JSON解析失败: {e}"),
            f"读取 {data_file}"
        )
        return None
    except Exception as e:
        from utils import DataError, handle_error
        handle_error(
            DataError(f"读取数据文件失败: {e}"),
            f"读取 {data_file}"
        )
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
    
    # 距离 (km) - 数据单位已经是km，不需要再转换
    distance = extract_metric_sum(metrics, 'walking_running_distance')
    
    # 活动能量 (kJ)
    active_energy = extract_metric_sum(metrics, 'active_energy')
    
    # 爬楼层数
    flights = extract_metric_sum(metrics, 'flights_climbed')
    
    # 站立时间 (分钟) - 保持分钟单位，不除以60
    stand_time = extract_metric_sum(metrics, 'apple_stand_time')
    
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
    
    # 睡眠数据 - V5.8.1: 使用统一解析函数
    from utils import parse_sleep_data_unified
    sleep_result = parse_sleep_data_unified(
        date_str, health_dir, 
        read_mode=sleep_config.get('read_mode', 'next_day'),
        start_hour=sleep_config.get('start_hour', 20),
        end_hour=sleep_config.get('end_hour', 12)
    )
    
    sleep_records = sleep_result['records']
    sleep_total = sleep_result['total_hours']
    sleep_deep = sleep_result['deep_hours']
    sleep_core = sleep_result['core_hours']
    sleep_rem = sleep_result['rem_hours']
    sleep_awake = sleep_result['awake_hours']
    
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
    sleep_config = get_sleep_config()
    
    # 限制最多 MAX_MEMBERS 位成员
    if len(members) > MAX_MEMBERS:
        print(f"⚠️ 成员数 {len(members)} 超过上限 {MAX_MEMBERS}，仅处理前 {MAX_MEMBERS} 位", file=sys.stderr)
        members = members[:MAX_MEMBERS]
    
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
        
        data = extract_daily_data(date_str, health_dir, workout_dir, profile, sleep_config)
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
        sleep_config = get_sleep_config()
        
        data = extract_daily_data(
            date_str, 
            member_config['health_dir'], 
            member_config['workout_dir'], 
            member_config['profile'],
            sleep_config
        )
    
    if data:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        sys.exit(1)
