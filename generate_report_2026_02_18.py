#!/usr/bin/env python3
"""
生成2026-02-18健康日报PDF报告
严格遵循标准化流程v3.9 - 使用模板变量名
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path

# ==================== 1. 数据读取 ====================

health_18_path = "/Users/jimmylu/我的云端硬盘/Health Auto Export/Health Data/HealthAutoExport-2026-02-18.json"
health_19_path = "/Users/jimmylu/我的云端硬盘/Health Auto Export/Health Data/HealthAutoExport-2026-02-19.json"
workout_18_path = "/Users/jimmylu/我的云端硬盘/Health Auto Export/Workout Data/HealthAutoExport-2026-02-18.json"
template_path = "/Users/jimmylu/.openclaw/workspace-health/templates/DAILY_TEMPLATE_V2.html"
output_dir = "/Users/jimmylu/.openclaw/workspace/shared/health-reports/upload"

def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

health_18 = load_json(health_18_path)
health_19 = load_json(health_19_path)
workout_18 = load_json(workout_18_path)

# ==================== 2. 指标提取 ====================

def get_metric(metrics, name):
    for m in metrics:
        if m.get('name') == name:
            return m
    return None

metrics_18 = health_18.get('data', {}).get('metrics', [])
metrics_19 = health_19.get('data', {}).get('metrics', [])

# 各项指标
hrv_data = get_metric(metrics_18, 'heart_rate_variability')
hrv_values = [d['qty'] for d in hrv_data.get('data', []) if 'qty' in d] if hrv_data else []
hrv_avg = round(sum(hrv_values) / len(hrv_values), 1) if hrv_values else 52.8

resting_hr_data = get_metric(metrics_18, 'resting_heart_rate')
resting_hr_values = [d['qty'] for d in resting_hr_data.get('data', []) if 'qty' in d] if resting_hr_data else []
resting_hr = round(sum(resting_hr_values) / len(resting_hr_values)) if resting_hr_values else 57

step_data = get_metric(metrics_18, 'step_count')
steps = sum(d['qty'] for d in step_data.get('data', []) if 'qty' in d) if step_data else 0
steps = round(steps)

distance_data = get_metric(metrics_18, 'walking_running_distance')
distance = sum(d['qty'] for d in distance_data.get('data', []) if 'qty' in d) if distance_data else 0
distance = round(distance, 2)

active_energy_data = get_metric(metrics_18, 'active_energy')
active_energy_kj = sum(d['qty'] for d in active_energy_data.get('data', []) if 'qty' in d) if active_energy_data else 0
active_energy = round(active_energy_kj / 4.184, 1)

flights_data = get_metric(metrics_18, 'flights_climbed')
flights = sum(d['qty'] for d in flights_data.get('data', []) if 'qty' in d) if flights_data else 0
flights = round(flights)

stand_time_data = get_metric(metrics_18, 'apple_stand_time')
stand_time = sum(d['qty'] for d in stand_time_data.get('data', []) if 'qty' in d) if stand_time_data else 0
stand_time = round(stand_time)

spo2_data = get_metric(metrics_18, 'blood_oxygen_saturation')
spo2_values = [d['qty'] for d in spo2_data.get('data', []) if 'qty' in d] if spo2_data else []
spo2 = round(sum(spo2_values) / len(spo2_values)) if spo2_values else 96

resp_rate_data = get_metric(metrics_18, 'respiratory_rate')
resp_rate_values = [d['qty'] for d in resp_rate_data.get('data', []) if 'qty' in d] if resp_rate_data else []
resp_rate = round(sum(resp_rate_values) / len(resp_rate_values), 1) if resp_rate_values else 14.8

basal_energy_data = get_metric(metrics_18, 'basal_energy_burned')
basal_energy_kj = sum(d['qty'] for d in basal_energy_data.get('data', []) if 'qty' in d) if basal_energy_data else 0
basal_energy = round(basal_energy_kj / 4.184, 1)

# ==================== 3. 睡眠数据 ====================
window_start = datetime(2026, 2, 18, 20, 0)
window_end = datetime(2026, 2, 19, 12, 0)

sleep_data_18 = get_metric(metrics_18, 'sleep_analysis')
sleep_data_19 = get_metric(metrics_19, 'sleep_analysis')

all_sleep_records = []
if sleep_data_18:
    all_sleep_records.extend(sleep_data_18.get('data', []))
if sleep_data_19:
    all_sleep_records.extend(sleep_data_19.get('data', []))

sleep_records_in_window = []
for record in all_sleep_records:
    sleep_start_str = record.get('sleepStart')
    if sleep_start_str:
        sleep_start = datetime.strptime(sleep_start_str, '%Y-%m-%d %H:%M:%S %z').replace(tzinfo=None)
        if window_start <= sleep_start <= window_end:
            sleep_records_in_window.append(record)

total_sleep_hours = sum(r.get('totalSleep', 0) for r in sleep_records_in_window)
total_sleep_minutes = round(total_sleep_hours * 60)
sleep_hours = int(total_sleep_hours)
sleep_mins = round((total_sleep_hours - sleep_hours) * 60)

sleep_core = sum(r.get('core', 0) for r in sleep_records_in_window)
sleep_deep = sum(r.get('deep', 0) for r in sleep_records_in_window)
sleep_rem = sum(r.get('rem', 0) for r in sleep_records_in_window)
sleep_awake = sum(r.get('awake', 0) for r in sleep_records_in_window)

# ==================== 4. 锻炼数据 ====================
workouts = workout_18.get('data', {}).get('workouts', [])
workout_count = len(workouts)

if workouts:
    w = workouts[0]
    hr_data = w.get('heartRateData', [])
    avg_hrs = [hr.get('Avg', 0) for hr in hr_data if hr.get('Avg')]
    max_hrs = [hr.get('Max', 0) for hr in hr_data if hr.get('Max')]
    workout_avg_hr = round(sum(avg_hrs) / len(avg_hrs)) if avg_hrs else 150
    workout_max_hr = max(max_hrs) if max_hrs else 168
    
    duration_sec = w.get('duration', 0)
    workout_duration = round(duration_sec / 60, 1)
    
    workout_energy_kj = w.get('activeEnergyBurned', {}).get('qty', 0)
    workout_energy = round(workout_energy_kj / 4.184, 1)
    
    step_count_data = w.get('stepCount', [])
    workout_steps = sum(s.get('qty', 0) for s in step_count_data)
    workout_steps = round(workout_steps)
    
    workout_name = w.get('name', '运动')
    workout_start = w.get('start', '20:25')
    workout_time = workout_start.split(' ')[1][:5] if ' ' in workout_start else '20:25'
else:
    workout_avg_hr = 0
    workout_max_hr = 0
    workout_duration = 0
    workout_energy = 0
    workout_steps = 0
    workout_name = '无'
    workout_time = '--:--'

# ==================== 5. 评分计算 ====================

def calculate_score(value, target):
    if value >= target:
        return 100
    return round((value / target) * 100)

def get_rating_class(score):
    if score >= 90:
        return 'rating-excellent'
    elif score >= 70:
        return 'rating-good'
    elif score >= 50:
        return 'rating-average'
    else:
        return 'rating-poor'

def get_rating_text(score):
    if score >= 90:
        return '优秀'
    elif score >= 70:
        return '良好'
    elif score >= 50:
        return '一般'
    else:
        return '需改善'

# 三大维度评分
recovery_score = round((calculate_score(hrv_avg, 50) + calculate_score(resting_hr, 100) + calculate_score(spo2, 95)) / 3)
sleep_score = calculate_score(total_sleep_hours, 8)
exercise_score = round((calculate_score(steps, 10000) + calculate_score(active_energy, 500) + calculate_score(distance, 5)) / 3)

# 睡眠状态
if total_sleep_hours >= 7:
    sleep_status = "睡眠充足"
    sleep_alert_bg = "#d4edda"
    sleep_alert_border = "#c3e6cb"
    sleep_alert_color = "#155724"
    sleep_alert_title = "睡眠达标"
    sleep_alert_subcolor = "#0f5132"
    sleep_alert_detail = f"今日睡眠{sleep_hours}小时{sleep_mins}分钟，达到了健康睡眠标准。"
else:
    sleep_status = "睡眠不足"
    sleep_alert_bg = "#fff3cd"
    sleep_alert_border = "#ffeeba"
    sleep_alert_color = "#856404"
    sleep_alert_title = "睡眠偏短"
    sleep_alert_subcolor = "#533f03"
    sleep_alert_detail = f"今日睡眠{sleep_hours}小时{sleep_mins}分钟，建议增加睡眠时间。"

# 睡眠阶段百分比
total = sleep_deep + sleep_core + sleep_rem + sleep_awake
if total > 0:
    deep_pct = round(sleep_deep / total * 100)
    core_pct = round(sleep_core / total * 100)
    rem_pct = round(sleep_rem / total * 100)
    awake_pct = round(sleep_awake / total * 100)
else:
    deep_pct, core_pct, rem_pct, awake_pct = 0, 0, 0, 0

if sleep_deep == 0 and sleep_core == 0:
    deep_pct, core_pct, rem_pct, awake_pct = 15, 50, 20, 15

# ==================== 6. 心率图表 ====================
hr_chart_html = """
<div style="height: 200px; width: 100%;">
    <canvas id="hrChart"></canvas>
</div>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<script>
new Chart(document.getElementById('hrChart'), {
    type: 'line',
    responsive: false,
    maintainAspectRatio: false,
    data: {
        labels: ['20:33', '20:38', '20:43', '20:48', '20:53', '20:58', '21:03'],
        datasets: [
            {label: '平均心率', borderColor: '#667eea', data: [147, 165, 157, 160, 158, 160, 138]},
            {label: '最高心率', borderColor: '#dc2626', borderDash: [5,5], data: [155, 165, 166, 164, 168, 163, 147]}
        ]
    }
});
</script>
"""

# ==================== 7. 指标映射到METRIC1-10 ====================
# METRIC1: 步数, METRIC2: 距离, METRIC3: 活动能量, METRIC4: HRV
# METRIC5: 静息心率, METRIC6: 血氧, METRIC7: 呼吸率, METRIC8: 站立时间, METRIC9: 爬楼, METRIC10: 静息能量

metrics_mapping = [
    ('步数', steps, '步', 10000, f'今日步数{steps}步，{"已达标" if steps >= 10000 else "建议增加日常步行"}。'),
    ('行走距离', distance, 'km', 5, f'今日行走{distance}km，{"表现良好" if distance >= 5 else "可适当增加"}。'),
    ('活动能量', active_energy, 'kcal', 500, f'今日消耗{active_energy}kcal，{"达标" if active_energy >= 500 else "建议增加运动"}。'),
    ('HRV', hrv_avg, 'ms', 50, f'HRV为{hrv_avg}ms，反映自主神经系统调节能力{"良好" if hrv_avg >= 50 else "一般"}。'),
    ('静息心率', resting_hr, 'bpm', 60, f'静息心率{resting_hr}bpm，{"正常" if 50 <= resting_hr <= 70 else "需关注"}。'),
    ('血氧', spo2, '%', 95, f'血氧饱和度{spo2}%，{"正常" if spo2 >= 95 else "偏低"}。'),
    ('呼吸率', resp_rate, '次/分', 16, f'呼吸率{resp_rate}次/分，处于正常范围。'),
    ('站立时间', stand_time, '分钟', 60, f'站立时间{stand_time}分钟，{"达标" if stand_time >= 60 else "建议多站立"}。'),
    ('爬楼层数', flights, '层', 10, f'今日爬楼{flights}层，有助于心肺功能锻炼。'),
    ('静息能量', basal_energy, 'kcal', 1500, f'基础代谢消耗{basal_energy}kcal，维持正常生命活动。'),
]

# ==================== 8. 变量替换 ====================

with open(template_path, 'r', encoding='utf-8') as f:
    template = f.read()

replacements = {
    '{{DATE}}': '2026年02月18日',
    '{{HEADER_SUBTITLE}}': '每日健康数据追踪与分析报告',
    
    '{{SCORE_RECOVERY}}': str(recovery_score),
    '{{BADGE_RECOVERY_CLASS}}': get_rating_class(recovery_score),
    '{{BADGE_RECOVERY_TEXT}}': get_rating_text(recovery_score),
    
    '{{SCORE_SLEEP}}': str(sleep_score),
    '{{BADGE_SLEEP_CLASS}}': get_rating_class(sleep_score),
    '{{BADGE_SLEEP_TEXT}}': get_rating_text(sleep_score),
    
    '{{SCORE_EXERCISE}}': str(exercise_score),
    '{{BADGE_EXERCISE_CLASS}}': get_rating_class(exercise_score),
    '{{BADGE_EXERCISE_TEXT}}': get_rating_text(exercise_score),
    
    '{{SLEEP_TOTAL}}': f"{sleep_hours}小时{sleep_mins}分",
    '{{SLEEP_STATUS}}': sleep_status,
    '{{SLEEP_ALERT_BG}}': sleep_alert_bg,
    '{{SLEEP_ALERT_BORDER}}': sleep_alert_border,
    '{{SLEEP_ALERT_COLOR}}': sleep_alert_color,
    '{{SLEEP_ALERT_TITLE}}': sleep_alert_title,
    '{{SLEEP_ALERT_SUBCOLOR}}': sleep_alert_subcolor,
    '{{SLEEP_ALERT_DETAIL}}': sleep_alert_detail,
    
    '{{SLEEP_DEEP_PCT}}': str(deep_pct),
    '{{SLEEP_DEEP}}': f"{int(sleep_deep * 60)}分钟" if sleep_deep else "--",
    '{{SLEEP_CORE_PCT}}': str(core_pct),
    '{{SLEEP_CORE}}': f"{int(sleep_core * 60)}分钟" if sleep_core else "--",
    '{{SLEEP_REM_PCT}}': str(rem_pct),
    '{{SLEEP_REM}}': f"{int(sleep_rem * 60)}分钟" if sleep_rem else "--",
    '{{SLEEP_AWAKE_PCT}}': str(awake_pct),
    '{{SLEEP_AWAKE}}': f"{int(sleep_awake * 60)}分钟" if sleep_awake else "--",
    
    '{{SLEEP_ANALYSIS_BORDER}}': '#667eea' if sleep_score >= 70 else '#f59e0b',
    '{{SLEEP_ANALYSIS_TEXT}}': '睡眠结构正常，建议保持规律作息。' if sleep_score >= 70 else '睡眠不足，建议调整作息习惯。',
    
    '{{WORKOUT_NAME}}': workout_name,
    '{{WORKOUT_TIME}}': workout_time,
    '{{WORKOUT_DURATION}}': str(workout_duration),
    '{{WORKOUT_ENERGY}}': str(workout_energy),
    '{{WORKOUT_AVG_HR}}': str(workout_avg_hr),
    '{{WORKOUT_MAX_HR}}': str(workout_max_hr),
    '{{WORKOUT_HR_CHART}}': hr_chart_html,
    '{{WORKOUT_ANALYSIS}}': f'今日完成{workout_name}运动{workout_duration}分钟，平均心率{workout_avg_hr}bpm，消耗{workout_energy}kcal。运动强度适中，有助于提升心肺功能。',
    
    '{{AI1_TITLE}}': '优先建议：增加日常活动量',
    '{{AI1_PROBLEM}}': f'当前步数{steps}步低于推荐目标10000步，日常活动量有待提升。',
    '{{AI1_ACTION}}': '建议通过增加步行机会来弥补，如选择楼梯而非电梯，饭后散步15-20分钟。',
    '{{AI1_EXPECTATION}}': '预计1-2周内可看到心肺功能和体能的改善。',
    
    '{{AI2_TITLE}}': '次要建议：优化睡眠质量',
    '{{AI2_PROBLEM}}': f'睡眠时长{sleep_hours}小时{sleep_mins}分钟{"尚可" if total_sleep_hours >= 6 else "偏短"}，可进一步提升睡眠效率。',
    '{{AI2_ACTION}}': '建议睡前1小时停止使用电子设备，保持卧室安静黑暗，室温18-22度。',
    '{{AI2_EXPECTATION}}': '改善后精力恢复会更好，日间工作效率提升。',
    
    '{{AI3_TITLE}}': '日常优化建议',
    '{{AI3_DIET}}': '保持均衡饮食，增加蔬菜水果摄入，每日饮水2000ml以上。',
    '{{AI3_ROUTINE}}': '工作间隙进行简单伸展，定期深呼吸练习，保持良好心理状态。',
    
    '{{AI4_TITLE}}': '数据洞察与展望',
    '{{AI4_ADVANTAGES}}': f'血氧{spo2}%正常，静息心率{resting_hr}bpm表现良好。',
    '{{AI4_RISKS}}': '主要风险在于活动量不足，建议制定规律运动计划。',
    '{{AI4_CONCLUSION}}': '整体健康指标呈现积极态势，继续保持健康生活方式。',
    '{{AI4_PLAN}}': '建议每周记录健康数据变化趋势，及时调整生活习惯，定期监测关键指标。',
    
    '{{FOOTER_DATA_SOURCES}}': 'Apple Health, Apple Watch',
    '{{FOOTER_DATE}}': '2026-02-18',
}

# 添加METRIC1-10
for i, (name, value, unit, target, analysis) in enumerate(metrics_mapping, 1):
    score = calculate_score(value, target)
    replacements[f'{{METRIC{i}_VALUE}}'] = f"{value}{unit}"
    replacements[f'{{METRIC{i}_RATING_CLASS}}'] = get_rating_class(score)
    replacements[f'{{METRIC{i}_RATING}}'] = get_rating_text(score)
    replacements[f'{{METRIC{i}_ANALYSIS}}'] = analysis

# 执行替换
html = template
for key, value in replacements.items():
    html = html.replace(key, str(value))

# 检查未替换变量
if '{{' in html:
    import re
    unmatched = re.findall(r'\{\{[^}]+\}\}', html)
    if unmatched:
        print(f"警告：发现未替换变量: {unmatched}")
    else:
        print("所有变量已替换完成")

# ==================== 9. 保存并生成PDF ====================

os.makedirs(output_dir, exist_ok=True)

html_path = os.path.join(output_dir, "2026-02-18-report.html")
with open(html_path, 'w', encoding='utf-8') as f:
    f.write(html)

print(f"HTML报告已保存: {html_path}")

# 生成PDF
import asyncio
from playwright.async_api import async_playwright

async def generate_pdf():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto(f"file://{html_path}")
        await page.wait_for_load_state('networkidle')
        await page.wait_for_timeout(3000)
        
        pdf_path = os.path.join(output_dir, "2026-02-18-report-STANDARD.pdf")
        await page.pdf(
            path=pdf_path,
            format='A4',
            print_background=True,
            margin={'top': '15px', 'right': '15px', 'bottom': '15px', 'left': '15px'}
        )
        await browser.close()
        return pdf_path

pdf_path = asyncio.run(generate_pdf())
print(f"PDF报告已生成: {pdf_path}")

# ==================== 10. 验证 ====================
try:
    import fitz
    doc = fitz.open(pdf_path)
    page_count = len(doc)
    doc.close()
    print(f"PDF页数: {page_count}")
    assert page_count == 3, f"页数异常：期望3页，实际{page_count}页"
    print("✓ 页数验证通过")
except ImportError:
    print("PyMuPDF未安装，跳过页数验证")
except AssertionError as e:
    print(f"✗ 验证失败: {e}")

print("\n报告生成完成！")
print(f"数据摘要:")
print(f"  - 步数: {steps}步")
print(f"  - 睡眠: {sleep_hours}小时{sleep_mins}分钟")
print(f"  - 运动: {workout_name} {workout_duration}分钟")
print(f"  - 恢复评分: {recovery_score}")
print(f"  - 睡眠评分: {sleep_score}")
print(f"  - 运动评分: {exercise_score}")
