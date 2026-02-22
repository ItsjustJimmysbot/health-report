#!/usr/bin/env python3
"""
健康报告生成脚本 - 生成日报、周报、月报
"""
import json
import os
from datetime import datetime, timedelta

def parse_health_data(file_path):
    """解析健康数据文件"""
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    metrics = data.get('data', {}).get('metrics', [])
    result = {}
    
    for metric in metrics:
        name = metric.get('name')
        result[name] = metric
    
    return result

def get_metric_value(metrics, name, agg='avg'):
    """获取指标值"""
    if name not in metrics:
        return None, 0
    
    data = metrics[name].get('data', [])
    if not data:
        return None, 0
    
    values = [d.get('qty', 0) for d in data if 'qty' in d]
    if not values:
        return None, 0
    
    if agg == 'avg':
        return sum(values) / len(values), len(values)
    elif agg == 'sum':
        return sum(values), len(values)
    elif agg == 'max':
        return max(values), len(values)
    elif agg == 'min':
        return min(values), len(values)
    
    return values[0], len(values)

def get_daily_summary(date_str, metrics):
    """获取单日汇总数据"""
    summary = {'date': date_str}
    
    # HRV (心率变异性)
    hrv_val, hrv_count = get_metric_value(metrics, 'heart_rate_variability', 'avg')
    summary['hrv'] = hrv_val
    summary['hrv_count'] = hrv_count
    
    # 静息心率
    resting_hr, _ = get_metric_value(metrics, 'resting_heart_rate', 'avg')
    summary['resting_hr'] = resting_hr
    
    # 步数
    steps, _ = get_metric_value(metrics, 'step_count', 'sum')
    summary['steps'] = steps
    
    # 行走距离
    distance, _ = get_metric_value(metrics, 'walking_running_distance', 'sum')
    summary['distance'] = distance
    
    # 活动能量
    energy, _ = get_metric_value(metrics, 'active_energy', 'sum')
    summary['energy'] = energy
    
    # 爬楼层数
    floors, _ = get_metric_value(metrics, 'flights_climbed', 'sum')
    summary['floors'] = floors
    
    # 站立时间
    stand_time, _ = get_metric_value(metrics, 'apple_stand_time', 'sum')
    summary['stand_time'] = stand_time
    
    # 血氧
    spo2, spo2_count = get_metric_value(metrics, 'blood_oxygen_saturation', 'avg')
    summary['spo2'] = spo2
    summary['spo2_count'] = spo2_count
    
    # 静息能量
    rest_energy, _ = get_metric_value(metrics, 'basal_energy_burned', 'sum')
    summary['rest_energy'] = rest_energy
    
    # 呼吸率
    resp_rate, _ = get_metric_value(metrics, 'respiratory_rate', 'avg')
    summary['resp_rate'] = resp_rate
    
    # 睡眠数据
    sleep_sessions = []
    if 'sleep_analysis' in metrics:
        for sleep in metrics['sleep_analysis'].get('data', []):
            sleep_start = sleep.get('startDate', '')
            sleep_end = sleep.get('endDate', '')
            sleep_qty = sleep.get('qty', 0)
            sleep_value = sleep.get('value', '')
            sleep_sessions.append({
                'start': sleep_start,
                'end': sleep_end,
                'hours': sleep_qty / 60 if sleep_qty else 0,
                'type': sleep_value
            })
    summary['sleep_sessions'] = sleep_sessions
    summary['sleep_total'] = sum(s['hours'] for s in sleep_sessions)
    
    # 运动数据
    workouts = []
    if 'workout' in metrics:
        for w in metrics['workout'].get('data', []):
            workouts.append({
                'type': w.get('value', ''),
                'start': w.get('startDate', ''),
                'end': w.get('endDate', ''),
                'duration': w.get('qty', 0),
                'energy': w.get('source', '')
            })
    summary['workouts'] = workouts
    summary['has_workout'] = len(workouts) > 0
    
    return summary

def analyze_trend(current, previous, higher_is_better=True):
    """分析趋势"""
    if not current or not previous:
        return 'stable', '持平'
    
    diff = current - previous
    pct = (diff / previous * 100) if previous else 0
    
    if abs(pct) < 5:
        return 'stable', '持平'
    
    if higher_is_better:
        if pct > 0:
            return 'up', f'↑{pct:.0f}%'
        else:
            return 'down', f'↓{abs(pct):.0f}%'
    else:
        if pct < 0:
            return 'up', f'↓{abs(pct):.0f}%'
        else:
            return 'down', f'↑{pct:.0f}%'

def get_rating(value, good_threshold, poor_threshold, higher_is_better=True):
    """获取评级"""
    if value is None:
        return '未知', 'rating-average', 'badge-average'
    
    if higher_is_better:
        if value >= good_threshold:
            return '优秀', 'rating-excellent', 'badge-excellent'
        elif value >= poor_threshold:
            return '良好', 'rating-good', 'badge-good'
        else:
            return '需改善', 'rating-poor', 'badge-poor'
    else:
        if value <= good_threshold:
            return '优秀', 'rating-excellent', 'badge-excellent'
        elif value <= poor_threshold:
            return '良好', 'rating-good', 'badge-good'
        else:
            return '需改善', 'rating-poor', 'badge-poor'

# 主程序
if __name__ == '__main__':
    base_dir = os.path.expanduser('~/我的云端硬盘/Health Auto Export/Health Data')
    
    # 读取5天数据
    dates = ['2026-02-18', '2026-02-19', '2026-02-20', '2026-02-21', '2026-02-22']
    daily_data = {}
    
    for date in dates:
        file_path = f"{base_dir}/HealthAutoExport-{date}.json"
        if os.path.exists(file_path):
            metrics = parse_health_data(file_path)
            daily_data[date] = get_daily_summary(date, metrics)
            print(f"✅ 已加载: {date}")
        else:
            print(f"❌ 缺失: {date}")
    
    print(f"\n📊 成功加载 {len(daily_data)} 天数据")
    
    # 打印2月18日数据示例
    if '2026-02-18' in daily_data:
        d = daily_data['2026-02-18']
        print(f"\n2月18日数据:")
        print(f"  HRV: {d.get('hrv', 'N/A')}")
        print(f"  步数: {d.get('steps', 'N/A')}")
        print(f"  睡眠: {d.get('sleep_total', 'N/A')}小时")
        print(f"  运动: {'有' if d.get('has_workout') else '无'}")
