#!/usr/bin/env python3
"""提取Apple Health数据用于V6.0.3报告生成 - 支持多成员"""

import json
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict


# V5.8.1: 使用共用工具函数
sys.path.insert(0, str(Path(__file__).parent))
from utils import load_config, MAX_MEMBERS, KJ_TO_KCAL, ConfigError, handle_error, infer_duration_unit, get_workout_field
from health_score import calculate_zone_times_from_workouts

def _sanitize_path(path_str, default_path):
    """路径安全验证：防止路径遍历攻击"""
    from pathlib import Path

    if not path_str:
        return Path(default_path).expanduser()

    # 展开用户目录
    path = Path(path_str).expanduser()

    # 解析绝对路径
    try:
        path = path.resolve()
    except (OSError, RuntimeError):
        # 如果解析失败，使用默认路径
        print(f"⚠️ 警告: 路径解析失败，使用默认路径: {default_path}", file=sys.stderr)
        return Path(default_path).expanduser()

    # 检查是否为绝对路径
    if not path.is_absolute():
        print(f"⚠️ 警告: 路径必须是绝对路径，使用默认路径: {default_path}", file=sys.stderr)
        return Path(default_path).expanduser()

    # 检查路径是否包含 .. (路径遍历)
    # resolve() 已经处理了 ..，但如果展开后仍在系统根目录外则有问题
    # 检查路径是否在合理的根目录下 ( home 目录或 /opt /var 等)
    home = Path.home().resolve()

    # 允许的根目录列表
    allowed_roots = [
        home,
        Path('/opt'),
        Path('/var'),
        Path('/tmp'),
        Path('/Users'),  # macOS
        Path('/home'),   # Linux
    ]

    # 检查是否在允许的根目录下
    is_allowed = any(
        str(path).startswith(str(root)) for root in allowed_roots if root.exists()
    )

    if not is_allowed:
        print(f"⚠️ 警告: 路径 {path} 不在允许的目录范围内，使用默认路径", file=sys.stderr)
        return Path(default_path).expanduser()

    return path


def get_member_config(member_idx=0):
    """获取指定成员的配置，优先从config.json读取"""
    config = load_config()
    members = config.get('members', [])

    # 检查成员列表是否为空
    if not members:
        handle_error(
            ConfigError("config.json 中未配置任何成员，请至少配置 1 位成员"),
            "读取成员配置",
            exit_on_fatal=False
        )
        return None

    # 检查成员数量限制（最多 MAX_MEMBERS 位）
    if len(members) > MAX_MEMBERS:
        print(f"⚠️ 警告: 成员数 {len(members)} 超过上限 {MAX_MEMBERS}，仅处理前 {MAX_MEMBERS} 位", file=sys.stderr)
        members = members[:MAX_MEMBERS]

    # 检查索引是否越界（同时防止负索引误取最后一个成员）
    if member_idx < 0 or member_idx >= len(members):
        print(f"⚠️ 警告: 成员索引 {member_idx} 超出范围，回退到第一个成员(0)", file=sys.stderr)
        member_idx = 0

    member = members[member_idx]

    # 安全处理路径
    health_dir = _sanitize_path(
        member.get('health_dir'),
        '~/Health Auto Export/Health Data'
    )
    workout_dir = _sanitize_path(
        member.get('workout_dir'),
        '~/Health Auto Export/Workout Data'
    )

    return {
        'health_dir': health_dir,
        'workout_dir': workout_dir,
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
    提取运动数据 - V5.8.1:
    1. 支持双文件名: YYYY-MM-DD.json 和 HealthAutoExport-YYYY-MM-DD.json
    2. 兼容 workout 结构: data.workouts.data 和 data.workouts
    """
    from datetime import datetime
    from pathlib import Path
    import re

    date = datetime.strptime(date_str, '%Y-%m-%d')

    # 使用传入的路径或全局默认路径
    if workout_dir is None:
        workout_dir = Path('~/Health Auto Export/Workout Data').expanduser()
    else:
        workout_dir = Path(workout_dir).expanduser()

    if health_dir is None:
        health_dir = Path('~/Health Auto Export/Health Data').expanduser()
    else:
        health_dir = Path(health_dir).expanduser()

    # 尝试多种文件路径
    workout_paths = [
        workout_dir / f'{date_str}.json',
        workout_dir / f'HealthAutoExport-{date_str}.json',
        health_dir / f'HealthAutoExport-{date_str}.json',
        health_dir / f'{date_str}.json',
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

    # 兼容多种 workout 结构
    workouts = []

    # 尝试结构1: data.workouts.data (字典嵌套)
    workout_data = data.get('data', {}).get('workouts', {})
    if isinstance(workout_data, dict) and 'data' in workout_data:
        workout_list = workout_data.get('data', [])
    elif isinstance(workout_data, list):
        # 结构: data.workouts = []
        workout_list = workout_data
    else:
        # 尝试结构2: data.workouts (直接是数组)
        workout_list = data.get('workouts', [])
        if not workout_list and 'data' in data:
            workout_list = data['data'].get('workouts', [])

    for workout in workout_list:
        try:
            # 解析开始时间（支持多种格式）
            start_ts = workout.get('start') or workout.get('startDate')
            if not start_ts:
                continue

            start_dt = None
            try:
                if isinstance(start_ts, (int, float)):
                    ts = float(start_ts)
                    if ts > 1e12:  # 毫秒时间戳
                        ts /= 1000.0
                    start_dt = datetime.fromtimestamp(ts)
                else:
                    # 尝试字符串时间戳
                    try:
                        ts = float(start_ts)
                        if ts > 1e12:  # 毫秒时间戳字符串
                            ts /= 1000.0
                        start_dt = datetime.fromtimestamp(ts)
                    except (ValueError, TypeError):
                        # 尝试 ISO 格式（支持 +0800 时区）
                        iso_str = str(start_ts).replace('Z', '+00:00')
                        # 处理 +0800 格式
                        match = re.match(r'(.+?)\s+([+-]\d{4})$', iso_str)
                        if match:
                            dt_str, tz_str = match.groups()
                            tz_formatted = tz_str[:3] + ':' + tz_str[3:]
                            iso_str = dt_str + tz_formatted
                        start_dt = datetime.fromisoformat(iso_str)
            except (ValueError, TypeError, OSError, OverflowError) as e:
                print(f"⚠️  时间解析失败: {start_ts} - {e}", file=sys.stderr)
                continue

            # V6.0.0: 仅保留目标日期的运动记录，避免跨天数据混入
            if start_dt.strftime('%Y-%m-%d') != date_str:
                continue

            # 计算 duration_min（使用智能单位推断）
            dur_raw = workout.get('duration', 0) or 0
            if dur_raw:
                duration_min, _ = infer_duration_unit(dur_raw, workout)
            else:
                duration_min = 0

            # 获取能量（兼容多种字段名）
            energy_kj = get_workout_field(workout, ['energy', 'activeEnergyBurned', 'totalEnergyBurned', 'activeEnergy'], 0)
            energy_kcal = energy_kj / 4.184 if energy_kj else 0

            # 获取心率（兼容多种字段名）
            # 首先尝试直接获取 avg_hr
            avg_hr = get_workout_field(workout, ['avg_hr', 'avgHeartRate', 'averageHeartRate'])

            # 如果失败，尝试从 heartRate 嵌套结构获取
            if avg_hr is None:
                hr_data = workout.get('heartRate')
                if hr_data and isinstance(hr_data, dict) and 'avg' in hr_data:
                    avg_hr = get_workout_field(hr_data, ['avg'], None)

            # 获取最大心率
            max_hr = get_workout_field(workout, ['max_hr', 'maxHeartRate', 'maximumHeartRate'])
            if max_hr is None:
                hr_data = workout.get('heartRate')
                if hr_data and isinstance(hr_data, dict) and 'max' in hr_data:
                    max_hr = get_workout_field(hr_data, ['max'], None)

            workouts.append({
                'type': workout.get('name', 'Unknown'),
                'name': workout.get('name', 'Unknown'),
                'start_time': start_dt.strftime('%H:%M'),
                'start': start_dt.strftime('%Y-%m-%d %H:%M'),
                'duration_min': duration_min,
                'energy_kcal': energy_kcal,
                'avg_hr': avg_hr,
                'max_hr': max_hr,
                'hr_timeline': workout.get('heartRateData', []) or workout.get('hrData', [])
            })
        except Exception as e:
            print(f"⚠️  解析单个 workout 失败: {e}", file=sys.stderr)
            continue

    # V6.0.3: 添加调试信息
    workout_file_name = workout_file.name if workout_file else "未找到"
    if workout_file and not workouts:
        print(f"   ℹ️ 运动文件存在但无有效记录: {workout_file_name}", file=sys.stderr)
        print(f"      提示: 检查文件是否包含 workouts 数组或 data.workouts 结构", file=sys.stderr)
    elif workouts:
        print(f"   ✓ 找到 {len(workouts)} 条运动记录", file=sys.stderr)
    else:
        print(f"   ℹ️ 未找到运动文件: 尝试路径包括 {date_str}.json 和 HealthAutoExport-{date_str}.json", file=sys.stderr)

    return workouts

def extract_daily_data(date_str, health_dir=None, workout_dir=None, user_profile=None, sleep_config=None):
    """提取完整的一天数据 - V5.8.1: 支持多成员路径传入"""
    date = datetime.strptime(date_str, '%Y-%m-%d')

    # V6.0.3: 使用传入的路径或全局默认路径
    if health_dir is None:
        health_dir = Path('~/Health Auto Export/Health Data').expanduser()
    else:
        health_dir = Path(health_dir).expanduser()

    if workout_dir is None:
        workout_dir = Path('~/Health Auto Export/Workout Data').expanduser()
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
            f"提取成员数据",
            exit_on_fatal=False
        )
        return None

    try:
        with open(data_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        from utils import DataError, handle_error
        handle_error(
            DataError(f"JSON解析失败: {e}"),
            f"读取 {data_file}",
            exit_on_fatal=False
        )
        return None
    except Exception as e:
        from utils import DataError, handle_error
        handle_error(
            DataError(f"读取数据文件失败: {e}"),
            f"读取 {data_file}",
            exit_on_fatal=False
        )
        return None

    # 提取指标
    metrics_list = data.get('data', {}).get('metrics', [])
    metrics = {m['name']: m for m in metrics_list if 'name' in m}

    # HRV (心率变异性)
    hrv_raw, hrv_measurement_count = extract_metric_avg(metrics, 'heart_rate_variability')

    # V5.8.1: 使用 resting_heart_rate 而不是 heart_rate
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

    # V5.8.1: 修复血氧百分比单位问题
    spo2_raw, _ = extract_metric_avg(metrics, 'blood_oxygen_saturation')
    if spo2_raw and spo2_raw <= 1.0:
        spo2 = spo2_raw * 100
    elif spo2_raw:
        spo2 = spo2_raw
    else:
        spo2 = None

    basal_energy = extract_metric_sum(metrics, 'basal_energy_burned')  # kJ
    respiratory, _ = extract_metric_avg(metrics, 'respiratory_rate')

    # ===== 高级指标提取（V6.0.0 新增）=====
    # 心肺能力
    vo2_max, _ = extract_metric_avg(metrics, 'vo2_max')
    physical_effort, _ = extract_metric_avg(metrics, 'physical_effort')

    # 步行步态
    walking_speed, _ = extract_metric_avg(metrics, 'walking_speed')
    walking_step_length, _ = extract_metric_avg(metrics, 'walking_step_length')
    walking_heart_rate_average, _ = extract_metric_avg(metrics, 'walking_heart_rate_average')
    walking_asymmetry_percentage, _ = extract_metric_avg(metrics, 'walking_asymmetry_percentage')
    walking_double_support_percentage, _ = extract_metric_avg(metrics, 'walking_double_support_percentage')

    # 高级跑步
    running_speed, _ = extract_metric_avg(metrics, 'running_speed')
    running_power, _ = extract_metric_avg(metrics, 'running_power')
    running_stride_length, _ = extract_metric_avg(metrics, 'running_stride_length')
    running_ground_contact_time, _ = extract_metric_avg(metrics, 'running_ground_contact_time')
    running_vertical_oscillation, _ = extract_metric_avg(metrics, 'running_vertical_oscillation')

    # 活动与机能
    apple_exercise_time = extract_metric_sum(metrics, 'apple_exercise_time')
    apple_stand_hour = extract_metric_sum(metrics, 'apple_stand_hour')
    stair_speed_up, _ = extract_metric_avg(metrics, 'stair_speed_up')

    # 睡眠相关
    breathing_disturbances, _ = extract_metric_avg(metrics, 'breathing_disturbances')

    # 环境暴露
    headphone_audio_exposure, _ = extract_metric_avg(metrics, 'headphone_audio_exposure')
    environmental_audio_exposure, _ = extract_metric_avg(metrics, 'environmental_audio_exposure')

    # 平均心率
    heart_rate_avg, _ = extract_metric_avg(metrics, 'heart_rate')
    running_vert_osc, _ = extract_metric_avg(metrics, 'running_vertical_oscillation')

    # V5.8.1: 睡眠数据使用统一解析函数
    from utils import parse_sleep_data_unified
    if sleep_config is None:
        sleep_config = {'read_mode': 'next_day', 'start_hour': 20, 'end_hour': 12}
    sleep_result = parse_sleep_data_unified(
        date_str, health_dir,
        read_mode=sleep_config.get('read_mode', 'next_day'),
        start_hour=sleep_config.get('start_hour', 20),
        end_hour=sleep_config.get('end_hour', 12)
    )

    # 确保 sleep_result 包含所有必要字段
    if not sleep_result:
        sleep_result = {
            'records': [],
            'total_hours': 0,
            'deep_hours': 0,
            'core_hours': 0,
            'rem_hours': 0,
            'awake_hours': 0,
            'bedtime': '--',
            'waketime': '--',
        }

    sleep_records = sleep_result['records']
    sleep_total = sleep_result['total_hours']
    sleep_deep = sleep_result['deep_hours']
    sleep_core = sleep_result['core_hours']
    sleep_rem = sleep_result['rem_hours']
    sleep_awake = sleep_result['awake_hours']

    # 运动数据
    workouts = extract_workout_data(date_str, workout_dir, health_dir)
    if workouts is None:
        workouts = []

    # 心率数据（用于计算心率区间）
    heart_rate_data = []
    hr_metric = metrics.get('heart_rate', {})
    for hr_point in hr_metric.get('data', []):
        ts = hr_point.get('date') or hr_point.get('startDate') or hr_point.get('timestamp')
        hr = hr_point.get('qty')
        if ts is not None and hr is not None:
            heart_rate_data.append({
                'timestamp': ts,
                'hr': hr
            })

    # 活动能量合并（统一换算到 kcal）
    # active_energy 来源于 Apple Health 指标，单位是 kJ；workout.energy_kcal 已经是 kcal
    if active_energy and active_energy > 0:
        total_energy_kcal = active_energy / KJ_TO_KCAL
    else:
        total_energy_kcal = sum(w.get('energy_kcal', 0) for w in workouts)

    # 计算是否有运动
    has_workout = len(workouts) > 0 if workouts else False

    # V6.0.3: 从 workout 心率时间线计算真实的心率区间时间
    user_age = user_profile.get('age', 30) if user_profile else 30
    if user_age is None:
        user_age = 30
    zone_times = calculate_zone_times_from_workouts(workouts, user_age)

    bedtime = sleep_records[0].get('start', '--') if sleep_records else '--'
    waketime = sleep_records[-1].get('end', '--') if sleep_records else '--'

    result = {
        'date': date_str,
        'data_source': 'Apple Health',
        'profile': user_profile,
        'hrv': {
            'value': round(hrv_raw, 1) if hrv_raw else None,
            'measurement_count': hrv_measurement_count,
            'unit': 'ms'
        },
        'resting_hr': {
            'value': round(resting_hr_raw) if resting_hr_raw else None
        },
        'steps': int(steps),

        # 距离字段：保留新旧别名，避免后续脚本口径不一致
        'distance': round(distance, 2),
        'distance_km': round(distance, 2),

        # 活动能量字段：保留新旧别名，统一单位为 kcal
        'active_energy': round(total_energy_kcal, 1),
        'active_energy_kcal': round(total_energy_kcal, 1),

        'flights_climbed': round(flights, 1) if flights else 0,

        # 站立字段：保留新旧别名
        'apple_stand_time': int(stand_time),
        'stand_time_min': int(stand_time),

        'spo2': round(spo2, 1) if spo2 else None,
        'basal_energy_kcal': round(basal_energy / KJ_TO_KCAL, 1) if basal_energy else 0,
        'respiratory_rate': round(respiratory, 1) if respiratory else None,

        # 高级指标
        'heart_rate_avg': round(heart_rate_avg, 1) if heart_rate_avg else None,
        'vo2_max': round(vo2_max, 1) if vo2_max else None,
        'physical_effort': round(physical_effort, 2) if physical_effort else None,
        'breathing_disturbances': round(breathing_disturbances, 1) if breathing_disturbances else None,
        'apple_exercise_time': int(apple_exercise_time) if apple_exercise_time else 0,
        'apple_stand_hour': int(apple_stand_hour) if apple_stand_hour else 0,
        'stair_speed_up': round(stair_speed_up, 2) if stair_speed_up else None,
        'running_speed': round(running_speed, 2) if running_speed else None,
        'running_power': round(running_power, 1) if running_power else None,
        'running_stride_length': round(running_stride_length, 1) if running_stride_length else None,
        'running_ground_contact_time': round(running_ground_contact_time, 1) if running_ground_contact_time else None,
        'running_vertical_oscillation': round(running_vertical_oscillation, 1) if running_vertical_oscillation else None,
        'walking_speed': round(walking_speed, 2) if walking_speed else None,
        'walking_step_length': round(walking_step_length, 1) if walking_step_length else None,
        'walking_heart_rate_average': round(walking_heart_rate_average, 1) if walking_heart_rate_average else None,
        'walking_asymmetry_percentage': round(walking_asymmetry_percentage, 2) if walking_asymmetry_percentage else None,
        'walking_double_support_percentage': round(walking_double_support_percentage, 2) if walking_double_support_percentage else None,
        'headphone_audio_exposure': round(headphone_audio_exposure, 1) if headphone_audio_exposure else None,
        'environmental_audio_exposure': round(environmental_audio_exposure, 1) if environmental_audio_exposure else None,

        'sleep': {
            'total_hours': round(sleep_total, 2),
            'deep_hours': round(sleep_deep, 2) if sleep_deep else 0,
            'core_hours': round(sleep_core, 2) if sleep_core else 0,
            'rem_hours': round(sleep_rem, 2) if sleep_rem else 0,
            'awake_hours': round(sleep_awake, 2) if sleep_awake else 0,
            'records': len(sleep_records) if sleep_records else 0,
            'bedtime': bedtime,
            'waketime': waketime,
        },

        'bedtime': bedtime,
        'waketime': waketime,
        'sleep_latency_min': 20,

        'workouts': workouts,
        'has_workout': has_workout,
        'heart_rate_data': heart_rate_data,
        'zone_times': zone_times,
    }

    return result

def extract_all_members_data(date_str):
    """V5.8.1: 提取所有成员的数据"""
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
        if not member_config:
            print(f"Warning: 成员 {idx} 配置无效，已跳过", file=sys.stderr)
            continue
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
        print("  python extract_data_v5.py 2026-03-01 all   # 提取所有成员数据（V5.8.1+）", file=sys.stderr)
        sys.exit(1)

    date_str = sys.argv[1]

    # 检查是否使用 'all' 参数
    if len(sys.argv) > 2 and sys.argv[2].lower() == 'all':
        # 提取所有成员数据
        data = extract_all_members_data(date_str)
    else:
        # 提取单个成员数据
        try:
            member_idx = int(sys.argv[2]) if len(sys.argv) > 2 else 0
        except ValueError:
            print(f"Error: member_index 必须是整数或 'all'，当前输入: {sys.argv[2]}", file=sys.stderr)
            sys.exit(1)
        member_config = get_member_config(member_idx)
        if not member_config:
            sys.exit(1)

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
