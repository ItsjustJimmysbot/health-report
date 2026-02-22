#!/usr/bin/env python3
"""
V5.0 Report Generator - 使用AI生成的完整分析内容
所有指标分析和AI建议都从JSON文件读取，不使用模板填充
"""
import json
from pathlib import Path
from datetime import datetime

def calc_recovery_score(hrv, resting_hr, sleep_hours):
    """计算恢复度评分"""
    score = 70
    if hrv and hrv > 50: score += 10
    if resting_hr and resting_hr < 65: score += 10
    if sleep_hours and sleep_hours >= 7: score += 10
    return min(100, score)

def calc_sleep_score(sleep_hours):
    """计算睡眠评分"""
    if sleep_hours == 0: return 0
    if sleep_hours < 6: return 30
    if sleep_hours < 7: return 50
    if sleep_hours < 8: return 70
    return 80

def calc_exercise_score(steps, has_workout, energy_kcal):
    """计算运动评分"""
    score = 50
    if steps > 5000: score += 10
    if steps > 8000: score += 10
    if steps > 10000: score += 10
    if has_workout: score += 15
    if energy_kcal > 500: score += 10
    return min(100, score)

def get_rating_class(score):
    """获取评分对应的CSS类"""
    if score >= 80:
        return 'rating-excellent', 'badge-excellent', '优秀'
    elif score >= 60:
        return 'rating-good', 'badge-good', '良好'
    elif score >= 40:
        return 'rating-average', 'badge-average', '一般'
    else:
        return 'rating-poor', 'badge-poor', '需改善'

def generate_hr_chart(workout):
    """生成Chart.js心率图表"""
    if not workout:
        return ''
    
    hr_data = workout.get('hr_data', [])
    if not hr_data:
        return ''
    
    times = []
    avg_hrs = []
    max_hrs = []
    
    for hr in hr_data:
        time_str = hr.get('date', '').split(' ')[1][:5] if hr.get('date') else ''
        if time_str and time_str not in times:
            times.append(time_str)
            avg_hrs.append(round(hr.get('Avg', 0)))
            max_hrs.append(round(hr.get('Max', 0)))
    
    if len(times) < 3:
        return ''
    
    times_str = ', '.join([f"'{t}'" for t in times[::2]])
    avg_str = ', '.join(map(str, avg_hrs[::2]))
    max_str = ', '.join(map(str, max_hrs[::2]))
    
    return f'''<div style="height:150px;">
  <canvas id="hrChart"></canvas>
</div>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<script>
  new Chart(document.getElementById('hrChart'), {{
    type: 'line',
    data: {{
      labels: [{times_str}],
      datasets: [
        {{label: '平均心率', data: [{avg_str}], borderColor: '#667eea', backgroundColor: 'rgba(102,126,234,0.1)', tension: 0.3, fill: true, pointRadius: 2}},
        {{label: '最高心率', data: [{max_str}], borderColor: '#dc2626', backgroundColor: 'rgba(220,38,38,0.05)', tension: 0.3, fill: false, pointRadius: 2}}
      ]
    }},
    options: {{
      responsive: true,
      maintainAspectRatio: false,
      plugins: {{legend: {{display: true, position: 'top', labels: {{font: {{size: 8}}, boxWidth: 10}}}}}},
      scales: {{
        y: {{min: {min(avg_hrs)-10}, max: {max(max_hrs)+10}, ticks: {{font: {{size: 7}}}}}},
        x: {{ticks: {{font: {{size: 7}}, maxRotation: 45}}}}
      }}
    }}
  }});
</script>
'''

def generate_report(data, template_path, output_path):
    """使用V2模板生成报告 - 所有分析内容从JSON读取"""
    
    with open(template_path, 'r', encoding='utf-8') as f:
        html = f.read()
    
    # 计算评分
    sleep_hours = data['sleep']['total_hours'] if data['sleep'] else 0
    recovery_score = calc_recovery_score(
        data['hrv']['value'],
        data['resting_hr']['value'],
        sleep_hours
    )
    sleep_score = calc_sleep_score(sleep_hours)
    
    has_workout = len(data.get('workouts', [])) > 0
    workout_energy = data['workouts'][0]['energy_kcal'] if has_workout else 0
    exercise_score = calc_exercise_score(
        data['steps']['value'],
        has_workout,
        workout_energy
    )
    
    # 评分CSS类
    recovery_rclass, recovery_bclass, recovery_text = get_rating_class(recovery_score)
    sleep_rclass, sleep_bclass, sleep_text = get_rating_class(sleep_score)
    exercise_rclass, exercise_bclass, exercise_text = get_rating_class(exercise_score)
    
    # 睡眠数据 - 只使用真实数据
    sleep_deep = data['sleep'].get('deep_hours', 0)
    sleep_core = data['sleep'].get('core_hours', 0)
    sleep_rem = data['sleep'].get('rem_hours', 0)
    sleep_awake = data['sleep'].get('awake_hours', 0)
    
    # 运动数据
    workout = data['workouts'][0] if has_workout else None
    hr_chart = generate_hr_chart(workout)
    
    # AI建议
    rec = data.get('ai_recommendations', {})
    high = rec.get('high_priority', {})
    medium = rec.get('medium_priority', {})
    routine = rec.get('routine', {})
    summary = rec.get('summary', {})
    
    # 变量替换 - 所有分析内容从JSON读取（AI生成）
    replacements = {
        '{{DATE}}': data['date'],
        '{{HEADER_SUBTITLE}}': f'{data["date"]} 健康数据分析报告',
        
        # 评分卡
        '{{SCORE_RECOVERY}}': str(recovery_score),
        '{{BADGE_RECOVERY_CLASS}}': recovery_bclass,
        '{{BADGE_RECOVERY_TEXT}}': recovery_text,
        '{{SCORE_SLEEP}}': str(sleep_score),
        '{{BADGE_SLEEP_CLASS}}': sleep_bclass,
        '{{BADGE_SLEEP_TEXT}}': sleep_text,
        '{{SCORE_EXERCISE}}': str(exercise_score),
        '{{BADGE_EXERCISE_CLASS}}': exercise_bclass,
        '{{BADGE_EXERCISE_TEXT}}': exercise_text,
        
        # 指标1: HRV - AI生成分析
        '{{METRIC1_VALUE}}': f"{data['hrv']['value']:.1f}ms ({data['hrv']['points']}点)" if data['hrv']['value'] else '--',
        '{{METRIC1_RATING_CLASS}}': 'rating-good' if data['hrv']['value'] > 50 else 'rating-average',
        '{{METRIC1_RATING}}': '良好' if data['hrv']['value'] > 50 else '一般',
        '{{METRIC1_ANALYSIS}}': data['hrv'].get('analysis', '暂无分析'),
        
        # 指标2: 静息心率 - AI生成分析
        '{{METRIC2_VALUE}}': f"{data['resting_hr']['value']}bpm" if data['resting_hr']['value'] else '--',
        '{{METRIC2_RATING_CLASS}}': 'rating-excellent' if data['resting_hr']['value'] < 60 else 'rating-good',
        '{{METRIC2_RATING}}': '优秀' if data['resting_hr']['value'] < 60 else '良好',
        '{{METRIC2_ANALYSIS}}': data['resting_hr'].get('analysis', '暂无分析'),
        
        # 指标3: 步数 - AI生成分析
        '{{METRIC3_VALUE}}': f"{data['steps']['value']:,}步",
        '{{METRIC3_RATING_CLASS}}': 'rating-good' if data['steps']['value'] > 8000 else 'rating-average' if data['steps']['value'] > 5000 else 'rating-poor',
        '{{METRIC3_RATING}}': '良好' if data['steps']['value'] > 8000 else '一般' if data['steps']['value'] > 5000 else '需改善',
        '{{METRIC3_ANALYSIS}}': data['steps'].get('analysis', '暂无分析'),
        
        # 指标4: 行走距离 - AI生成分析
        '{{METRIC4_VALUE}}': f"{data['walking_distance']['value']:.2f}km ({data['walking_distance']['points']}点)" if data.get('walking_distance', {}).get('value') else '--',
        '{{METRIC4_RATING_CLASS}}': 'rating-good',
        '{{METRIC4_RATING}}': '良好',
        '{{METRIC4_ANALYSIS}}': data['walking_distance'].get('analysis', '暂无分析') if data.get('walking_distance') else '暂无分析',
        
        # 指标5: 活动能量 - AI生成分析
        '{{METRIC5_VALUE}}': f"{data['active_energy']['value']:.1f}kcal" if data.get('active_energy', {}).get('value') else '--',
        '{{METRIC5_RATING_CLASS}}': 'rating-good' if data['active_energy']['value'] > 200 else 'rating-average',
        '{{METRIC5_RATING}}': '良好' if data['active_energy']['value'] > 200 else '一般',
        '{{METRIC5_ANALYSIS}}': data['active_energy'].get('analysis', '暂无分析') if data.get('active_energy') else '暂无分析',
        
        # 指标6: 爬楼层数 - AI生成分析
        '{{METRIC6_VALUE}}': f"{data['flights_climbed']['value']:.0f}层" if data.get('flights_climbed', {}).get('value') else '--',
        '{{METRIC6_RATING_CLASS}}': 'rating-excellent' if data['flights_climbed']['value'] > 50 else 'rating-good' if data['flights_climbed']['value'] > 10 else 'rating-average',
        '{{METRIC6_RATING}}': '优秀' if data['flights_climbed']['value'] > 50 else '良好' if data['flights_climbed']['value'] > 10 else '一般',
        '{{METRIC6_ANALYSIS}}': data['flights_climbed'].get('analysis', '暂无分析') if data.get('flights_climbed') else '暂无分析',
        
        # 指标7: 站立时间 - AI生成分析
        '{{METRIC7_VALUE}}': f"{data['stand_time']['value']:.0f}min" if data.get('stand_time', {}).get('value') else '--',
        '{{METRIC7_RATING_CLASS}}': 'rating-good' if data['stand_time']['value'] > 120 else 'rating-average',
        '{{METRIC7_RATING}}': '良好' if data['stand_time']['value'] > 120 else '一般',
        '{{METRIC7_ANALYSIS}}': data['stand_time'].get('analysis', '暂无分析') if data.get('stand_time') else '暂无分析',
        
        # 指标8: 血氧饱和度 - AI生成分析
        '{{METRIC8_VALUE}}': f"{data['spo2']['value']}%" if data['spo2']['value'] else '--',
        '{{METRIC8_RATING_CLASS}}': 'rating-excellent' if data['spo2']['value'] >= 95 else 'rating-good',
        '{{METRIC8_RATING}}': '正常',
        '{{METRIC8_ANALYSIS}}': data['spo2'].get('analysis', '暂无分析') if data.get('spo2') else '暂无分析',
        
        # 指标9: 静息能量 - AI生成分析
        '{{METRIC9_VALUE}}': f"{data['basal_energy']['value']:.1f}kcal" if data.get('basal_energy', {}).get('value') else '--',
        '{{METRIC9_RATING_CLASS}}': 'rating-good',
        '{{METRIC9_RATING}}': '正常',
        '{{METRIC9_ANALYSIS}}': data['basal_energy'].get('analysis', '暂无分析') if data.get('basal_energy') else '暂无分析',
        
        # 指标10: 呼吸率 - AI生成分析
        '{{METRIC10_VALUE}}': f"{data['respiratory_rate']['value']:.1f}次/分" if data.get('respiratory_rate', {}).get('value') else '--',
        '{{METRIC10_RATING_CLASS}}': 'rating-good',
        '{{METRIC10_RATING}}': '正常',
        '{{METRIC10_ANALYSIS}}': data['respiratory_rate'].get('analysis', '暂无分析') if data.get('respiratory_rate') else '暂无分析',
        
        # 睡眠分析
        '{{SLEEP_STATUS}}': '严重不足' if sleep_hours < 6 else '偏少' if sleep_hours < 7 else '正常',
        '{{SLEEP_ALERT_BG}}': '#fee2e2' if sleep_hours < 6 else '#fef3c7' if sleep_hours < 7 else '#dcfce7',
        '{{SLEEP_ALERT_BORDER}}': '#ef4444' if sleep_hours < 6 else '#f59e0b' if sleep_hours < 7 else '#22c55e',
        '{{SLEEP_ALERT_COLOR}}': '#991b1b' if sleep_hours < 6 else '#92400e' if sleep_hours < 7 else '#166534',
        '{{SLEEP_ALERT_SUBCOLOR}}': '#7f1d1d' if sleep_hours < 6 else '#78350f' if sleep_hours < 7 else '#14532d',
        '{{SLEEP_ALERT_TITLE}}': '⚠️ 睡眠时长严重不足' if sleep_hours < 6 else '⚡ 睡眠时长偏少' if sleep_hours < 7 else '✅ 睡眠时长正常',
        '{{SLEEP_ALERT_DETAIL}}': f'实际睡眠{sleep_hours:.1f}小时，远低于7-9小时推荐标准' if sleep_hours < 6 else f'实际睡眠{sleep_hours:.1f}小时，建议增加至7-8小时' if sleep_hours < 7 else f'实际睡眠{sleep_hours:.1f}小时，处于推荐范围内',
        '{{SLEEP_TOTAL}}': f"{sleep_hours:.1f}",
        '{{SLEEP_DEEP}}': f"{sleep_deep:.1f}" if sleep_deep > 0 else '--',
        '{{SLEEP_CORE}}': f"{sleep_core:.1f}" if sleep_core > 0 else '--',
        '{{SLEEP_REM}}': f"{sleep_rem:.1f}" if sleep_rem > 0 else '--',
        '{{SLEEP_AWAKE}}': f"{sleep_awake:.1f}" if sleep_awake > 0 else '--',
        '{{SLEEP_DEEP_PCT}}': str(round(sleep_deep / sleep_hours * 100)) if sleep_deep > 0 and sleep_hours > 0 else '--',
        '{{SLEEP_CORE_PCT}}': str(round(sleep_core / sleep_hours * 100)) if sleep_core > 0 and sleep_hours > 0 else '--',
        '{{SLEEP_REM_PCT}}': str(round(sleep_rem / sleep_hours * 100)) if sleep_rem > 0 and sleep_hours > 0 else '--',
        '{{SLEEP_AWAKE_PCT}}': str(round(sleep_awake / sleep_hours * 100)) if sleep_awake > 0 and sleep_hours > 0 else '--',
        '{{SLEEP_ANALYSIS_BORDER}}': '#ef4444' if sleep_hours < 6 else '#f59e0b' if sleep_hours < 7 else '#22c55e',
        '{{SLEEP_ANALYSIS_TEXT}}': data['sleep'].get('analysis', '暂无分析') if data.get('sleep') else '暂无分析',
        
        # 运动记录
        '{{WORKOUT_NAME}}': workout['name'] if workout else '无',
        '{{WORKOUT_TIME}}': workout['start'].split(' ')[1][:5] if workout else '--',
        '{{WORKOUT_DURATION}}': str(round(workout['duration_min'], 1)) if workout else '--',
        '{{WORKOUT_ENERGY}}': str(workout['energy_kcal']) if workout else '--',
        '{{WORKOUT_AVG_HR}}': f"{workout['avg_hr']}bpm" if workout else '--',
        '{{WORKOUT_MAX_HR}}': f"{workout['max_hr']}bpm" if workout else '--',
        '{{WORKOUT_HR_CHART}}': hr_chart,
        '{{WORKOUT_ANALYSIS}}': workout.get('analysis', '今日无运动记录') if workout else '今日无运动记录',
        
        # AI建议 - 全部从JSON读取（AI生成）
        '{{AI1_TITLE}}': high.get('title', '暂无'),
        '{{AI1_PROBLEM}}': high.get('problem', '暂无'),
        '{{AI1_ACTION}}': high.get('action', '暂无'),
        '{{AI1_EXPECTATION}}': high.get('expected', '暂无'),
        
        '{{AI2_TITLE}}': medium.get('title', '暂无'),
        '{{AI2_PROBLEM}}': medium.get('problem', '暂无'),
        '{{AI2_ACTION}}': medium.get('action', '暂无'),
        '{{AI2_EXPECTATION}}': medium.get('expected', '暂无'),
        
        '{{AI3_TITLE}}': routine.get('title', '暂无'),
        '{{AI3_DIET}}': routine.get('diet', '暂无'),
        '{{AI3_ROUTINE}}': routine.get('schedule', '暂无'),
        
        '{{AI4_TITLE}}': summary.get('title', '暂无'),
        '{{AI4_ADVANTAGES}}': summary.get('advantages', '暂无'),
        '{{AI4_RISKS}}': summary.get('risks', '暂无'),
        '{{AI4_CONCLUSION}}': summary.get('conclusion', '暂无'),
        '{{AI4_PLAN}}': summary.get('plan', '暂无'),
        
        # 页脚
        '{{FOOTER_DATA_SOURCES}}': f'数据来源: {data.get("data_source", "Apple Health")}',
        '{{FOOTER_DATE}}': datetime.now().strftime('%Y-%m-%d %H:%M'),
    }
    
    # 替换所有变量
    for key, value in replacements.items():
        html = html.replace(key, str(value))
    
    # 检查未替换变量
    import re
    unreplaced = re.findall(r'\{\{[^}]+\}\}', html)
    if unreplaced:
        print(f"⚠️ 未替换变量: {unreplaced}")
    
    # 写入文件
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    return output_path

if __name__ == '__main__':
    import sys
    
    data_file = sys.argv[1] if len(sys.argv) > 1 else 'data.json'
    template_file = sys.argv[2] if len(sys.argv) > 2 else 'templates/DAILY_TEMPLATE_V2.html'
    output_file = sys.argv[3] if len(sys.argv) > 3 else 'report_v2.html'
    
    with open(data_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    result = generate_report(data, template_file, output_file)
    print(f"报告已生成: {result}")
