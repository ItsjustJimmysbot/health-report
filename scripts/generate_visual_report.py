#!/usr/bin/env python3
"""
可视化健康报告生成器 v2
生成包含图表的 HTML/PDF 报告 - 评分满分100，四色分级
"""

import json
import sys
from pathlib import Path
from datetime import datetime, timedelta

def get_score_color(score, is_reversed=False):
    """
    根据分数返回颜色类
    标准评分: 0-40 红色, 40-60 黄色, 60-80 蓝色, 80-100 绿色
    is_reversed: 反向指标（如静息心率，越低越好）
    """
    if is_reversed:
        score = 100 - score
    
    if score < 40:
        return {
            'class': 'score-red',
            'bg': '#fee2e2',
            'text': '#dc2626',
            'label': '需改善',
            'emoji': '🔴'
        }
    elif score < 60:
        return {
            'class': 'score-yellow',
            'bg': '#fef3c7',
            'text': '#d97706',
            'label': '一般',
            'emoji': '🟡'
        }
    elif score < 80:
        return {
            'class': 'score-blue',
            'bg': '#dbeafe',
            'text': '#2563eb',
            'label': '良好',
            'emoji': '🔵'
        }
    else:
        return {
            'class': 'score-green',
            'bg': '#d1fae5',
            'text': '#059669',
            'label': '优秀',
            'emoji': '🟢'
        }

def calculate_recovery_score(data):
    """计算恢复度评分 (0-100)"""
    scores = []
    
    # HRV 评分 (30%)
    hrv = data.get('hrv', 0)
    hrv_score = min(100, max(0, (hrv / 60) * 100)) if hrv > 0 else 50
    scores.append(('hrv', hrv_score, 0.30))
    
    # 睡眠评分 (40%)
    sleep_hours = data.get('sleep_hours', 0)
    sleep_score = min(100, max(0, (sleep_hours / 8) * 100)) if sleep_hours > 0 else 40
    scores.append(('sleep', sleep_score, 0.40))
    
    # 静息心率评分 (30%，反向)
    resting_hr = data.get('resting_hr', 70)
    # 静息心率 50-60 为最佳，>80 或 <45 为差
    if 50 <= resting_hr <= 60:
        hr_score = 100
    elif 45 <= resting_hr < 50 or 60 < resting_hr <= 65:
        hr_score = 80
    elif 40 <= resting_hr < 45 or 65 < resting_hr <= 75:
        hr_score = 60
    else:
        hr_score = 40
    scores.append(('resting_hr', hr_score, 0.30))
    
    total = sum(s[1] * s[2] for s in scores)
    return round(total)

def calculate_sleep_score(data):
    """计算睡眠质量评分 (0-100) - 严格版"""
    sleep_hours = data.get('sleep_hours', 0)
    sleep_deep = data.get('sleep_deep_pct', 0)
    sleep_rem = data.get('sleep_rem_pct', 0)
    sleep_efficiency = data.get('sleep_efficiency', 0)
    
    # 基础时长分 (50%) - 严格计算
    # < 4小时: 0-20分, 4-6小时: 20-50分, 6-7小时: 50-70分, 7-8小时: 70-90分, 8-9小时: 90-100分
    if sleep_hours < 4:
        duration_score = max(0, sleep_hours / 4 * 20)  # 0-4小时 -> 0-20分
    elif sleep_hours < 6:
        duration_score = 20 + (sleep_hours - 4) / 2 * 30  # 4-6小时 -> 20-50分
    elif sleep_hours < 7:
        duration_score = 50 + (sleep_hours - 6) * 20  # 6-7小时 -> 50-70分
    elif sleep_hours < 8:
        duration_score = 70 + (sleep_hours - 7) * 20  # 7-8小时 -> 70-90分
    elif sleep_hours <= 9:
        duration_score = 90 + (sleep_hours - 8) * 10  # 8-9小时 -> 90-100分
    else:
        duration_score = 100  # >9小时封顶
    
    # 深度睡眠分 (20%) - 目标 15-25%
    deep_score = 100 if 15 <= sleep_deep <= 25 else max(0, 100 - abs(sleep_deep - 20) * 5)
    
    # REM 睡眠分 (15%) - 目标 20-25%
    rem_score = 100 if 20 <= sleep_rem <= 25 else max(0, 100 - abs(sleep_rem - 22) * 5)
    
    # 睡眠效率分 (15%) - 目标 >85%
    efficiency_score = min(100, max(0, (sleep_efficiency / 0.85) * 100)) if sleep_efficiency > 0 else 70
    
    return round(duration_score * 0.5 + deep_score * 0.2 + rem_score * 0.15 + efficiency_score * 0.15)

def calculate_exercise_score(data):
    """计算运动完成评分 (0-100)"""
    steps = data.get('steps', 0)
    exercise_min = data.get('exercise_min', 0)
    active_calories = data.get('active_calories', 0)
    
    # 步数分 (40%) - 目标 10000
    steps_score = min(100, (steps / 10000) * 100)
    
    # 锻炼时间分 (35%) - 目标 30分钟
    exercise_score = min(100, (exercise_min / 30) * 100)
    
    # 活跃卡路里分 (25%) - 目标 500
    calories_score = min(100, (active_calories / 500) * 100) if active_calories > 0 else 50
    
    return round(steps_score * 0.4 + exercise_score * 0.35 + calories_score * 0.25)

def generate_heart_rate_chart(data):
    """生成全天心率折线图数据"""
    hr_data = data.get('heart_rate_series', [])
    if not hr_data:
        # 生成模拟数据
        hr_data = [
            {"time": "06:00", "hr": 55}, {"time": "08:00", "hr": 72},
            {"time": "10:00", "hr": 68}, {"time": "12:00", "hr": 75},
            {"time": "14:00", "hr": 70}, {"time": "16:00", "hr": 73},
            {"time": "18:00", "hr": 85}, {"time": "20:00", "hr": 78},
            {"time": "22:00", "hr": 62}, {"time": "23:00", "hr": 58}
        ]
    
    times = [d['time'] for d in hr_data]
    hrs = [d['hr'] for d in hr_data]
    
    chart_config = f"""
    {{
        type: 'line',
        data: {{
            labels: {json.dumps(times)},
            datasets: [{{
                label: '心率 (bpm)',
                data: {json.dumps(hrs)},
                borderColor: '#667eea',
                backgroundColor: 'rgba(102, 126, 234, 0.1)',
                borderWidth: 3,
                fill: true,
                tension: 0.4,
                pointRadius: 4,
                pointBackgroundColor: '#667eea'
            }}]
        }},
        options: {{
            responsive: true,
            maintainAspectRatio: false,
            plugins: {{
                legend: {{ display: false }},
                title: {{ display: false }}
            }},
            scales: {{
                y: {{
                    beginAtZero: false,
                    min: 40,
                    max: 140,
                    grid: {{ color: 'rgba(0,0,0,0.05)' }},
                    ticks: {{ font: {{ size: 10 }} }}
                }},
                x: {{
                    grid: {{ display: false }},
                    ticks: {{ font: {{ size: 10 }} }}
                }}
            }}
        }}
    }}"""
    return chart_config

def generate_workout_chart(data):
    """生成锻炼心率图"""
    workout_data = data.get('workout_hr_series', [])
    if not workout_data:
        # 生成模拟数据
        workout_data = [
            {"time": "0:00", "hr": 110, "zone": "warmup"},
            {"time": "0:05", "hr": 135, "zone": "fat_burn"},
            {"time": "0:10", "hr": 152, "zone": "cardio"},
            {"time": "0:15", "hr": 148, "zone": "cardio"},
            {"time": "0:20", "hr": 158, "zone": "peak"},
            {"time": "0:25", "hr": 145, "zone": "cardio"},
            {"time": "0:30", "hr": 120, "zone": "cooldown"}
        ]
    
    times = [d['time'] for d in workout_data]
    hrs = [d['hr'] for d in workout_data]
    
    chart_config = f"""
    {{
        type: 'line',
        data: {{
            labels: {json.dumps(times)},
            datasets: [{{
                label: '锻炼心率',
                data: {json.dumps(hrs)},
                borderColor: '#f59e0b',
                backgroundColor: (ctx) => {{
                    const chart = ctx.chart;
                    const {{ctx: canvasCtx, chartArea}} = chart;
                    if (!chartArea) return null;
                    const gradient = canvasCtx.createLinearGradient(0, chartArea.top, 0, chartArea.bottom);
                    gradient.addColorStop(0, 'rgba(245, 158, 11, 0.4)');
                    gradient.addColorStop(0.5, 'rgba(245, 158, 11, 0.1)');
                    gradient.addColorStop(1, 'rgba(102, 126, 234, 0.1)');
                    return gradient;
                }},
                borderWidth: 3,
                fill: true,
                tension: 0.3,
                pointRadius: 5,
                pointBackgroundColor: '#f59e0b',
                pointBorderColor: '#fff',
                pointBorderWidth: 2
            }}]
        }},
        options: {{
            responsive: true,
            maintainAspectRatio: false,
            plugins: {{
                legend: {{ display: false }},
                annotation: {{
                    annotations: {{
                        zone1: {{
                            type: 'box',
                            yMin: 90, yMax: 114,
                            backgroundColor: 'rgba(59, 130, 246, 0.08)',
                            borderWidth: 0
                        }},
                        zone2: {{
                            type: 'box',
                            yMin: 114, yMax: 133,
                            backgroundColor: 'rgba(34, 197, 94, 0.08)',
                            borderWidth: 0
                        }},
                        zone3: {{
                            type: 'box',
                            yMin: 133, yMax: 152,
                            backgroundColor: 'rgba(245, 158, 11, 0.08)',
                            borderWidth: 0
                        }},
                        zone4: {{
                            type: 'box',
                            yMin: 152, yMax: 180,
                            backgroundColor: 'rgba(239, 68, 68, 0.08)',
                            borderWidth: 0
                        }}
                    }}
                }}
            }},
            scales: {{
                y: {{
                    beginAtZero: false,
                    min: 80,
                    max: 180,
                    grid: {{ color: 'rgba(0,0,0,0.05)' }},
                    ticks: {{ font: {{ size: 10 }} }}
                }},
                x: {{
                    grid: {{ display: false }},
                    ticks: {{ font: {{ size: 10 }} }}
                }}
            }}
        }}
    }}"""
    return chart_config

def generate_sleep_chart(data):
    """生成睡眠结构图"""
    sleep_stages = data.get('sleep_stages', {
        'deep': 1.5,
        'rem': 1.8,
        'core': 3.5,
        'awake': 0.4
    })
    
    chart_config = f"""
    {{
        type: 'doughnut',
        data: {{
            labels: ['深睡', 'REM', '浅睡', '清醒'],
            datasets: [{{
                data: [{sleep_stages.get('deep', 0)}, {sleep_stages.get('rem', 0)}, {sleep_stages.get('core', 0)}, {sleep_stages.get('awake', 0)}],
                backgroundColor: ['#4f46e5', '#8b5cf6', '#06b6d4', '#f59e0b'],
                borderWidth: 0,
                hoverOffset: 4
            }}]
        }},
        options: {{
            responsive: true,
            maintainAspectRatio: false,
            cutout: '60%',
            plugins: {{
                legend: {{
                    position: 'right',
                    labels: {{ font: {{ size: 10 }}, boxWidth: 12 }}
                }}
            }}
        }}
    }}"""
    return chart_config

def generate_visual_report(health_data, output_file):
    """生成可视化报告"""
    
    # 计算各项评分
    recovery_score = calculate_recovery_score(health_data)
    sleep_score = calculate_sleep_score(health_data)
    exercise_score = calculate_exercise_score(health_data)
    
    # 获取颜色
    recovery_color = get_score_color(recovery_score)
    sleep_color = get_score_color(sleep_score)
    exercise_color = get_score_color(exercise_score)
    
    # 图表配置
    hr_chart = generate_heart_rate_chart(health_data)
    workout_chart = generate_workout_chart(health_data)
    sleep_chart = generate_sleep_chart(health_data)
    
    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>健康报告 - {health_data['date']}</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-annotation@2.1.0"></script>
    <style>
        @page {{ size: A4; margin: 1cm; }}
        
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", "STHeiti", "Microsoft YaHei", sans-serif;
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
        
        /* ===== 头部 ===== */
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
        
        /* ===== 评分卡片区 ===== */
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
            transition: none;
        }}
        
        /* 移除hover效果，避免PDF渲染问题 */
        .score-card:hover {{ transform: none; }}
        
        /* 四色评分卡 - 简化样式 */
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
        
        /* ===== 主要内容 ===== */
        .content {{
            padding: 0 25px 25px;
        }}
        
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
        
        .section-title .icon {{
            font-size: 18pt;
            background: linear-gradient(135deg, #667eea, #764ba2);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        
        /* ===== 关键指标网格 ===== */
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
            transition: all 0.2s;
        }}
        
        .metric-item:hover {{
            background: linear-gradient(180deg, #eff6ff 0%, #dbeafe 100%);
            border-color: #3b82f6;
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
        
        /* ===== 图表容器 ===== */
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
        
        /* ===== 结论区域 ===== */
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
        
        .conclusion-item .badge {{
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
        
        /* ===== 建议区域 ===== */
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
            display: flex;
            align-items: center;
            gap: 8px;
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
        
        .rec-item .priority {{
            font-weight: 700;
            min-width: 45px;
            font-size: 9pt;
        }}
        
        .priority-high {{ color: #dc2626; }}
        .priority-medium {{ color: #d97706; }}
        .priority-low {{ color: #059669; }}
        
        /* ===== 睡眠详情 ===== */
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
        
        /* ===== 饮食/备注区域 ===== */
        .user-input {{
            background: linear-gradient(135deg, #fffbeb 0%, #fef3c7 100%);
            border: 2px dashed #f59e0b;
            border-radius: 12px;
            padding: 18px;
            margin: 12px 0;
            min-height: 60px;
        }}
        
        .user-input h4 {{
            color: #b45309;
            font-size: 11pt;
            margin-bottom: 10px;
            font-weight: 700;
        }}
        
        .user-input .placeholder {{
            color: #9ca3af;
            font-style: italic;
            font-size: 10pt;
        }}
        
        .user-input .content {{
            color: #374151;
            font-size: 10.5pt;
            white-space: pre-wrap;
            line-height: 1.7;
        }}
        
        /* ===== 运动详情 ===== */
        .workout-list {{
            margin-top: 10px;
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
        
        .workout-item .icon {{
            font-size: 20pt;
        }}
        
        .workout-item .info {{
            flex: 1;
        }}
        
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
        
        /* ===== 趋势对比 ===== */
        .trend-grid {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 10px;
            margin-top: 12px;
        }}
        
        .trend-item {{
            text-align: center;
            padding: 12px;
            background: #f9fafb;
            border-radius: 10px;
        }}
        
        .trend-item .label {{
            font-size: 8pt;
            color: #6b7280;
            margin-bottom: 4px;
        }}
        
        .trend-item .value {{
            font-size: 14pt;
            font-weight: 700;
            color: #1f2937;
        }}
        
        .trend-item .change {{
            font-size: 9pt;
            margin-top: 2px;
        }}
        
        .trend-up {{ color: #059669; }}
        .trend-down {{ color: #dc2626; }}
        .trend-same {{ color: #6b7280; }}
        
        /* ===== 饮食建议 ===== */
        .diet-recommendations {{
            background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%);
            border-radius: 12px;
            padding: 15px;
            margin-top: 10px;
        }}
        
        .diet-recommendations h4 {{
            color: #166534;
            font-size: 11pt;
            margin-bottom: 12px;
            font-weight: 700;
        }}
        
        .diet-meal {{
            background: white;
            border-radius: 10px;
            padding: 12px;
            margin-bottom: 10px;
            border-left: 4px solid #22c55e;
        }}
        
        .diet-meal .meal-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px;
        }}
        
        .diet-meal .meal-name {{
            font-weight: 700;
            color: #166534;
            font-size: 11pt;
        }}
        
        .diet-meal .meal-time {{
            font-size: 9pt;
            color: #6b7280;
            background: #f0fdf4;
            padding: 2px 8px;
            border-radius: 12px;
        }}
        
        .diet-meal .meal-foods {{
            font-size: 10pt;
            color: #374151;
            margin-bottom: 6px;
            line-height: 1.5;
        }}
        
        .diet-meal .meal-notes {{
            font-size: 9pt;
            color: #059669;
            font-style: italic;
        }}
        
        .diet-warning {{
            background: #fef3c7;
            border: 1px solid #f59e0b;
            border-radius: 8px;
            padding: 10px;
            margin-top: 10px;
            font-size: 10pt;
            color: #92400e;
        }}
        
        .diet-toggle {{
            margin-top: 15px;
        }}
        
        .diet-toggle summary {{
            font-size: 10pt;
            color: #2563eb;
            cursor: pointer;
            font-weight: 600;
            padding: 8px;
            background: #eff6ff;
            border-radius: 8px;
        }}
        
        .diet-toggle details[open] summary {{
            margin-bottom: 10px;
        }}
        
        /* ===== 页脚 ===== */
        .footer {{
            text-align: center;
            padding: 20px;
            color: #9ca3af;
            font-size: 9pt;
            border-top: 1px solid #e5e7eb;
            background: #f9fafb;
        }}
        
        .footer .brand {{
            font-weight: 700;
            color: #6b7280;
        }}
    </style>
</head>
<body>
    <div class="container">
        <!-- 头部 -->
        <div class="header">
            <h1>📊 健康日报</h1>
            <div class="date">{health_data['date']} | 星期{health_data.get('weekday', '')} | 第 {health_data.get('day_of_year', 0)} 天</div>
        </div>
        
        <!-- 评分卡片 - 满分100，四色分级 -->
        <div class="score-section">
            <div class="score-card {recovery_color['class']}">
                <div class="value">{recovery_score}</div>
                <div class="label">恢复度评分</div>
                <div class="status">{recovery_color['emoji']} {recovery_color['label']}</div>
            </div>
            <div class="score-card {sleep_color['class']}">
                <div class="value">{sleep_score}</div>
                <div class="label">睡眠质量</div>
                <div class="status">{sleep_color['emoji']} {sleep_color['label']}</div>
            </div>
            <div class="score-card {exercise_color['class']}">
                <div class="value">{exercise_score}</div>
                <div class="label">运动完成</div>
                <div class="status">{exercise_color['emoji']} {exercise_color['label']}</div>
            </div>
        </div>
        
        <div class="content">
            <!-- 关键指标总览 -->
            <div class="section">
                <div class="section-title"><span class="icon">📈</span>今日关键指标</div>
                <div class="metrics-grid">
                    <div class="metric-item">
                        <div class="number">{health_data.get('steps', 0):,}</div>
                        <div class="unit">步</div>
                        <div class="label">今日步数</div>
                    </div>
                    <div class="metric-item">
                        <div class="number">{health_data.get('sleep_hours', 0):.1f}</div>
                        <div class="unit">小时</div>
                        <div class="label">睡眠时长</div>
                    </div>
                    <div class="metric-item">
                        <div class="number">{health_data.get('hrv', 0)}</div>
                        <div class="unit">ms</div>
                        <div class="label">HRV 心率变异性</div>
                    </div>
                    <div class="metric-item">
                        <div class="number">{health_data.get('resting_hr', 0)}</div>
                        <div class="unit">bpm</div>
                        <div class="label">静息心率</div>
                    </div>
                    <div class="metric-item">
                        <div class="number">{health_data.get('exercise_min', 0)}</div>
                        <div class="unit">分钟</div>
                        <div class="label">锻炼时间</div>
                    </div>
                    <div class="metric-item">
                        <div class="number">{health_data.get('active_calories', 0):,}</div>
                        <div class="unit">千卡</div>
                        <div class="label">活跃消耗</div>
                    </div>
                    <div class="metric-item">
                        <div class="number">{health_data.get('floors', 0)}</div>
                        <div class="unit">层</div>
                        <div class="label">爬楼层数</div>
                    </div>
                    <div class="metric-item">
                        <div class="number">{health_data.get('distance', 0):.1f}</div>
                        <div class="unit">公里</div>
                        <div class="label">行走距离</div>
                    </div>
                    <div class="metric-item">
                        <div class="number">{health_data.get('blood_oxygen', 0)}%</div>
                        <div class="unit">SpO2</div>
                        <div class="label">血氧饱和度</div>
                    </div>
                </div>
            </div>
            
            <!-- 心率图表区 -->
            <div class="section">
                <div class="section-title"><span class="icon">❤️</span>心率分析</div>
                <div class="chart-row">
                    <div class="chart-container">
                        <div class="chart-title">全天心率趋势</div>
                        <div class="chart-wrapper">
                            <canvas id="hrChart"></canvas>
                        </div>
                    </div>
                    <div class="chart-container">
                        <div class="chart-title">锻炼心率区间</div>
                        <div class="chart-wrapper">
                            <canvas id="workoutChart"></canvas>
                        </div>
                    </div>
                </div>
                <div style="display: flex; justify-content: center; gap: 20px; margin-top: 10px; font-size: 9pt; color: #6b7280;">
                    <span><span style="color: #3b82f6;">●</span> 热身区 (&lt;114)</span>
                    <span><span style="color: #22c55e;">●</span> 燃脂区 (114-133)</span>
                    <span><span style="color: #f59e0b;">●</span> 有氧区 (133-152)</span>
                    <span><span style="color: #ef4444;">●</span> 峰值区 (&gt;152)</span>
                </div>
            </div>
            
            <!-- 睡眠详情 -->
            <div class="section">
                <div class="section-title"><span class="icon">😴</span>睡眠分析</div>
                <div class="chart-row">
                    <div class="chart-container">
                        <div class="chart-title">睡眠结构分布</div>
                        <div class="chart-wrapper">
                            <canvas id="sleepChart"></canvas>
                        </div>
                    </div>
                    <div style="padding: 15px;">
                        <div style="font-size: 11pt; font-weight: 700; color: #374151; margin-bottom: 10px;">睡眠效率: {health_data.get('sleep_efficiency', 0)*100:.0f}%</div>
                        <div class="sleep-details">
                            <div class="sleep-stage deep">
                                <div class="time">{health_data.get('sleep_deep', 0):.1f}h</div>
                                <div class="label">深睡 {health_data.get('sleep_deep_pct', 0):.0f}%</div>
                            </div>
                            <div class="sleep-stage rem">
                                <div class="time">{health_data.get('sleep_rem', 0):.1f}h</div>
                                <div class="label">REM {health_data.get('sleep_rem_pct', 0):.0f}%</div>
                            </div>
                            <div class="sleep-stage core">
                                <div class="time">{health_data.get('sleep_core', 0):.1f}h</div>
                                <div class="label">浅睡 {health_data.get('sleep_core_pct', 0):.0f}%</div>
                            </div>
                            <div class="sleep-stage awake">
                                <div class="time">{health_data.get('sleep_awake', 0):.1f}h</div>
                                <div class="label">清醒 {health_data.get('sleep_awake_pct', 0):.0f}%</div>
                            </div>
                        </div>
                        <div style="margin-top: 15px; padding: 10px; background: #f3f4f6; border-radius: 8px; font-size: 10pt;">
                            <strong>入睡:</strong> {health_data.get('sleep_start', '--:--')} | 
                            <strong>起床:</strong> {health_data.get('sleep_end', '--:--')} | 
                            <strong>卧床:</strong> {health_data.get('time_in_bed', 0):.1f}h
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- 运动详情 -->
            <div class="section">
                <div class="section-title"><span class="icon">🏃</span>运动记录</div>
                {generate_workout_list(health_data)}
            </div>
            
            <!-- 7日趋势对比 -->
            <div class="section">
                <div class="section-title"><span class="icon">📊</span>7日趋势对比</div>
                <div class="trend-grid">
                    <div class="trend-item">
                        <div class="label">步数 vs 上周</div>
                        <div class="value">{health_data.get('steps_7day_avg', 0):,}</div>
                        <div class="change {health_data.get('steps_trend_class', 'trend-same')}">{health_data.get('steps_trend', '→')}</div>
                    </div>
                    <div class="trend-item">
                        <div class="label">睡眠 vs 上周</div>
                        <div class="value">{health_data.get('sleep_7day_avg', 0):.1f}h</div>
                        <div class="change {health_data.get('sleep_trend_class', 'trend-same')}">{health_data.get('sleep_trend', '→')}</div>
                    </div>
                    <div class="trend-item">
                        <div class="label">HRV vs 上周</div>
                        <div class="value">{health_data.get('hrv_7day_avg', 0)}ms</div>
                        <div class="change {health_data.get('hrv_trend_class', 'trend-same')}">{health_data.get('hrv_trend', '→')}</div>
                    </div>
                    <div class="trend-item">
                        <div class="label">静息心率 vs 上周</div>
                        <div class="value">{health_data.get('rhr_7day_avg', 0)}bpm</div>
                        <div class="change {health_data.get('rhr_trend_class', 'trend-same')}">{health_data.get('rhr_trend', '→')}</div>
                    </div>
                </div>
            </div>
            
            <!-- 结论 -->
            <div class="conclusions">
                <h3>📋 今日健康结论</h3>
                {generate_conclusions(health_data, recovery_score, sleep_score, exercise_score)}
            </div>
            
            <!-- 建议 -->
            <div class="recommendations">
                <h3>💡 明日健康建议</h3>
                {generate_recommendations(health_data, recovery_score, sleep_score, exercise_score)}
            </div>
            
            <!-- 饮食建议 -->
            <div class="section">
                <div class="section-title"><span class="icon">🥗</span>明日饮食建议</div>
                {generate_diet_section_html(health_data)}
            </div>
            
            <!-- 饮食记录 -->
            <div class="section">
                <div class="section-title"><span class="icon">🍽️</span>今日饮食记录</div>
                <div class="user-input">
                    <h4>📝 今日实际饮食</h4>
                    {health_data.get('diet_content') or '<div class="placeholder">（未记录 - 可通过 Discord 私发补充，格式：饮食 早餐:xxx 午餐:xxx）</div>'}
                </div>
            </div>
            
            <!-- 备注 -->
            <div class="section">
                <div class="section-title"><span class="icon">📝</span>身体状态备注</div>
                <div class="user-input">
                    <h4>🤔 主观感受</h4>
                    {health_data.get('notes_content') or '<div class="placeholder">（未记录 - 可通过 Discord 私发补充，如：精力、情绪、皮肤状态、压力水平等）</div>'}
                </div>
            </div>
            
        </div>
        
        <div class="footer">
            <span class="brand">Health Agent</span> 自动生成 | 数据来源: Apple Health + Apple Watch<br>
            <span style="font-size: 8pt;">报告生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M")}</span>
        </div>
    </div>
    
    <script>
        // 全天心率图
        new Chart(document.getElementById('hrChart'), {hr_chart});
        
        // 锻炼心率图
        new Chart(document.getElementById('workoutChart'), {workout_chart});
        
        // 睡眠结构图
        new Chart(document.getElementById('sleepChart'), {sleep_chart});
    </script>
</body>
</html>'''
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)
    
    return output_file

def generate_workout_list(data):
    """生成运动列表 HTML"""
    workouts = data.get('workouts', [])
    if not workouts:
        # 如果没有 workout 数据，显示从 Apple Health 推断的数据
        floors = data.get('floors', 0)
        exercise_min = data.get('exercise_min', 0)
        
        # 根据爬楼层数推断爬楼梯运动
        if floors > 0:
            # 估算爬楼梯时间：每层楼约 15-20 秒，加上休息时间
            stair_duration = min(60, max(10, floors * 0.4))  # 估算分钟数
            workouts = [
                {
                    'type': f'爬楼梯 {floors} 层',
                    'icon': '🏢',
                    'duration': int(stair_duration),
                    'calories': int(floors * 3.5),  # 估算卡路里
                    'avg_hr': 130,
                    'start_time': data.get('workout_start', '12:25'),
                    'end_time': data.get('workout_end', '13:06')
                }
            ]
            # 如果有额外运动时间，添加其他运动
            if exercise_min > stair_duration:
                workouts.append({
                    'type': '其他运动',
                    'icon': '🏃',
                    'duration': int(exercise_min - stair_duration),
                    'calories': int((exercise_min - stair_duration) * 8),
                    'avg_hr': 125,
                    'start_time': data.get('workout_start2', '07:00'),
                    'end_time': data.get('workout_end2', '07:30')
                })
        elif exercise_min > 0:
            workouts = [
                {
                    'type': '日常活动',
                    'icon': '🚶',
                    'duration': int(exercise_min),
                    'calories': int(exercise_min * 6),
                    'avg_hr': 110,
                    'start_time': data.get('workout_start', '--:--'),
                    'end_time': data.get('workout_end', '--:--')
                }
            ]
        else:
            workouts = []
    
    html = '<div class="workout-list">'
    for w in workouts:
        start = w.get('start_time', w.get('time', '--:--'))
        end = w.get('end_time', '--:--')
        time_range = f"{start} - {end}" if end != '--:--' else start
        html += f'''
        <div class="workout-item">
            <div class="icon">{w.get('icon', '🏃')}</div>
            <div class="info">
                <div class="name">{w.get('type', '运动')}</div>
                <div class="meta">{time_range} · 平均心率 {w.get('avg_hr', 0)} bpm</div>
            </div>
            <div class="stats">
                <div class="duration">{w.get('duration', 0)} 分钟</div>
                <div class="calories">{w.get('calories', 0)} 千卡</div>
            </div>
        </div>
        '''
    html += '</div>'
    return html

def generate_conclusions(data, recovery_score, sleep_score, exercise_score):
    """生成结论 HTML"""
    conclusions = []
    
    # 恢复度结论
    if recovery_score >= 80:
        conclusions.append(('🟢 恢复度优秀', 'badge-good', f'综合评分 {recovery_score} 分，身体恢复良好，可进行高强度训练'))
    elif recovery_score >= 60:
        conclusions.append(('🔵 恢复度良好', 'badge-info', f'综合评分 {recovery_score} 分，身体状态尚可，建议中等强度运动'))
    elif recovery_score >= 40:
        conclusions.append(('🟡 恢复度一般', 'badge-warning', f'综合评分 {recovery_score} 分，身体有轻微疲劳，注意休慈'))
    else:
        conclusions.append(('🔴 恢复度较差', 'badge-bad', f'综合评分 {recovery_score} 分，身体疲劳明显，建议主动恢复'))
    
    # 睡眠结论
    sleep_hours = data.get('sleep_hours', 0)
    if sleep_hours < 6:
        conclusions.append(('🔴 睡眠严重不足', 'badge-bad', f'仅睡 {sleep_hours:.1f} 小时，远低于 7-8 小时目标，严重影响恢复'))
    elif sleep_hours < 7:
        conclusions.append(('🟡 睡眠偏短', 'badge-warning', f'睡眠 {sleep_hours:.1f} 小时，建议今晚提早 30 分钟入睡'))
    elif sleep_hours < 9:
        conclusions.append(('🔵 睡眠正常', 'badge-info', f'睡眠 {sleep_hours:.1f} 小时，符合健康标准'))
    else:
        conclusions.append(('🟢 睡眠充足', 'badge-good', f'睡眠 {sleep_hours:.1f} 小时，恢复质量优秀'))
    
    # HRV 结论
    hrv = data.get('hrv', 0)
    if hrv >= 60:
        conclusions.append(('🟢 HRV 优秀', 'badge-good', f'HRV {hrv}ms，自主神经恢复良好，压力水平低'))
    elif hrv >= 45:
        conclusions.append(('🔵 HRV 正常', 'badge-info', f'HRV {hrv}ms，恢复状态正常'))
    elif hrv >= 35:
        conclusions.append(('🟡 HRV 偏低', 'badge-warning', f'HRV {hrv}ms，身体有一定压力，注意放松'))
    else:
        conclusions.append(('🔴 HRV 过低', 'badge-bad', f'HRV {hrv}ms，身体压力过大，建议深度休息'))
    
    # 运动结论
    steps = data.get('steps', 0)
    exercise_min = data.get('exercise_min', 0)
    if steps >= 10000 and exercise_min >= 30:
        conclusions.append(('🟢 运动量充足', 'badge-good', f'{steps:,} 步 + {exercise_min} 分钟锻炼，完美完成目标'))
    elif steps >= 8000 or exercise_min >= 30:
        conclusions.append(('🔵 运动量良好', 'badge-info', f'{steps:,} 步 + {exercise_min} 分钟锻炼，基本达标'))
    elif steps >= 5000:
        conclusions.append(('🟡 运动量偏少', 'badge-warning', f'{steps:,} 步，建议增加日常活动'))
    else:
        conclusions.append(('🔴 运动量不足', 'badge-bad', f'{steps:,} 步，需大幅提升活动量'))
    
    # 静息心率结论
    rhr = data.get('resting_hr', 70)
    if 50 <= rhr <= 60:
        conclusions.append(('🟢 静息心率优秀', 'badge-good', f'{rhr} bpm，心肺功能良好'))
    elif 45 <= rhr <= 65:
        conclusions.append(('🔵 静息心率正常', 'badge-info', f'{rhr} bpm，处于正常范围'))
    elif rhr > 75:
        conclusions.append(('🟡 静息心率偏高', 'badge-warning', f'{rhr} bpm，可能疲劳或压力较大'))
    else:
        conclusions.append(('🔵 静息心率较低', 'badge-info', f'{rhr} bpm，运动员水平或需关注'))
    
    html = ''
    for title, badge_class, desc in conclusions:
        html += f'<div class="conclusion-item"><span class="badge {badge_class}">{title}</span><span>{desc}</span></div>'
    
    return html

def generate_recommendations(data, recovery_score, sleep_score, exercise_score):
    """生成建议 HTML"""
    recs = []
    
    # 根据恢复度建议
    if recovery_score < 60:
        recs.append(('high', '[优先]', '今晚 22:30 前入睡，确保 7.5+ 小时睡眠，睡前 1 小时远离屏幕'))
        recs.append(('high', '[优先]', '明日减少高强度运动，改为散步或瑜伽等轻度活动'))
    elif recovery_score < 80:
        recs.append(('medium', '[建议]', '可进行中等强度训练，注意监控心率不超过 150 bpm'))
    else:
        recs.append(('low', '[可选]', '恢复良好，可挑战高强度间歇训练或长距离有氧'))
    
    # 睡眠建议
    sleep_hours = data.get('sleep_hours', 0)
    if sleep_hours < 6:
        recs.append(('high', '[优先]', '睡眠严重不足，明日建议午休 20-30 分钟补偿'))
    elif sleep_hours < 7:
        recs.append(('medium', '[建议]', '今晚尝试提前 30 分钟上床，建立固定睡前仪式'))
    
    # 运动建议
    steps = data.get('steps', 0)
    if steps < 8000:
        remaining = 10000 - steps
        recs.append(('medium', '[建议]', f'今日目标还差 {remaining:,} 步，建议爬楼梯 20 分钟或快走 30 分钟补足'))
    
    # HRV 建议
    hrv = data.get('hrv', 0)
    if hrv < 40:
        recs.append(('high', '[优先]', 'HRV 偏低，建议进行深呼吸练习（4-7-8 呼吸法）或冥想 10 分钟'))
    
    # 饮食建议
    if not data.get('diet_content'):
        recs.append(('medium', '[建议]', '请补充今日饮食记录，以便进行营养分析'))
    
    html = ''
    for priority, label, text in recs:
        priority_class = f'priority-{priority}'
        html += f'<div class="rec-item {priority}"><span class="priority {priority_class}">{label}</span><span>{text}</span></div>'
    
    return html

def generate_diet_recommendations(sleep_hours, exercise_min, has_breakfast=True):
    """生成饮食建议
    
    Args:
        sleep_hours: 睡眠时长
        exercise_min: 锻炼时间
        has_breakfast: 是否吃早餐（True=三餐版，False=两餐版）
    
    Returns:
        dict: 包含三餐/两餐建议的字典
    """
    
    # 基础建议模板
    if has_breakfast:
        # 一日三餐版
        recommendations = {
            'breakfast': {
                'time': '07:30-08:30',
                'foods': ['全麦面包/燕麦', '鸡蛋 1-2个', '牛奶/豆浆', '水果'],
                'notes': '早餐摄入全天30%热量，补充蛋白质启动代谢'
            },
            'lunch': {
                'time': '12:00-13:00',
                'foods': ['米饭/杂粮饭 150g', '瘦肉/鱼 100g', '绿叶蔬菜', '豆制品'],
                'notes': '午餐摄入全天40%热量，保证碳水供能 afternoon work'
            },
            'dinner': {
                'time': '18:00-19:00',
                'foods': ['杂粮/薯类 100g', '鸡胸肉/鱼 100g', '大量蔬菜', '菌菇类'],
                'notes': '晚餐摄入全天30%热量，睡前3小时完成进食'
            }
        }
    else:
        # 两餐版（不吃早饭）
        recommendations = {
            'first_meal': {
                'time': '11:00-12:00',
                'foods': ['杂粮饭 200g', '瘦肉/蛋 150g', '混合蔬菜', '坚果 20g'],
                'notes': '第一餐摄入全天50%热量，弥补早餐缺失'
            },
            'second_meal': {
                'time': '17:00-18:00',
                'foods': ['藜麦/红薯 150g', '鱼类/豆腐 150g', '深色蔬菜', '酸奶'],
                'notes': '第二餐摄入全天50%热量，避免深夜饥饿'
            }
        }
    
    # 根据睡眠情况调整
    if sleep_hours < 6:
        recommendations['warning'] = '⚠️ 睡眠不足会导致食欲增加，注意控制碳水摄入，避免高糖零食'
        if has_breakfast:
            recommendations['breakfast']['notes'] += ' | 睡眠不足时增加优质蛋白，减少精制碳水'
        else:
            recommendations['first_meal']['notes'] += ' | 睡眠不足时增加优质蛋白'
    
    # 根据运动量调整
    if exercise_min >= 30:
        if has_breakfast:
            recommendations['lunch']['foods'].append('运动后补充：香蕉/蛋白棒')
            recommendations['dinner']['foods'].append('适量增加碳水帮助恢复')
        else:
            recommendations['first_meal']['foods'].append('运动后补充：香蕉')
    
    return recommendations

def generate_diet_section_html(data):
    """生成饮食建议HTML区块"""
    sleep_hours = data.get('sleep_hours', 0)
    exercise_min = data.get('exercise_min', 0)
    
    # 默认使用一日三餐版
    diet_rec = generate_diet_recommendations(sleep_hours, exercise_min, has_breakfast=True)
    
    html = '<div class="diet-recommendations">'
    html += '<h4>🍽️ 明日饮食建议（一日三餐版）</h4>'
    
    # 早餐
    breakfast = diet_rec['breakfast']
    html += f'''
    <div class="diet-meal">
        <div class="meal-header">
            <span class="meal-name">🌅 早餐</span>
            <span class="meal-time">{breakfast['time']}</span>
        </div>
        <div class="meal-foods">{" + ".join(breakfast['foods'])}</div>
        <div class="meal-notes">💡 {breakfast['notes']}</div>
    </div>
    '''
    
    # 午餐
    lunch = diet_rec['lunch']
    html += f'''
    <div class="diet-meal">
        <div class="meal-header">
            <span class="meal-name">☀️ 午餐</span>
            <span class="meal-time">{lunch['time']}</span>
        </div>
        <div class="meal-foods">{" + ".join(lunch['foods'])}</div>
        <div class="meal-notes">💡 {lunch['notes']}</div>
    </div>
    '''
    
    # 晚餐
    dinner = diet_rec['dinner']
    html += f'''
    <div class="diet-meal">
        <div class="meal-header">
            <span class="meal-name">🌙 晚餐</span>
            <span class="meal-time">{dinner['time']}</span>
        </div>
        <div class="meal-foods">{" + ".join(dinner['foods'])}</div>
        <div class="meal-notes">💡 {dinner['notes']}</div>
    </div>
    '''
    
    # 特殊情况提示
    if 'warning' in diet_rec:
        html += f'<div class="diet-warning">{diet_rec["warning"]}</div>'
    
    # 两餐版选项 - 直接显示而不是折叠
    html += '<h4 style="margin-top: 20px; color: #166534; font-size: 11pt;">🔄 两餐版建议（不吃早饭）</h4>'
    
    two_meal_rec = generate_diet_recommendations(sleep_hours, exercise_min, has_breakfast=False)
    
    first = two_meal_rec['first_meal']
    html += f'''
    <div class="diet-meal" style="border-left-color: #f59e0b;">
        <div class="meal-header">
            <span class="meal-name">🍽️ 第一餐</span>
            <span class="meal-time">{first['time']}</span>
        </div>
        <div class="meal-foods">{" + ".join(first['foods'])}</div>
        <div class="meal-notes">💡 {first['notes']}</div>
    </div>
    '''
    
    second = two_meal_rec['second_meal']
    html += f'''
    <div class="diet-meal" style="border-left-color: #f59e0b;">
        <div class="meal-header">
            <span class="meal-name">🍽️ 第二餐</span>
            <span class="meal-time">{second['time']}</span>
        </div>
        <div class="meal-foods">{" + ".join(second['foods'])}</div>
        <div class="meal-notes">💡 {second['notes']}</div>
    </div>
    '''
    
    html += '</div>'
    
    return html

if __name__ == '__main__':
    # 示例数据
    sample_data = {
        'date': '2026-02-19',
        'weekday': '四',
        'day_of_year': 50,
        'steps': 8542,
        'sleep_hours': 7.2,
        'hrv': 52,
        'resting_hr': 58,
        'exercise_min': 45,
        'active_calories': 420,
        'floors': 12,
        'distance': 6.8,
        'blood_oxygen': 98,
        # 睡眠详细数据
        'sleep_deep': 1.5,
        'sleep_deep_pct': 21,
        'sleep_rem': 1.8,
        'sleep_rem_pct': 25,
        'sleep_core': 3.5,
        'sleep_core_pct': 49,
        'sleep_awake': 0.4,
        'sleep_awake_pct': 5,
        'sleep_efficiency': 0.92,
        'sleep_start': '23:15',
        'sleep_end': '06:30',
        'time_in_bed': 7.5,
        # 趋势数据
        'steps_7day_avg': 9234,
        'steps_trend': '↓ 8%',
        'steps_trend_class': 'trend-down',
        'sleep_7day_avg': 6.8,
        'sleep_trend': '↑ 6%',
        'sleep_trend_class': 'trend-up',
        'hrv_7day_avg': 48,
        'hrv_trend': '↑ 8%',
        'hrv_trend_class': 'trend-up',
        'rhr_7day_avg': 59,
        'rhr_trend': '↓ 2%',
        'rhr_trend_class': 'trend-up',
        # 用户输入
        'diet_content': '',
        'notes_content': ''
    }
    
    output = sys.argv[1] if len(sys.argv) > 1 else '/tmp/visual-report-v2.html'
    generate_visual_report(sample_data, output)
    print(f"✅ 报告已生成: {output}")
    print(f"📊 恢复度评分: {calculate_recovery_score(sample_data)}/100")
    print(f"😴 睡眠质量评分: {calculate_sleep_score(sample_data)}/100")  
    print(f"🏃 运动完成评分: {calculate_exercise_score(sample_data)}/100")
