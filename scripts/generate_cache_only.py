#!/usr/bin/env python3
"""批量生成健康数据缓存 - V6.0.3

用途：一次性生成历史日期的数据缓存，无需生成PDF报告
节省时间和资源，特别适合补历史数据

用法：
  python3 scripts/generate_cache_only.py 2026-02-01 2026-03-05    # 批量生成
  python3 scripts/generate_cache_only.py 2026-03-01               # 单日
"""

import sys
import json
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from extract_data_v5 import extract_daily_data
from health_score import calculate_all_scores, HealthScoreHistory
from utils import safe_member_name


def load_config():
    """加载配置"""
    config_paths = [
        Path(__file__).parent.parent / "config.json",
        Path.home() / '.openclaw' / 'workspace-health' / 'config.json',
    ]
    for config_path in config_paths:
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
    print("❌ 找不到 config.json")
    sys.exit(1)


def get_member_config(config, index):
    """获取成员配置"""
    members = config.get("members", [])
    if index < len(members):
        return members[index]
    return None


def generate_cache_for_date(date_str, member_idx, member_name, config):
    """为指定日期和成员生成缓存"""
    
    # 提取数据
    try:
        member_cfg = get_member_config(config, member_idx)
        if not member_cfg:
            print(f"   ❌ {date_str} - 成员配置不存在")
            return False
        
        # 获取睡眠配置
        sleep_config = config.get('sleep_config', {'read_mode': 'next_day', 'start_hour': 20, 'end_hour': 12})

        profile = {
            'name': member_cfg.get('name', ''),
            'age': member_cfg.get('age'),
            'gender': member_cfg.get('gender'),
            'height_cm': member_cfg.get('height_cm'),
            'weight_kg': member_cfg.get('weight_kg'),
        }

        data = extract_daily_data(
            date_str,
            health_dir=member_cfg.get('health_dir'),
            workout_dir=member_cfg.get('workout_dir'),
            user_profile=profile,
            sleep_config=sleep_config
        )
        if not data:
            print(f"   ⚠️  {date_str} - 无数据")
            return False
        
        # 检查数据有效性
        if not isinstance(data, dict) or 'hrv' not in data:
            print(f"   ⚠️  {date_str} - 数据格式异常")
            return False
            
    except Exception as e:
        print(f"   ❌ {date_str} - 提取失败: {e}")
        return False
    
    # 初始化历史记录管理器
    cache_dir = Path(config.get("cache_dir", str(Path(__file__).parent.parent / 'cache' / 'daily'))).expanduser()
    history = HealthScoreHistory(cache_dir)
    
    # 计算健康评分
    try:
        zone_times = data.get('zone_times', {'zone_1': 0, 'zone_2': 0, 'zone_3': 0, 'zone_4': 0, 'zone_5': 0})
        health_scores = calculate_all_scores(data, member_cfg, history, zone_times)
    except Exception as e:
        print(f"   ⚠️ {date_str} - 评分计算失败: {e}，使用默认值")
        health_scores = {
            'strain': 10.0, 'recovery': 50, 'recovery_status': 'yellow',
            'sleep_performance': 70, 'sleep_need': 7.8,
            'actual_sleep_hours': data.get('sleep', {}).get('total_hours', 7),
            'body_age': member_cfg.get('age', 30),
            'chronological_age': member_cfg.get('age', 30),
            'age_impact': 0.0, 'pace_of_aging': 0.0
        }
    
    # 计算睡眠债：允许少量还债
    sleep_total = data.get('sleep', {}).get('total_hours', 0)
    sleep_need = health_scores['sleep_need']
    daily_debt = round(sleep_need - sleep_total, 2)
    # 允许少量"还债"，但不要无限负向累积
    if daily_debt < 0:
        daily_debt = max(-1.0, daily_debt)

    prev_date = (datetime.strptime(date_str, '%Y-%m-%d') - timedelta(days=1)).strftime('%Y-%m-%d')
    try:
        prev_debt = history.get_sleep_debt(prev_date, member_name)
        accumulated_debt = max(0, prev_debt + daily_debt)
    except Exception:
        accumulated_debt = max(0, daily_debt)
    
    # 准备缓存数据
    safe_name = safe_member_name(member_name)
    apple_stand_min = data.get('apple_stand_time')
    if apple_stand_min is None:
        apple_stand_min = data.get('stand_time_min', 0)
    stand_hour_cache = float(apple_stand_min) / 60.0 if isinstance(apple_stand_min, (int, float)) else 0.0

    cache_data = {
        'date': date_str,
        'member': member_name,
        'hrv': data.get('hrv'),
        'resting_hr': data.get('resting_hr'),
        'respiratory_rate': data.get('respiratory_rate'),
        'steps': data.get('steps'),
        'distance': data.get('distance') or data.get('distance_km') or 0,
        'distance_km': data.get('distance_km') or data.get('distance') or 0,
        'active_energy': data.get('active_energy') or data.get('active_energy_kcal') or 0,
        'active_energy_kcal': data.get('active_energy_kcal') or data.get('active_energy') or 0,
        'apple_stand_time': apple_stand_min or 0,
        'apple_stand_hour': round(stand_hour_cache, 2),
        'spo2': data.get('spo2'),
        'workouts': data.get('workouts', []),
        'has_workout': data.get('has_workout', False),
        'zone_times': data.get('zone_times', {'zone_1': 0, 'zone_2': 0, 'zone_3': 0, 'zone_4': 0, 'zone_5': 0}),
        'sleep': data.get('sleep', {}),
        'bedtime': data.get('bedtime') or data.get('sleep', {}).get('bedtime', '--'),
        'waketime': data.get('waketime') or data.get('sleep', {}).get('waketime', '--'),
        'sleep_latency_min': data.get('sleep_latency_min', 20),
        'sleep_debt_daily': round(daily_debt, 2),
        'sleep_debt_accumulated': round(accumulated_debt, 2),
        'health_scores': {
            'strain': health_scores['strain'],
            'recovery': health_scores['recovery'],
            'recovery_status': health_scores['recovery_status'],
            'sleep_performance': health_scores['sleep_performance'],
            'sleep_need': health_scores['sleep_need'],
            'actual_sleep_hours': round(sleep_total, 2),
            'body_age': health_scores['body_age'],
            'chronological_age': health_scores['chronological_age'],
            'age_impact': health_scores['age_impact'],
            'pace_of_aging': health_scores['pace_of_aging'],
            'zone_times': health_scores.get('zone_times', {
                'zone_1': 0, 'zone_2': 0, 'zone_3': 0, 'zone_4': 0, 'zone_5': 0
            }),
            'hrv_rmssd': data.get('hrv', {}).get('value', 0) if isinstance(data.get('hrv'), dict) else 0,
            'rhr': data.get('resting_hr', {}).get('value', 0) if isinstance(data.get('resting_hr'), dict) else 0
        }
    }
    
    # 保存缓存
    cache_file = cache_dir / f"{date_str}_{safe_name}.json"
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    with open(cache_file, 'w', encoding='utf-8') as f:
        json.dump(cache_data, f, ensure_ascii=False, indent=2)
    
    print(f"   ✅ {date_str} - Strain:{health_scores['strain']:.1f} Recovery:{health_scores['recovery']}% BodyAge:{health_scores['body_age']:.1f}")
    return True


def generate_date_range(start_date, end_date):
    """生成日期范围"""
    dates = []
    current = datetime.strptime(start_date, '%Y-%m-%d')
    end = datetime.strptime(end_date, '%Y-%m-%d')
    while current <= end:
        dates.append(current.strftime('%Y-%m-%d'))
        current += timedelta(days=1)
    return dates


def main():
    if len(sys.argv) < 2:
        print("用法:")
        print(f"  python3 {sys.argv[0]} START_DATE [END_DATE]")
        print(f"  python3 {sys.argv[0]} 2026-02-01 2026-03-05    # 批量生成")
        print(f"  python3 {sys.argv[0]} 2026-03-01               # 单日")
        sys.exit(1)
    
    start_date, end_date = sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else sys.argv[1]
    
    try:
        datetime.strptime(start_date, '%Y-%m-%d')
        datetime.strptime(end_date, '%Y-%m-%d')
    except ValueError:
        print("❌ 日期格式错误，应为 YYYY-MM-DD")
        sys.exit(1)
    
    config = load_config()
    members = config.get("members", [])
    if not members:
        print("❌ config.json 中没有配置成员")
        sys.exit(1)
    
    dates = generate_date_range(start_date, end_date)
    print(f"📅 将生成 {len(dates)} 天的缓存 ({start_date} 到 {end_date})")
    print(f"👥 成员数: {len(members)}\n")
    
    total_generated, total_failed = 0, 0
    
    for idx, member in enumerate(members):
        member_name = member.get('name', f'成员{idx+1}')
        print(f"\n👤 成员 {idx+1}/{len(members)}: {member_name}")
        success_count, fail_count = 0, 0
        
        for date_str in dates:
            if generate_cache_for_date(date_str, idx, member_name, config):
                success_count += 1
            else:
                fail_count += 1
        
        print(f"   完成: {success_count} 成功, {fail_count} 失败")
        total_generated += success_count
        total_failed += fail_count
    
    print(f"\n{'='*50}")
    print(f"✅ 缓存生成完成")
    print(f"   总计: {total_generated} 成功, {total_failed} 失败")
    if len(dates) >= 14:
        print(f"💡 已生成 {len(dates)} 天数据，Pace of Aging 趋势将准确计算")
    else:
        print(f"⚠️  只生成了 {len(dates)} 天数据，Pace of Aging 需要至少14天才能准确计算")


if __name__ == '__main__':
    main()
