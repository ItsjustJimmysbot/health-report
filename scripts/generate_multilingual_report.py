#!/usr/bin/env python3
"""
多语言每日健康报告生成器
支持中文(zh)和英文(en)
"""
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from i18n import get_text, get_score_label, get_sleep_status, get_weekday_cn, get_weekday_en

def generate_multilingual_report(health_data, output_file, lang='zh'):
    """生成多语言 HTML 报告"""
    
    # 计算评分
    recovery_score = health_data.get('recovery_score', 70)
    sleep_score = health_data.get('sleep_score', 70)
    exercise_score = health_data.get('exercise_score', 70)
    
    # 获取标签
    recovery_label = get_score_label(recovery_score, lang)
    sleep_label = get_sleep_status(health_data.get('sleep_hours', 0), 
                                    health_data.get('has_sleep_data', False), lang)
    
    # 星期
    weekday = health_data.get('weekday', '0')
    if lang == 'zh':
        weekday_str = get_weekday_cn(weekday)
    else:
        weekday_str = get_weekday_en(weekday)
    
    # 生成图表配置
    hr_chart = generate_heart_rate_chart(health_data, lang)
    workout_chart = generate_workout_chart(health_data, lang)
    sleep_chart = generate_sleep_chart(health_data, lang)
    
    # 语言特定的样式调整
    font_family = '"PingFang SC", "STHeiti", "Microsoft YaHei", sans-serif' if lang == 'zh' else '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
    
    html = f'''<!DOCTYPE html>
<html lang="{lang}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{get_text('title', lang)} - {health_data['date']}</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-annotation@2.1.0"></script>
    <style>
        @page {{ size: A4; margin: 1cm; }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: {font_family};
            font-size: 10pt;
            line-height: 1.6;
            color: #1f2937;
            background: #f3f4f6;
            padding: 15px;
        }}
        .container {{
            max-width: 800px;
            margin: 0 auto;
            background: white;
            border-radius: 16px;
            box-shadow: 0 4px 30px rgba(0,0,0,0.08);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 35px 30px;
            text-align: center;
            position: relative;
        }}
        .header::after {{
            content: '';
            position: absolute;
            bottom: 0;
            left: 0;
            right: 0;
            height: 4px;
            background: linear-gradient(90deg, #dc2626, #f59e0b, #3b82f6, #10b981);
        }}
        .header h1 {{
            font-size: 28pt;
            margin-bottom: 8px;
            font-weight: 700;
            letter-spacing: 2px;
        }}
        .header .date {{
            opacity: 0.95;
            font-size: 13pt;
            font-weight: 400;
        }}
        .score-section {{
            display: flex;
            justify-content: center;
            padding: 30px 20px;
            gap: 20px;
            flex-wrap: wrap;
            background: #fff;
        }}
        .score-card {{
            background: white;
            border-radius: 20px;
            padding: 25px 30px;
            text-align: center;
            min-width: 150px;
            border: 3px solid transparent;
        }}
        .score-red {{ border-color: #fca5a5; background: #fef2f2; }}
        .score-yellow {{ border-color: #fcd34d; background: #fffbeb; }}
        .score-blue {{ border-color: #93c5fd; background: #eff6ff; }}
        .score-green {{ border-color: #86efac; background: #f0fdf4; }}
        .score-card .value {{
            font-size: 42pt;
            font-weight: 800;
            line-height: 1;
            margin-bottom: 8px;
        }}
        .score-red .value {{ color: #dc2626; }}
        .score-yellow .value {{ color: #d97706; }}
        .score-blue .value {{ color: #2563eb; }}
        .score-green .value {{ color: #059669; }}
        .score-card .label {{
            font-size: 11pt;
            color: #6b7280;
            font-weight: 600;
            margin-bottom: 6px;
        }}
        .score-card .status {{
            font-size: 12pt;
            font-weight: 700;
            padding: 4px 12px;
            border-radius: 20px;
            display: inline-block;
        }}
        .score-red .status {{ background: #fee2e2; color: #dc2626; }}
        .score-yellow .status {{ background: #fef3c7; color: #d97706; }}
        .score-blue .status {{ background: #dbeafe; color: #2563eb; }}
        .score-green .status {{ background: #d1fae5; color: #059669; }}
        .content {{ padding: 0 25px 25px; }}
        .section {{
            margin-bottom: 22px;
            background: #fff;
            border-radius: 14px;
            padding: 20px;
            border: 1px solid #e5e7eb;
            box-shadow: 0 2px 8px rgba(0,0,0,0.03);
        }}
        .section-title {{
            font-size: 13pt;
            font-weight: 700;
            color: #111827;
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            gap: 10px;
            padding-bottom: 10px;
            border-bottom: 2px solid #f3f4f6;
        }}
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 12px;
            margin: 15px 0;
        }}
        .metric-item {{
            text-align: center;
            padding: 15px 10px;
            background: linear-gradient(180deg, #f9fafb 0%, #f3f4f6 100%);
            border-radius: 12px;
            border: 1px solid #e5e7eb;
        }}
        .metric-item .number {{
            font-size: 22pt;
            font-weight: 800;
            color: #1f2937;
            line-height: 1.2;
        }}
        .metric-item .unit {{
            font-size: 9pt;
            color: #9ca3af;
            font-weight: 500;
        }}
        .metric-item .label {{
            font-size: 9pt;
            color: #6b7280;
            margin-top: 6px;
            font-weight: 600;
        }}
        .chart-row {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
            margin: 15px 0;
        }}
        .chart-container {{
            position: relative;
            height: 220px;
            background: #f9fafb;
            border-radius: 12px;
            padding: 15px;
            border: 1px solid #e5e7eb;
        }}
        .chart-title {{
            font-size: 11pt;
            font-weight: 700;
            color: #374151;
            margin-bottom: 10px;
            text-align: center;
        }}
        .chart-wrapper {{
            position: relative;
            height: calc(100% - 30px);
        }}
        .sleep-details {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 10px;
            margin-top: 15px;
        }}
        .sleep-stage {{
            text-align: center;
            padding: 12px 8px;
            border-radius: 10px;
            background: #f9fafb;
        }}
        .sleep-stage.deep {{ background: #e0e7ff; color: #3730a3; }}
        .sleep-stage.rem {{ background: #f3e8ff; color: #6b21a8; }}
        .sleep-stage.core {{ background: #cffafe; color: #0e7490; }}
        .sleep-stage.awake {{ background: #fef3c7; color: #92400e; }}
        .sleep-stage .time {{
            font-size: 16pt;
            font-weight: 800;
        }}
        .sleep-stage .label {{
            font-size: 9pt;
            margin-top: 4px;
            font-weight: 600;
        }}
        .workout-item {{
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 12px;
            background: #f9fafb;
            border-radius: 10px;
            margin-bottom: 8px;
        }}
        .workout-item .icon {{ font-size: 20pt; }}
        .workout-item .info {{ flex: 1; }}
        .workout-item .name {{
            font-weight: 700;
            color: #111827;
            font-size: 11pt;
        }}
        .workout-item .meta {{
            font-size: 9pt;
            color: #6b7280;
            margin-top: 2px;
        }}
        .workout-item .stats {{
            text-align: right;
        }}
        .workout-item .duration {{
            font-weight: 700;
            color: #059669;
            font-size: 12pt;
        }}
        .workout-item .calories {{
            font-size: 9pt;
            color: #9ca3af;
        }}
        .conclusions {{
            background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
            border-left: 5px solid #0ea5e9;
            padding: 20px;
            border-radius: 0 14px 14px 0;
            margin: 20px 0;
        }}
        .conclusions h3 {{
            color: #0369a1;
            font-size: 12pt;
            margin-bottom: 15px;
            font-weight: 700;
        }}
        .conclusion-item {{
            display: flex;
            align-items: flex-start;
            gap: 12px;
            margin: 12px 0;
            font-size: 10.5pt;
            padding: 10px 12px;
            background: rgba(255,255,255,0.7);
            border-radius: 8px;
        }}
        .badge {{
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 9pt;
            font-weight: 700;
            white-space: nowrap;
        }}
        .badge-good {{ background: #d1fae5; color: #065f46; }}
        .badge-warning {{ background: #fef3c7; color: #92400e; }}
        .badge-bad {{ background: #fee2e2; color: #991b1b; }}
        .badge-info {{ background: #dbeafe; color: #1e40af; }}
        .recommendations {{
            background: linear-gradient(135deg, #fdf4ff 0%, #fae8ff 100%);
            border: 2px solid #e879f9;
            border-radius: 14px;
            padding: 20px;
            margin: 20px 0;
        }}
        .recommendations h3 {{
            color: #a21caf;
            font-size: 12pt;
            margin-bottom: 15px;
            font-weight: 700;
        }}
        .rec-item {{
            display: flex;
            gap: 12px;
            margin: 10px 0;
            padding: 12px 15px;
            background: rgba(255,255,255,0.8);
            border-radius: 10px;
            font-size: 10.5pt;
            border-left: 4px solid transparent;
        }}
        .rec-item.high {{ border-left-color: #dc2626; }}
        .rec-item.medium {{ border-left-color: #f59e0b; }}
        .rec-item.low {{ border-left-color: #10b981; }}
        .priority {{
            font-weight: 700;
            min-width: 60px;
            font-size: 9pt;
        }}
        .footer {{
            text-align: center;
            padding: 20px;
            color: #9ca3af;
            font-size: 9pt;
            border-top: 1px solid #e5e7eb;
            background: #f9fafb;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 {get_text('title', lang)}</h1>
            <div class="date">{health_data['date']} | {weekday_str} | {get_text('day_prefix', lang)} {health_data.get('day_of_year', 0)} {get_text('day_suffix', lang)}</div>
        </div>
        
        <div class="score-section">
            {generate_score_card(recovery_score, get_text('recovery_score', lang), recovery_label, lang)}
            {generate_score_card(sleep_score, get_text('sleep_quality', lang), sleep_label, lang)}
            {generate_score_card(exercise_score, get_text('exercise_completion', lang), get_score_label(exercise_score, lang), lang)}
        </div>
        
        <div class="content">
            <!-- Key Metrics -->
            <div class="section">
                <div class="section-title"><span class="icon">📈</span>{get_text('heart_rate_analysis', lang)}</div>
                <div class="metrics-grid">
                    {generate_metric_item(health_data.get('steps', 0), '', get_text('steps', lang))}
                    {generate_metric_item(f"{health_data.get('sleep_hours', 0):.1f}", get_text('hour' if lang == 'zh' else 'hrs', lang), get_text('sleep_duration', lang))}
                    {generate_metric_item(health_data.get('hrv', 0), 'ms', get_text('hrv', lang))}
                    {generate_metric_item(health_data.get('resting_hr', 0), 'bpm', get_text('resting_hr', lang))}
                    {generate_metric_item(health_data.get('exercise_min', 0), get_text('min' if lang == 'zh' else 'min', lang), get_text('exercise_time', lang))}
                    {generate_metric_item(health_data.get('active_calories', 0), 'kcal', get_text('active_calories', lang))}
                    {generate_metric_item(health_data.get('floors', 0), '', get_text('floors', lang))}
                    {generate_metric_item(f"{health_data.get('distance', 0):.1f}", 'km', get_text('distance', lang))}
                    {generate_metric_item(f"{health_data.get('blood_oxygen', 0)}", '% SpO2', get_text('blood_oxygen', lang))}
                </div>
            </div>
            
            <!-- Heart Rate Charts -->
            <div class="section">
                <div class="section-title"><span class="icon">❤️</span>{get_text('heart_rate_analysis', lang)}</div>
                <div class="chart-row">
                    <div class="chart-container">
                        <div class="chart-title">{get_text('all_day_hr', lang)}</div>
                        <div class="chart-wrapper">
                            <canvas id="hrChart"></canvas>
                        </div>
                    </div>
                    <div class="chart-container">
                        <div class="chart-title">{get_text('workout_hr', lang)}</div>
                        <div class="chart-wrapper">
                            <canvas id="workoutChart"></canvas>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Sleep Analysis -->
            <div class="section">
                <div class="section-title"><span class="icon">😴</span>{get_text('sleep_analysis', lang)}</div>
                <div class="chart-row">
                    <div class="chart-container">
                        <div class="chart-title">{get_text('sleep_structure', lang)}</div>
                        <div class="chart-wrapper">
                            <canvas id="sleepChart"></canvas>
                        </div>
                    </div>
                    <div style="padding: 15px;">
                        <div style="font-size: 11pt; font-weight: 700; color: #374151; margin-bottom: 10px;">
                            {get_text('sleep_efficiency', lang)}: {health_data.get('sleep_efficiency', 0)*100:.0f}%
                        </div>
                        <div class="sleep-details">
                            <div class="sleep-stage deep">
                                <div class="time">{health_data.get('sleep_deep', 0):.1f}h</div>
                                <div class="label">{get_text('deep_sleep', lang)} {health_data.get('sleep_deep_pct', 0):.0f}%</div>
                            </div>
                            <div class="sleep-stage rem">
                                <div class="time">{health_data.get('sleep_rem', 0):.1f}h</div>
                                <div class="label">{get_text('rem_sleep', lang)} {health_data.get('sleep_rem_pct', 0):.0f}%</div>
                            </div>
                            <div class="sleep-stage core">
                                <div class="time">{health_data.get('sleep_core', 0):.1f}h</div>
                                <div class="label">{get_text('light_sleep', lang)} {health_data.get('sleep_core_pct', 0):.0f}%</div>
                            </div>
                            <div class="sleep-stage awake">
                                <div class="time">{health_data.get('sleep_awake', 0):.1f}h</div>
                                <div class="label">{get_text('awake', lang)} {health_data.get('sleep_awake_pct', 0):.0f}%</div>
                            </div>
                        </div>
                        <div style="margin-top: 15px; padding: 10px; background: #f3f4f6; border-radius: 8px; font-size: 10pt;">
                            <strong>{get_text('bed_time', lang)}:</strong> {health_data.get('sleep_start', '--:--')} | 
                            <strong>{get_text('wake_time', lang)}:</strong> {health_data.get('sleep_end', '--:--')} | 
                            <strong>{get_text('time_in_bed', lang)}:</strong> {health_data.get('time_in_bed', 0):.1f}h
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Exercise Records -->
            <div class="section">
                <div class="section-title"><span class="icon">🏃</span>{get_text('exercise_records', lang)}</div>
                {generate_workout_list(health_data, lang)}
            </div>
            
            <!-- Conclusions -->
            <div class="conclusions">
                <h3>📋 {get_text('conclusions', lang)}</h3>
                {generate_conclusions(health_data, recovery_score, sleep_score, exercise_score, lang)}
            </div>
        </div>
        
        <div class="footer">
            <span style="font-weight: 700; color: #6b7280;">Health Report</span> {get_text('generated_by', lang)} | 
            {get_text('data_source', lang)}: Apple Health + Apple Watch<br>
            <span style="font-size: 8pt;">{get_text('generated_by', lang)}: {datetime.now().strftime("%Y-%m-%d %H:%M")}</span>
        </div>
    </div>
    
    <script>
        new Chart(document.getElementById('hrChart'), {hr_chart});
        new Chart(document.getElementById('workoutChart'), {workout_chart});
        new Chart(document.getElementById('sleepChart'), {sleep_chart});
    </script>
</body>
</html>'''
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)
    
    return output_file

def generate_score_card(score, label, status, lang):
    """生成评分卡片 HTML"""
    if score >= 80:
        color_class = 'score-green'
    elif score >= 60:
        color_class = 'score-blue'
    elif score >= 40:
        color_class = 'score-yellow'
    else:
        color_class = 'score-red'
    
    return f'''
    <div class="score-card {color_class}">
        <div class="value">{score}</div>
        <div class="label">{label}</div>
        <div class="status">{status}</div>
    </div>
    '''

def generate_metric_item(number, unit, label):
    """生成指标项 HTML"""
    return f'''
    <div class="metric-item">
        <div class="number">{number}</div>
        <div class="unit">{unit}</div>
        <div class="label">{label}</div>
    </div>
    '''

def generate_workout_list(data, lang):
    """生成运动列表 HTML"""
    workouts = data.get('workouts', [])
    
    if not workouts:
        return f'<div style="text-align: center; padding: 20px; color: #6b7280;">{get_text("no_workout", lang)}</div>'
    
    html = '<div class="workout-list">'
    for w in workouts:
        start = w.get('start_time', w.get('time', '--:--'))
        end = w.get('end_time', '--:--')
        time_range = f"{start} - {end}" if end != '--:--' else start
        
        duration = w.get('duration', 0)
        if isinstance(duration, (int, float)) and duration > 100:
            duration = round(duration / 60)
        
        html += f'''
        <div class="workout-item">
            <div class="icon">{w.get('icon', '🏃')}</div>
            <div class="info">
                <div class="name">{w.get('type', 'Workout')}</div>
                <div class="meta">{time_range} · Avg HR {w.get('avg_hr', 0)} bpm</div>
            </div>
            <div class="stats">
                <div class="duration">{duration} min</div>
                <div class="calories">{w.get('calories', 0)} kcal</div>
            </div>
        </div>
        '''
    html += '</div>'
    return html

def generate_conclusions(data, recovery_score, sleep_score, exercise_score, lang):
    """生成结论 HTML"""
    conclusions = []
    
    # Recovery conclusion
    if recovery_score >= 80:
        conclusions.append(('🟢', 'badge-good', f'Recovery score {recovery_score}: Excellent condition for high-intensity training' if lang == 'en' else f'恢复度评分 {recovery_score} 分，身体恢复良好'))
    elif recovery_score >= 60:
        conclusions.append(('🔵', 'badge-info', f'Recovery score {recovery_score}: Good condition for moderate exercise' if lang == 'en' else f'恢复度评分 {recovery_score} 分，身体状态尚可'))
    else:
        conclusions.append(('🟡', 'badge-warning', f'Recovery score {recovery_score}: Take it easy today' if lang == 'en' else f'恢复度评分 {recovery_score} 分，注意休息'))
    
    # Sleep conclusion
    sleep_hours = data.get('sleep_hours', 0)
    has_sleep = data.get('has_sleep_data', False)
    
    if not has_sleep:
        conclusions.append(('⚪', 'badge-info', 'No sleep data recorded' if lang == 'en' else '无睡眠数据记录'))
    elif sleep_hours < 6:
        conclusions.append(('🔴', 'badge-bad', f'Only {sleep_hours:.1f}h sleep - insufficient for recovery' if lang == 'en' else f'仅睡 {sleep_hours:.1f} 小时，睡眠严重不足'))
    elif sleep_hours < 7:
        conclusions.append(('🟡', 'badge-warning', f'{sleep_hours:.1f}h sleep - consider earlier bedtime' if lang == 'en' else f'睡眠 {sleep_hours:.1f} 小时，建议早睡'))
    else:
        conclusions.append(('🟢', 'badge-good', f'{sleep_hours:.1f}h sleep - good recovery' if lang == 'en' else f'睡眠 {sleep_hours:.1f} 小时，恢复良好'))
    
    # Exercise conclusion
    steps = data.get('steps', 0)
    if steps >= 10000:
        conclusions.append(('🟢', 'badge-good', f'{steps:,} steps - great activity level!' if lang == 'en' else f'{steps:,} 步，运动量充足'))
    elif steps >= 6000:
        conclusions.append(('🔵', 'badge-info', f'{steps:,} steps - decent activity' if lang == 'en' else f'{steps:,} 步，运动量良好'))
    else:
        conclusions.append(('🟡', 'badge-warning', f'{steps:,} steps - try to move more' if lang == 'en' else f'{steps:,} 步，运动量偏少'))
    
    html = ''
    for emoji, badge_class, desc in conclusions:
        html += f'<div class="conclusion-item"><span class="badge {badge_class}">{emoji}</span><span>{desc}</span></div>'
    
    return html

def generate_heart_rate_chart(data, lang):
    """生成全天心率图表配置"""
    hr_data = data.get('heart_rate_series', [])
    
    if not hr_data:
        return json.dumps({
            'type': 'line',
            'data': {'labels': [], 'datasets': [{'data': []}]},
            'options': {
                'responsive': True,
                'maintainAspectRatio': False,
                'plugins': {'title': {'display': True, 'text': get_text('no_hr_data', lang)}}
            }
        })
    
    # Sample data if too many points
    if len(hr_data) > 20:
        step = len(hr_data) // 15
        hr_data = hr_data[::step]
    
    times = [d['time'] for d in hr_data]
    hrs = [d['hr'] for d in hr_data]
    
    return json.dumps({
        'type': 'line',
        'data': {
            'labels': times,
            'datasets': [{
                'label': 'HR (bpm)',
                'data': hrs,
                'borderColor': '#667eea',
                'backgroundColor': 'rgba(102, 126, 234, 0.1)',
                'borderWidth': 3,
                'fill': True,
                'tension': 0.4
            }]
        },
        'options': {
            'responsive': True,
            'maintainAspectRatio': False,
            'plugins': {'legend': {'display': False}},
            'scales': {
                'y': {'min': max(30, min(hrs) - 10), 'max': max(180, max(hrs) + 20)},
                'x': {'grid': {'display': False}}
            }
        }
    })

def generate_workout_chart(data, lang):
    """生成锻炼心率图表配置"""
    workout_data = data.get('workout_hr_series', [])
    
    if not workout_data:
        return json.dumps({
            'type': 'line',
            'data': {'labels': [], 'datasets': [{'data': []}]},
            'options': {
                'responsive': True,
                'maintainAspectRatio': False,
                'plugins': {'title': {'display': True, 'text': get_text('no_workout', lang)}}
            }
        })
    
    if len(workout_data) > 15:
        step = len(workout_data) // 10
        workout_data = workout_data[::step]
    
    times = [d['time'] for d in workout_data]
    hrs = [d['hr'] for d in workout_data]
    
    return json.dumps({
        'type': 'line',
        'data': {
            'labels': times,
            'datasets': [{
                'label': 'Workout HR',
                'data': hrs,
                'borderColor': '#f59e0b',
                'backgroundColor': 'rgba(245, 158, 11, 0.2)',
                'borderWidth': 3,
                'fill': True
            }]
        },
        'options': {
            'responsive': True,
            'maintainAspectRatio': False,
            'plugins': {'legend': {'display': False}},
            'scales': {
                'y': {'min': 80, 'max': max(180, max(hrs) + 10)},
                'x': {'grid': {'display': False}}
            }
        }
    })

def generate_sleep_chart(data, lang):
    """生成睡眠结构图表配置"""
    sleep_deep = data.get('sleep_deep', 1)
    sleep_rem = data.get('sleep_rem', 1.5)
    sleep_core = data.get('sleep_core', 3)
    sleep_awake = data.get('sleep_awake', 0.5)
    
    return json.dumps({
        'type': 'doughnut',
        'data': {
            'labels': [get_text('deep_sleep', lang), get_text('rem_sleep', lang), 
                      get_text('light_sleep', lang), get_text('awake', lang)],
            'datasets': [{
                'data': [sleep_deep, sleep_rem, sleep_core, sleep_awake],
                'backgroundColor': ['#4f46e5', '#8b5cf6', '#06b6d4', '#f59e0b'],
                'borderWidth': 0
            }]
        },
        'options': {
            'responsive': True,
            'maintainAspectRatio': False,
            'cutout': '60%',
            'plugins': {
                'legend': {
                    'position': 'right',
                    'labels': {'font': {'size': 10}, 'boxWidth': 12}
                }
            }
        }
    })

if __name__ == '__main__':
    # Test with sample data
    sample_data = {
        'date': '2026-02-20',
        'weekday': '4',
        'day_of_year': 51,
        'recovery_score': 75,
        'sleep_score': 68,
        'exercise_score': 82,
        'steps': 8542,
        'sleep_hours': 6.5,
        'has_sleep_data': True,
        'hrv': 52,
        'resting_hr': 58,
        'exercise_min': 45,
        'active_calories': 420,
        'floors': 12,
        'distance': 6.8,
        'blood_oxygen': 98,
        'sleep_deep': 1.3,
        'sleep_rem': 1.6,
        'sleep_core': 3.2,
        'sleep_awake': 0.4,
        'sleep_deep_pct': 20,
        'sleep_rem_pct': 25,
        'sleep_core_pct': 49,
        'sleep_awake_pct': 6,
        'sleep_efficiency': 0.94,
        'sleep_start': '23:30',
        'sleep_end': '06:00',
        'time_in_bed': 6.5,
        'workouts': [
            {
                'type': 'Stair Climbing' if False else '爬楼梯',
                'icon': '🏢',
                'duration': 2000,
                'calories': 280,
                'avg_hr': 150,
                'start_time': '20:25',
                'end_time': '21:06'
            }
        ],
        'heart_rate_series': [
            {'time': '06:00', 'hr': 55},
            {'time': '08:00', 'hr': 72},
            {'time': '10:00', 'hr': 68},
            {'time': '12:00', 'hr': 75},
            {'time': '14:00', 'hr': 70},
            {'time': '16:00', 'hr': 73},
            {'time': '18:00', 'hr': 85},
            {'time': '20:00', 'hr': 140},
            {'time': '22:00', 'hr': 62},
        ],
        'workout_hr_series': [
            {'time': '20:25', 'hr': 130},
            {'time': '20:30', 'hr': 145},
            {'time': '20:35', 'hr': 155},
            {'time': '20:40', 'hr': 160},
            {'time': '20:45', 'hr': 158},
            {'time': '20:50', 'hr': 152},
            {'time': '20:55', 'hr': 148},
            {'time': '21:00', 'hr': 140},
        ]
    }
    
    # Generate both versions
    output_dir = '/tmp/health-report-test'
    import os
    os.makedirs(output_dir, exist_ok=True)
    
    generate_multilingual_report(sample_data, f'{output_dir}/report-zh.html', 'zh')
    generate_multilingual_report(sample_data, f'{output_dir}/report-en.html', 'en')
    
    print(f"✅ Reports generated:")
    print(f"   Chinese: {output_dir}/report-zh.html")
    print(f"   English: {output_dir}/report-en.html")