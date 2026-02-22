#!/usr/bin/env python3
"""
V5.0 Report Generator - HTML Template with Chart.js
"""
import json
from pathlib import Path
from datetime import datetime

def calc_recovery_score(hrv, resting_hr, sleep_hours):
    """计算恢复度评分"""
    score = 70
    if hrv and hrv > 50: score += 10
    if resting_hr and resting_hr < 65: score += 10
    if sleep_hours and sleep_hours > 7: score += 10
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
        return 'rating-excellent', '优秀'
    elif score >= 60:
        return 'rating-good', '良好'
    elif score >= 40:
        return 'rating-average', '一般'
    else:
        return 'rating-poor', '需改善'

def generate_hr_chart(workout):
    """生成心率图表"""
    hr_data = workout.get('hr_data', [])
    if not hr_data:
        return ''
    
    times = []
    avg_hrs = []
    max_hrs = []
    
    for hr in hr_data:
        time_str = hr.get('date', '').split(' ')[1][:5] if hr.get('date') else ''
        if time_str:
            times.append(f"'{time_str}'")
            avg_hrs.append(round(hr.get('Avg', 0)))
            max_hrs.append(round(hr.get('Max', 0)))
    
    if not times:
        return ''
    
    times_str = ', '.join(times)
    avg_str = ', '.join(map(str, avg_hrs))
    max_str = ', '.join(map(str, max_hrs))
    min_val = min(avg_hrs) - 10 if avg_hrs else 100
    max_val = max(max_hrs) + 10 if max_hrs else 180
    
    return f'''
<div style="height:200px;width:100%;margin:20px 0;">
  <canvas id="hrChart"></canvas>
</div>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<script>
  new Chart(document.getElementById('hrChart'), {{
    type: 'line',
    data: {{
      labels: [{times_str}],
      datasets: [
        {{label: '平均心率', data: [{avg_str}], borderColor: '#667eea', backgroundColor: 'rgba(102,126,234,0.1)', tension: 0.3, fill: true}},
        {{label: '最高心率', data: [{max_str}], borderColor: '#dc2626', backgroundColor: 'rgba(220,38,38,0.05)', tension: 0.3, fill: false}}
      ]
    }},
    options: {{
      responsive: false,
      maintainAspectRatio: false,
      scales: {{y: {{min: {min_val}, max: {max_val}, title: {{display: true, text: '心率 (bpm)'}}}}}},
      plugins: {{title: {{display: true, text: '运动心率变化'}}}}
    }}
  }});
</script>
'''

def generate_report(data, ai_analyses, output_path):
    """生成完整HTML报告"""
    
    # 计算评分
    recovery_score = calc_recovery_score(
        data['hrv']['value'],
        data['resting_hr']['value'],
        data['sleep']['total_hours'] if data['sleep'] else 0
    )
    sleep_score = calc_sleep_score(data['sleep']['total_hours'] if data['sleep'] else 0)
    exercise_score = calc_exercise_score(
        data['steps']['value'],
        len(data['workouts']) > 0,
        data['workouts'][0]['energy_kcal'] if data['workouts'] else 0
    )
    
    recovery_class, recovery_text = get_rating_class(recovery_score)
    sleep_class, sleep_text = get_rating_class(sleep_score)
    exercise_class, exercise_text = get_rating_class(exercise_score)
    
    # 运动心率图表
    hr_chart = ''
    if data['workouts']:
        hr_chart = generate_hr_chart(data['workouts'][0])
    
    # HTML模板
    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>健康日报 - {data['date']}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; line-height: 1.6; color: #333; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 20px; }}
        .container {{ max-width: 800px; margin: 0 auto; background: white; border-radius: 16px; box-shadow: 0 20px 60px rgba(0,0,0,0.3); overflow: hidden; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; }}
        .header h1 {{ font-size: 28px; margin-bottom: 8px; }}
        .header .date {{ opacity: 0.9; font-size: 16px; }}
        .content {{ padding: 30px; }}
        .section {{ margin-bottom: 30px; }}
        .section-title {{ font-size: 20px; font-weight: 600; color: #667eea; margin-bottom: 15px; padding-bottom: 8px; border-bottom: 2px solid #e0e0e0; }}
        .metrics-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px; margin-bottom: 20px; }}
        .metric-card {{ background: #f8f9fa; border-radius: 12px; padding: 15px; text-align: center; border-left: 4px solid #667eea; }}
        .metric-label {{ font-size: 12px; color: #666; margin-bottom: 5px; }}
        .metric-value {{ font-size: 24px; font-weight: 700; color: #333; }}
        .metric-unit {{ font-size: 12px; color: #888; }}
        .rating-excellent {{ color: #22c55e; }}
        .rating-good {{ color: #3b82f6; }}
        .rating-average {{ color: #f59e0b; }}
        .rating-poor {{ color: #ef4444; }}
        .badge {{ display: inline-block; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 600; }}
        .badge-excellent {{ background: #dcfce7; color: #166534; }}
        .badge-good {{ background: #dbeafe; color: #1e40af; }}
        .badge-average {{ background: #fef3c7; color: #92400e; }}
        .badge-poor {{ background: #fee2e2; color: #991b1b; }}
        .analysis-box {{ background: #f0f9ff; border-radius: 12px; padding: 20px; margin: 15px 0; border-left: 4px solid #0ea5e9; }}
        .analysis-box h4 {{ color: #0284c7; margin-bottom: 10px; font-size: 16px; }}
        .analysis-box p {{ line-height: 1.8; color: #374151; }}
        .priority-box {{ background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%); border-radius: 12px; padding: 20px; margin: 20px 0; border: 2px solid #f59e0b; }}
        .priority-box h4 {{ color: #92400e; margin-bottom: 15px; font-size: 18px; }}
        .priority-box ol {{ margin-left: 20px; }}
        .priority-box li {{ margin: 8px 0; color: #78350f; }}
        .workout-info {{ background: #f3f4f6; border-radius: 8px; padding: 15px; margin: 10px 0; }}
        .workout-info strong {{ color: #667eea; }}
        .footer {{ text-align: center; padding: 20px; color: #888; font-size: 12px; background: #f8f9fa; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🫀 健康日报</h1>
            <div class="date">{data['date']}</div>
        </div>
        
        <div class="content">
            <!-- 总体评分 -->
            <div class="section">
                <div class="section-title">📊 今日健康评分</div>
                <div class="metrics-grid">
                    <div class="metric-card">
                        <div class="metric-label">恢复度</div>
                        <div class="metric-value {recovery_class}">{recovery_score}<span class="metric-unit">分</span></div>
                        <span class="badge badge{recovery_class.replace('rating', '')}">{recovery_text}</span>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">睡眠质量</div>
                        <div class="metric-value {sleep_class}">{sleep_score}<span class="metric-unit">分</span></div>
                        <span class="badge badge{sleep_class.replace('rating', '')}">{sleep_text}</span>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">运动表现</div>
                        <div class="metric-value {exercise_class}">{exercise_score}<span class="metric-unit">分</span></div>
                        <span class="badge badge{exercise_class.replace('rating', '')}">{exercise_text}</span>
                    </div>
                </div>
            </div>
            
            <!-- 关键指标 -->
            <div class="section">
                <div class="section-title">📈 关键指标</div>
                <div class="metrics-grid">
                    <div class="metric-card">
                        <div class="metric-label">HRV</div>
                        <div class="metric-value">{data['hrv']['value'] or '--'}<span class="metric-unit">ms</span></div>
                        <div style="font-size:11px;color:#888;">{data['hrv']['points']}个数据点</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">静息心率</div>
                        <div class="metric-value">{data['resting_hr']['value'] or '--'}<span class="metric-unit">bpm</span></div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">步数</div>
                        <div class="metric-value">{data['steps']['value']:,}<span class="metric-unit">步</span></div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">血氧</div>
                        <div class="metric-value">{data['spo2']['value'] or '--'}<span class="metric-unit">%</span></div>
                    </div>
                </div>
            </div>
            
            <!-- HRV分析 -->
            <div class="section">
                <div class="section-title">💓 HRV分析</div>
                <div class="analysis-box">
                    <h4>🔬 深度解读</h4>
                    <p>{ai_analyses['hrv']}</p>
                </div>
            </div>
            
            <!-- 睡眠分析 -->
            <div class="section">
                <div class="section-title">😴 睡眠分析</div>
                <div class="analysis-box">
                    <h4>🌙 睡眠状况</h4>
                    <p>{ai_analyses['sleep']}</p>
                </div>
            </div>
            
            <!-- 运动分析 -->
            <div class="section">
                <div class="section-title">🏃 运动分析</div>
                <div class="workout-info">
                    <strong>今日运动：</strong>{data['workouts'][0]['name'] if data['workouts'] else '无'}<br>
                    <strong>时长：</strong>{round(data['workouts'][0]['duration_min'], 1) if data['workouts'] else 0}分钟 | 
                    <strong>平均心率：</strong>{data['workouts'][0]['avg_hr'] if data['workouts'] else '--'}bpm | 
                    <strong>最高心率：</strong>{data['workouts'][0]['max_hr'] if data['workouts'] else '--'}bpm | 
                    <strong>消耗：</strong>{data['workouts'][0]['energy_kcal'] if data['workouts'] else 0}千卡
                </div>
                {hr_chart}
                <div class="analysis-box">
                    <h4>⚡ 运动表现</h4>
                    <p>{ai_analyses['exercise']}</p>
                </div>
            </div>
            
            <!-- 最高优先级建议 -->
            <div class="section">
                <div class="section-title">🎯 最高优先级建议</div>
                <div class="priority-box">
                    <h4>🔥 立即行动</h4>
                    <p style="margin-bottom:15px;">{ai_analyses['priority']}</p>
                </div>
            </div>
        </div>
        
        <div class="footer">
            生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | V5.0 AI生成报告
        </div>
    </div>
</body>
</html>
'''
    
    # 写入文件
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    return output_path

if __name__ == '__main__':
    import sys
    
    data_file = sys.argv[1] if len(sys.argv) > 1 else 'data.json'
    output_file = sys.argv[2] if len(sys.argv) > 2 else 'report.html'
    
    with open(data_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    ai_analyses = data.get('ai_analyses', {})
    
    result = generate_report(data, ai_analyses, output_file)
    print(f"报告已生成: {result}")
