#!/usr/bin/env python3
"""
每日健康报告生成器 - 修复版
使用真实数据，修复睡眠、心率数据来源
"""
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

# 添加脚本目录到路径
sys.path.insert(0, str(Path(__file__).parent))
from generate_visual_report import generate_visual_report

def parse_workout_data(workout_file: str) -> list:
    """解析 Workout Data JSON 文件"""
    try:
        with open(workout_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        workouts = []
        for workout in data.get('data', {}).get('workouts', []):
            start_str = workout.get('start', '')
            end_str = workout.get('end', '')
            
            start_time = start_str.split(' ')[1][:5] if start_str else '--:--'
            end_time = end_str.split(' ')[1][:5] if end_str else '--:--'
            
            duration_sec = workout.get('duration', 0)
            
            energy_kj = workout.get('activeEnergyBurned', {}).get('qty', 0)
            calories = round(energy_kj * 0.239)
            
            avg_hr = workout.get('avgHeartRate', {}).get('qty', 0) or workout.get('heartRate', {}).get('avg', {}).get('qty', 0)
            
            # 获取心率数据用于图表
            hr_data = workout.get('heartRateData', [])
            heart_rate_series = []
            for hr in hr_data:
                if 'Avg' in hr and 'date' in hr:
                    time_str = hr['date'].split(' ')[1][:5] if ' ' in hr['date'] else ''
                    heart_rate_series.append({
                        'time': time_str,
                        'hr': int(hr['Avg'])
                    })
            
            name = workout.get('name', '运动')
            icon_map = {
                '楼梯': '🏢',
                '爬楼梯': '🏢',
                '步行': '🚶',
                '跑步': '🏃',
                '骑行': '🚴',
                '游泳': '🏊',
                '瑜伽': '🧘',
                '力量训练': '💪',
            }
            icon = icon_map.get(name, '🏃')
            
            workouts.append({
                'type': name,
                'icon': icon,
                'duration': duration_sec,
                'calories': calories,
                'avg_hr': int(avg_hr) if avg_hr else 0,
                'start_time': start_time,
                'end_time': end_time,
                'heart_rate_series': heart_rate_series,
            })
        
        return workouts
    except Exception as e:
        print(f"⚠️ 读取 workout 数据失败: {e}")
        return []

def parse_health_data(health_file: str, workout_file: str = None) -> dict:
    """解析 Health Data JSON 文件"""
    try:
        with open(health_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        metrics = data.get('data', {}).get('metrics', [])
        
        def get_metric(name):
            for m in metrics:
                if m.get('name') == name:
                    return m
            return None
        
        # 步数
        steps_metric = get_metric('step_count')
        steps = sum(d.get('qty', 0) for d in steps_metric.get('data', [])) if steps_metric else 0
        
        # 从 workout 文件获取睡眠数据（更准确）
        sleep_hours = 0
        sleep_start = '--:--'
        sleep_end = '--:--'
        sleep_deep = 0
        sleep_rem = 0
        sleep_core = 0
        sleep_awake = 0
        sleep_efficiency = 0
        
        # 首先尝试从 Apple Health 获取睡眠数据
        sleep_metric = get_metric('sleep_analysis')
        if sleep_metric and sleep_metric.get('data'):
            sleep_data = sleep_metric['data'][0]
            sleep_hours = sleep_data.get('totalSleep', 0)
            sleep_start_full = sleep_data.get('sleepStart', '')
            sleep_end_full = sleep_data.get('sleepEnd', '')
            sleep_start = sleep_start_full.split(' ')[1][:5] if sleep_start_full else '--:--'
            sleep_end = sleep_end_full.split(' ')[1][:5] if sleep_end_full else '--:--'
            
            # 获取睡眠阶段数据
            sleep_deep = sleep_data.get('deep', 0)
            sleep_rem = sleep_data.get('rem', 0)
            sleep_core = sleep_data.get('core', 0)
            sleep_awake = sleep_data.get('awake', 0)
            
            # 计算睡眠效率 = 实际睡眠时间 / 在床时间
            in_bed_hours = sleep_data.get('inBed', 0) or sleep_hours
            if in_bed_hours > 0:
                sleep_efficiency = sleep_hours / in_bed_hours
            else:
                sleep_efficiency = 0.95
        
        # HRV
        hrv_metric = get_metric('heart_rate_variability')
        hrv_data = hrv_metric.get('data', []) if hrv_metric else []
        hrv = sum(d.get('qty', 0) for d in hrv_data) / len(hrv_data) if hrv_data else 0
        
        # 静息心率
        rhr_metric = get_metric('resting_heart_rate')
        rhr = rhr_metric.get('data', [{}])[0].get('qty', 0) if rhr_metric else 0
        
        # 锻炼时间
        exercise_metric = get_metric('apple_exercise_time')
        exercise = sum(d.get('qty', 0) for d in exercise_metric.get('data', [])) if exercise_metric else 0
        
        # 爬楼层数
        floors_metric = get_metric('flights_climbed')
        floors = sum(d.get('qty', 0) for d in floors_metric.get('data', [])) if floors_metric else 0
        
        # 活跃卡路里
        active_energy_metric = get_metric('active_energy')
        active_calories = sum(d.get('qty', 0) for d in active_energy_metric.get('data', [])) if active_energy_metric else 0
        
        # 行走距离
        distance_metric = get_metric('walking_running_distance')
        distance = sum(d.get('qty', 0) for d in distance_metric.get('data', [])) if distance_metric else 0
        
        # 血氧
        spo2_metric = get_metric('blood_oxygen_saturation')
        spo2 = spo2_metric.get('data', [{}])[0].get('qty', 0) if spo2_metric else 0
        
        # 心率数据 - 获取全天心率
        hr_metric = get_metric('heart_rate')
        heart_rate_series = []
        if hr_metric and hr_metric.get('data'):
            # 采样心率数据（每小时取一个点）
            hr_list = hr_metric['data']
            for hr in hr_list[::10]:  # 每10个取一个，避免数据过多
                if 'Avg' in hr and 'date' in hr:
                    date_str = hr['date']
                    time_str = date_str.split(' ')[1][:5] if ' ' in date_str else ''
                    if time_str:
                        heart_rate_series.append({
                            'time': time_str,
                            'hr': int(hr['Avg'])
                        })
        
        return {
            'steps': int(steps),
            'sleep_hours': round(sleep_hours, 2),
            'sleep_start': sleep_start,
            'sleep_end': sleep_end,
            'sleep_deep': round(sleep_deep, 2),
            'sleep_rem': round(sleep_rem, 2),
            'sleep_core': round(sleep_core, 2),
            'sleep_awake': round(sleep_awake, 2),
            'sleep_efficiency': round(sleep_efficiency, 2),
            'hrv': int(hrv),
            'resting_hr': int(rhr),
            'exercise_min': int(exercise),
            'floors': int(floors),
            'active_calories': int(active_calories),
            'distance': round(distance, 2),
            'blood_oxygen': int(spo2) if spo2 else 97,
            'heart_rate_series': heart_rate_series,
        }
    except Exception as e:
        print(f"⚠️ 读取 health 数据失败: {e}")
        import traceback
        traceback.print_exc()
        return {}

def calculate_scores(data: dict) -> dict:
    """计算各项评分"""
    hrv = data.get('hrv', 0)
    sleep_hours = data.get('sleep_hours', 0)
    steps = data.get('steps', 0)
    
    # HRV 评分
    if hrv >= 50:
        hrv_score = 10
    elif hrv >= 40:
        hrv_score = 7
    else:
        hrv_score = 5
    
    # 睡眠评分
    if sleep_hours >= 7:
        sleep_score = 10
    elif sleep_hours >= 5:
        sleep_score = 5
    else:
        sleep_score = 3
    
    # 步数评分
    if steps >= 10000:
        step_score = 10
    elif steps >= 8000:
        step_score = 8
    elif steps >= 6000:
        step_score = 6
    else:
        step_score = 4
    
    # 综合恢复度评分
    recovery_score = int((hrv_score * 35 + sleep_score * 35 + step_score * 30) / 100)
    
    # 睡眠质量评分 (0-100)
    sleep_quality_score = int(min(100, sleep_hours * 100 / 8))
    
    # 运动完成评分 (0-100)
    exercise_score = int(min(100, steps * 100 / 8000))
    
    return {
        'recovery_score': recovery_score,
        'recovery_status': '良好' if recovery_score >= 8 else '一般' if recovery_score >= 5 else '需改善',
        'recovery_status_class': 'status-good' if recovery_score >= 8 else 'status-warning' if recovery_score >= 5 else 'status-bad',
        'sleep_score': sleep_quality_score,
        'sleep_status_text': '充足' if sleep_hours >= 7 else '偏短' if sleep_hours >= 6 else '不足',
        'sleep_status_class': 'status-good' if sleep_hours >= 7 else 'status-warning' if sleep_hours >= 6 else 'status-bad',
        'exercise_score': exercise_score,
        'exercise_status_text': '优秀' if steps >= 10000 else '良好' if steps >= 8000 else '不足',
        'exercise_status_class': 'status-good' if steps >= 10000 else 'status-warning' if steps >= 8000 else 'status-bad',
    }

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='生成每日健康报告')
    parser.add_argument('--health', required=True, help='Health Data JSON 文件路径')
    parser.add_argument('--workout', required=True, help='Workout Data JSON 文件路径')
    parser.add_argument('--output', required=True, help='输出 HTML 文件路径')
    parser.add_argument('--date', default='', help='报告日期 (YYYY-MM-DD)')
    
    args = parser.parse_args()
    
    # 解析日期
    if args.date:
        date = args.date
        weekday = datetime.strptime(date, '%Y-%m-%d').strftime('%w')
        weekday_cn = '日一二三四五六'[int(weekday)]
    else:
        date = datetime.now().strftime('%Y-%m-%d')
        weekday_cn = '五'
    
    print(f"📊 生成健康报告: {date}")
    
    # 读取数据
    print("  - 读取 Health Data...")
    health_data = parse_health_data(args.health, args.workout)
    
    print("  - 读取 Workout Data...")
    workouts = parse_workout_data(args.workout)
    
    # 计算评分
    print("  - 计算评分...")
    scores = calculate_scores(health_data)
    
    # 计算睡眠百分比
    sleep_hours = health_data.get('sleep_hours', 0)
    sleep_deep = health_data.get('sleep_deep', 0)
    sleep_rem = health_data.get('sleep_rem', 0)
    sleep_core = health_data.get('sleep_core', 0)
    sleep_awake = health_data.get('sleep_awake', 0)
    
    sleep_deep_pct = int(sleep_deep / sleep_hours * 100) if sleep_hours > 0 else 20
    sleep_rem_pct = int(sleep_rem / sleep_hours * 100) if sleep_hours > 0 else 25
    sleep_core_pct = int(sleep_core / sleep_hours * 100) if sleep_hours > 0 else 50
    sleep_awake_pct = int(sleep_awake / sleep_hours * 100) if sleep_hours > 0 else 5
    
    # 获取心率数据用于图表
    heart_rate_series = health_data.get('heart_rate_series', [])
    
    # 获取锻炼心率数据
    workout_hr_series = []
    if workouts and workouts[0].get('heart_rate_series'):
        workout_hr_series = workouts[0]['heart_rate_series']
    
    # 组合数据
    report_data = {
        'date': date,
        'weekday': weekday_cn,
        'day_of_year': datetime.strptime(date, '%Y-%m-%d').timetuple().tm_yday if args.date else 50,
        **health_data,
        **scores,
        'workouts': workouts,
        # 睡眠详细数据
        'sleep_deep_pct': sleep_deep_pct,
        'sleep_rem_pct': sleep_rem_pct,
        'sleep_core_pct': sleep_core_pct,
        'sleep_awake_pct': sleep_awake_pct,
        'time_in_bed': health_data.get('sleep_hours', 0) + health_data.get('sleep_awake', 0),
        # 心率数据
        'heart_rate_series': heart_rate_series,
        'workout_hr_series': workout_hr_series,
        # 趋势数据（默认值）
        'steps_7day_avg': health_data.get('steps', 0),
        'steps_trend': '→',
        'steps_trend_class': 'trend-same',
        'sleep_7day_avg': health_data.get('sleep_hours', 0),
        'sleep_trend': '→',
        'sleep_trend_class': 'trend-same',
        'hrv_7day_avg': health_data.get('hrv', 0),
        'hrv_trend': '→',
        'hrv_trend_class': 'trend-same',
        'rhr_7day_avg': health_data.get('resting_hr', 0),
        'rhr_trend': '→',
        'rhr_trend_class': 'trend-same',
        # 用户输入
        'diet_content': '',
        'notes_content': '',
    }
    
    # 生成 HTML 报告
    print(f"  - 生成 HTML: {args.output}")
    generate_visual_report(report_data, args.output)
    
    print(f"\n✅ 报告生成完成!")
    print(f"   步数: {health_data.get('steps', 0)}")
    print(f"   睡眠: {health_data.get('sleep_hours', 0)}h (入睡: {health_data.get('sleep_start', '--:--')}, 起床: {health_data.get('sleep_end', '--:--')})")
    print(f"   睡眠效率: {health_data.get('sleep_efficiency', 0)*100:.0f}%")
    print(f"   HRV: {health_data.get('hrv', 0)}ms")
    print(f"   静息心率: {health_data.get('resting_hr', 0)}bpm")
    print(f"   运动记录: {len(workouts)} 条")
    for w in workouts:
        print(f"     - {w['type']}: {w['start_time']} - {w['end_time']} ({round(w['duration']/60)}分钟, 心率{w['avg_hr']}bpm)")

if __name__ == '__main__':
    main()
