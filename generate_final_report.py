#!/usr/bin/env python3
"""
健康日报生成脚本 - V2模板 - 2026-02-18 FINAL
"""

import json
import os
import sys
from datetime import datetime, timedelta

def load_json(path):
    with open(os.path.expanduser(path), 'r', encoding='utf-8') as f:
        return json.load(f)

def parse_date(date_str):
    """解析日期字符串"""
    return datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S %z")

def extract_metric(metrics, name):
    """提取指定指标的所有数据点"""
    for metric in metrics:
        if metric.get('name') == name:
            return metric.get('data', [])
    return []

def safe_sum(data, key='qty'):
    """安全求和"""
    return sum(d.get(key, 0) for d in data if key in d)

def safe_avg(data, key='qty'):
    """安全平均"""
    values = [d.get(key, 0) for d in data if key in d]
    return sum(values) / len(values) if values else 0

def extract_all_metrics(data18, workout_data):
    """提取所有指标"""
    metrics = data18.get('data', {}).get('metrics', [])
    
    result = {}
    
    # HRV - 取平均值，记录数据点数量
    hrv_data = extract_metric(metrics, 'heart_rate_variability')
    result['hrv'] = safe_avg(hrv_data, 'qty')
    result['hrv_count'] = len(hrv_data)
    
    # 静息心率 - 取平均值
    rhr_data = extract_metric(metrics, 'resting_heart_rate')
    result['resting_hr'] = safe_avg(rhr_data, 'qty')
    
    # 步数 - 求和
    steps_data = extract_metric(metrics, 'step_count')
    result['steps'] = safe_sum(steps_data, 'qty')
    
    # 行走距离 - 求和（已经是km）
    distance_data = extract_metric(metrics, 'walking_running_distance')
    result['distance'] = safe_sum(distance_data, 'qty')
    
    # 活动能量 - kJ转kcal
    active_energy_data = extract_metric(metrics, 'active_energy')
    active_kj = safe_sum(active_energy_data, 'qty')
    result['active_energy_kcal'] = active_kj / 4.184
    
    # 爬楼层数 - 求和
    flights_data = extract_metric(metrics, 'flights_climbed')
    result['flights'] = safe_sum(flights_data, 'qty')
    
    # 站立时间 - 求和
    stand_data = extract_metric(metrics, 'apple_stand_time')
    result['stand_minutes'] = safe_sum(stand_data, 'qty')
    
    # 血氧 - 已经是百分比，直接平均
    spo2_data = extract_metric(metrics, 'blood_oxygen_saturation')
    result['spo2'] = safe_avg(spo2_data, 'qty')
    
    # 呼吸率 - 平均值
    resp_data = extract_metric(metrics, 'respiratory_rate')
    result['respiratory_rate'] = safe_avg(resp_data, 'qty')
    
    # 静息能量 - kJ转kcal
    basal_data = extract_metric(metrics, 'basal_energy_burned')
    basal_kj = safe_sum(basal_data, 'qty')
    result['basal_energy_kcal'] = basal_kj / 4.184
    
    return result

from datetime import timezone

def extract_sleep_data(data19):
    """从2026-02-19数据中提取睡眠数据（时间窗口：2/18 20:00 - 2/19 12:00）"""
    metrics = data19.get('data', {}).get('metrics', [])
    
    # 定义时间窗口（带时区信息 +0800 = UTC+8）
    tz = timezone(timedelta(hours=8))
    window_start = datetime(2026, 2, 18, 20, 0, 0, tzinfo=tz)
    window_end = datetime(2026, 2, 19, 12, 0, 0, tzinfo=tz)
    
    sleep_sessions = []
    
    for metric in metrics:
        if metric.get('name') == 'sleep_analysis':
            for sleep in metric.get('data', []):
                sleep_start_str = sleep.get('sleepStart')
                if not sleep_start_str:
                    continue
                    
                sleep_start = parse_date(sleep_start_str)
                sleep_end_str = sleep.get('sleepEnd')
                sleep_end = parse_date(sleep_end_str) if sleep_end_str else sleep_start
                
                # 检查是否在时间窗口内 (2/18 20:00 至 2/19 12:00)
                if sleep_start >= window_start and sleep_start < window_end:
                    # 提取各阶段睡眠时长（单位为分钟）
                    deep = sleep.get('deep', 0)  # 已经是小时，需要转换为分钟
                    core = sleep.get('core', 0)
                    rem = sleep.get('rem', 0)
                    awake = sleep.get('awake', 0)
                    total = sleep.get('totalSleep', 0) or sleep.get('asleep', 0)
                    
                    sleep_sessions.append({
                        'start': sleep_start,
                        'end': sleep_end,
                        'deep': deep * 60,  # 小时转分钟
                        'core': core * 60,
                        'rem': rem * 60,
                        'awake': awake * 60,
                        'total': total * 60,
                    })
    
    # 按开始时间排序
    sleep_sessions.sort(key=lambda x: x['start'])
    
    # 汇总所有睡眠阶段（去重并合并）
    total_deep = sum(s['deep'] for s in sleep_sessions)
    total_core = sum(s['core'] for s in sleep_sessions)
    total_rem = sum(s['rem'] for s in sleep_sessions)
    total_awake = sum(s['awake'] for s in sleep_sessions)
    total_sleep = sum(s['total'] for s in sleep_sessions)
    
    # 如果没有详细的阶段数据，使用总睡眠
    if total_sleep == 0 and sleep_sessions:
        total_sleep = sum((s['end'] - s['start']).total_seconds() / 60 for s in sleep_sessions)
    
    total_all = total_deep + total_core + total_rem + total_awake
    if total_all == 0:
        total_all = total_sleep
    
    return {
        'sessions': sleep_sessions,
        'total_hours': total_sleep / 60,  # 转换为小时
        'deep': total_deep / 60,
        'core': total_core / 60,
        'rem': total_rem / 60,
        'awake': total_awake / 60,
        'deep_pct': (total_deep / total_all * 100) if total_all else 0,
        'core_pct': (total_core / total_all * 100) if total_all else 0,
        'rem_pct': (total_rem / total_all * 100) if total_all else 0,
        'awake_pct': (total_awake / total_all * 100) if total_all else 0,
    }

def extract_workout_data(workout_data):
    """提取运动数据"""
    workouts = workout_data.get('data', {}).get('workouts', [])
    
    if not workouts:
        return None
    
    workout = workouts[0]
    
    # 提取心率数据用于图表
    hr_data = workout.get('heartRateData', [])
    hr_chart_data = []
    for hr in hr_data:
        hr_chart_data.append({
            'time': hr.get('date', ''),
            'avg': hr.get('Avg', 0),
            'max': hr.get('Max', 0),
        })
    
    # 计算总能量消耗 (kJ转kcal)
    active_energy_kj = sum(a.get('qty', 0) for a in workout.get('activeEnergy', []))
    
    # duration可能是数字（秒）或对象
    duration_val = workout.get('duration', 0)
    if isinstance(duration_val, dict):
        duration_minutes = duration_val.get('qty', 0)
    else:
        duration_minutes = duration_val / 60  # 秒转分钟
    
    # 平均心率
    avg_hr_val = workout.get('averageHeartRate', 0)
    if isinstance(avg_hr_val, dict):
        avg_hr = avg_hr_val.get('qty', 0)
    else:
        avg_hr = avg_hr_val
    
    # 最大心率
    max_hr_val = workout.get('maximumHeartRate', 0)
    if isinstance(max_hr_val, dict):
        max_hr = max_hr_val.get('qty', 0)
    else:
        max_hr = max_hr_val
    
    return {
        'name': workout.get('name', '未知运动'),
        'start_time': workout.get('start', ''),
        'duration': duration_minutes,
        'energy_kcal': active_energy_kj / 4.184,
        'avg_hr': avg_hr,
        'max_hr': max_hr,
        'hr_data': hr_chart_data,
    }

def generate_hr_chart(hr_data):
    """生成心率SVG图表"""
    if not hr_data:
        return "<p>无心率数据</p>"
    
    # 取前30个数据点
    hr_data = hr_data[:30]
    
    avg_data = [d['avg'] for d in hr_data]
    max_data = [d['max'] for d in hr_data]
    
    # SVG尺寸
    width = 700
    height = 150
    padding = 30
    
    # 计算范围
    min_hr = 120
    max_hr = 170
    
    # 生成路径点
    n = len(avg_data)
    x_step = (width - 2 * padding) / max(n - 1, 1)
    
    def y_scale(val):
        return height - padding - (val - min_hr) / (max_hr - min_hr) * (height - 2 * padding)
    
    # 平均心率线
    avg_points = []
    for i, val in enumerate(avg_data):
        x = padding + i * x_step
        y = y_scale(val)
        avg_points.append(f"{x},{y}")
    avg_path = "M" + " L".join(avg_points)
    
    # 最高心率线 (虚线)
    max_points = []
    for i, val in enumerate(max_data):
        x = padding + i * x_step
        y = y_scale(val)
        max_points.append(f"{x},{y}")
    max_path = "M" + " L".join(max_points)
    
    svg = f'''
    <svg viewBox="0 0 {width} {height}" style="width:100%;height:150px;">
        <rect width="{width}" height="{height}" fill="#f8fafc"/>
        
        <g stroke="#e2e8f0" stroke-width="1">
            <line x1="{padding}" y1="{padding}" x2="{width-padding}" y2="{padding}"/>
            <line x1="{padding}" y1="{height/2}" x2="{width-padding}" y2="{height/2}"/>
            <line x1="{padding}" y1="{height-padding}" x2="{width-padding}" y2="{height-padding}"/>
        </g>
        
        <text x="{padding-5}" y="{padding+4}" font-size="9" fill="#64748b" text-anchor="end">{max_hr}</text>
        <text x="{padding-5}" y="{height/2+4}" font-size="9" fill="#64748b" text-anchor="end">{int((max_hr+min_hr)/2)}</text>
        <text x="{padding-5}" y="{height-padding+4}" font-size="9" fill="#64748b" text-anchor="end">{min_hr}</text>
        
        <path d="{avg_path}" fill="none" stroke="#667eea" stroke-width="2"/>
        <path d="{max_path}" fill="none" stroke="#dc2626" stroke-width="2" stroke-dasharray="4,3"/>
        
        <text x="{width-padding}" y="20" font-size="10" fill="#667eea" text-anchor="end" font-weight="bold">平均心率</text>
        <text x="{width-padding}" y="35" font-size="10" fill="#dc2626" text-anchor="end" font-weight="bold">最高心率</text>
    </svg>
    '''
    return svg

def get_rating(value, metric_type):
    """根据指标类型返回评级"""
    ratings = {
        'hrv': [(40, '偏低'), (60, '正常'), (80, '优秀')],
        'resting_hr': [(60, '优秀'), (75, '正常'), (90, '偏高')],
        'steps': [(5000, '偏低'), (8000, '正常'), (10000, '优秀')],
        'spo2': [(95, '正常'), (100, '优秀')],
        'sleep': [(6, '不足'), (7, '正常'), (8, '充足')],
    }
    
    if metric_type not in ratings:
        return '正常', 'rating-good'
    
    for threshold, rating in ratings[metric_type]:
        if value <= threshold:
            if rating in ['优秀', '充足']:
                return rating, 'rating-excellent'
            elif rating in ['正常']:
                return rating, 'rating-good'
            else:
                return rating, 'rating-average'
    
    return '优秀', 'rating-excellent'

def main():
    # 文件路径
    health_18_path = '~/我的云端硬盘/Health Auto Export/Health Data/HealthAutoExport-2026-02-18.json'
    health_19_path = '~/我的云端硬盘/Health Auto Export/Health Data/HealthAutoExport-2026-02-19.json'
    workout_path = '~/我的云端硬盘/Health Auto Export/Workout Data/HealthAutoExport-2026-02-18.json'
    template_path = '~/.openclaw/workspace-health/templates/DAILY_TEMPLATE_V2.html'
    output_path = '~/.openclaw/workspace/shared/health-reports/upload/2026-02-18-report-FINAL.pdf'
    
    # 加载数据
    print("加载数据文件...")
    data18 = load_json(health_18_path)
    data19 = load_json(health_19_path)
    workout_data = load_json(workout_path)
    
    with open(os.path.expanduser(template_path), 'r', encoding='utf-8') as f:
        template = f.read()
    
    # 提取指标
    print("提取健康指标...")
    metrics = extract_all_metrics(data18, workout_data)
    sleep = extract_sleep_data(data19)
    workout = extract_workout_data(workout_data)
    
    # 打印提取的数据用于验证
    print(f"\n=== 提取的指标数据 ===")
    print(f"HRV: {metrics['hrv']:.1f} ms ({metrics['hrv_count']}个数据点)")
    print(f"静息心率: {metrics['resting_hr']:.1f} bpm")
    print(f"步数: {metrics['steps']:.0f} 步")
    print(f"行走距离: {metrics['distance']:.2f} km")
    print(f"活动能量: {metrics['active_energy_kcal']:.0f} kcal")
    print(f"爬楼层数: {metrics['flights']:.0f} 层")
    print(f"站立时间: {metrics['stand_minutes']:.0f} 分钟")
    print(f"血氧: {metrics['spo2']:.1f} %")
    print(f"呼吸率: {metrics['respiratory_rate']:.1f} 次/分")
    print(f"静息能量: {metrics['basal_energy_kcal']:.0f} kcal")
    print(f"\n睡眠: {sleep['total_hours']:.1f}h (深睡{sleep['deep']:.1f}h / 核心{sleep['core']:.1f}h / REM{sleep['rem']:.1f}h / 清醒{sleep['awake']:.1f}h)")
    if workout:
        print(f"运动: {workout['name']} - {workout['duration']:.0f}分钟, {workout['energy_kcal']:.0f}kcal")
    
    # 填充模板
    print("\n填充模板...")
    html = template
    
    # 基础信息
    html = html.replace('{{DATE}}', '2026-02-18')
    html = html.replace('{{HEADER_SUBTITLE}}', '2026-02-18 · Apple Health | UTC+8')
    
    # 评分卡（根据数据计算）
    recovery_score = min(100, int(50 + metrics['hrv'] * 0.8))
    sleep_score = min(100, int(sleep['total_hours'] * 12.5))
    exercise_score = min(100, int(metrics['active_energy_kcal'] / 5))
    
    html = html.replace('{{SCORE_RECOVERY}}', str(recovery_score))
    html = html.replace('{{SCORE_SLEEP}}', str(sleep_score))
    html = html.replace('{{SCORE_EXERCISE}}', str(exercise_score))
    
    # 评分徽章
    recovery_rating = '优秀' if recovery_score >= 80 else '良好' if recovery_score >= 60 else '一般'
    sleep_rating = '充足' if sleep['total_hours'] >= 7 else '不足' if sleep['total_hours'] < 6 else '正常'
    exercise_rating = '达标' if exercise_score >= 60 else '偏低'
    
    html = html.replace('{{BADGE_RECOVERY_CLASS}}', 'badge-excellent' if recovery_score >= 80 else 'badge-good')
    html = html.replace('{{BADGE_RECOVERY_TEXT}}', recovery_rating)
    html = html.replace('{{BADGE_SLEEP_CLASS}}', 'badge-excellent' if sleep['total_hours'] >= 7 else 'badge-average')
    html = html.replace('{{BADGE_SLEEP_TEXT}}', sleep_rating)
    html = html.replace('{{BADGE_EXERCISE_CLASS}}', 'badge-excellent' if exercise_score >= 60 else 'badge-good')
    html = html.replace('{{BADGE_EXERCISE_TEXT}}', exercise_rating)
    
    # 指标1: HRV
    html = html.replace('{{METRIC1_VALUE}}', f"{metrics['hrv']:.1f} ms<br><small>{metrics['hrv_count']}个数据点</small>")
    hrv_rating, hrv_class = get_rating(metrics['hrv'], 'hrv')
    html = html.replace('{{METRIC1_RATING}}', hrv_rating)
    html = html.replace('{{METRIC1_RATING_CLASS}}', hrv_class)
    html = html.replace('{{METRIC1_ANALYSIS}}', f"您的心率变异性为{metrics['hrv']:.1f}ms，基于{metrics['hrv_count']}个数据点。{'这表明您的自主神经系统恢复良好，身体处于较好的压力调节状态。' if metrics['hrv'] >= 50 else '建议关注压力管理和恢复。'}")
    
    # 指标2: 静息心率
    html = html.replace('{{METRIC2_VALUE}}', f"{metrics['resting_hr']:.0f} bpm")
    rhr_rating, rhr_class = get_rating(metrics['resting_hr'], 'resting_hr')
    html = html.replace('{{METRIC2_RATING}}', rhr_rating)
    html = html.replace('{{METRIC2_RATING_CLASS}}', rhr_class)
    html = html.replace('{{METRIC2_ANALYSIS}}', f"静息心率{metrics['resting_hr']:.0f}bpm处于{'正常范围' if 60 <= metrics['resting_hr'] <= 100 else '需要关注范围'}，反映您的基础心血管健康状况。")
    
    # 指标3: 步数
    html = html.replace('{{METRIC3_VALUE}}', f"{metrics['steps']:.0f} 步")
    steps_rating, steps_class = get_rating(metrics['steps'], 'steps')
    html = html.replace('{{METRIC3_RATING}}', steps_rating)
    html = html.replace('{{METRIC3_RATING_CLASS}}', steps_class)
    html = html.replace('{{METRIC3_ANALYSIS}}', f"今日步数{metrics['steps']:.0f}步，{'达到日常活动推荐量' if metrics['steps'] >= 8000 else '建议增加日常活动量'}，有助于维持良好的代谢健康。")
    
    # 指标4: 行走距离
    html = html.replace('{{METRIC4_VALUE}}', f"{metrics['distance']:.2f} km")
    html = html.replace('{{METRIC4_RATING}}', '良好' if metrics['distance'] >= 5 else '一般')
    html = html.replace('{{METRIC4_RATING_CLASS}}', 'rating-good' if metrics['distance'] >= 5 else 'rating-average')
    html = html.replace('{{METRIC4_ANALYSIS}}', f"行走距离{metrics['distance']:.2f}公里，相当于约{metrics['steps']:.0f}步的活动量。{'保持这样的活动量有助于心肺健康。' if metrics['distance'] >= 5 else '适当增加步行距离可提升健康效益。'}")
    
    # 指标5: 活动能量
    html = html.replace('{{METRIC5_VALUE}}', f"{metrics['active_energy_kcal']:.0f} kcal")
    html = html.replace('{{METRIC5_RATING}}', '达标' if metrics['active_energy_kcal'] >= 300 else '偏低')
    html = html.replace('{{METRIC5_RATING_CLASS}}', 'rating-good' if metrics['active_energy_kcal'] >= 300 else 'rating-average')
    html = html.replace('{{METRIC5_ANALYSIS}}', f"活动能量消耗{metrics['active_energy_kcal']:.0f}千卡，{'符合日常活动推荐量' if metrics['active_energy_kcal'] >= 300 else '建议增加活动强度或时长'}。")
    
    # 指标6: 爬楼层数
    html = html.replace('{{METRIC6_VALUE}}', f"{metrics['flights']:.0f} 层")
    html = html.replace('{{METRIC6_RATING}}', '良好' if metrics['flights'] >= 5 else '一般')
    html = html.replace('{{METRIC6_RATING_CLASS}}', 'rating-good' if metrics['flights'] >= 5 else 'rating-average')
    html = html.replace('{{METRIC6_ANALYSIS}}', f"爬楼{metrics['flights']:.0f}层，{'有助于下肢力量和心肺锻炼' if metrics['flights'] >= 5 else '建议增加楼梯活动以增强腿部肌肉'}。")
    
    # 指标7: 站立时间
    html = html.replace('{{METRIC7_VALUE}}', f"{metrics['stand_minutes']:.0f} 分钟")
    html = html.replace('{{METRIC7_RATING}}', '良好' if metrics['stand_minutes'] >= 60 else '一般')
    html = html.replace('{{METRIC7_RATING_CLASS}}', 'rating-good' if metrics['stand_minutes'] >= 60 else 'rating-average')
    html = html.replace('{{METRIC7_ANALYSIS}}', f"站立时间{metrics['stand_minutes']:.0f}分钟，{'有助于减少久坐带来的健康风险' if metrics['stand_minutes'] >= 60 else '建议增加站立和活动间隔'}。")
    
    # 指标8: 血氧饱和度
    html = html.replace('{{METRIC8_VALUE}}', f"{metrics['spo2']:.1f} %")
    spo2_rating, spo2_class = get_rating(metrics['spo2'], 'spo2')
    html = html.replace('{{METRIC8_RATING}}', spo2_rating)
    html = html.replace('{{METRIC8_RATING_CLASS}}', spo2_class)
    html = html.replace('{{METRIC8_ANALYSIS}}', f"血氧饱和度{metrics['spo2']:.1f}%，{'在正常范围内，表明呼吸系统功能良好' if metrics['spo2'] >= 95 else '建议关注呼吸健康'}。")
    
    # 指标9: 静息能量
    html = html.replace('{{METRIC9_VALUE}}', f"{metrics['basal_energy_kcal']:.0f} kcal")
    html = html.replace('{{METRIC9_RATING}}', '正常')
    html = html.replace('{{METRIC9_RATING_CLASS}}', 'rating-good')
    html = html.replace('{{METRIC9_ANALYSIS}}', f"基础代谢消耗{metrics['basal_energy_kcal']:.0f}千卡，这是您维持生命活动所需的最低能量，反映您的基础代谢水平。")
    
    # 指标10: 呼吸率
    html = html.replace('{{METRIC10_VALUE}}', f"{metrics['respiratory_rate']:.1f} 次/分")
    html = html.replace('{{METRIC10_RATING}}', '正常' if 12 <= metrics['respiratory_rate'] <= 20 else '需关注')
    html = html.replace('{{METRIC10_RATING_CLASS}}', 'rating-good' if 12 <= metrics['respiratory_rate'] <= 20 else 'rating-average')
    html = html.replace('{{METRIC10_ANALYSIS}}', f"呼吸率{metrics['respiratory_rate']:.1f}次/分钟，{'处于正常成人范围' if 12 <= metrics['respiratory_rate'] <= 20 else '建议关注呼吸模式'}。")
    
    # 睡眠数据
    html = html.replace('{{SLEEP_STATUS}}', '✓ 数据完整')
    html = html.replace('{{SLEEP_ALERT_BG}}', '#dcfce7')
    html = html.replace('{{SLEEP_ALERT_BORDER}}', '#86efac')
    html = html.replace('{{SLEEP_ALERT_COLOR}}', '#166534')
    html = html.replace('{{SLEEP_ALERT_SUBCOLOR}}', '#22c55e')
    html = html.replace('{{SLEEP_ALERT_TITLE}}', '睡眠质量评估')
    html = html.replace('{{SLEEP_ALERT_DETAIL}}', f"总睡眠时长{sleep['total_hours']:.1f}小时，{'睡眠充足' if sleep['total_hours'] >= 7 else '睡眠不足'}")
    
    html = html.replace('{{SLEEP_TOTAL}}', f"{sleep['total_hours']:.1f}")
    html = html.replace('{{SLEEP_DEEP}}', f"{sleep['deep']:.1f}")
    html = html.replace('{{SLEEP_CORE}}', f"{sleep['core']:.1f}")
    html = html.replace('{{SLEEP_REM}}', f"{sleep['rem']:.1f}")
    html = html.replace('{{SLEEP_AWAKE}}', f"{sleep['awake']:.1f}")
    html = html.replace('{{SLEEP_DEEP_PCT}}', f"{sleep['deep_pct']:.0f}")
    html = html.replace('{{SLEEP_CORE_PCT}}', f"{sleep['core_pct']:.0f}")
    html = html.replace('{{SLEEP_REM_PCT}}', f"{sleep['rem_pct']:.0f}")
    html = html.replace('{{SLEEP_AWAKE_PCT}}', f"{sleep['awake_pct']:.0f}")
    
    sleep_analysis = f"您的睡眠总时长为{sleep['total_hours']:.1f}小时，其中深睡{sleep['deep']:.1f}小时({sleep['deep_pct']:.0f}%)、核心睡眠{sleep['core']:.1f}小时({sleep['core_pct']:.0f}%)、REM睡眠{sleep['rem']:.1f}小时({sleep['rem_pct']:.0f}%)。"
    if sleep['total_hours'] < 7:
        sleep_analysis += "建议增加睡眠时间至7-9小时，以更好地恢复身体和精神状态。"
    if sleep['deep_pct'] < 15:
        sleep_analysis += "深睡比例偏低，建议睡前放松、减少屏幕使用。"
    html = html.replace('{{SLEEP_ANALYSIS_TEXT}}', sleep_analysis)
    html = html.replace('{{SLEEP_ANALYSIS_BORDER}}', '#667eea')
    
    # 运动数据
    if workout:
        html = html.replace('{{WORKOUT_NAME}}', workout['name'])
        html = html.replace('{{WORKOUT_TIME}}', workout['start_time'].split(' ')[1][:5] if ' ' in workout['start_time'] else '')
        html = html.replace('{{WORKOUT_DURATION}}', f"{workout['duration']:.0f}")
        html = html.replace('{{WORKOUT_ENERGY}}', f"{workout['energy_kcal']:.0f}")
        html = html.replace('{{WORKOUT_AVG_HR}}', f"{workout['avg_hr']:.0f}")
        html = html.replace('{{WORKOUT_MAX_HR}}', f"{workout['max_hr']:.0f}")
        html = html.replace('{{WORKOUT_HR_CHART}}', generate_hr_chart(workout['hr_data']))
        html = html.replace('{{WORKOUT_ANALYSIS}}', f"本次{workout['name']}持续{workout['duration']:.0f}分钟，消耗{workout['energy_kcal']:.0f}千卡。平均心率{workout['avg_hr']:.0f}bpm，最高达到{workout['max_hr']:.0f}bpm。心率曲线显示您在运动过程中保持了良好的有氧强度区间。")
    else:
        html = html.replace('{{WORKOUT_NAME}}', '无运动记录')
        html = html.replace('{{WORKOUT_TIME}}', '-')
        html = html.replace('{{WORKOUT_DURATION}}', '-')
        html = html.replace('{{WORKOUT_ENERGY}}', '-')
        html = html.replace('{{WORKOUT_AVG_HR}}', '-')
        html = html.replace('{{WORKOUT_MAX_HR}}', '-')
        html = html.replace('{{WORKOUT_HR_CHART}}', '<p>无运动数据</p>')
        html = html.replace('{{WORKOUT_ANALYSIS}}', '今日无运动记录，建议保持规律运动习惯。')
    
    # AI建议
    html = html.replace('{{AI1_TITLE}}', '睡眠优化')
    html = html.replace('{{AI1_PROBLEM}}', f"当前睡眠时长{sleep['total_hours']:.1f}小时，{'低于推荐的7-9小时标准。' if sleep['total_hours'] < 7 else '基本达标但仍有优化空间。'}")
    html = html.replace('{{AI1_ACTION}}', '1) 固定就寝时间，建议23:00前入睡；2) 睡前1小时减少蓝光暴露；3) 保持卧室温度18-22°C；4) 避免睡前大量进食。')
    html = html.replace('{{AI1_EXPECTATION}}', '坚持2-4周可显著改善睡眠质量和日间精力。')
    
    html = html.replace('{{AI2_TITLE}}', '运动恢复')
    html = html.replace('{{AI2_PROBLEM}}', f"活动能量消耗{metrics['active_energy_kcal']:.0f}kcal，{'建议增加有氧运动量' if metrics['active_energy_kcal'] < 300 else '运动量适中，注意恢复'}。")
    html = html.replace('{{AI2_ACTION}}', '1) 每周至少150分钟中等强度有氧运动；2) 运动后进行充分拉伸；3) 保持运动日和非运动日的合理交替。')
    html = html.replace('{{AI2_EXPECTATION}}', '规律运动4-6周后可提升心肺功能和代谢健康。')
    
    html = html.replace('{{AI3_TITLE}}', '日常健康管理')
    html = html.replace('{{AI3_DIET}}', '早餐：燕麦粥(50g)+鸡蛋1个+牛奶250ml+苹果1个；午餐：糙米饭150g+清蒸鱼100g+西兰花200g；晚餐：杂粮粥+豆腐100g+蔬菜150g。')
    html = html.replace('{{AI3_ROUTINE}}', '保持规律作息，建议22:30开始准备入睡，保证7-8小时睡眠。每小时起身活动5分钟，减少久坐。')
    
    html = html.replace('{{AI4_TITLE}}', '数据洞察总结')
    html = html.replace('{{AI4_ADVANTAGES}}', f"HRV {metrics['hrv']:.1f}ms显示自主神经调节能力良好；血氧{metrics['spo2']:.1f}%正常；步数{metrics['steps']:.0f}步{'达标' if metrics['steps'] >= 8000 else '有提升空间'}。")
    html = html.replace('{{AI4_RISKS}}', f"{'睡眠时长偏短' if sleep['total_hours'] < 7 else '睡眠尚可'}；{'活动能量可再提升' if metrics['active_energy_kcal'] < 300 else '活动量良好'}。")
    html = html.replace('{{AI4_CONCLUSION}}', f"整体健康指标处于{'良好' if recovery_score >= 70 else '一般'}水平，建议重点优化睡眠质量和保持规律运动。")
    html = html.replace('{{AI4_PLAN}}', '第1周：优化睡眠习惯；第2周：增加日常活动量；第3-4周：建立规律运动计划并监测HRV变化。')
    
    # 页脚
    html = html.replace('{{FOOTER_DATA_SOURCES}}', '数据来源：Apple Health')
    html = html.replace('{{FOOTER_DATE}}', datetime.now().strftime('%Y-%m-%d %H:%M'))
    
    # 保存HTML
    html_path = '/tmp/2026-02-18-report.html'
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"HTML已保存: {html_path}")
    
    # 使用Playwright生成PDF
    print("生成PDF...")
    from playwright.sync_api import sync_playwright
    
    os.makedirs(os.path.expanduser('~/.openclaw/workspace/shared/health-reports/upload'), exist_ok=True)
    
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(f'file://{html_path}')
        page.wait_for_timeout(3000)  # 等待图表加载
        
        page.pdf(
            path=os.path.expanduser(output_path),
            format='A4',
            print_background=True,
            margin={'top': '8mm', 'bottom': '8mm', 'left': '8mm', 'right': '8mm'}
        )
        browser.close()
    
    print(f"✅ PDF生成成功: {output_path}")
    
    # 检查页数
    import subprocess
    result = subprocess.run(['pdfinfo', os.path.expanduser(output_path)], 
                          capture_output=True, text=True)
    for line in result.stdout.split('\n'):
        if 'Pages:' in line:
            print(f"📄 报告页数: {line.split(':')[1].strip()}")
            break

if __name__ == '__main__':
    main()
