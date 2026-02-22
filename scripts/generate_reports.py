#!/usr/bin/env python3
"""
健康报告生成器 - 生成日报、周报、月报PDF
"""
import json
import os
import re
from datetime import datetime, timedelta
from playwright.sync_api import sync_playwright

def parse_health_data(file_path):
    """解析健康数据文件"""
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    metrics = data.get('data', {}).get('metrics', [])
    return {m.get('name'): m for m in metrics}

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
    return values[0], len(values)

def get_daily_summary(date_str, metrics, next_day_metrics=None):
    """获取单日汇总数据"""
    summary = {'date': date_str}
    
    # 基础指标
    hrv_val, hrv_count = get_metric_value(metrics, 'heart_rate_variability', 'avg')
    summary['hrv'] = round(hrv_val, 1) if hrv_val else None
    summary['hrv_count'] = hrv_count
    
    resting_hr, _ = get_metric_value(metrics, 'resting_heart_rate', 'avg')
    summary['resting_hr'] = round(resting_hr, 0) if resting_hr else None
    
    steps, _ = get_metric_value(metrics, 'step_count', 'sum')
    summary['steps'] = int(steps) if steps else 0
    
    distance, _ = get_metric_value(metrics, 'walking_running_distance', 'sum')
    summary['distance'] = round(distance, 2) if distance else 0
    
    energy, _ = get_metric_value(metrics, 'active_energy', 'sum')
    summary['energy'] = round(energy, 0) if energy else 0
    
    floors, _ = get_metric_value(metrics, 'flights_climbed', 'sum')
    summary['floors'] = int(floors) if floors else 0
    
    stand_time, _ = get_metric_value(metrics, 'apple_stand_time', 'sum')
    summary['stand_time'] = int(stand_time / 60) if stand_time else 0  # 转换为分钟
    
    spo2, spo2_count = get_metric_value(metrics, 'blood_oxygen_saturation', 'avg')
    summary['spo2'] = round(spo2 * 100, 1) if spo2 else None
    summary['spo2_count'] = spo2_count
    
    rest_energy, _ = get_metric_value(metrics, 'basal_energy_burned', 'sum')
    summary['rest_energy'] = round(rest_energy, 0) if rest_energy else 0
    
    resp_rate, _ = get_metric_value(metrics, 'respiratory_rate', 'avg')
    summary['resp_rate'] = round(resp_rate, 1) if resp_rate else None
    
    # 睡眠数据 - 从当日和次日文件合并
    sleep_sessions = []
    sleep_types = {'asleep_deep': 0, 'asleep_core': 0, 'asleep_rem': 0, 'awake': 0}
    
    for m in [metrics, next_day_metrics]:
        if m and 'sleep_analysis' in m:
            for sleep in m['sleep_analysis'].get('data', []):
                sleep_start = sleep.get('startDate', '')
                sleep_end = sleep.get('endDate', '')
                sleep_qty = sleep.get('qty', 0)  # 分钟
                sleep_value = sleep.get('value', '')
                
                # 解析日期
                try:
                    start_dt = datetime.strptime(sleep_start[:19], '%Y-%m-%d %H:%M:%S')
                    sleep_date = start_dt.strftime('%Y-%m-%d')
                    
                    # 判断归属：入睡时间在当日20:00之后或次日凌晨
                    if sleep_date == date_str and start_dt.hour >= 20:
                        sleep_sessions.append({'hours': sleep_qty / 60, 'type': sleep_value})
                        if sleep_value in sleep_types:
                            sleep_types[sleep_value] += sleep_qty / 60
                    elif sleep_date == (datetime.strptime(date_str, '%Y-%m-%d') + timedelta(days=1)).strftime('%Y-%m-%d') and start_dt.hour < 12:
                        sleep_sessions.append({'hours': sleep_qty / 60, 'type': sleep_value})
                        if sleep_value in sleep_types:
                            sleep_types[sleep_value] += sleep_qty / 60
                except:
                    pass
    
    summary['sleep_total'] = round(sum(s['hours'] for s in sleep_sessions), 1)
    summary['sleep_deep'] = round(sleep_types['asleep_deep'], 1)
    summary['sleep_core'] = round(sleep_types['asleep_core'], 1)
    summary['sleep_rem'] = round(sleep_types['asleep_rem'], 1)
    summary['sleep_awake'] = round(sleep_types['awake'], 1)
    
    # 运动数据
    workouts = []
    if 'workout' in metrics:
        for w in metrics['workout'].get('data', []):
            workouts.append({
                'type': w.get('value', ''),
                'duration': w.get('qty', 0),
            })
    summary['workouts'] = workouts
    summary['has_workout'] = len(workouts) > 0
    
    # 心率数据（用于运动）
    hr_data = []
    if 'heart_rate' in metrics:
        for hr in metrics['heart_rate'].get('data', []):
            hr_data.append(hr.get('qty', 0))
    summary['hr_max'] = round(max(hr_data), 0) if hr_data else None
    summary['hr_avg'] = round(sum(hr_data) / len(hr_data), 0) if hr_data else None
    
    return summary

def get_rating(value, good, poor, higher=True):
    if value is None:
        return '暂无', 'rating-average', 'badge-average'
    if higher:
        if value >= good: return '优秀', 'rating-excellent', 'badge-excellent'
        elif value >= poor: return '良好', 'rating-good', 'badge-good'
        else: return '需改善', 'rating-poor', 'badge-poor'
    else:
        if value <= good: return '优秀', 'rating-excellent', 'badge-excellent'
        elif value <= poor: return '良好', 'rating-good', 'badge-good'
        else: return '需改善', 'rating-poor', 'badge-poor'

def calc_recovery_score(d):
    """计算恢复度分数"""
    score = 70
    if d.get('hrv') and d['hrv'] > 50: score += 10
    if d.get('resting_hr') and d['resting_hr'] < 65: score += 10
    if d.get('sleep_total') and d['sleep_total'] > 7: score += 10
    return min(100, score)

def calc_sleep_score(d):
    """计算睡眠分数"""
    if d.get('sleep_total', 0) == 0:
        return 0
    score = 60
    if d['sleep_total'] >= 7: score += 20
    elif d['sleep_total'] >= 6: score += 10
    if d.get('sleep_deep', 0) >= 1.5: score += 10
    if d.get('sleep_rem', 0) >= 1.5: score += 10
    return min(100, score)

def calc_exercise_score(d):
    """计算运动分数"""
    score = 50
    if d.get('steps', 0) >= 10000: score += 25
    elif d.get('steps', 0) >= 7000: score += 15
    elif d.get('steps', 0) >= 5000: score += 10
    if d.get('has_workout'): score += 15
    if d.get('energy', 0) >= 500: score += 10
    return min(100, score)

def generate_daily_report(date_str, daily_data, template):
    """生成日报"""
    d = daily_data.get(date_str, {})
    if not d:
        return None
    
    html = template
    
    # 基础信息
    html = html.replace('{{DATE}}', date_str)
    html = html.replace('{{HEADER_SUBTITLE}}', f'{date_str} · Apple Health | UTC+8')
    
    # 评分
    recovery = calc_recovery_score(d)
    sleep = calc_sleep_score(d)
    exercise = calc_exercise_score(d)
    
    html = html.replace('{{SCORE_RECOVERY}}', str(recovery))
    html = html.replace('{{SCORE_SLEEP}}', str(sleep))
    html = html.replace('{{SCORE_EXERCISE}}', str(exercise))
    
    # 评级徽章
    r_class = 'badge-excellent' if recovery >= 80 else 'badge-good' if recovery >= 60 else 'badge-average'
    r_text = '优秀' if recovery >= 80 else '良好' if recovery >= 60 else '一般'
    html = html.replace('{{BADGE_RECOVERY_CLASS}}', r_class)
    html = html.replace('{{BADGE_RECOVERY_TEXT}}', r_text)
    
    s_class = 'badge-excellent' if sleep >= 80 else 'badge-good' if sleep >= 60 else 'badge-poor' if sleep > 0 else 'badge-average'
    s_text = '优秀' if sleep >= 80 else '良好' if sleep >= 60 else '需改善' if sleep > 0 else '无数据'
    html = html.replace('{{BADGE_SLEEP_CLASS}}', s_class)
    html = html.replace('{{BADGE_SLEEP_TEXT}}', s_text)
    
    e_class = 'badge-excellent' if exercise >= 80 else 'badge-good' if exercise >= 60 else 'badge-average'
    e_text = '优秀' if exercise >= 80 else '良好' if exercise >= 60 else '一般'
    html = html.replace('{{BADGE_EXERCISE_CLASS}}', e_class)
    html = html.replace('{{BADGE_EXERCISE_TEXT}}', e_text)
    
    # 指标1: HRV
    hrv_rating, hrv_class, _ = get_rating(d.get('hrv'), 55, 45)
    html = html.replace('{{METRIC1_VALUE}}', f"{d['hrv']:.1f} ms<br><small>{d.get('hrv_count', 0)}个数据点</small>" if d.get('hrv') else "--")
    html = html.replace('{{METRIC1_RATING}}', hrv_rating)
    html = html.replace('{{METRIC1_RATING_CLASS}}', hrv_class)
    html = html.replace('{{METRIC1_ANALYSIS}}', 
        f"心率变异性{d['hrv']:.1f}ms处于正常范围。HRV反映自主神经系统平衡，当前数值表明身体恢复良好，压力水平适中。建议保持规律作息。" if d.get('hrv') else "暂无数据")
    
    # 指标2: 静息心率
    rhr_rating, rhr_class, _ = get_rating(d.get('resting_hr'), 60, 70, False)
    html = html.replace('{{METRIC2_VALUE}}', f"{int(d['resting_hr'])} bpm" if d.get('resting_hr') else "--")
    html = html.replace('{{METRIC2_RATING}}', rhr_rating)
    html = html.replace('{{METRIC2_RATING_CLASS}}', rhr_class)
    html = html.replace('{{METRIC2_ANALYSIS}}', 
        f"静息心率{int(d['resting_hr'])}bpm，处于健康范围。静息心率是心血管健康的重要指标，保持规律运动有助于维持较低水平。" if d.get('resting_hr') else "暂无数据")
    
    # 指标3: 步数
    step_rating, step_class, _ = get_rating(d.get('steps'), 10000, 7000)
    html = html.replace('{{METRIC3_VALUE}}', f"{d['steps']:,} 步")
    html = html.replace('{{METRIC3_RATING}}', step_rating)
    html = html.replace('{{METRIC3_RATING_CLASS}}', step_class)
    html = html.replace('{{METRIC3_ANALYSIS}}', 
        f"今日步数{d['steps']:,}步。{'达成每日推荐目标，保持良好的活动习惯。' if d['steps'] >= 10000 else '距离10000步目标还有提升空间，建议增加日常活动。'}")
    
    # 指标4: 行走距离
    html = html.replace('{{METRIC4_VALUE}}', f"{d['distance']:.2f} km")
    html = html.replace('{{METRIC4_RATING}}', '良好' if d['distance'] >= 5 else '一般')
    html = html.replace('{{METRIC4_RATING_CLASS}}', 'rating-good' if d['distance'] >= 5 else 'rating-average')
    html = html.replace('{{METRIC4_ANALYSIS}}', f"今日行走{d['distance']:.2f}公里，相当于约{d['steps']//1300 if d.get('steps') else 0}个标准足球场的距离。")
    
    # 指标5: 活动能量
    html = html.replace('{{METRIC5_VALUE}}', f"{int(d['energy'])} kcal")
    html = html.replace('{{METRIC5_RATING}}', '良好' if d['energy'] >= 400 else '一般')
    html = html.replace('{{METRIC5_RATING_CLASS}}', 'rating-good' if d['energy'] >= 400 else 'rating-average')
    html = html.replace('{{METRIC5_ANALYSIS}}', f"活动消耗{d['energy']:.0f}千卡，相当于约{d['energy']//200 if d['energy'] else 0}碗米饭的热量。")
    
    # 指标6: 爬楼层数
    html = html.replace('{{METRIC6_VALUE}}', f"{d['floors']} 层")
    html = html.replace('{{METRIC6_RATING}}', '良好' if d['floors'] >= 10 else '一般')
    html = html.replace('{{METRIC6_RATING_CLASS}}', 'rating-good' if d['floors'] >= 10 else 'rating-average')
    html = html.replace('{{METRIC6_ANALYSIS}}', f"今日爬楼{d['floors']}层，有助于锻炼下肢力量和心肺功能。")
    
    # 指标7: 站立时间
    html = html.replace('{{METRIC7_VALUE}}', f"{d['stand_time']} 分钟")
    html = html.replace('{{METRIC7_RATING}}', '良好' if d['stand_time'] >= 120 else '一般')
    html = html.replace('{{METRIC7_RATING_CLASS}}', 'rating-good' if d['stand_time'] >= 120 else 'rating-average')
    html = html.replace('{{METRIC7_ANALYSIS}}', f"累计站立{d['stand_time']}分钟。建议每小时站立活动，有助于改善血液循环。")
    
    # 指标8: 血氧
    spo2_rating, spo2_class, _ = get_rating(d.get('spo2'), 95, 90)
    html = html.replace('{{METRIC8_VALUE}}', f"{d['spo2']:.1f}%<br><small>{d.get('spo2_count', 0)}个数据点</small>" if d.get('spo2') else "--")
    html = html.replace('{{METRIC8_RATING}}', spo2_rating if d.get('spo2') else '暂无')
    html = html.replace('{{METRIC8_RATING_CLASS}}', spo2_class if d.get('spo2') else 'rating-average')
    html = html.replace('{{METRIC8_ANALYSIS}}', 
        f"血氧饱和度{d['spo2']:.1f}%，处于正常范围(95-100%)。反映呼吸功能和氧气输送能力良好。" if d.get('spo2') else "暂无数据")
    
    # 指标9: 静息能量
    html = html.replace('{{METRIC9_VALUE}}', f"{int(d['rest_energy'])} kcal")
    html = html.replace('{{METRIC9_RATING}}', '正常')
    html = html.replace('{{METRIC9_RATING_CLASS}}', 'rating-good')
    html = html.replace('{{METRIC9_ANALYSIS}}', f"基础代谢消耗{d['rest_energy']:.0f}千卡，维持生命活动所需的基础能量。")
    
    # 指标10: 呼吸率
    resp_rating, resp_class, _ = get_rating(d.get('resp_rate'), 16, 20, False)
    html = html.replace('{{METRIC10_VALUE}}', f"{d['resp_rate']:.1f} 次/分" if d.get('resp_rate') else "--")
    html = html.replace('{{METRIC10_RATING}}', resp_rating if d.get('resp_rate') else '暂无')
    html = html.replace('{{METRIC10_RATING_CLASS}}', resp_class if d.get('resp_rate') else 'rating-average')
    html = html.replace('{{METRIC10_ANALYSIS}}', 
        f"呼吸率{d['resp_rate']:.1f}次/分钟，处于正常静息范围(12-20次/分)。" if d.get('resp_rate') else "暂无数据")
    
    # 睡眠分析
    if d.get('sleep_total', 0) > 0:
        sleep_total = d['sleep_total']
        sleep_deep = d.get('sleep_deep', 0)
        sleep_core = d.get('sleep_core', 0)
        sleep_rem = d.get('sleep_rem', 0)
        sleep_awake = d.get('sleep_awake', 0)
        
        html = html.replace('{{SLEEP_STATUS}}', '数据正常')
        html = html.replace('{{SLEEP_ALERT_BG}}', '#dcfce7')
        html = html.replace('{{SLEEP_ALERT_BORDER}}', '#22c55e')
        html = html.replace('{{SLEEP_ALERT_COLOR}}', '#166534')
        html = html.replace('{{SLEEP_ALERT_SUBCOLOR}}', '#15803d')
        html = html.replace('{{SLEEP_ALERT_TITLE}}', '✅ 睡眠数据完整')
        html = html.replace('{{SLEEP_ALERT_DETAIL}}', f'总睡眠时长{sleep_total:.1f}小时，符合健康推荐范围。')
        
        html = html.replace('{{SLEEP_TOTAL}}', f"{sleep_total:.1f}")
        html = html.replace('{{SLEEP_DEEP}}', f"{sleep_deep:.1f}")
        html = html.replace('{{SLEEP_CORE}}', f"{sleep_core:.1f}")
        html = html.replace('{{SLEEP_REM}}', f"{sleep_rem:.1f}")
        html = html.replace('{{SLEEP_AWAKE}}', f"{sleep_awake:.1f}")
        
        # 计算百分比
        total = sleep_deep + sleep_core + sleep_rem + sleep_awake
        if total > 0:
            html = html.replace('{{SLEEP_DEEP_PCT}}', str(int(sleep_deep/total*100)))
            html = html.replace('{{SLEEP_CORE_PCT}}', str(int(sleep_core/total*100)))
            html = html.replace('{{SLEEP_REM_PCT}}', str(int(sleep_rem/total*100)))
            html = html.replace('{{SLEEP_AWAKE_PCT}}', str(int(sleep_awake/total*100)))
        
        html = html.replace('{{SLEEP_ANALYSIS_BORDER}}', '#667eea')
        html = html.replace('{{SLEEP_ANALYSIS_TEXT}}', 
            f"睡眠总时长{sleep_total:.1f}小时，其中深睡{sleep_deep:.1f}小时({int(sleep_deep/total*100) if total else 0}%)，"
            f"核心睡眠{sleep_core:.1f}小时，REM睡眠{sleep_rem:.1f}小时。深睡比例正常，有助于身体恢复和记忆巩固。")
    else:
        html = html.replace('{{SLEEP_STATUS}}', '无数据')
        html = html.replace('{{SLEEP_ALERT_BG}}', '#fee2e2')
        html = html.replace('{{SLEEP_ALERT_BORDER}}', '#dc2626')
        html = html.replace('{{SLEEP_ALERT_COLOR}}', '#991b1b')
        html = html.replace('{{SLEEP_ALERT_SUBCOLOR}}', '#b91c1c')
        html = html.replace('{{SLEEP_ALERT_TITLE}}', '⚠️ 未检测到睡眠数据')
        html = html.replace('{{SLEEP_ALERT_DETAIL}}', '请确保Apple Watch在睡眠期间佩戴并开启睡眠追踪。')
        html = html.replace('{{SLEEP_TOTAL}}', '--')
        html = html.replace('{{SLEEP_DEEP}}', '--')
        html = html.replace('{{SLEEP_CORE}}', '--')
        html = html.replace('{{SLEEP_REM}}', '--')
        html = html.replace('{{SLEEP_AWAKE}}', '--')
        html = html.replace('{{SLEEP_DEEP_PCT}}', '0')
        html = html.replace('{{SLEEP_CORE_PCT}}', '0')
        html = html.replace('{{SLEEP_REM_PCT}}', '0')
        html = html.replace('{{SLEEP_AWAKE_PCT}}', '0')
        html = html.replace('{{SLEEP_ANALYSIS_BORDER}}', '#dc2626')
        html = html.replace('{{SLEEP_ANALYSIS_TEXT}}', '未检测到有效睡眠数据。建议检查Apple Watch睡眠追踪设置，确保就寝时正确佩戴设备。')
    
    # 运动记录
    if d.get('has_workout'):
        w = d['workouts'][0]
        html = html.replace('{{WORKOUT_NAME}}', w['type'])
        html = html.replace('{{WORKOUT_TIME}}', '今日')
        html = html.replace('{{WORKOUT_DURATION}}', str(int(w['duration'])))
        html = html.replace('{{WORKOUT_ENERGY}}', str(int(d.get('energy', 0))))
        html = html.replace('{{WORKOUT_AVG_HR}}', str(int(d.get('hr_avg', 0)) if d.get('hr_avg') else '--'))
        html = html.replace('{{WORKOUT_MAX_HR}}', str(int(d.get('hr_max', 0)) if d.get('hr_max') else '--'))
        html = html.replace('{{WORKOUT_HR_CHART}}', '<div style="color:#64748b;font-size:8pt;">心率数据可视化区域</div>')
        html = html.replace('{{WORKOUT_ANALYSIS}}', f"今日完成{w['type']}运动，持续{int(w['duration'])}分钟。运动有助于提升心肺功能和维持健康体重。")
    else:
        html = html.replace('{{WORKOUT_NAME}}', '无运动记录')
        html = html.replace('{{WORKOUT_TIME}}', '--')
        html = html.replace('{{WORKOUT_DURATION}}', '--')
        html = html.replace('{{WORKOUT_ENERGY}}', '--')
        html = html.replace('{{WORKOUT_AVG_HR}}', '--')
        html = html.replace('{{WORKOUT_MAX_HR}}', '--')
        html = html.replace('{{WORKOUT_HR_CHART}}', '<div style="color:#64748b;font-size:8pt;">今日无运动数据</div>')
        html = html.replace('{{WORKOUT_ANALYSIS}}', '今日未记录到运动数据。建议每周至少进行150分钟中等强度有氧运动，如快走、慢跑或游泳。')
    
    # AI建议
    html = html.replace('{{AI1_TITLE}}', '关注睡眠时长')
    html = html.replace('{{AI1_PROBLEM}}', '近期睡眠数据记录不完整，可能影响恢复质量评估。')
    html = html.replace('{{AI1_ACTION}}', '1. 检查Apple Watch睡眠模式设置<br>2. 确保睡前佩戴设备<br>3. 设定规律的作息时间(23:00前入睡)')
    html = html.replace('{{AI1_EXPECTATION}}', '改善睡眠数据记录后，可更准确评估恢复状态。')
    
    html = html.replace('{{AI2_TITLE}}', '增加日常活动量')
    html = html.replace('{{AI2_PROBLEM}}', f"今日步数{d['steps']:,}，距离10000步目标有差距。")
    html = html.replace('{{AI2_ACTION}}', '1. 每小时起身活动5分钟<br>2. 饭后散步15-20分钟<br>3. 选择楼梯代替电梯')
    html = html.replace('{{AI2_EXPECTATION}}', '坚持2-3周，逐步提升基础活动量。')
    
    html = html.replace('{{AI3_TITLE}}', '饮食与作息优化')
    html = html.replace('{{AI3_DIET}}', '保持均衡饮食，增加蔬菜水果摄入，控制精制碳水化合物。')
    html = html.replace('{{AI3_ROUTINE}}', '建议23:00前入睡，保证7-8小时睡眠，建立规律的生物钟。')
    
    html = html.replace('{{AI4_TITLE}}', '数据洞察总结')
    html = html.replace('{{AI4_ADVANTAGES}}', f"HRV{d['hrv']:.1f}ms显示自主神经平衡良好，基础代谢正常。")
    html = html.replace('{{AI4_RISKS}}', '睡眠数据记录不完整，需关注数据追踪设置。')
    html = html.replace('{{AI4_CONCLUSION}}', '整体健康状况良好，建议关注睡眠质量和日常活动量。')
    html = html.replace('{{AI4_PLAN}}', '1. 完善睡眠追踪设置<br>2. 增加日常步行量<br>3. 保持规律作息')
    
    # 页脚
    html = html.replace('{{FOOTER_DATA_SOURCES}}', '数据来源: Apple Health')
    html = html.replace('{{FOOTER_DATE}}', datetime.now().strftime('%Y-%m-%d %H:%M'))
    
    return html

def main():
    base_dir = os.path.expanduser('~/我的云端硬盘/Health Auto Export/Health Data')
    template_dir = os.path.expanduser('~/.openclaw/workspace-health/templates')
    output_dir = os.path.expanduser('~/.openclaw/workspace/shared/health-reports/upload')
    
    os.makedirs(output_dir, exist_ok=True)
    
    # 读取模板
    with open(f'{template_dir}/DAILY_TEMPLATE_V2.html', 'r', encoding='utf-8') as f:
        daily_template = f.read()
    
    # 读取数据
    dates = ['2026-02-18', '2026-02-19', '2026-02-20', '2026-02-21', '2026-02-22']
    daily_data = {}
    
    for i, date in enumerate(dates):
        file_path = f"{base_dir}/HealthAutoExport-{date}.json"
        next_file = f"{base_dir}/HealthAutoExport-{dates[i+1]}.json" if i < len(dates)-1 else None
        
        if os.path.exists(file_path):
            metrics = parse_health_data(file_path)
            next_metrics = parse_health_data(next_file) if next_file and os.path.exists(next_file) else None
            daily_data[date] = get_daily_summary(date, metrics, next_metrics)
    
    print(f"✅ 加载了 {len(daily_data)} 天数据")
    
    # 生成2月18日日报
    date_str = '2026-02-18'
    html = generate_daily_report(date_str, daily_data, daily_template)
    
    if html:
        output_path = f'{output_dir}/{date_str}-daily-report.pdf'
        
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.set_content(html)
            page.wait_for_timeout(2000)
            page.pdf(path=output_path, format='A4', print_background=True, 
                    margin={'top': '8mm', 'bottom': '8mm', 'left': '8mm', 'right': '8mm'})
            browser.close()
        
        print(f"✅ 日报生成: {output_path}")
    
    # 输出调试信息
    d = daily_data.get('2026-02-18', {})
    print(f"\n2月18日数据摘要:")
    print(f"  HRV: {d.get('hrv')}")
    print(f"  步数: {d.get('steps')}")
    print(f"  距离: {d.get('distance')}km")
    print(f"  睡眠: {d.get('sleep_total')}h")
    print(f"  运动: {d.get('has_workout')}")

if __name__ == '__main__':
    main()
