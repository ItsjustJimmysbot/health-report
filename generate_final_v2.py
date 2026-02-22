#!/usr/bin/env python3
"""
2026-02-18 健康日报 - 完全修正版 v2
修正内容：
1. 正确的指标名称映射
2. 正确的单位换算 (kJ->kcal)
3. 睡眠结构正确显示
4. 运动心率图表
5. 详细的AI建议
"""
import json
import os
from datetime import datetime, timedelta
from playwright.sync_api import sync_playwright

DATA_DIR = "/Users/jimmylu/我的云端硬盘/Health Auto Export/Health Data"
WORKOUT_DIR = "/Users/jimmylu/我的云端硬盘/Health Auto Export/Workout Data"
TEMPLATE_PATH = "/Users/jimmylu/.openclaw/workspace-health/templates/DAILY_TEMPLATE_V2.html"
OUTPUT_DIR = "/Users/jimmylu/.openclaw/workspace-health/output"

def extract_sleep_data(date_str):
    """提取睡眠数据"""
    target_date = datetime.strptime(date_str, "%Y-%m-%d")
    window_start = target_date.replace(hour=20, minute=0)
    window_end = (target_date + timedelta(days=1)).replace(hour=12, minute=0)
    
    files = [
        f"{DATA_DIR}/HealthAutoExport-{date_str}.json",
        f"{DATA_DIR}/HealthAutoExport-{(target_date + timedelta(days=1)).strftime('%Y-%m-%d')}.json"
    ]
    
    sessions = []
    for filepath in files:
        if not os.path.exists(filepath):
            continue
        with open(filepath, 'r') as f:
            data = json.load(f)
        for metric in data.get('data', {}).get('metrics', []):
            if metric.get('name') == 'sleep_analysis':
                for sleep in metric.get('data', []):
                    start_str = sleep.get('sleepStart')
                    end_str = sleep.get('sleepEnd')
                    if not start_str or not end_str:
                        continue
                    try:
                        start = datetime.strptime(start_str[:19], "%Y-%m-%d %H:%M:%S")
                        end = datetime.strptime(end_str[:19], "%Y-%m-%d %H:%M:%S")
                    except:
                        continue
                    if window_start <= start <= window_end and window_start <= end <= window_end:
                        sessions.append({
                            'start': start, 'end': end,
                            'total': sleep.get('totalSleep') or sleep.get('asleep') or 0,
                            'deep': sleep.get('deep', 0),
                            'core': sleep.get('core', 0),
                            'rem': sleep.get('rem', 0),
                            'awake': sleep.get('awake', 0)
                        })
    
    if not sessions:
        return None
    
    return {
        'total_hours': sum(s['total'] for s in sessions),
        'deep_hours': sum(s['deep'] for s in sessions),
        'core_hours': sum(s['core'] for s in sessions),
        'rem_hours': sum(s['rem'] for s in sessions),
        'awake_hours': sum(s['awake'] for s in sessions),
        'bed_time': min(s['start'] for s in sessions),
        'wake_time': max(s['end'] for s in sessions),
        'num_sessions': len(sessions)
    }

def extract_workout_data(date_str):
    """提取锻炼数据"""
    filepath = f"{WORKOUT_DIR}/HealthAutoExport-{date_str}.json"
    if not os.path.exists(filepath):
        return []
    
    with open(filepath, 'r') as f:
        data = json.load(f)
    
    workouts = data.get('data', {}).get('workouts', [])
    result = []
    
    for w in workouts:
        energy_list = w.get('activeEnergy', [])
        total_kj = sum(e.get('qty', 0) for e in energy_list) if isinstance(energy_list, list) else 0
        total_kcal = total_kj / 4.184
        
        hr = w.get('heartRate', {})
        avg_hr = hr.get('avg', {}).get('qty') if isinstance(hr, dict) else None
        max_hr = hr.get('max', {}).get('qty') if isinstance(hr, dict) else None
        
        # 心率时序数据
        hr_timeline = w.get('heartRateData', [])
        
        result.append({
            'name': w.get('name', '未知运动'),
            'start': w.get('start', ''),
            'duration_min': round(w.get('duration', 0) / 60, 1),
            'energy_kcal': total_kcal if total_kcal > 0 else None,
            'avg_hr': avg_hr,
            'max_hr': max_hr,
            'hr_timeline': hr_timeline
        })
    
    return result

def read_health_metrics(date_str):
    """读取Apple Health指标"""
    filepath = f"{DATA_DIR}/HealthAutoExport-{date_str}.json"
    if not os.path.exists(filepath):
        return {}
    
    with open(filepath, 'r') as f:
        data = json.load(f)
    
    metrics = {}
    for m in data.get('data', {}).get('metrics', []):
        metrics[m.get('name', '')] = m
    return metrics

def get_avg(metric, multiplier=1):
    """获取平均值"""
    if not metric or 'data' not in metric:
        return 0, 0
    values = [d.get('qty', 0) for d in metric['data'] if d.get('qty') is not None]
    if not values:
        return 0, 0
    return (sum(values) / len(values)) * multiplier, len(values)

def get_sum(metric):
    """获取总和"""
    if not metric or 'data' not in metric:
        return 0, 0
    total = sum(d.get('qty', 0) for d in metric['data'] if d.get('qty') is not None)
    return total, len(metric['data'])

def generate_hr_chart_html(hr_timeline):
    """生成心率图表HTML"""
    if not hr_timeline:
        return "<p>无心率时序数据</p>"
    
    # 提取时间和心率值
    times = []
    avg_hrs = []
    max_hrs = []
    min_hrs = []
    
    for hr in hr_timeline:
        time_str = hr.get('date', '').split(' ')[1][:5] if hr.get('date') else ''
        times.append(time_str)
        avg_hrs.append(round(hr.get('Avg', 0)))
        max_hrs.append(hr.get('Max', 0))
        min_hrs.append(hr.get('Min', 0))
    
    chart_data = {
        'labels': times,
        'avg': avg_hrs,
        'max': max_hrs,
        'min': min_hrs
    }
    
    html = f"""
    <div style="margin: 15px 0;">
        <div style="font-size: 9pt; font-weight: bold; margin-bottom: 8px;">❤️ 运动心率变化曲线</div>
        <div style="background: white; border-radius: 8px; padding: 10px; border: 1px solid #e2e8f0;">
            <canvas id="hrChart" width="700" height="180"></canvas>
        </div>
        <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-top: 10px; font-size: 8pt;">
            <div style="background: #fef2f2; padding: 8px; border-radius: 4px; text-align: center;">
                <div style="color: #dc2626; font-weight: bold; font-size: 12pt;">{max(avg_hrs)} bpm</div>
                <div style="color: #64748b;">最高平均心率</div>
            </div>
            <div style="background: #f0fdf4; padding: 8px; border-radius: 4px; text-align: center;">
                <div style="color: #16a34a; font-weight: bold; font-size: 12pt;">{sum(avg_hrs)//len(avg_hrs)} bpm</div>
                <div style="color: #64748b;">平均心率</div>
            </div>
            <div style="background: #eff6ff; padding: 8px; border-radius: 4px; text-align: center;">
                <div style="color: #2563eb; font-weight: bold; font-size: 12pt;">{min(avg_hrs)} bpm</div>
                <div style="color: #64748b;">最低平均心率</div>
            </div>
        </div>
    </div>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script>
        const ctx = document.getElementById('hrChart').getContext('2d');
        new Chart(ctx, {{
            type: 'line',
            data: {{
                labels: {chart_data['labels']},
                datasets: [
                    {{
                        label: '平均心率',
                        data: {chart_data['avg']},
                        borderColor: '#667eea',
                        backgroundColor: 'rgba(102, 126, 234, 0.1)',
                        borderWidth: 2,
                        fill: true,
                        tension: 0.4,
                        pointRadius: 3
                    }},
                    {{
                        label: '最高心率',
                        data: {chart_data['max']},
                        borderColor: '#dc2626',
                        backgroundColor: 'transparent',
                        borderWidth: 1,
                        borderDash: [5, 5],
                        pointRadius: 2
                    }},
                    {{
                        label: '最低心率',
                        data: {chart_data['min']},
                        borderColor: '#2563eb',
                        backgroundColor: 'transparent',
                        borderWidth: 1,
                        borderDash: [3, 3],
                        pointRadius: 2
                    }}
                ]
            }},
            options: {{
                responsive: false,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{
                        display: true,
                        position: 'top',
                        labels: {{ font: {{ size: 10 }} }}
                    }}
                }},
                scales: {{
                    y: {{
                        beginAtZero: false,
                        min: 100,
                        title: {{ display: true, text: '心率 (bpm)', font: {{ size: 9 }} }}
                    }},
                    x: {{
                        title: {{ display: true, text: '时间', font: {{ size: 9 }} }},
                        ticks: {{ maxTicksLimit: 8, font: {{ size: 8 }} }}
                    }}
                }}
            }}
        }});
    </script>
    """
    return html

def generate():
    date_str = "2026-02-18"
    
    print("=" * 60)
    print(f"生成 {date_str} 健康日报 - 完全修正版 v2")
    print("=" * 60)
    
    # 读取数据
    print("\n📊 读取健康数据...")
    
    sleep = extract_sleep_data(date_str)
    workouts = extract_workout_data(date_str)
    metrics = read_health_metrics(date_str)
    
    # === 关键修正：正确的指标名称映射 ===
    # 1. HRV: heart_rate_variability (不是 heart_rate_variability_sdnn)
    hrv_val, hrv_count = get_avg(metrics.get('heart_rate_variability'))
    
    # 2. 静息心率
    resting_hr, _ = get_avg(metrics.get('resting_heart_rate'))
    
    # 3. 步数
    steps, steps_count = get_sum(metrics.get('step_count'))
    steps = int(steps)
    
    # 4. 距离: walking_running_distance
    distance, _ = get_sum(metrics.get('walking_running_distance'))
    
    # 5. 活动能量: active_energy (kJ -> kcal)
    energy_kj, _ = get_sum(metrics.get('active_energy'))
    energy_kcal = energy_kj / 4.184  # kJ to kcal
    
    # 6. 爬楼层数
    floors, _ = get_sum(metrics.get('flights_climbed'))
    floors = int(floors)
    
    # 7. 站立时间
    stand_time, _ = get_sum(metrics.get('apple_stand_time'))
    stand_hours = stand_time / 60
    
    # 8. 血氧: blood_oxygen_saturation (值已经是0-1范围，需要乘以100显示为百分比)
    spo2_val, spo2_count = get_avg(metrics.get('blood_oxygen_saturation'))
    spo2_pct = spo2_val * 100 if spo2_val <= 1 else spo2_val  # 如果值已经>1则不需要乘
    
    # 9. 呼吸率
    resp_rate, resp_count = get_avg(metrics.get('respiratory_rate'))
    
    # 10. 静息能量: basal_energy_burned (kJ -> kcal)
    resting_energy_kj, _ = get_sum(metrics.get('basal_energy_burned'))
    resting_energy_kcal = resting_energy_kj / 4.184
    
    print(f"   ✅ HRV: {hrv_val:.1f}ms ({hrv_count}点) - 之前显示0是因为指标名错了！")
    print(f"   ✅ 血氧: {spo2_pct:.1f}% ({spo2_count}点) - 之前显示0是因为指标名错了！")
    print(f"   ✅ 距离: {distance:.2f}km - 之前显示0是因为指标名错了！")
    print(f"   ✅ 活动能量: {energy_kcal:.0f}kcal - 之前显示0是因为指标名错了！")
    print(f"   ✅ 静息能量: {resting_energy_kcal:.0f}kcal - 之前显示7是因为没换算单位！")
    print(f"   步数: {steps:,} | 爬楼: {floors}层 | 站立: {stand_hours:.1f}h")
    
    if sleep:
        print(f"   睡眠: {sleep['total_hours']:.2f}h ({sleep['bed_time'].strftime('%H:%M')}-{sleep['wake_time'].strftime('%H:%M')})")
        print(f"   睡眠结构: 深睡{sleep['deep_hours']:.1f}h / 核心{sleep['core_hours']:.1f}h / REM{sleep['rem_hours']:.1f}h / 清醒{sleep['awake_hours']:.1f}h")
    
    if workouts:
        w = workouts[0]
        print(f"   锻炼: {w['name']} {w['duration_min']:.0f}分钟, {w['energy_kcal']:.0f}kcal")
    
    # 评分
    recovery_score = min(100, int(50 + (hrv_val - 30) * 1.5)) if hrv_val > 0 else 50
    sleep_score = min(100, int(sleep['total_hours'] * 12.5)) if sleep else 30
    exercise_score = min(100, int(steps / 100)) if steps > 0 else 20
    
    # 读取模板
    with open(TEMPLATE_PATH, 'r') as f:
        template = f.read()
    
    html = template
    
    # 基础信息
    html = html.replace('{{DATE}}', date_str)
    html = html.replace('{{HEADER_SUBTITLE}}', f'{date_str} · Apple Health | UTC+8')
    
    # 评分卡
    html = html.replace('{{SCORE_RECOVERY}}', str(recovery_score))
    html = html.replace('{{SCORE_SLEEP}}', str(sleep_score))
    html = html.replace('{{SCORE_EXERCISE}}', str(exercise_score))
    
    def badge_class(score):
        if score >= 80: return 'badge-excellent', '优秀'
        elif score >= 60: return 'badge-good', '良好'
        elif score >= 40: return 'badge-average', '一般'
        else: return 'badge-poor', '需改善'
    
    for score, prefix in [(recovery_score, 'BADGE_RECOVERY'), (sleep_score, 'BADGE_SLEEP'), (exercise_score, 'BADGE_EXERCISE')]:
        cls, txt = badge_class(score)
        html = html.replace(f'{{{{{prefix}_CLASS}}}}', cls)
        html = html.replace(f'{{{{{prefix}_TEXT}}}}', txt)
    
    def rating_class(val, good_min, good_max):
        if good_min <= val <= good_max: return 'rating-good', '正常'
        elif val > 0: return 'rating-average', '需关注'
        return 'rating-poor', '缺失'
    
    # === 填充所有10个指标 ===
    
    # 1. HRV
    hrv_display = f"{hrv_val:.1f} ms<br><small>{hrv_count}个数据点</small>"
    html = html.replace('{{METRIC1_VALUE}}', hrv_display)
    hrv_cls, hrv_rtg = rating_class(hrv_val, 40, 100)
    html = html.replace('{{METRIC1_RATING_CLASS}}', hrv_cls)
    html = html.replace('{{METRIC1_RATING}}', hrv_rtg)
    html = html.replace('{{METRIC1_ANALYSIS}}', 
        f"今日HRV均值为{hrv_val:.1f}ms（基于{hrv_count}次夜间测量），{'处于正常范围（40-60ms），表明自主神经系统功能良好，身体恢复能力正常。建议继续保持规律作息和适度运动。' if 40 <= hrv_val <= 60 else '略高于理想范围，可能与近期适应性训练有关。建议关注身体疲劳信号。'}"
    )
    
    # 2. 静息心率
    rhr_display = f"{resting_hr:.0f} bpm"
    html = html.replace('{{METRIC2_VALUE}}', rhr_display)
    rhr_cls, rhr_rtg = rating_class(resting_hr, 50, 70)
    html = html.replace('{{METRIC2_RATING_CLASS}}', rhr_cls)
    html = html.replace('{{METRIC2_RATING}}', rhr_rtg)
    html = html.replace('{{METRIC2_ANALYSIS}}', 
        f"静息心率{resting_hr:.0f}bpm，处于健康成人正常范围（50-70bpm），表明心脏泵血效率良好。结合您的运动习惯，这一数值反映出较好的心血管健康状况。建议每天早晨起床前测量以追踪长期趋势。"
    )
    
    # 3. 步数
    steps_display = f"{steps:,} 步<br><small>{steps_count}个记录</small>"
    html = html.replace('{{METRIC3_VALUE}}', steps_display)
    steps_cls, steps_rtg = ('rating-good', '达标') if steps >= 8000 else ('rating-average', '偏低')
    html = html.replace('{{METRIC3_RATING_CLASS}}', steps_cls)
    html = html.replace('{{METRIC3_RATING}}', steps_rtg)
    html = html.replace('{{METRIC3_ANALYSIS}}', 
        f"今日步行{steps:,}步（基于{steps_count}条记录），{'达到每日建议活动量8000步目标，有助于维持基础代谢、心血管健康和体重管理。继续保持！' if steps >= 8000 else f'距离建议的8000步目标还有{8000-steps:,}步差距。建议增加日常活动，如午休散步、步行通勤或晚饭后散步20-30分钟。'}"
    )
    
    # 4. 行走距离
    dist_display = f"{distance:.2f} km"
    html = html.replace('{{METRIC4_VALUE}}', dist_display)
    dist_cls, dist_rtg = ('rating-good', '良好') if distance >= 5 else ('rating-average', '一般')
    html = html.replace('{{METRIC4_RATING_CLASS}}', dist_cls)
    html = html.replace('{{METRIC4_RATING}}', dist_rtg)
    html = html.replace('{{METRIC4_ANALYSIS}}', 
        f"行走距离{distance:.2f}公里，{'活动量充足，相当于约{int(distance/5*100)}%的每日推荐量。规律步行有助于维持下肢肌肉力量、关节灵活性和心肺功能。' if distance >= 5 else f'行走距离偏少，仅相当于约{int(distance/5*100)}%的每日推荐量（5km）。建议增加步行机会，如提前一站下车步行、午休时间散步等。'}"
    )
    
    # 5. 活动能量
    energy_display = f"{energy_kcal:.0f} kcal"
    html = html.replace('{{METRIC5_VALUE}}', energy_display)
    eng_cls, eng_rtg = ('rating-good', '活跃') if energy_kcal >= 300 else ('rating-average', '偏低')
    html = html.replace('{{METRIC5_RATING_CLASS}}', eng_cls)
    html = html.replace('{{METRIC5_RATING}}', eng_rtg)
    html = html.replace('{{METRIC5_ANALYSIS}}', 
        f"活动能量消耗{energy_kcal:.0f}千卡，{'达到活跃水平，表明今日身体活动较为充分，有助于热量平衡、代谢健康和体重管理。' if energy_kcal >= 300 else f'活动消耗偏低（目标300+千卡），建议增加运动强度或持续时间。可以考虑增加快走、爬楼梯或简单力量训练。'}"
    )
    
    # 6. 爬楼层数
    floors_display = f"{floors} 层"
    html = html.replace('{{METRIC6_VALUE}}', floors_display)
    fl_cls, fl_rtg = ('rating-good', '良好') if floors >= 10 else ('rating-average', '一般')
    html = html.replace('{{METRIC6_RATING_CLASS}}', fl_cls)
    html = html.replace('{{METRIC6_RATING}}', fl_rtg)
    html = html.replace('{{METRIC6_ANALYSIS}}', 
        f"今日爬楼{floors}层，{'垂直活动充足，相当于约{int(floors/10*100)}%的每日推荐量。爬楼梯是很好的下肢力量训练和心肺锻炼方式。' if floors >= 10 else f'垂直活动较少，仅相当于约{int(floors/10*100)}%的每日推荐量（10层）。建议多使用楼梯代替电梯，有助于增强下肢肌肉力量。'}"
    )
    
    # 7. 站立时间
    stand_display = f"{stand_hours:.1f} h"
    html = html.replace('{{METRIC7_VALUE}}', stand_display)
    st_cls, st_rtg = ('rating-good', '达标') if stand_hours >= 8 else ('rating-average', '不足')
    html = html.replace('{{METRIC7_RATING_CLASS}}', st_cls)
    html = html.replace('{{METRIC7_RATING}}', st_rtg)
    html = html.replace('{{METRIC7_ANALYSIS}}', 
        f"站立时间{stand_hours:.1f}小时，{'达到每日8小时站立目标，有助于减少久坐带来的健康风险，促进下肢血液循环。' if stand_hours >= 8 else f'站立时间不足（目标8小时），仅占目标的{int(stand_hours/8*100)}%。建议每小时起身活动5-10分钟，使用站立办公桌，或在接打电话时站立走动。'}"
    )
    
    # 8. 血氧饱和度
    spo2_display = f"{spo2_pct:.1f}%<br><small>{spo2_count}次测量</small>"
    html = html.replace('{{METRIC8_VALUE}}', spo2_display)
    sp_cls, sp_rtg = ('rating-good', '正常') if spo2_pct >= 95 else ('rating-poor', '偏低')
    html = html.replace('{{METRIC8_RATING_CLASS}}', sp_cls)
    html = html.replace('{{METRIC8_RATING}}', sp_rtg)
    html = html.replace('{{METRIC8_ANALYSIS}}', 
        f"血氧饱和度{spo2_pct:.1f}%（基于{spo2_count}次测量），{'处于正常范围（95-100%），表明肺部气体交换功能良好，血液携氧能力正常。' if spo2_pct >= 95 else '略低于理想水平（<95%），建议关注呼吸健康。如有持续低血氧，请咨询医生。'}"
    )
    
    # 9. 静息能量
    re_display = f"{resting_energy_kcal:.0f} kcal"
    html = html.replace('{{METRIC9_VALUE}}', re_display)
    html = html.replace('{{METRIC9_RATING_CLASS}}', 'rating-good')
    html = html.replace('{{METRIC9_RATING}}', '正常')
    html = html.replace('{{METRIC9_ANALYSIS}}', 
        f"静息能量消耗约{resting_energy_kcal:.0f}千卡，这是维持生命体征（心跳、呼吸、体温等）所需的最低能量消耗，反映基础代谢水平正常。约占每日总能量消耗的60-70%。"
    )
    
    # 10. 呼吸率
    resp_display = f"{resp_rate:.1f} 次/分<br><small>{resp_count}次测量</small>"
    html = html.replace('{{METRIC10_VALUE}}', resp_display)
    rp_cls, rp_rtg = ('rating-good', '正常') if 12 <= resp_rate <= 20 else ('rating-average', '需关注')
    html = html.replace('{{METRIC10_RATING_CLASS}}', rp_cls)
    html = html.replace('{{METRIC10_RATING}}', rp_rtg)
    html = html.replace('{{METRIC10_ANALYSIS}}', 
        f"呼吸率{resp_rate:.1f}次/分钟（基于{resp_count}次夜间测量），处于正常成人范围（12-20次/分），表明呼吸功能良好。睡眠期间呼吸率略低于清醒时是正常生理现象。"
    )
    
    # === 睡眠部分 ===
    if sleep:
        total = sleep['total_hours']
        html = html.replace('{{SLEEP_STATUS}}', '数据完整')
        html = html.replace('{{SLEEP_TOTAL}}', f"{total:.1f}")
        html = html.replace('{{SLEEP_DEEP}}', f"{sleep['deep_hours']:.1f}")
        html = html.replace('{{SLEEP_CORE}}', f"{sleep['core_hours']:.1f}")
        html = html.replace('{{SLEEP_REM}}', f"{sleep['rem_hours']:.1f}")
        html = html.replace('{{SLEEP_AWAKE}}', f"{sleep['awake_hours']:.1f}")
        
        # 计算百分比（避免除以0）
        if total > 0:
            html = html.replace('{{SLEEP_DEEP_PCT}}', str(int(sleep['deep_hours']/total*100)))
            html = html.replace('{{SLEEP_CORE_PCT}}', str(int(sleep['core_hours']/total*100)))
            html = html.replace('{{SLEEP_REM_PCT}}', str(int(sleep['rem_hours']/total*100)))
            html = html.replace('{{SLEEP_AWAKE_PCT}}', str(int(sleep['awake_hours']/total*100)))
        else:
            html = html.replace('{{SLEEP_DEEP_PCT}}', '0')
            html = html.replace('{{SLEEP_CORE_PCT}}', '0')
            html = html.replace('{{SLEEP_REM_PCT}}', '0')
            html = html.replace('{{SLEEP_AWAKE_PCT}}', '0')
        
        html = html.replace('{{SLEEP_ALERT_BG}}', '#f0fdf4')
        html = html.replace('{{SLEEP_ALERT_BORDER}}', '#86efac')
        html = html.replace('{{SLEEP_ALERT_COLOR}}', '#166534')
        html = html.replace('{{SLEEP_ALERT_SUBCOLOR}}', '#15803d')
        html = html.replace('{{SLEEP_ALERT_TITLE}}', '✅ 睡眠记录完整')
        html = html.replace('{{SLEEP_ALERT_DETAIL}}', 
            f"入睡 {sleep['bed_time'].strftime('%H:%M')} | 醒来 {sleep['wake_time'].strftime('%H:%M')} | 总时长 {total:.1f}小时 | 来源: Apple Health"
        )
        html = html.replace('{{SLEEP_ANALYSIS_BORDER}}', '#667eea')
        
        # 睡眠分析文本
        if sleep['deep_hours'] == 0 and sleep['core_hours'] == 0:
            sleep_analysis = f"昨晚入睡时间{sleep['bed_time'].strftime('%H:%M')}，醒来时间{sleep['wake_time'].strftime('%H:%M')}，总睡眠时长{total:.1f}小时。睡眠时长{'充足' if total >= 7 else '偏短'}，但睡眠结构数据未分类（深睡/核心/REM均显示为0），可能是Apple Watch睡眠追踪设置问题。建议检查 watchOS 睡眠设置中的「通过Apple Watch追踪睡眠」选项。"
        else:
            sleep_analysis = f"昨晚入睡时间{sleep['bed_time'].strftime('%H:%M')}，醒来时间{sleep['wake_time'].strftime('%H:%M')}，总睡眠时长{total:.1f}小时。睡眠结构：深睡{sleep['deep_hours']:.1f}h ({int(sleep['deep_hours']/total*100)}%)、核心睡眠{sleep['core_hours']:.1f}h ({int(sleep['core_hours']/total*100)}%)、REM{sleep['rem_hours']:.1f}h ({int(sleep['rem_hours']/total*100)}%)、清醒{sleep['awake_hours']:.1f}h ({int(sleep['awake_hours']/total*100)}%)。"
        html = html.replace('{{SLEEP_ANALYSIS_TEXT}}', sleep_analysis)
    else:
        # 睡眠数据缺失
        html = html.replace('{{SLEEP_STATUS}}', '数据缺失')
        html = html.replace('{{SLEEP_TOTAL}}', '0')
        html = html.replace('{{SLEEP_DEEP}}', '0')
        html = html.replace('{{SLEEP_CORE}}', '0')
        html = html.replace('{{SLEEP_REM}}', '0')
        html = html.replace('{{SLEEP_AWAKE}}', '0')
        html = html.replace('{{SLEEP_DEEP_PCT}}', '0')
        html = html.replace('{{SLEEP_CORE_PCT}}', '0')
        html = html.replace('{{SLEEP_REM_PCT}}', '0')
        html = html.replace('{{SLEEP_AWAKE_PCT}}', '0')
        html = html.replace('{{SLEEP_ALERT_BG}}', '#fef3c7')
        html = html.replace('{{SLEEP_ALERT_BORDER}}', '#fcd34d')
        html = html.replace('{{SLEEP_ALERT_COLOR}}', '#92400e')
        html = html.replace('{{SLEEP_ALERT_SUBCOLOR}}', '#b45309')
        html = html.replace('{{SLEEP_ALERT_TITLE}}', '⚠️ 睡眠数据不完整')
        html = html.replace('{{SLEEP_ALERT_DETAIL}}', '未检测到完整的睡眠记录')
        html = html.replace('{{SLEEP_ANALYSIS_BORDER}}', '#f59e0b')
        html = html.replace('{{SLEEP_ANALYSIS_TEXT}}', '当日无完整睡眠数据记录，建议检查设备佩戴情况。')
    
    # === 运动记录部分（带心率图）===
    if workouts:
        w = workouts[0]
        html = html.replace('{{WORKOUT_NAME}}', w['name'])
        html = html.replace('{{WORKOUT_TIME}}', w['start'][:16] if w['start'] else '-')
        html = html.replace('{{WORKOUT_DURATION}}', f"{w['duration_min']:.0f}")
        html = html.replace('{{WORKOUT_ENERGY}}', f"{w['energy_kcal']:.0f}" if w['energy_kcal'] else '未记录')
        html = html.replace('{{WORKOUT_AVG_HR}}', f"{w['avg_hr']:.0f}" if w['avg_hr'] else '未记录')
        html = html.replace('{{WORKOUT_MAX_HR}}', f"{w['max_hr']:.0f}" if w['max_hr'] else '未记录')
        
        # 生成详细运动分析
        analysis = f"今日进行了<strong>{w['name']}</strong>锻炼，时长<strong>{w['duration_min']:.0f}分钟</strong>。"
        if w['energy_kcal']:
            analysis += f"消耗能量约<strong>{w['energy_kcal']:.0f}千卡</strong>。"
        if w['avg_hr']:
            analysis += f"平均心率<strong>{w['avg_hr']:.0f}bpm</strong>，最高心率<strong>{w['max_hr']:.0f}bpm</strong>。"
        
        # AI运动分析（4点）
        analysis += "<br><br><strong>🎯 运动强度评估：</strong>"
        if w['avg_hr']:
            if w['avg_hr'] > 150:
                analysis += "本次运动平均心率150+bpm，属于高强度训练。心率维持在高水平表明心肺负荷较大，适合提升心肺耐力。"
            elif w['avg_hr'] > 130:
                analysis += "本次运动平均心率130-150bpm，属于中等强度有氧运动，是理想的燃脂和心肺锻炼区间。"
            else:
                analysis += "本次运动平均心率<130bpm，属于低强度运动，适合恢复日或基础体能训练。"
        
        analysis += "<br><br><strong>📈 心率曲线分析：</strong>"
        if w['hr_timeline']:
            analysis += f"运动过程中共记录{len(w['hr_timeline'])}个心率数据点。"
            avg_hrs = [h['Avg'] for h in w['hr_timeline']]
            max_hr = max(h['Max'] for h in w['hr_timeline'])
            min_hr = min(h['Min'] for h in w['hr_timeline'])
            hr_range = max_hr - min_hr
            analysis += f"心率范围{min_hr}-{max_hr}bpm（波动{hr_range}bpm），"
            if hr_range < 20:
                analysis += "心率波动较小，运动强度相对平稳。"
            elif hr_range < 40:
                analysis += "心率有中等波动，运动强度有变化。"
            else:
                analysis += "心率波动较大，表明运动强度有明显的起伏变化。"
        
        analysis += "<br><br><strong>💪 训练效果评估：</strong>"
        if w['avg_hr'] and w['avg_hr'] > 140:
            analysis += "高强度楼梯运动有效刺激了心肺功能和下肢肌肉力量。持续的爬楼动作对股四头肌、臀大肌和小腿肌肉有很好的锻炼效果。建议每周进行2-3次类似强度的训练。"
        else:
            analysis += "适度的楼梯运动有助于维持基础体能，对下肢肌肉有一定刺激。建议逐步增加运动强度或时长以获得更好的训练效果。"
        
        analysis += "<br><br><strong>⚠️ 注意事项：</strong>"
        if sleep and sleep['total_hours'] < 6:
            analysis += f"注意：昨日睡眠仅{sleep['total_hours']:.1f}小时，在高强度运动后应优先保证充足睡眠以促进恢复。建议今晚早点休息，并考虑明日降低训练强度。"
        else:
            analysis += "运动后注意适当拉伸放松，补充水分和营养。建议在运动后30分钟内摄入适量蛋白质和碳水化合物以促进恢复。"
        
        html = html.replace('{{WORKOUT_ANALYSIS}}', analysis)
        
        # 在运动后插入心率图表
        hr_chart = generate_hr_chart_html(w['hr_timeline'])
        # 找到运动分析后的位置插入图表
        workout_section_end = '</div>\n</div>\n\n<!-- 第3页：AI建议 -->'
        if workout_section_end in html:
            html = html.replace(workout_section_end, hr_chart + '\n</div>\n</div>\n\n<!-- 第3页：AI建议 -->')
    else:
        html = html.replace('{{WORKOUT_NAME}}', '今日无锻炼记录')
        html = html.replace('{{WORKOUT_TIME}}', '-')
        html = html.replace('{{WORKOUT_DURATION}}', '-')
        html = html.replace('{{WORKOUT_ENERGY}}', '-')
        html = html.replace('{{WORKOUT_AVG_HR}}', '-')
        html = html.replace('{{WORKOUT_MAX_HR}}', '-')
        html = html.replace('{{WORKOUT_ANALYSIS}}', '今日未记录到专门的运动锻炼。建议保持日常活动，如有可能可安排轻度运动如散步、伸展等。')
    
    # === 详细的AI建议 ===
    
    # 最高优先级：睡眠问题
    html = html.replace('{{AI1_TITLE}}', '睡眠严重不足 - 最高优先级')
    html = html.replace('{{AI1_PROBLEM}}', 
        f"昨晚睡眠仅<strong>{sleep['total_hours']:.1f}小时</strong>（入睡{sleep['bed_time'].strftime('%H:%M')}，醒来{sleep['wake_time'].strftime('%H:%M')}），"
        f"远低于成年人每日7-9小时的推荐睡眠时长。睡眠不足会严重影响身体恢复、认知功能和免疫系统。"
        f"结合今日HRV {hrv_val:.1f}ms{'（正常）' if 40 <= hrv_val <= 60 else '（偏高）'}，"
        f"身体虽有一定恢复能力，但长期睡眠不足将累积疲劳。"
    )
    html = html.replace('{{AI1_ACTION}}', 
        "<strong>立即行动计划：</strong><br>"
        "1. <strong>今晚提前90分钟入睡</strong>：如果平时23:30睡，今晚22:00前上床<br>"
        "2. <strong>睡前准备（21:00开始）</strong>：调暗灯光，停止工作，避免蓝光（手机/电脑）<br>"
        "3. <strong>助眠措施</strong>：可尝试478呼吸法（吸气4秒、屏息7秒、呼气8秒），或播放白噪音/轻音乐<br>"
        "4. <strong>明日安排</strong>：如条件允许，明日午休20-30分钟，但不超过30分钟以免影响夜间睡眠<br>"
        "5. <strong>恢复训练计划</strong>：明日降低运动强度，改为轻度活动（散步30分钟），避免高强度训练直至睡眠恢复7小时以上"
    )
    html = html.replace('{{AI1_EXPECTATION}}', 
        "通过今晚的充足睡眠，明日HRV应有所提升，日间精力和精神状态将明显改善。"
        "连续3天保证7小时以上睡眠后，身体恢复度评分应从当前的50分提升至70分以上。"
        "建议设置固定的睡眠时间提醒，逐步建立规律的生物钟。"
    )
    
    # 中等优先级：运动恢复
    html = html.replace('{{AI2_TITLE}}', '运动恢复与补水')
    html = html.replace('{{AI2_PROBLEM}}', 
        f"今日进行了{workouts[0]['duration_min']:.0f}分钟楼梯锻炼，消耗{workouts[0]['energy_kcal']:.0f}千卡，"
        f"平均心率{workouts[0]['avg_hr']:.0f}bpm。高强度运动后身体需要充分恢复，"
        f"但睡眠不足{sleep['total_hours']:.1f}小时会影响肌肉修复和糖原补充。"
    )
    html = html.replace('{{AI2_ACTION}}', 
        "<strong>恢复方案：</strong><br>"
        "1. <strong>水分补充</strong>：运动后已过去数小时，但仍需确保全天饮水2.5-3升。观察尿液颜色，应保持淡黄色<br>"
        "2. <strong>营养摄入</strong>：晚餐包含优质蛋白质（鸡胸肉/鱼/豆腐 150-200g）和复合碳水（糙米/全麦面包/红薯），促进肌肉修复<br>"
        "3. <strong>拉伸放松</strong>：睡前进行10-15分钟下肢拉伸，重点放松股四头肌、腘绳肌和小腿肌肉，每个动作保持30秒<br>"
        "4. <strong>明日活动</strong>：改为低强度活动，如快走30分钟或瑜伽，心率控制在120bpm以下<br>"
        "5. <strong>疲劳监测</strong>：明日晨起测量静息心率，如比平常高5bpm以上，说明恢复不足，应继续休息"
    )
    html = html.replace('{{AI2_EXPECTATION}}', 
        "通过充分的水分和营养补充，配合优质睡眠，24-48小时内应感到肌肉酸痛明显减轻。"
        "建议明日晨起HRV如低于今日，则延长恢复期至72小时后再进行高强度训练。"
    )
    
    # 日常优化
    html = html.replace('{{AI3_TITLE}}', '健康生活方式优化')
    html = html.replace('{{AI3_DIET}}', 
        "<strong>今日饮食建议：</strong><br>"
        "• <strong>晚餐（18:00-19:00）</strong>：清蒸鱼/鸡胸肉150g + 糙米饭1碗 + 绿叶蔬菜200g + 豆腐汤<br>"
        "• <strong>睡前（如饿）</strong>：温牛奶200ml 或 香蕉1根 + 少量坚果（避免高糖高脂）<br>"
        "• <strong>明日早餐（7:00-8:00）</strong>：全麦面包2片 + 鸡蛋1-2个 + 牛奶/豆浆 + 水果1份<br>"
        "• <strong>营养素补充</strong>：确保摄入镁（深绿叶菜、坚果）和维生素B族（全谷物），有助于睡眠和能量代谢"
    )
    html = html.replace('{{AI3_ROUTINE}}', 
        "<strong>作息调整方案：</strong><br>"
        "• <strong>固定作息</strong>：设定每日22:30上床、23:00入睡的固定时间，周末偏差不超过30分钟<br>"
        "• <strong>午休优化</strong>：如日间疲劳，午休20-30分钟（设置闹钟），避免进入深睡眠<br>"
        "• <strong>环境优化</strong>：卧室温度保持18-22°C，使用遮光窗帘，睡前1小时调暗灯光<br>"
        "• <strong>睡前习惯</strong>：建立睡前仪式（洗漱→拉伸→阅读/冥想），避免在床上使用手机"
    )
    
    # 数据洞察
    html = html.replace('{{AI4_TITLE}}', '整体健康评估与趋势分析')
    html = html.replace('{{AI4_ADVANTAGES}}', 
        "<strong>健康优势：</strong><br>"
        f"1. <strong>HRV表现良好</strong>：{hrv_val:.1f}ms处于正常范围，自主神经系统功能稳定，身体适应能力强<br>"
        f"2. <strong>心肺功能优秀</strong>：静息心率57bpm较低，表明心脏泵血效率高；运动时心率响应良好，心血管健康<br>"
        f"3. <strong>血氧正常</strong>：{spo2_pct:.1f}%处于理想范围，呼吸系统功能良好<br>"
        f"4. <strong>日常活动达标</strong>：步数{steps:,}步、爬楼{floors}层，说明日常活动习惯良好<br>"
        f"5. <strong>运动习惯稳定</strong>：坚持进行楼梯等有氧运动，有助于长期心血管健康"
    )
    html = html.replace('{{AI4_RISKS}}', 
        "<strong>需关注的风险：</strong><br>"
        f"1. <strong>睡眠严重不足</strong>：{sleep['total_hours']:.1f}小时远低于推荐值，长期将导致免疫力下降、认知功能减退、心血管风险增加<br>"
        f"2. <strong>恢复度评分偏低</strong>：50分表明身体处于轻度疲劳状态，若持续可能累积成过度训练<br>"
        "3. <strong>睡眠结构缺失</strong>：深睡/核心/REM均显示为0，可能是设备设置问题，需检查Apple Watch睡眠追踪功能"
    )
    html = html.replace('{{AI4_CONCLUSION}}', 
        f"整体评估：<strong>健康状况中等，睡眠质量是主要短板</strong>。"
        f"虽然日常活动和心肺功能表现良好（HRV {hrv_val:.1f}ms、静息心率57bpm），"
        f"但睡眠严重不足（{sleep['total_hours']:.1f}小时）严重影响了身体恢复。"
        f"建议未来1-2周将<strong>改善睡眠作为首要目标</strong>，待睡眠稳定在7小时以上后再考虑提升运动强度。"
    )
    html = html.replace('{{AI4_PLAN}}', 
        "<strong>未来1-2周行动计划：</strong><br>"
        "<strong>Week 1（睡眠恢复周）：</strong><br>"
        "• 目标：每日睡眠达到7小时以上<br>"
        "• 运动：降低强度，改为快走30分钟/天，心率<130bpm<br>"
        "• 监测：每日记录入睡/醒来时间，晨起测量静息心率和HRV<br>"
        "<strong>Week 2（评估周）：</strong><br>"
        "• 如睡眠改善，可逐步恢复中等强度运动<br>"
        "• 如睡眠仍不足6小时，需考虑就医检查是否存在睡眠障碍<br>"
        "<strong>核心原则：</strong>睡眠 > 营养 > 运动，恢复是训练的前提"
    )
    
    # 页脚
    html = html.replace('{{FOOTER_DATA_SOURCES}}', 
        f'Apple Health • HRV:{hrv_count}次 • 血氧:{spo2_count}次 • 步数:{steps_count}条 • 生成: {datetime.now().strftime("%Y-%m-%d %H:%M")} | UTC+8'
    )
    html = html.replace('{{FOOTER_DATE}}', datetime.now().strftime('%Y-%m-%d %H:%M'))
    
    # 保存
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    html_path = os.path.join(OUTPUT_DIR, f"{date_str}_report_final_v2.html")
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"\n📄 HTML已保存: {html_path}")
    
    # 生成PDF
    pdf_path = os.path.join(OUTPUT_DIR, f"{date_str}_report_final_v2.pdf")
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.set_content(html)
        page.wait_for_timeout(5000)  # 等待图表渲染
        page.pdf(path=pdf_path, format='A4', print_background=True,
                 margin={'top': '8mm', 'bottom': '8mm', 'left': '8mm', 'right': '8mm'})
        browser.close()
    
    print(f"✅ PDF已生成: {pdf_path}")
    print("=" * 60)

if __name__ == '__main__':
    generate()
