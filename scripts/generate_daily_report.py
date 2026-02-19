#!/usr/bin/env python3
"""
每日健康报告生成器 - 完整版
读取 Apple Health Data 和 Workout Data，生成可视化报告
"""
import json
import sys
from datetime import datetime
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
            # 提取开始和结束时间
            start_str = workout.get('start', '')
            end_str = workout.get('end', '')
            
            # 解析时间 (格式: 2026-02-18 20:25:19 +0800)
            start_time = start_str.split(' ')[1][:5] if start_str else '--:--'
            end_time = end_str.split(' ')[1][:5] if end_str else '--:--'
            
            # 获取持续时间（秒）并转换为分钟
            duration_sec = workout.get('duration', 0)
            
            # 获取卡路里（从 activeEnergyBurned 或计算）
            energy_kj = workout.get('activeEnergyBurned', {}).get('qty', 0)
            calories = round(energy_kj * 0.239)  # kJ 转换为 kcal
            
            # 获取平均心率
            avg_hr = workout.get('avgHeartRate', {}).get('qty', 0) or workout.get('heartRate', {}).get('avg', {}).get('qty', 0)
            
            # 获取运动名称
            name = workout.get('name', '运动')
            # 映射图标
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
                'duration': duration_sec,  # 保持秒数，在显示时转换
                'calories': calories,
                'avg_hr': int(avg_hr) if avg_hr else 0,
                'start_time': start_time,
                'end_time': end_time,
            })
        
        return workouts
    except Exception as e:
        print(f"⚠️ 读取 workout 数据失败: {e}")
        return []

def parse_health_data(health_file: str) -> dict:
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
        
        # 睡眠
        sleep_metric = get_metric('sleep_analysis')
        sleep_hours = sleep_metric.get('data', [{}])[0].get('totalSleep', 0) if sleep_metric else 0
        
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
        
        return {
            'steps': int(steps),
            'sleep_hours': round(sleep_hours, 2),
            'hrv': int(hrv),
            'resting_hr': int(rhr),
            'exercise_min': int(exercise),
            'floors': int(floors),
            'active_calories': int(active_calories),
            'distance': round(distance, 2),
            'blood_oxygen': int(spo2) if spo2 else 97,
        }
    except Exception as e:
        print(f"⚠️ 读取 health 数据失败: {e}")
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
    health_data = parse_health_data(args.health)
    
    print("  - 读取 Workout Data...")
    workouts = parse_workout_data(args.workout)
    
    # 计算评分
    print("  - 计算评分...")
    scores = calculate_scores(health_data)
    
    # 组合数据
    report_data = {
        'date': date,
        'weekday': weekday_cn,
        'day_of_year': datetime.strptime(date, '%Y-%m-%d').timetuple().tm_yday if args.date else 50,
        **health_data,
        **scores,
        'workouts': workouts,
        # 睡眠详细数据（默认值）
        'sleep_deep': 1.0,
        'sleep_deep_pct': 20,
        'sleep_rem': 1.5,
        'sleep_rem_pct': 25,
        'sleep_core': 3.0,
        'sleep_core_pct': 55,
        'sleep_awake': 0.1,
        'sleep_awake_pct': 5,
        'sleep_efficiency': 0.95,
        'sleep_start': '23:00',
        'sleep_end': '06:30',
        'time_in_bed': health_data.get('sleep_hours', 0),
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
    print(f"   睡眠: {health_data.get('sleep_hours', 0)}h")
    print(f"   HRV: {health_data.get('hrv', 0)}ms")
    print(f"   运动记录: {len(workouts)} 条")
    for w in workouts:
        print(f"     - {w['type']}: {w['start_time']} - {w['end_time']} ({round(w['duration']/60)}分钟)")

if __name__ == '__main__':
    main()
