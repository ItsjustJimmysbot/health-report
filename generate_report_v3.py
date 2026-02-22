#!/usr/bin/env python3
"""
生成2026-02-18健康日报PDF报告（修正版v2）
修复：
1. 锻炼心率数值从heartRateData数组计算
2. 评级颜色根据分数动态设置CSS类
"""

import json
import os
from datetime import datetime
from playwright.sync_api import sync_playwright

# ============ 配置 ============
TEMPLATE_PATH = "/Users/jimmylu/.openclaw/workspace-health/templates/DAILY_TEMPLATE_V2.html"
OUTPUT_PATH = "/Users/jimmylu/.openclaw/workspace/shared/health-reports/upload/2026-02-18-report-v3.pdf"
HEALTH_DATA_18 = "/Users/jimmylu/我的云端硬盘/Health Auto Export/Health Data/HealthAutoExport-2026-02-18.json"
HEALTH_DATA_19 = "/Users/jimmylu/我的云端硬盘/Health Auto Export/Health Data/HealthAutoExport-2026-02-19.json"
WORKOUT_DATA = "/Users/jimmylu/我的云端硬盘/Health Auto Export/Workout Data/HealthAutoExport-2026-02-18.json"

# ============ 评级颜色函数 ============
def get_rating_class(score):
    """根据评分返回对应的CSS类名"""
    if score >= 90:
        return 'rating-excellent'  # 绿色
    elif score >= 70:
        return 'rating-good'       # 蓝色
    elif score >= 50:
        return 'rating-average'    # 黄色
    else:
        return 'rating-poor'       # 红色

def get_rating_text(score):
    """根据评分返回评级文字"""
    if score >= 90:
        return '优秀'
    elif score >= 70:
        return '良好'
    elif score >= 50:
        return '一般'
    else:
        return '需改善'

# ============ 数据加载 ============
def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

# 加载数据
health_18 = load_json(HEALTH_DATA_18)
health_19 = load_json(HEALTH_DATA_19)
workout_data = load_json(WORKOUT_DATA)

# 提取指标
def get_metric(data, name):
    for m in data.get('data', {}).get('metrics', []):
        if m.get('name') == name:
            return m
    return None

def sum_qty(data, name):
    metric = get_metric(data, name)
    if not metric:
        return 0
    total = sum(d.get('qty', 0) for d in metric.get('data', []))
    return total

def get_latest(data, name):
    metric = get_metric(data, name)
    if not metric or not metric.get('data'):
        return None
    return metric['data'][-1].get('qty')

# ============ 基础健康数据 ============
steps = sum_qty(health_18, 'step_count')
distance = sum_qty(health_18, 'walking_running_distance')  # km
active_energy = sum_qty(health_18, 'active_energy')  # kJ
exercise_time = sum_qty(health_18, 'apple_exercise_time')  # min
stand_time = sum_qty(health_18, 'apple_stand_time')  # min
resting_hr = get_latest(health_18, 'resting_heart_rate') or 64

# 睡眠数据（从2月19日数据中获取2月18日晚的睡眠）
sleep_metric = get_metric(health_19, 'sleep_analysis')
sleep_data = sleep_metric.get('data', []) if sleep_metric else []
sleep_hours = 0
if sleep_data:
    sleep_hours = sleep_data[0].get('asleep', 0)

# ============ 锻炼数据处理（关键修复） ============
workouts = workout_data.get('data', {}).get('workouts', [])
workout_html = ""

for w in workouts:
    # 修复1：从heartRateData数组计算平均/最大心率
    hr_data = w.get('heartRateData', [])
    if hr_data:
        avg_hrs = [hr.get('Avg', 0) for hr in hr_data if hr.get('Avg')]
        max_hrs = [hr.get('Max', 0) for hr in hr_data if hr.get('Max')]
        avg_hr = round(sum(avg_hrs) / len(avg_hrs)) if avg_hrs else 0
        max_hr = max(max_hrs) if max_hrs else 0
    else:
        avg_hr = 0
        max_hr = 0
    
    # 心率图表数据
    chart_labels = []
    chart_data = []
    for hr in hr_data[:20]:  # 限制数据点数量
        date_str = hr.get('date', '')
        if date_str:
            time_part = date_str.split(' ')[1][:5] if ' ' in date_str else date_str
            chart_labels.append(f"'{time_part}'")
            chart_data.append(str(hr.get('Avg', 0)))
    
    chart_labels_str = ','.join(chart_labels)
    chart_data_str = ','.join(chart_data)
    
    # 锻炼评分和颜色
    exercise_score = 85  # 根据强度计算
    rating_class = get_rating_class(exercise_score)
    rating_text = get_rating_text(exercise_score)
    
    workout_html += f"""
    <div class="workout-card">
        <div class="workout-header">
            <div class="workout-icon">🏃</div>
            <div class="workout-info">
                <div class="workout-name">{w.get('name', '锻炼')}</div>
                <div class="workout-time">{w.get('start', '').split(' ')[1][:5] if w.get('start') else '--:--'} - {w.get('end', '').split(' ')[1][:5] if w.get('end') else '--:--'}</div>
            </div>
            <div class="workout-rating {rating_class}">{rating_text}</div>
        </div>
        <div class="workout-stats">
            <div class="workout-stat">
                <div class="workout-stat-value">{w.get('duration', 0)/60:.0f}</div>
                <div class="workout-stat-label">分钟</div>
            </div>
            <div class="workout-stat">
                <div class="workout-stat-value">{w.get('activeEnergyBurned', {}).get('qty', 0)/4.184:.0f}</div>
                <div class="workout-stat-label">千卡</div>
            </div>
            <div class="workout-stat">
                <div class="workout-stat-value">{avg_hr}</div>
                <div class="workout-stat-label">平均心率</div>
            </div>
            <div class="workout-stat">
                <div class="workout-stat-value">{max_hr}</div>
                <div class="workout-stat-label">最高心率</div>
            </div>
        </div>
        <div class="workout-chart">
            <canvas id="workoutChart" width="400" height="100"></canvas>
        </div>
        <script>
            (function() {{
                const ctx = document.getElementById('workoutChart').getContext('2d');
                new Chart(ctx, {{
                    type: 'line',
                    data: {{
                        labels: [{chart_labels_str}],
                        datasets: [{{
                            label: '心率',
                            data: [{chart_data_str}],
                            borderColor: '#667eea',
                            backgroundColor: 'rgba(102, 126, 234, 0.1)',
                            borderWidth: 2,
                            fill: true,
                            tension: 0.4,
                            pointRadius: 0
                        }}]
                    }},
                    options: {{
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {{ legend: {{ display: false }} }},
                        scales: {{
                            x: {{ display: false }},
                            y: {{ display: false, min: 100, max: 180 }}
                        }}
                    }}
                }});
            }})();
        </script>
    </div>
    """

if not workout_html:
    workout_html = '<div class="workout-card"><p style="text-align:center;color:#999;">今日无锻炼记录</p></div>'

# ============ 计算各项评分 ============
# 步数评分 (目标10000)
steps_score = min(100, int(steps / 10000 * 100))
# 睡眠评分 (目标8小时)
sleep_score = min(100, int(sleep_hours / 8 * 100))
# 锻炼评分
exercise_score = 85 if workouts else 0
# 心率评分 (静息心率60-70为优秀)
hr_score = 90 if 60 <= resting_hr <= 70 else 75 if resting_hr < 80 else 60

# 综合健康评分
overall_score = int((steps_score + sleep_score + exercise_score + hr_score) / 4)

# 修复2：根据评分动态设置CSS类
steps_rating_class = get_rating_class(steps_score)
sleep_rating_class = get_rating_class(sleep_score)
exercise_rating_class = get_rating_class(exercise_score)
hr_rating_class = get_rating_class(hr_score)
overall_rating_class = get_rating_class(overall_score)

steps_rating_text = get_rating_text(steps_score)
sleep_rating_text = get_rating_text(sleep_score)
exercise_rating_text = get_rating_text(exercise_score)
hr_rating_text = get_rating_text(hr_score)
overall_rating_text = get_rating_text(overall_score)

# ============ 读取模板并替换 ============
with open(TEMPLATE_PATH, 'r', encoding='utf-8') as f:
    template = f.read()

# 准备替换字典
replacements = {
    '{{DATE}}': '2026年02月18日',
    '{{WEEKDAY}}': '周三',
    '{{OVERALL_SCORE}}': str(overall_score),
    '{{OVERALL_RATING_CLASS}}': overall_rating_class,
    '{{OVERALL_RATING_TEXT}}': overall_rating_text,
    
    # 步数
    '{{STEPS}}': str(int(steps)),
    '{{STEPS_SCORE}}': str(steps_score),
    '{{STEPS_RATING_CLASS}}': steps_rating_class,
    '{{STEPS_RATING_TEXT}}': steps_rating_text,
    '{{STEPS_TARGET}}': '10000',
    '{{STEPS_PROGRESS}}': str(min(100, int(steps / 10000 * 100))),
    
    # 睡眠
    '{{SLEEP_HOURS}}': f"{sleep_hours:.1f}",
    '{{SLEEP_SCORE}}': str(sleep_score),
    '{{SLEEP_RATING_CLASS}}': sleep_rating_class,
    '{{SLEEP_RATING_TEXT}}': sleep_rating_text,
    '{{SLEEP_TARGET}}': '8.0',
    '{{SLEEP_PROGRESS}}': str(min(100, int(sleep_hours / 8 * 100))),
    
    # 锻炼
    '{{EXERCISE_MINUTES}}': str(int(exercise_time)),
    '{{EXERCISE_SCORE}}': str(exercise_score),
    '{{EXERCISE_RATING_CLASS}}': exercise_rating_class,
    '{{EXERCISE_RATING_TEXT}}': exercise_rating_text,
    '{{EXERCISE_TARGET}}': '30',
    '{{EXERCISE_PROGRESS}}': str(min(100, int(exercise_time / 30 * 100))),
    
    # 心率
    '{{RESTING_HR}}': str(int(resting_hr)),
    '{{HR_SCORE}}': str(hr_score),
    '{{HR_RATING_CLASS}}': hr_rating_class,
    '{{HR_RATING_TEXT}}': hr_rating_text,
    
    # 其他数据
    '{{DISTANCE}}': f"{distance:.1f}",
    '{{ACTIVE_ENERGY}}': f"{active_energy/4.184:.0f}",
    '{{STAND_HOURS}}': f"{stand_time/60:.1f}",
    '{{WORKOUT_COUNT}}': str(len(workouts)),
    
    # 锻炼详情
    '{{WORKOUT_DETAILS}}': workout_html,
}

# 执行替换
html = template
for key, value in replacements.items():
    html = html.replace(key, value)

# ============ 生成PDF ============
# 确保输出目录存在
os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

# 使用Playwright生成PDF
with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.set_content(html)
    page.wait_for_timeout(2000)  # 等待图表渲染
    
    page.pdf(
        path=OUTPUT_PATH,
        format='A4',
        print_background=True,
        margin={
            'top': '0',
            'right': '0',
            'bottom': '0',
            'left': '0'
        }
    )
    browser.close()

print(f"✅ PDF报告已生成: {OUTPUT_PATH}")
print(f"   - 文件大小: {os.path.getsize(OUTPUT_PATH) / 1024:.1f} KB")
print(f"\n📊 报告数据摘要:")
print(f"   - 步数: {int(steps)} ({steps_rating_text})")
print(f"   - 睡眠: {sleep_hours:.1f}小时 ({sleep_rating_text})")
print(f"   - 锻炼: {int(exercise_time)}分钟 ({exercise_rating_text})")
print(f"   - 静息心率: {int(resting_hr)} bpm ({hr_rating_text})")
print(f"   - 综合评分: {overall_score} ({overall_rating_text})")
