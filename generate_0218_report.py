#!/usr/bin/env python3
"""
生成2026-02-18健康日报 - V2模板
"""
import json
import os
from datetime import datetime, timedelta
from playwright.sync_api import sync_playwright

# 数据路径
DATA_DIR = "/Users/jimmylu/我的云端硬盘/Health Auto Export/Health Data"
TEMPLATE_PATH = "/Users/jimmylu/.openclaw/workspace-health/templates/DAILY_TEMPLATE_V2.html"
OUTPUT_DIR = "/Users/jimmylu/.openclaw/workspace-health/output"

def read_json_file(filename):
    """读取JSON文件"""
    filepath = os.path.join(DATA_DIR, filename)
    if not os.path.exists(filepath):
        return None
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def extract_metrics(data):
    """提取所有指标"""
    metrics = {}
    if not data or 'data' not in data:
        return metrics
    
    for metric in data['data'].get('metrics', []):
        name = metric.get('name', '')
        metrics[name] = metric
    return metrics

def get_daily_sum(metric_data):
    """计算日总和"""
    if not metric_data or 'data' not in metric_data:
        return 0, 0
    
    total = sum(d.get('qty', 0) for d in metric_data['data'])
    return total, len(metric_data['data'])

def get_daily_avg(metric_data):
    """计算日平均值"""
    if not metric_data or 'data' not in metric_data or not metric_data['data']:
        return 0, 0
    
    values = [d.get('qty', 0) for d in metric_data['data'] if d.get('qty')]
    if not values:
        return 0, 0
    return sum(values) / len(values), len(values)

def get_sleep_data(data_19):
    """从2月19日文件提取2月18日晚上的睡眠数据"""
    if not data_19:
        return None
    
    metrics = extract_metrics(data_19)
    sleep_metric = metrics.get('sleep_analysis')
    
    if not sleep_metric or 'data' not in sleep_metric:
        return None
    
    # 筛选2月18日20:00到2月19日12:00的睡眠
    window_start = datetime(2026, 2, 18, 20, 0)
    window_end = datetime(2026, 2, 19, 12, 0)
    
    sleep_sessions = []
    for sleep in sleep_metric['data']:
        start_str = sleep.get('startDate', '')
        end_str = sleep.get('endDate', '')
        
        try:
            start = datetime.strptime(start_str[:19], "%Y-%m-%d %H:%M:%S")
            end = datetime.strptime(end_str[:19], "%Y-%m-%d %H:%M:%S")
        except:
            continue
        
        # 检查是否在时间窗口内
        if start < window_end and end > window_start:
            sleep_sessions.append({
                'start': start,
                'end': end,
                'duration': sleep.get('qty', 0),
                'value': sleep.get('value', '')
            })
    
    if not sleep_sessions:
        return None
    
    # 合并计算总睡眠
    total_hours = sum(s['duration'] for s in sleep_sessions) / 60
    
    # 简化：按睡眠阶段分类（这里根据value字段推断）
    # Apple Health睡眠阶段：HKCategoryValueSleepAnalysisAsleepUnspecified/AsleepCore/AsleepDeep/AsleepREM
    deep_hours = sum(s['duration'] for s in sleep_sessions if 'Deep' in s.get('value', '')) / 60
    rem_hours = sum(s['duration'] for s in sleep_sessions if 'REM' in s.get('value', '')) / 60
    core_hours = total_hours - deep_hours - rem_hours if total_hours > 0 else 0
    
    # 找最早入睡和最晚醒来时间
    bed_time = min(s['start'] for s in sleep_sessions)
    wake_time = max(s['end'] for s in sleep_sessions)
    
    return {
        'total_hours': total_hours,
        'deep_hours': max(0, deep_hours),
        'core_hours': max(0, core_hours),
        'rem_hours': max(0, rem_hours),
        'bed_time': bed_time,
        'wake_time': wake_time,
        'sessions': len(sleep_sessions)
    }

def check_workout(data_18, data_19):
    """检查是否有锻炼记录"""
    # 检查Workout Data目录
    workout_file = f"/Users/jimmylu/我的云端硬盘/Health Auto Export/Workout Data/HealthAutoExport-2026-02-18.json"
    if os.path.exists(workout_file):
        try:
            with open(workout_file, 'r', encoding='utf-8') as f:
                workout_data = json.load(f)
            if workout_data and 'data' in workout_data and 'workouts' in workout_data['data']:
                return workout_data['data']['workouts']
        except:
            pass
    return None

def generate_report():
    """生成健康报告"""
    date_str = "2026-02-18"
    
    # 读取数据
    data_18 = read_json_file(f"HealthAutoExport-{date_str}.json")
    data_19 = read_json_file("HealthAutoExport-2026-02-19.json")
    
    if not data_18:
        print(f"错误: 找不到{date_str}的数据文件")
        return
    
    # 提取指标
    metrics_18 = extract_metrics(data_18)
    
    # 各项指标提取
    # 1. HRV
    hrv_metric = metrics_18.get('heart_rate_variability_sdnn')
    hrv_avg, hrv_count = get_daily_avg(hrv_metric)
    
    # 2. 静息心率
    resting_hr_metric = metrics_18.get('resting_heart_rate')
    resting_hr, _ = get_daily_avg(resting_hr_metric)
    
    # 3. 步数
    steps_metric = metrics_18.get('step_count')
    steps, steps_count = get_daily_sum(steps_metric)
    steps = int(steps)
    
    # 4. 行走距离
    distance_metric = metrics_18.get('distance_walking_running')
    distance, _ = get_daily_sum(distance_metric)
    distance_km = distance / 1000
    
    # 5. 活动能量
    energy_metric = metrics_18.get('active_energy_burned')
    energy, _ = get_daily_sum(energy_metric)
    energy_kcal = energy / 1000
    
    # 6. 爬楼层数
    floors_metric = metrics_18.get('flights_climbed')
    floors, _ = get_daily_sum(floors_metric)
    floors = int(floors)
    
    # 7. 站立时间
    stand_metric = metrics_18.get('apple_stand_time')
    stand_hours, _ = get_daily_sum(stand_metric)
    stand_hours = stand_hours / 60
    
    # 8. 血氧
    spo2_metric = metrics_18.get('oxygen_saturation')
    spo2_avg, spo2_count = get_daily_avg(spo2_metric)
    spo2_pct = spo2_avg * 100
    
    # 9. 静息能量
    resting_energy_metric = metrics_18.get('basal_energy_burned')
    resting_energy, _ = get_daily_sum(resting_energy_metric)
    resting_energy_kcal = resting_energy / 1000
    
    # 10. 呼吸率
    resp_metric = metrics_18.get('respiratory_rate')
    resp_rate, resp_count = get_daily_avg(resp_metric)
    
    # 睡眠数据（从2月19日文件）
    sleep_data = get_sleep_data(data_19)
    
    # 锻炼数据
    workouts = check_workout(data_18, data_19)
    
    # 计算评分
    recovery_score = min(100, int(50 + (hrv_avg - 30) * 1.5)) if hrv_avg > 0 else 50
    sleep_score = min(100, int(sleep_data['total_hours'] * 12.5)) if sleep_data else 30
    exercise_score = min(100, int(steps / 100)) if steps > 0 else 20
    
    # 读取模板
    with open(TEMPLATE_PATH, 'r', encoding='utf-8') as f:
        template = f.read()
    
    # 填充模板
    html = template
    
    # 基础信息
    html = html.replace('{{DATE}}', date_str)
    html = html.replace('{{HEADER_SUBTITLE}}', f'{date_str} · Apple Health | UTC+8')
    
    # 评分卡
    html = html.replace('{{SCORE_RECOVERY}}', str(recovery_score))
    html = html.replace('{{SCORE_SLEEP}}', str(sleep_score))
    html = html.replace('{{SCORE_EXERCISE}}', str(exercise_score))
    
    # 评分徽章
    def get_badge(score):
        if score >= 80:
            return 'badge-excellent', '优秀'
        elif score >= 60:
            return 'badge-good', '良好'
        elif score >= 40:
            return 'badge-average', '一般'
        else:
            return 'badge-poor', '需改善'
    
    rec_class, rec_text = get_badge(recovery_score)
    sleep_class, sleep_text = get_badge(sleep_score)
    ex_class, ex_text = get_badge(exercise_score)
    
    html = html.replace('{{BADGE_RECOVERY_CLASS}}', rec_class)
    html = html.replace('{{BADGE_RECOVERY_TEXT}}', rec_text)
    html = html.replace('{{BADGE_SLEEP_CLASS}}', sleep_class)
    html = html.replace('{{BADGE_SLEEP_TEXT}}', sleep_text)
    html = html.replace('{{BADGE_EXERCISE_CLASS}}', ex_class)
    html = html.replace('{{BADGE_EXERCISE_TEXT}}', ex_text)
    
    # 指标数据
    # 1. HRV
    html = html.replace('{{METRIC1_VALUE}}', f"{hrv_avg:.1f} ms<br><small>{hrv_count}个数据点</small>")
    html = html.replace('{{METRIC1_RATING_CLASS}}', 'rating-good' if hrv_avg > 40 else 'rating-average')
    html = html.replace('{{METRIC1_RATING}}', '正常' if hrv_avg > 40 else '偏低')
    html = html.replace('{{METRIC1_ANALYSIS}}', 
        f"今日HRV均值为{hrv_avg:.1f}ms（基于{hrv_count}次测量），"
        f"{'处于正常范围，表明自主神经系统功能良好，身体恢复能力正常。' if hrv_avg > 40 else '略低于理想水平，可能与睡眠不足或轻度压力有关。'}"
        f"建议关注休息质量，保持规律作息。"
    )
    
    # 2. 静息心率
    html = html.replace('{{METRIC2_VALUE}}', f"{resting_hr:.0f} bpm")
    html = html.replace('{{METRIC2_RATING_CLASS}}', 'rating-good' if 50 <= resting_hr <= 70 else 'rating-average')
    html = html.replace('{{METRIC2_RATING}}', '正常' if 50 <= resting_hr <= 70 else '需关注')
    html = html.replace('{{METRIC2_ANALYSIS}}', 
        f"静息心率{resting_hr:.0f}bpm，"
        f"{'处于健康范围内，心脏功能良好。' if 50 <= resting_hr <= 70 else '略高于理想范围，建议关注心血管健康。'}"
    )
    
    # 3. 步数
    html = html.replace('{{METRIC3_VALUE}}', f"{steps:,} 步<br><small>{steps_count}个记录</small>")
    html = html.replace('{{METRIC3_RATING_CLASS}}', 'rating-good' if steps >= 8000 else 'rating-average')
    html = html.replace('{{METRIC3_RATING}}', '达标' if steps >= 8000 else '偏低')
    html = html.replace('{{METRIC3_ANALYSIS}}', 
        f"今日步行{steps:,}步，"
        f"{'达到每日建议活动量，对维持基础代谢和心血管健康有益。' if steps >= 8000 else '低于建议的8000步目标，建议增加日常活动量。'}"
    )
    
    # 4. 行走距离
    html = html.replace('{{METRIC4_VALUE}}', f"{distance_km:.2f} km")
    html = html.replace('{{METRIC4_RATING_CLASS}}', 'rating-good' if distance_km >= 5 else 'rating-average')
    html = html.replace('{{METRIC4_RATING}}', '良好' if distance_km >= 5 else '一般')
    html = html.replace('{{METRIC4_ANALYSIS}}', 
        f"行走距离{distance_km:.2f}公里，"
        f"{'活动量充足，有助于维持下肢肌肉力量和关节灵活性。' if distance_km >= 5 else '建议适当增加步行距离以提升心肺功能。'}"
    )
    
    # 5. 活动能量
    html = html.replace('{{METRIC5_VALUE}}', f"{energy_kcal:.0f} kcal")
    html = html.replace('{{METRIC5_RATING_CLASS}}', 'rating-good' if energy_kcal >= 300 else 'rating-average')
    html = html.replace('{{METRIC5_RATING}}', '活跃' if energy_kcal >= 300 else '偏低')
    html = html.replace('{{METRIC5_ANALYSIS}}', 
        f"活动能量消耗{energy_kcal:.0f}千卡，"
        f"{'今日身体活动较为活跃，有助于热量平衡和代谢健康。' if energy_kcal >= 300 else '活动消耗偏低，建议增加运动强度。'}"
    )
    
    # 6. 爬楼层数
    html = html.replace('{{METRIC6_VALUE}}', f"{floors} 层")
    html = html.replace('{{METRIC6_RATING_CLASS}}', 'rating-good' if floors >= 5 else 'rating-average')
    html = html.replace('{{METRIC6_RATING}}', '良好' if floors >= 5 else '一般')
    html = html.replace('{{METRIC6_ANALYSIS}}', 
        f"今日爬楼{floors}层，"
        f"{'垂直活动充足，有助于下肢力量训练。' if floors >= 5 else '垂直活动较少，建议多使用楼梯代替电梯。'}"
    )
    
    # 7. 站立时间
    html = html.replace('{{METRIC7_VALUE}}', f"{stand_hours:.1f} h")
    html = html.replace('{{METRIC7_RATING_CLASS}}', 'rating-good' if stand_hours >= 8 else 'rating-average')
    html = html.replace('{{METRIC7_RATING}}', '达标' if stand_hours >= 8 else '不足')
    html = html.replace('{{METRIC7_ANALYSIS}}', 
        f"站立时间{stand_hours:.1f}小时，"
        f"{'站立活动充足，有助于减少久坐带来的健康风险。' if stand_hours >= 8 else '站立时间不足，建议每小时起身活动。'}"
    )
    
    # 8. 血氧
    html = html.replace('{{METRIC8_VALUE}}', f"{spo2_pct:.1f}%<br><small>{spo2_count}次测量</small>" if spo2_count > 0 else "无数据")
    html = html.replace('{{METRIC8_RATING_CLASS}}', 'rating-good' if spo2_pct >= 95 else 'rating-poor' if spo2_count > 0 else 'rating-average')
    html = html.replace('{{METRIC8_RATING}}', '正常' if spo2_pct >= 95 else '偏低' if spo2_count > 0 else '无数据')
    html = html.replace('{{METRIC8_ANALYSIS}}', 
        f"血氧饱和度{spo2_pct:.1f}%（{spo2_count}次测量），"
        f"{'处于正常范围，血液携氧能力良好。' if spo2_pct >= 95 else '略低于理想水平，建议关注呼吸健康。' if spo2_count > 0 else '当日无血氧数据记录。'}"
    )
    
    # 9. 静息能量
    html = html.replace('{{METRIC9_VALUE}}', f"{resting_energy_kcal:.0f} kcal")
    html = html.replace('{{METRIC9_RATING_CLASS}}', 'rating-good')
    html = html.replace('{{METRIC9_RATING}}', '正常')
    html = html.replace('{{METRIC9_ANALYSIS}}', 
        f"静息能量消耗约{resting_energy_kcal:.0f}千卡，"
        f"反映基础代谢水平正常。这是维持生命体征所需的最低能量消耗。"
    )
    
    # 10. 呼吸率
    html = html.replace('{{METRIC10_VALUE}}', f"{resp_rate:.1f} 次/分<br><small>{resp_count}次测量</small>" if resp_count > 0 else "无数据")
    html = html.replace('{{METRIC10_RATING_CLASS}}', 'rating-good' if 12 <= resp_rate <= 20 else 'rating-average' if resp_count > 0 else 'rating-average')
    html = html.replace('{{METRIC10_RATING}}', '正常' if 12 <= resp_rate <= 20 else '需关注' if resp_count > 0 else '无数据')
    html = html.replace('{{METRIC10_ANALYSIS}}', 
        f"呼吸率{resp_rate:.1f}次/分钟（{resp_count}次测量），"
        f"{'处于正常成人范围，呼吸功能良好。' if 12 <= resp_rate <= 20 else '建议关注呼吸模式。' if resp_count > 0 else '当日无呼吸率数据记录。'}"
    )
    
    # 睡眠部分
    if sleep_data:
        sleep_total = sleep_data['total_hours']
        sleep_deep = sleep_data['deep_hours']
        sleep_core = sleep_data['core_hours']
        sleep_rem = sleep_data['rem_hours']
        sleep_awake = max(0, sleep_total - sleep_deep - sleep_core - sleep_rem)
        
        # 计算百分比
        deep_pct = int(sleep_deep / sleep_total * 100) if sleep_total > 0 else 0
        core_pct = int(sleep_core / sleep_total * 100) if sleep_total > 0 else 0
        rem_pct = int(sleep_rem / sleep_total * 100) if sleep_total > 0 else 0
        awake_pct = int(sleep_awake / sleep_total * 100) if sleep_total > 0 else 0
        
        html = html.replace('{{SLEEP_STATUS}}', '数据完整')
        html = html.replace('{{SLEEP_ALERT_BG}}', '#f0fdf4')
        html = html.replace('{{SLEEP_ALERT_BORDER}}', '#86efac')
        html = html.replace('{{SLEEP_ALERT_COLOR}}', '#166534')
        html = html.replace('{{SLEEP_ALERT_SUBCOLOR}}', '#15803d')
        html = html.replace('{{SLEEP_ALERT_TITLE}}', '✅ 睡眠记录正常')
        html = html.replace('{{SLEEP_ALERT_DETAIL}}', 
            f"入睡时间：{sleep_data['bed_time'].strftime('%H:%M')} | "
            f"醒来时间：{sleep_data['wake_time'].strftime('%H:%M')} | "
            f"总睡眠：{sleep_total:.1f}小时"
        )
        
        html = html.replace('{{SLEEP_TOTAL}}', f"{sleep_total:.1f}")
        html = html.replace('{{SLEEP_DEEP}}', f"{sleep_deep:.1f}")
        html = html.replace('{{SLEEP_CORE}}', f"{sleep_core:.1f}")
        html = html.replace('{{SLEEP_REM}}', f"{sleep_rem:.1f}")
        html = html.replace('{{SLEEP_AWAKE}}', f"{sleep_awake:.1f}")
        
        html = html.replace('{{SLEEP_DEEP_PCT}}', str(deep_pct))
        html = html.replace('{{SLEEP_CORE_PCT}}', str(core_pct))
        html = html.replace('{{SLEEP_REM_PCT}}', str(rem_pct))
        html = html.replace('{{SLEEP_AWAKE_PCT}}', str(awake_pct))
        
        html = html.replace('{{SLEEP_ANALYSIS_BORDER}}', '#667eea')
        html = html.replace('{{SLEEP_ANALYSIS_TEXT}}',
            f"昨晚总睡眠时长{sleep_total:.1f}小时，"
            f"入睡时间为{sleep_data['bed_time'].strftime('%H:%M')}，"
            f"醒来时间为{sleep_data['wake_time'].strftime('%H:%M')}。"
            f"{'睡眠时长充足，有助于身体恢复。' if sleep_total >= 7 else '睡眠时长偏短，建议今晚提前入睡。'}"
        )
    else:
        html = html.replace('{{SLEEP_STATUS}}', '数据缺失')
        html = html.replace('{{SLEEP_ALERT_BG}}', '#fef3c7')
        html = html.replace('{{SLEEP_ALERT_BORDER}}', '#fcd34d')
        html = html.replace('{{SLEEP_ALERT_COLOR}}', '#92400e')
        html = html.replace('{{SLEEP_ALERT_SUBCOLOR}}', '#b45309')
        html = html.replace('{{SLEEP_ALERT_TITLE}}', '⚠️ 睡眠数据不完整')
        html = html.replace('{{SLEEP_ALERT_DETAIL}}', '未检测到完整的睡眠记录，请确保佩戴设备入睡')
        html = html.replace('{{SLEEP_TOTAL}}', '0')
        html = html.replace('{{SLEEP_DEEP}}', '0')
        html = html.replace('{{SLEEP_CORE}}', '0')
        html = html.replace('{{SLEEP_REM}}', '0')
        html = html.replace('{{SLEEP_AWAKE}}', '0')
        html = html.replace('{{SLEEP_DEEP_PCT}}', '0')
        html = html.replace('{{SLEEP_CORE_PCT}}', '0')
        html = html.replace('{{SLEEP_REM_PCT}}', '0')
        html = html.replace('{{SLEEP_AWAKE_PCT}}', '0')
        html = html.replace('{{SLEEP_ANALYSIS_BORDER}}', '#f59e0b')
        html = html.replace('{{SLEEP_ANALYSIS_TEXT}}', '当日无完整睡眠数据记录，建议检查设备佩戴情况。')
    
    # 运动记录
    if workouts:
        workout = workouts[0]  # 取第一个运动
        html = html.replace('{{WORKOUT_NAME}}', workout.get('name', '未知运动'))
        html = html.replace('{{WORKOUT_TIME}}', workout.get('start', '')[:16])
        
        duration = workout.get('duration', 0)
        duration_min = int(duration / 60) if duration else 0
        
        html = html.replace('{{WORKOUT_DURATION}}', str(duration_min))
        html = html.replace('{{WORKOUT_ENERGY}}', f"{workout.get('energy', 0):.0f}")
        html = html.replace('{{WORKOUT_AVG_HR}}', f"{workout.get('heart_rate_avg', 0):.0f}")
        html = html.replace('{{WORKOUT_MAX_HR}}', f"{workout.get('heart_rate_max', 0):.0f}")
        
        html = html.replace('{{WORKOUT_ANALYSIS}}',
            f"今日进行了{workout.get('name', '运动')}，"
            f"时长{duration_min}分钟，消耗{workout.get('energy', 0):.0f}千卡。"
            f"平均心率{workout.get('heart_rate_avg', 0):.0f}bpm，"
            f"最高心率{workout.get('heart_rate_max', 0):.0f}bpm。"
            f"运动强度适中，有助于心肺功能提升。"
        )
    else:
        html = html.replace('{{WORKOUT_NAME}}', '今日无锻炼记录')
        html = html.replace('{{WORKOUT_TIME}}', '-')
        html = html.replace('{{WORKOUT_DURATION}}', '-')
        html = html.replace('{{WORKOUT_ENERGY}}', '-')
        html = html.replace('{{WORKOUT_AVG_HR}}', '-')
        html = html.replace('{{WORKOUT_MAX_HR}}', '-')
        html = html.replace('{{WORKOUT_ANALYSIS}}', 
            '今日未记录到专门的运动锻炼。建议保持日常活动，如有可能可安排轻度运动如散步、伸展等。'
        )
    
    # AI建议
    html = html.replace('{{AI1_TITLE}}', '睡眠优化')
    html = html.replace('{{AI1_PROBLEM}}', 
        f"{'昨晚睡眠时长{:.1f}小时，略短于推荐的7-8小时。'.format(sleep_data['total_hours']) if sleep_data and sleep_data['total_hours'] < 7 else '睡眠质量有待提升，建议优化睡前习惯。'}"
    )
    html = html.replace('{{AI1_ACTION}}',
        '1. 今晚尝试提前30分钟上床\n'
        '2. 睡前1小时避免使用电子屏幕\n'
        '3. 保持卧室温度在18-22°C\n'
        '4. 如有条件，可进行10分钟冥想放松'
    )
    html = html.replace('{{AI1_EXPECTATION}}', '坚持一周后，睡眠质量和日间精力将有明显改善。')
    
    html = html.replace('{{AI2_TITLE}}', '日常活动提升')
    html = html.replace('{{AI2_PROBLEM}}',
        f"{'今日步数{:,}，距离目标还有差距。'.format(steps) if steps < 8000 else '活动量达标，可尝试增加运动多样性。'}"
    )
    html = html.replace('{{AI2_ACTION}}',
        '1. 每小时起身活动5分钟\n'
        '2. 午休时间进行15分钟散步\n'
        '3. 尽量选择楼梯而非电梯\n'
        '4. 晚饭后散步20-30分钟'
    )
    html = html.replace('{{AI2_EXPECTATION}}', '2周内形成习惯，基础代谢和心肺功能将有提升。')
    
    html = html.replace('{{AI3_TITLE}}', '健康生活方式')
    html = html.replace('{{AI3_DIET}}',
        '建议保持均衡饮食，多摄入蔬菜水果，控制精制糖和饱和脂肪摄入。'
    )
    html = html.replace('{{AI3_ROUTINE}}',
        '保持规律作息，固定睡眠时间。工作间隙进行眼部放松和肩颈伸展。'
    )
    
    html = html.replace('{{AI4_TITLE}}', '整体健康评估')
    html = html.replace('{{AI4_ADVANTAGES}}',
        f"心率变异性{'良好' if hrv_avg > 40 else '正常'}，自主神经功能稳定。静息心率处于健康范围。"
    )
    html = html.replace('{{AI4_RISKS}}',
        f"{'睡眠时长需关注，可能影响日间精力。' if sleep_data and sleep_data['total_hours'] < 7 else ''}"
        f"{'步数偏低，建议增加日常活动。' if steps < 6000 else ''}"
    )
    html = html.replace('{{AI4_CONCLUSION}}',
        '整体健康状况良好，主要指标在正常范围内。建议关注睡眠质量和日常活动量的平衡。'
    )
    html = html.replace('{{AI4_PLAN}}',
        '本周重点：1)优化睡眠习惯 2)增加日常步行 3)保持规律作息 4)监测HRV变化趋势'
    )
    
    # 页脚
    html = html.replace('{{FOOTER_DATA_SOURCES}}', 
        f'Apple Watch • {hrv_count}次HRV • {steps_count}条步数记录'
    )
    html = html.replace('{{FOOTER_DATE}}', datetime.now().strftime('%Y-%m-%d %H:%M'))
    
    # 确保输出目录存在
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # 保存HTML
    html_path = os.path.join(OUTPUT_DIR, f"{date_str}_report.html")
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"✅ HTML已保存: {html_path}")
    
    # 生成PDF
    pdf_path = os.path.join(OUTPUT_DIR, f"{date_str}_report.pdf")
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.set_content(html)
        page.wait_for_timeout(2000)  # 等待渲染
        page.pdf(
            path=pdf_path,
            format='A4',
            print_background=True,
            margin={'top': '8mm', 'bottom': '8mm', 'left': '8mm', 'right': '8mm'}
        )
        browser.close()
    
    print(f"✅ PDF已生成: {pdf_path}")
    return pdf_path

if __name__ == '__main__':
    generate_report()
