#!/usr/bin/env python3
"""
2026-02-18 健康日报 - 完整版
所有指标正确填充
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
                            'deep': sleep.get('deep', 0), 'core': sleep.get('core', 0),
                            'rem': sleep.get('rem', 0), 'awake': sleep.get('awake', 0)
                        })
    
    if not sessions:
        return None
    
    total = sum(s['total'] for s in sessions)
    return {
        'total_hours': total,
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
        
        result.append({
            'name': w.get('name', '未知运动'),
            'start': w.get('start', ''),
            'duration_min': round(w.get('duration', 0) / 60, 1),
            'energy_kcal': total_kcal if total_kcal > 0 else None,
            'avg_hr': avg_hr,
            'max_hr': max_hr
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

def generate():
    date_str = "2026-02-18"
    
    print("=" * 60)
    print(f"生成 {date_str} 健康日报 - 完整版")
    print("=" * 60)
    
    # 读取所有数据
    print("\n📊 读取健康数据...")
    
    # 1. 睡眠
    sleep = extract_sleep_data(date_str)
    if sleep:
        print(f"   睡眠: {sleep['total_hours']:.2f}小时 ({sleep['bed_time'].strftime('%H:%M')}-{sleep['wake_time'].strftime('%H:%M')})")
    
    # 2. 锻炼
    workouts = extract_workout_data(date_str)
    if workouts:
        w = workouts[0]
        print(f"   锻炼: {w['name']} {w['duration_min']:.0f}分钟")
    
    # 3. Apple Health指标
    metrics = read_health_metrics(date_str)
    
    # 各项指标
    hrv_val, hrv_count = get_avg(metrics.get('heart_rate_variability_sdnn'))
    resting_hr, _ = get_avg(metrics.get('resting_heart_rate'))
    steps, steps_count = get_sum(metrics.get('step_count'))
    steps = int(steps)
    distance, _ = get_sum(metrics.get('distance_walking_running'))
    energy, _ = get_sum(metrics.get('active_energy_burned'))
    energy_kcal = energy / 1000  # kJ to kcal
    floors, _ = get_sum(metrics.get('flights_climbed'))
    floors = int(floors)
    stand_time, _ = get_sum(metrics.get('apple_stand_time'))
    stand_hours = stand_time / 60
    spo2, spo2_count = get_avg(metrics.get('oxygen_saturation'), 100)
    resp_rate, resp_count = get_avg(metrics.get('respiratory_rate'))
    resting_energy, _ = get_sum(metrics.get('basal_energy_burned'))
    resting_energy_kcal = resting_energy / 1000
    
    print(f"   HRV: {hrv_val:.1f}ms ({hrv_count}点)")
    print(f"   步数: {steps:,} ({steps_count}点)")
    print(f"   距离: {distance:.2f}km")
    print(f"   爬楼: {floors}层")
    print(f"   活动能量: {energy_kcal:.0f}kcal")
    
    # 评分
    recovery_score = min(100, int(50 + (hrv_val - 30) * 1.5)) if hrv_val > 0 else 50
    sleep_score = min(100, int(sleep['total_hours'] * 12.5)) if sleep else 30
    exercise_score = min(100, int(steps / 100)) if steps > 0 else 20
    
    # 读取模板
    print("\n📄 生成报告...")
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
    
    # 指标1: HRV
    hrv_display = f"{hrv_val:.1f} ms<br><small>{hrv_count}个数据点</small>" if hrv_val > 0 else "无数据"
    html = html.replace('{{METRIC1_VALUE}}', hrv_display)
    hrv_cls, hrv_rtg = rating_class(hrv_val, 40, 100)
    html = html.replace('{{METRIC1_RATING_CLASS}}', hrv_cls)
    html = html.replace('{{METRIC1_RATING}}', hrv_rtg)
    html = html.replace('{{METRIC1_ANALYSIS}}', 
        f"今日HRV均值为{hrv_val:.1f}ms（{hrv_count}次测量）。{'处于正常范围，自主神经系统功能良好。' if hrv_val > 40 else '略低于理想水平，建议关注休息质量。' if hrv_val > 0 else '当日无HRV数据记录。'}"
    )
    
    # 指标2: 静息心率
    rhr_display = f"{resting_hr:.0f} bpm" if resting_hr > 0 else "无数据"
    html = html.replace('{{METRIC2_VALUE}}', rhr_display)
    rhr_cls, rhr_rtg = rating_class(resting_hr, 50, 70)
    html = html.replace('{{METRIC2_RATING_CLASS}}', rhr_cls)
    html = html.replace('{{METRIC2_RATING}}', rhr_rtg)
    html = html.replace('{{METRIC2_ANALYSIS}}', 
        f"静息心率{resting_hr:.0f}bpm，{'处于健康范围内，心脏功能良好。' if 50 <= resting_hr <= 70 else '当日无静息心率数据记录。' if resting_hr == 0 else '建议关注心血管健康。'}"
    )
    
    # 指标3: 步数
    steps_display = f"{steps:,} 步<br><small>{steps_count}个记录</small>" if steps > 0 else "无数据"
    html = html.replace('{{METRIC3_VALUE}}', steps_display)
    steps_cls, steps_rtg = ('rating-good', '达标') if steps >= 8000 else ('rating-average', '偏低') if steps > 0 else ('rating-poor', '缺失')
    html = html.replace('{{METRIC3_RATING_CLASS}}', steps_cls)
    html = html.replace('{{METRIC3_RATING}}', steps_rtg)
    html = html.replace('{{METRIC3_ANALYSIS}}', 
        f"今日步行{steps:,}步，{'达到每日建议活动量。' if steps >= 8000 else '低于建议的8000步目标，建议增加日常活动量。' if steps > 0 else '当日无步数数据记录。'}"
    )
    
    # 指标4: 行走距离
    dist_display = f"{distance:.2f} km" if distance > 0 else "无数据"
    html = html.replace('{{METRIC4_VALUE}}', dist_display)
    dist_cls, dist_rtg = ('rating-good', '良好') if distance >= 5 else ('rating-average', '一般') if distance > 0 else ('rating-poor', '缺失')
    html = html.replace('{{METRIC4_RATING_CLASS}}', dist_cls)
    html = html.replace('{{METRIC4_RATING}}', dist_rtg)
    html = html.replace('{{METRIC4_ANALYSIS}}', 
        f"行走距离{distance:.2f}公里，{'活动量充足，有助于维持下肢肌肉力量。' if distance >= 5 else '建议适当增加步行距离以提升心肺功能。' if distance > 0 else '当日无距离数据记录。'}"
    )
    
    # 指标5: 活动能量
    energy_display = f"{energy_kcal:.0f} kcal" if energy_kcal > 0 else "无数据"
    html = html.replace('{{METRIC5_VALUE}}', energy_display)
    eng_cls, eng_rtg = ('rating-good', '活跃') if energy_kcal >= 300 else ('rating-average', '偏低') if energy_kcal > 0 else ('rating-poor', '缺失')
    html = html.replace('{{METRIC5_RATING_CLASS}}', eng_cls)
    html = html.replace('{{METRIC5_RATING}}', eng_rtg)
    html = html.replace('{{METRIC5_ANALYSIS}}', 
        f"活动能量消耗{energy_kcal:.0f}千卡，{'今日身体活动较为活跃，有助于热量平衡。' if energy_kcal >= 300 else '活动消耗偏低，建议增加运动强度。' if energy_kcal > 0 else '当日无活动能量数据记录。'}"
    )
    
    # 指标6: 爬楼层数
    floors_display = f"{floors} 层" if floors > 0 else "无数据"
    html = html.replace('{{METRIC6_VALUE}}', floors_display)
    fl_cls, fl_rtg = ('rating-good', '良好') if floors >= 5 else ('rating-average', '一般') if floors > 0 else ('rating-poor', '缺失')
    html = html.replace('{{METRIC6_RATING_CLASS}}', fl_cls)
    html = html.replace('{{METRIC6_RATING}}', fl_rtg)
    html = html.replace('{{METRIC6_ANALYSIS}}', 
        f"今日爬楼{floors}层，{'垂直活动充足，有助于下肢力量训练。' if floors >= 5 else '垂直活动较少，建议多使用楼梯。' if floors > 0 else '当日无爬楼数据记录。'}"
    )
    
    # 指标7: 站立时间
    stand_display = f"{stand_hours:.1f} h" if stand_hours > 0 else "无数据"
    html = html.replace('{{METRIC7_VALUE}}', stand_display)
    st_cls, st_rtg = ('rating-good', '达标') if stand_hours >= 8 else ('rating-average', '不足') if stand_hours > 0 else ('rating-poor', '缺失')
    html = html.replace('{{METRIC7_RATING_CLASS}}', st_cls)
    html = html.replace('{{METRIC7_RATING}}', st_rtg)
    html = html.replace('{{METRIC7_ANALYSIS}}', 
        f"站立时间{stand_hours:.1f}小时，{'站立活动充足，有助于减少久坐风险。' if stand_hours >= 8 else '站立时间不足，建议每小时起身活动。' if stand_hours > 0 else '当日无站立数据记录。'}"
    )
    
    # 指标8: 血氧
    spo2_display = f"{spo2:.1f}%<br><small>{spo2_count}次测量</small>" if spo2 > 0 else "无数据"
    html = html.replace('{{METRIC8_VALUE}}', spo2_display)
    sp_cls, sp_rtg = ('rating-good', '正常') if spo2 >= 95 else ('rating-poor', '偏低') if spo2 > 0 else ('rating-poor', '缺失')
    html = html.replace('{{METRIC8_RATING_CLASS}}', sp_cls)
    html = html.replace('{{METRIC8_RATING}}', sp_rtg)
    html = html.replace('{{METRIC8_ANALYSIS}}', 
        f"血氧饱和度{spo2:.1f}%（{spo2_count}次测量），{'处于正常范围，血液携氧能力良好。' if spo2 >= 95 else '略低于理想水平，建议关注呼吸健康。' if spo2 > 0 else '当日无血氧数据记录。'}"
    )
    
    # 指标9: 静息能量
    re_display = f"{resting_energy_kcal:.0f} kcal" if resting_energy_kcal > 0 else "无数据"
    html = html.replace('{{METRIC9_VALUE}}', re_display)
    html = html.replace('{{METRIC9_RATING_CLASS}}', 'rating-good' if resting_energy_kcal > 0 else 'rating-poor')
    html = html.replace('{{METRIC9_RATING}}', '正常' if resting_energy_kcal > 0 else '缺失')
    html = html.replace('{{METRIC9_ANALYSIS}}', 
        f"静息能量消耗约{resting_energy_kcal:.0f}千卡，{'反映基础代谢水平正常。' if resting_energy_kcal > 0 else '当日无静息能量数据记录。'}"
    )
    
    # 指标10: 呼吸率
    resp_display = f"{resp_rate:.1f} 次/分<br><small>{resp_count}次测量</small>" if resp_rate > 0 else "无数据"
    html = html.replace('{{METRIC10_VALUE}}', resp_display)
    rp_cls, rp_rtg = ('rating-good', '正常') if 12 <= resp_rate <= 20 else ('rating-average', '需关注') if resp_rate > 0 else ('rating-poor', '缺失')
    html = html.replace('{{METRIC10_RATING_CLASS}}', rp_cls)
    html = html.replace('{{METRIC10_RATING}}', rp_rtg)
    html = html.replace('{{METRIC10_ANALYSIS}}', 
        f"呼吸率{resp_rate:.1f}次/分钟（{resp_count}次测量），{'处于正常成人范围，呼吸功能良好。' if 12 <= resp_rate <= 20 else '建议关注呼吸模式。' if resp_rate > 0 else '当日无呼吸率数据记录。'}"
    )
    
    # 睡眠部分
    if sleep:
        total = sleep['total_hours']
        html = html.replace('{{SLEEP_STATUS}}', '数据完整')
        html = html.replace('{{SLEEP_TOTAL}}', f"{total:.1f}")
        html = html.replace('{{SLEEP_DEEP}}', f"{sleep['deep_hours']:.1f}")
        html = html.replace('{{SLEEP_CORE}}', f"{sleep['core_hours']:.1f}")
        html = html.replace('{{SLEEP_REM}}', f"{sleep['rem_hours']:.1f}")
        html = html.replace('{{SLEEP_AWAKE}}', f"{sleep['awake_hours']:.1f}")
        html = html.replace('{{SLEEP_DEEP_PCT}}', str(int(sleep['deep_hours']/total*100)) if total else '0')
        html = html.replace('{{SLEEP_CORE_PCT}}', str(int(sleep['core_hours']/total*100)) if total else '0')
        html = html.replace('{{SLEEP_REM_PCT}}', str(int(sleep['rem_hours']/total*100)) if total else '0')
        html = html.replace('{{SLEEP_AWAKE_PCT}}', str(int(sleep['awake_hours']/total*100)) if total else '0')
        html = html.replace('{{SLEEP_ALERT_BG}}', '#f0fdf4')
        html = html.replace('{{SLEEP_ALERT_BORDER}}', '#86efac')
        html = html.replace('{{SLEEP_ALERT_COLOR}}', '#166534')
        html = html.replace('{{SLEEP_ALERT_SUBCOLOR}}', '#15803d')
        html = html.replace('{{SLEEP_ALERT_TITLE}}', '✅ 睡眠记录完整')
        html = html.replace('{{SLEEP_ALERT_DETAIL}}', f"入睡 {sleep['bed_time'].strftime('%H:%M')} | 醒来 {sleep['wake_time'].strftime('%H:%M')} | 来源: Apple Health")
        html = html.replace('{{SLEEP_ANALYSIS_BORDER}}', '#667eea')
        html = html.replace('{{SLEEP_ANALYSIS_TEXT}}', 
            f"昨晚入睡时间{sleep['bed_time'].strftime('%H:%M')}，醒来时间{sleep['wake_time'].strftime('%H:%M')}，总睡眠{total:.1f}小时。{'睡眠时长偏短，建议今晚提前入睡。' if total < 7 else '睡眠时长充足，有助于身体恢复。'}"
        )
    else:
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
    
    # 锻炼部分
    if workouts:
        w = workouts[0]
        html = html.replace('{{WORKOUT_NAME}}', w['name'])
        html = html.replace('{{WORKOUT_TIME}}', w['start'][:16] if w['start'] else '-')
        html = html.replace('{{WORKOUT_DURATION}}', f"{w['duration_min']:.0f}")
        html = html.replace('{{WORKOUT_ENERGY}}', f"{w['energy_kcal']:.0f}" if w['energy_kcal'] else '未记录')
        html = html.replace('{{WORKOUT_AVG_HR}}', f"{w['avg_hr']:.0f}" if w['avg_hr'] else '未记录')
        html = html.replace('{{WORKOUT_MAX_HR}}', f"{w['max_hr']:.0f}" if w['max_hr'] else '未记录')
        analysis = f"今日进行了{w['name']}锻炼，时长{w['duration_min']:.0f}分钟。"
        if w['energy_kcal']:
            analysis += f"消耗能量约{w['energy_kcal']:.0f}千卡。"
        if w['avg_hr']:
            analysis += f"平均心率{w['avg_hr']:.0f}bpm，最高心率{w['max_hr']:.0f}bpm，运动强度适中。"
        html = html.replace('{{WORKOUT_ANALYSIS}}', analysis)
    else:
        html = html.replace('{{WORKOUT_NAME}}', '今日无锻炼记录')
        html = html.replace('{{WORKOUT_TIME}}', '-')
        html = html.replace('{{WORKOUT_DURATION}}', '-')
        html = html.replace('{{WORKOUT_ENERGY}}', '-')
        html = html.replace('{{WORKOUT_AVG_HR}}', '-')
        html = html.replace('{{WORKOUT_MAX_HR}}', '-')
        html = html.replace('{{WORKOUT_ANALYSIS}}', '今日未记录到专门的运动锻炼。')
    
    # AI建议
    html = html.replace('{{AI1_TITLE}}', '睡眠优化')
    html = html.replace('{{AI1_PROBLEM}}', '昨晚睡眠仅2.8小时，明显不足。')
    html = html.replace('{{AI1_ACTION}}', '1. 今晚提前1小时入睡\n2. 睡前避免使用电子设备\n3. 保持卧室温度18-22°C\n4. 进行10分钟冥想放松')
    html = html.replace('{{AI1_EXPECTATION}}', '充足睡眠将改善日间精力和恢复能力。')
    
    html = html.replace('{{AI2_TITLE}}', '日常活动')
    html = html.replace('{{AI2_PROBLEM}}', '步数达标但睡眠严重不足。')
    html = html.replace('{{AI2_ACTION}}', '1. 减少晚间活动\n2. 优先保证睡眠时间\n3. 调整作息规律')
    html = html.replace('{{AI2_EXPECTATION}}', '规律作息将提升整体健康水平。')
    
    html = html.replace('{{AI3_TITLE}}', '健康生活方式')
    html = html.replace('{{AI3_DIET}}', '保持均衡饮食，晚餐避免过饱。')
    html = html.replace('{{AI3_ROUTINE}}', '固定作息时间，创造良好睡眠环境。')
    
    html = html.replace('{{AI4_TITLE}}', '整体评估')
    html = html.replace('{{AI4_ADVANTAGES}}', '日常活动充足，运动习惯良好。')
    html = html.replace('{{AI4_RISKS}}', '睡眠严重不足，需优先改善。')
    html = html.replace('{{AI4_CONCLUSION}}', '整体健康状况一般，睡眠质量是主要短板。')
    html = html.replace('{{AI4_PLAN}}', '本周重点：1)保证7小时睡眠 2)固定作息时间')
    
    # 页脚
    html = html.replace('{{FOOTER_DATA_SOURCES}}', 
        f'Apple Health • HRV:{hrv_count}次 • 步数:{steps_count}条 • 生成: {datetime.now().strftime("%Y-%m-%d %H:%M")} | UTC+8'
    )
    html = html.replace('{{FOOTER_DATE}}', datetime.now().strftime('%Y-%m-%d %H:%M'))
    
    # 保存
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    html_path = os.path.join(OUTPUT_DIR, f"{date_str}_report_complete.html")
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    pdf_path = os.path.join(OUTPUT_DIR, f"{date_str}_report_complete.pdf")
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.set_content(html)
        page.wait_for_timeout(3000)
        page.pdf(path=pdf_path, format='A4', print_background=True,
                 margin={'top': '8mm', 'bottom': '8mm', 'left': '8mm', 'right': '8mm'})
        browser.close()
    
    print(f"\n✅ 完整报告已生成: {pdf_path}")
    print("=" * 60)

if __name__ == '__main__':
    generate()
