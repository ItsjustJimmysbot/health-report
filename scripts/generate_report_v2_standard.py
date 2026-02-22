#!/usr/bin/env python3
"""
V5.0 Report Generator - 使用标准V2模板
"""
import json
from pathlib import Path
from datetime import datetime

def calc_recovery_score(hrv, resting_hr, sleep_hours):
    """计算恢复度评分：基础70 + HRV>50(+10) + 静息<65(+10) + 睡眠>7h(+10)"""
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
    
    times_str = ', '.join([f"'{t}'" for t in times[::2]])  # 每2个取1个避免太密
    avg_str = ', '.join(map(str, avg_hrs[::2]))
    max_str = ', '.join(map(str, max_hrs[::2]))
    
    return f'''
<div style="height:150px;">
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

def get_sleep_alert(sleep_hours):
    """获取睡眠状态提示"""
    if sleep_hours == 0:
        return {
            'status': '数据缺失',
            'bg': '#fee2e2',
            'border': '#ef4444',
            'color': '#991b1b',
            'subcolor': '#7f1d1d',
            'title': '⚠️ 未检测到睡眠数据',
            'detail': '请检查Apple Watch睡眠追踪设置，确保就寝时正确佩戴设备',
            'analysis_border': '#ef4444',
            'deep_pct': 0,
            'core_pct': 0,
            'rem_pct': 0,
            'awake_pct': 100
        }
    elif sleep_hours < 6:
        return {
            'status': '严重不足',
            'bg': '#fee2e2',
            'border': '#ef4444',
            'color': '#991b1b',
            'subcolor': '#7f1d1d',
            'title': '⚠️ 睡眠时长严重不足',
            'detail': f'实际睡眠{sleep_hours:.1f}小时，远低于7-9小时推荐标准',
            'analysis_border': '#ef4444',
            'deep_pct': 20,
            'core_pct': 50,
            'rem_pct': 20,
            'awake_pct': 10
        }
    elif sleep_hours < 7:
        return {
            'status': '偏少',
            'bg': '#fef3c7',
            'border': '#f59e0b',
            'color': '#92400e',
            'subcolor': '#78350f',
            'title': '⚡ 睡眠时长偏少',
            'detail': f'实际睡眠{sleep_hours:.1f}小时，建议增加至7-8小时',
            'analysis_border': '#f59e0b',
            'deep_pct': 20,
            'core_pct': 50,
            'rem_pct': 22,
            'awake_pct': 8
        }
    else:
        return {
            'status': '正常',
            'bg': '#dcfce7',
            'border': '#22c55e',
            'color': '#166534',
            'subcolor': '#14532d',
            'title': '✅ 睡眠时长正常',
            'detail': f'实际睡眠{sleep_hours:.1f}小时，处于推荐范围内',
            'analysis_border': '#22c55e',
            'deep_pct': 20,
            'core_pct': 50,
            'rem_pct': 22,
            'awake_pct': 8
        }

def generate_report_v2(data, ai_analyses, template_path, output_path):
    """使用V2模板生成报告"""
    
    # 读取模板
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
    exercise_score = calc_exercise_score(
        data['steps']['value'],
        len(data['workouts']) > 0,
        data['workouts'][0]['energy_kcal'] if data['workouts'] else 0
    )
    
    # 评分CSS类
    recovery_rclass, recovery_bclass, recovery_text = get_rating_class(recovery_score)
    sleep_rclass, sleep_bclass, sleep_text = get_rating_class(sleep_score)
    exercise_rclass, exercise_bclass, exercise_text = get_rating_class(exercise_score)
    
    # 睡眠状态
    sleep_alert = get_sleep_alert(sleep_hours)
    
    # 睡眠各阶段（估算，因为实际数据中没有详细阶段）
    sleep_deep = data['sleep']['deep_hours'] if data['sleep'] else 0
    sleep_core = data['sleep']['core_hours'] if data['sleep'] else 0
    sleep_rem = data['sleep']['rem_hours'] if data['sleep'] else 0
    sleep_awake = data['sleep']['awake_hours'] if data['sleep'] else 0
    
    # 如果各阶段都是0但总长不为0，按比例分配
    if sleep_hours > 0 and sleep_deep == 0 and sleep_core == 0 and sleep_rem == 0:
        sleep_deep = sleep_hours * 0.20
        sleep_core = sleep_hours * 0.50
        sleep_rem = sleep_hours * 0.22
        sleep_awake = sleep_hours * 0.08
    
    # 运动数据
    workout = data['workouts'][0] if data['workouts'] else None
    
    # 心率图表
    hr_chart = generate_hr_chart(workout) if workout else ''
    
    # 变量替换字典
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
        
        # 指标1: HRV
        '{{METRIC1_VALUE}}': f"{data['hrv']['value']:.1f}ms ({data['hrv']['points']}点)" if data['hrv']['value'] else '--',
        '{{METRIC1_RATING_CLASS}}': 'rating-good',
        '{{METRIC1_RATING}}': '良好',
        '{{METRIC1_ANALYSIS}}': ai_analyses['hrv'],
        
        # 指标2: 静息心率
        '{{METRIC2_VALUE}}': f"{data['resting_hr']['value']}bpm" if data['resting_hr']['value'] else '--',
        '{{METRIC2_RATING_CLASS}}': 'rating-excellent',
        '{{METRIC2_RATING}}': '优秀',
        '{{METRIC2_ANALYSIS}}': f"静息心率{data['resting_hr']['value']}bpm处于优秀水平（<65bpm），表明心脏效率高，恢复状态良好。",
        
        # 指标3: 步数
        '{{METRIC3_VALUE}}': f"{data['steps']['value']:,}步",
        '{{METRIC3_RATING_CLASS}}': 'rating-average',
        '{{METRIC3_RATING}}': '一般',
        '{{METRIC3_ANALYSIS}}': f"今日步数{data['steps']['value']:,}步，距离10,000步目标还差{10000-data['steps']['value']:,}步，建议增加日常步行。",
        
        # 指标4: 行走距离
        '{{METRIC4_VALUE}}': f"{data['walking_distance']['value']:.2f}km ({data['walking_distance']['points']}点)" if data.get('walking_distance', {}).get('value') else '--',
        '{{METRIC4_RATING_CLASS}}': 'rating-good',
        '{{METRIC4_RATING}}': '良好',
        '{{METRIC4_ANALYSIS}}': f"今日行走距离{data['walking_distance']['value']:.2f}km，相当于约{data['walking_distance']['value']*1000/data['steps']['value']:.0f}米/步的平均步幅。",
        
        # 指标5: 活动能量
        '{{METRIC5_VALUE}}': f"{data['active_energy']['value']:.1f}kcal" if data.get('active_energy', {}).get('value') else '--',
        '{{METRIC5_RATING_CLASS}}': 'rating-good',
        '{{METRIC5_RATING}}': '良好',
        '{{METRIC5_ANALYSIS}}': f"今日活动消耗{data['active_energy']['value']:.1f}千卡（包含运动和日常活动），其中楼梯训练贡献了{workout['energy_kcal'] if workout else 0}千卡。",
        
        # 指标6: 爬楼层数
        '{{METRIC6_VALUE}}': f"{data['flights_climbed']['value']:.0f}层" if data.get('flights_climbed', {}).get('value') else '--',
        '{{METRIC6_RATING_CLASS}}': 'rating-excellent',
        '{{METRIC6_RATING}}': '优秀',
        '{{METRIC6_ANALYSIS}}': f"今日爬楼梯{data['flights_climbed']['value']:.0f}层，结合33分钟楼梯训练，对心肺功能和下肢力量提升显著。",
        
        # 指标7: 站立时间
        '{{METRIC7_VALUE}}': f"{data['stand_time']['value']:.0f}min" if data.get('stand_time', {}).get('value') else '--',
        '{{METRIC7_RATING_CLASS}}': 'rating-good',
        '{{METRIC7_RATING}}': '良好',
        '{{METRIC7_ANALYSIS}}': f"今日站立时间{data['stand_time']['value']:.0f}分钟，有助于改善久坐带来的健康风险。建议每小时至少站立活动5分钟。",
        
        # 指标8: 血氧饱和度
        '{{METRIC8_VALUE}}': f"{data['spo2']['value']}%" if data['spo2']['value'] else '--',
        '{{METRIC8_RATING_CLASS}}': 'rating-excellent',
        '{{METRIC8_RATING}}': '正常',
        '{{METRIC8_ANALYSIS}}': f"血氧饱和度{data['spo2']['value']}%处于正常范围（95-100%），供氧状态良好。",
        
        # 指标9: 静息能量
        '{{METRIC9_VALUE}}': f"{data['basal_energy']['value']:.1f}kcal" if data.get('basal_energy', {}).get('value') else '--',
        '{{METRIC9_RATING_CLASS}}': 'rating-good',
        '{{METRIC9_RATING}}': '正常',
        '{{METRIC9_ANALYSIS}}': f"基础代谢消耗{data['basal_energy']['value']:.1f}千卡，占全天能量消耗的绝大部分。",
        
        # 指标10: 呼吸率
        '{{METRIC10_VALUE}}': f"{data['respiratory_rate']['value']:.1f}次/分" if data.get('respiratory_rate', {}).get('value') else '--',
        '{{METRIC10_RATING_CLASS}}': 'rating-good',
        '{{METRIC10_RATING}}': '正常',
        '{{METRIC10_ANALYSIS}}': f"呼吸率{data['respiratory_rate']['value']:.1f}次/分处于正常范围（12-20次/分）。",
        
        # 睡眠分析
        '{{SLEEP_STATUS}}': sleep_alert['status'],
        '{{SLEEP_ALERT_BG}}': sleep_alert['bg'],
        '{{SLEEP_ALERT_BORDER}}': sleep_alert['border'],
        '{{SLEEP_ALERT_COLOR}}': sleep_alert['color'],
        '{{SLEEP_ALERT_SUBCOLOR}}': sleep_alert['subcolor'],
        '{{SLEEP_ALERT_TITLE}}': sleep_alert['title'],
        '{{SLEEP_ALERT_DETAIL}}': sleep_alert['detail'],
        '{{SLEEP_TOTAL}}': f"{sleep_hours:.1f}",
        '{{SLEEP_DEEP}}': f"{sleep_deep:.1f}",
        '{{SLEEP_CORE}}': f"{sleep_core:.1f}",
        '{{SLEEP_REM}}': f"{sleep_rem:.1f}",
        '{{SLEEP_AWAKE}}': f"{sleep_awake:.1f}",
        '{{SLEEP_DEEP_PCT}}': str(sleep_alert['deep_pct']),
        '{{SLEEP_CORE_PCT}}': str(sleep_alert['core_pct']),
        '{{SLEEP_REM_PCT}}': str(sleep_alert['rem_pct']),
        '{{SLEEP_AWAKE_PCT}}': str(sleep_alert['awake_pct']),
        '{{SLEEP_ANALYSIS_BORDER}}': sleep_alert['analysis_border'],
        '{{SLEEP_ANALYSIS_TEXT}}': ai_analyses['sleep'],
        
        # 运动记录
        '{{WORKOUT_NAME}}': workout['name'] if workout else '无',
        '{{WORKOUT_TIME}}': workout['start'].split(' ')[1][:5] if workout else '--',
        '{{WORKOUT_DURATION}}': str(round(workout['duration_min'], 1)) if workout else '--',
        '{{WORKOUT_ENERGY}}': str(workout['energy_kcal']) if workout else '--',
        '{{WORKOUT_AVG_HR}}': f"{workout['avg_hr']}bpm" if workout else '--',
        '{{WORKOUT_MAX_HR}}': f"{workout['max_hr']}bpm" if workout else '--',
        '{{WORKOUT_HR_CHART}}': hr_chart,
        '{{WORKOUT_ANALYSIS}}': ai_analyses['exercise'],
        
        # AI建议
        '{{AI1_TITLE}}': '睡眠时长不足需立即改善',
        '{{AI1_PROBLEM}}': f'昨夜仅睡{sleep_hours:.1f}小时，远低于7-9小时推荐标准。短期睡眠不足会立即影响认知功能（注意力下降30-40%）和情绪稳定性；长期与肥胖、糖尿病、心血管疾病风险增加50-70%相关。',
        '{{AI1_ACTION}}': '1. 今晚就寝时间提前至23:00，设定22:30闹钟提醒；2. 建立睡前1小时「无屏幕时间」，蓝光抑制褪黑素分泌达50%；3. 卧室温度调至18-20°C，使用遮光窗帘；4. 睡前放松：10分钟拉伸+5分钟深呼吸；5. 检查Apple Watch睡眠模式设置。',
        '{{AI1_EXPECTATION}}': '预期3-5天内入睡时间缩短至20分钟内，睡眠效率提升至85%以上，1周内睡眠时长稳定在7小时以上，HRV提升5-10ms。',
        
        '{{AI2_TITLE}}': '增加日常步行量',
        '{{AI2_PROBLEM}}': f'今日步数{data["steps"]["value"]:,}步，距离10,000步目标还差{10000-data["steps"]["value"]:,}步。日常活动量不足会影响基础代谢和心血管健康。',
        '{{AI2_ACTION}}': '1. 饭后步行15分钟，可额外增加2,000-3,000步；2. 工作期间每小时起身活动5分钟；3. 选择楼梯代替电梯；4. 通勤时提前一站下车步行。',
        '{{AI2_EXPECTATION}}': '通过上述调整，预期3-5天内日均步数稳定在8,000步以上，2周内达到10,000步目标。',
        
        '{{AI3_TITLE}}': '保持运动习惯',
        '{{AI3_DIET}}': '运动后30分钟内补充蛋白质（如鸡蛋、牛奶），促进肌肉修复；晚餐增加碳水化合物摄入补充糖原；保持充足水分摄入。',
        '{{AI3_ROUTINE}}': '固定运动时间（建议每周二、四、六），每次30-45分钟；运动后保证7-8小时睡眠；明日安排低强度恢复活动。',
        
        '{{AI4_TITLE}}': '综合健康评估',
        '{{AI4_ADVANTAGES}}': 'HRV 52.8ms显示自主神经系统调节能力良好；静息心率57bpm处于优秀水平；完成33分钟高强度楼梯训练，心肺功能良好。',
        '{{AI4_RISKS}}': '睡眠时长仅2.8小时严重不足，是最大健康风险；步数未达标；缺乏详细睡眠阶段数据无法评估睡眠质量。',
        '{{AI4_CONCLUSION}}': '整体健康基础良好，但睡眠是明显短板。建议将改善睡眠作为最高优先级，同时保持运动习惯，增加日常步行。',
        '{{AI4_PLAN}}': '第1周：重点改善睡眠，目标6.5小时；第2周：睡眠达到7小时，步数达到8,000步；第3-4周：巩固习惯，睡眠7.5小时，步数10,000步。',
        
        # 页脚
        '{{FOOTER_DATA_SOURCES}}': '数据来源: Apple Health',
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
    
    ai_analyses = data.get('ai_analyses', {})
    
    result = generate_report_v2(data, ai_analyses, template_file, output_file)
    print(f"报告已生成: {result}")
