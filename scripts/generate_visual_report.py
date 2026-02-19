#!/usr/bin/env python3
"""
可视化健康报告生成器
生成包含图表的 HTML/PDF 报告
"""

import json
import sys
from pathlib import Path
from datetime import datetime, timedelta

def generate_visual_report(health_data, output_file):
    """生成可视化报告"""
    
    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>健康报告 - {health_data['date']}</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        @page {{ size: A4; margin: 1.5cm; }}
        
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", sans-serif;
            font-size: 10pt;
            line-height: 1.5;
            color: #333;
            background: #f5f5f5;
            padding: 20px;
        }}
        
        .container {{
            max-width: 800px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 2px 20px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        
        /* 头部 */
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        
        .header h1 {{
            font-size: 24pt;
            margin-bottom: 10px;
            font-weight: 600;
        }}
        
        .header .date {{
            opacity: 0.9;
            font-size: 12pt;
        }}
        
        /* 评分卡片 */
        .score-section {{
            display: flex;
            justify-content: center;
            padding: 30px;
            gap: 20px;
            flex-wrap: wrap;
        }}
        
        .score-card {{
            background: #f8f9fa;
            border-radius: 16px;
            padding: 25px 35px;
            text-align: center;
            min-width: 140px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.08);
        }}
        
        .score-card .value {{
            font-size: 36pt;
            font-weight: 700;
            color: #667eea;
            line-height: 1;
        }}
        
        .score-card .label {{
            font-size: 10pt;
            color: #666;
            margin-top: 8px;
        }}
        
        .score-card .status {{
            font-size: 11pt;
            font-weight: 600;
            margin-top: 5px;
        }}
        
        .status-good {{ color: #27ae60; }}
        .status-warning {{ color: #f39c12; }}
        .status-bad {{ color: #e74c3c; }}
        
        /* 主要内容区 */
        .content {{
            padding: 0 30px 30px;
        }}
        
        .section {{
            margin-bottom: 25px;
            background: #fff;
            border-radius: 12px;
            padding: 20px;
            border: 1px solid #eee;
        }}
        
        .section-title {{
            font-size: 14pt;
            font-weight: 600;
            color: #2c3e50;
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        
        .section-title .icon {{
            font-size: 18pt;
        }}
        
        /* 图表容器 */
        .chart-container {{
            position: relative;
            height: 200px;
            margin: 15px 0;
        }}
        
        .chart-container.large {{
            height: 250px;
        }}
        
        /* 关键指标网格 */
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
            gap: 15px;
            margin: 15px 0;
        }}
        
        .metric-item {{
            text-align: center;
            padding: 15px;
            background: #f8f9fa;
            border-radius: 10px;
        }}
        
        .metric-item .number {{
            font-size: 20pt;
            font-weight: 700;
            color: #667eea;
        }}
        
        .metric-item .unit {{
            font-size: 9pt;
            color: #999;
        }}
        
        .metric-item .label {{
            font-size: 9pt;
            color: #666;
            margin-top: 5px;
        }}
        
        /* 结论区域 */
        .conclusions {{
            background: linear-gradient(135deg, #f5f7fa 0%, #e4e8ec 100%);
            border-left: 4px solid #667eea;
            padding: 20px;
            border-radius: 0 12px 12px 0;
            margin: 20px 0;
        }}
        
        .conclusions h3 {{
            color: #667eea;
            font-size: 12pt;
            margin-bottom: 12px;
        }}
        
        .conclusion-item {{
            display: flex;
            align-items: flex-start;
            gap: 10px;
            margin: 10px 0;
            font-size: 10pt;
        }}
        
        .conclusion-item .badge {{
            padding: 3px 8px;
            border-radius: 12px;
            font-size: 8pt;
            font-weight: 600;
            white-space: nowrap;
        }}
        
        .badge-good {{ background: #d4edda; color: #155724; }}
        .badge-warning {{ background: #fff3cd; color: #856404; }}
        .badge-bad {{ background: #f8d7da; color: #721c24; }}
        
        /* 建议 */
        .recommendations {{
            background: #fff;
            border: 2px solid #667eea;
            border-radius: 12px;
            padding: 20px;
            margin: 20px 0;
        }}
        
        .recommendations h3 {{
            color: #667eea;
            font-size: 12pt;
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        
        .rec-item {{
            display: flex;
            gap: 10px;
            margin: 10px 0;
            padding: 12px;
            background: #f8f9fa;
            border-radius: 8px;
            font-size: 10pt;
        }}
        
        .rec-item .priority {{
            font-weight: 700;
            min-width: 40px;
        }}
        
        .priority-high {{ color: #e74c3c; }}
        .priority-medium {{ color: #f39c12; }}
        .priority-low {{ color: #27ae60; }}
        
        /* 饮食/备注区域 */
        .user-input {{
            background: #fff9e6;
            border: 2px dashed #f39c12;
            border-radius: 12px;
            padding: 20px;
            margin: 15px 0;
            min-height: 80px;
        }}
        
        .user-input h4 {{
            color: #f39c12;
            font-size: 11pt;
            margin-bottom: 10px;
        }}
        
        .user-input .placeholder {{
            color: #999;
            font-style: italic;
            font-size: 10pt;
        }}
        
        .user-input .content {{
            color: #333;
            font-size: 10pt;
            white-space: pre-wrap;
        }}
        
        /* 页脚 */
        .footer {{
            text-align: center;
            padding: 20px;
            color: #999;
            font-size: 9pt;
            border-top: 1px solid #eee;
        }}
    </style>
</head>
<body>
    <div class="container">
        <!-- 头部 -->
        <div class="header">
            <h1>健康日报</h1>
            <div class="date">{health_data['date']} | 星期{health_data.get('weekday', '')}</div>
        </div>
        
        <!-- 评分卡片 -->
        <div class="score-section">
            <div class="score-card">
                <div class="value">{health_data.get('recovery_score', 0)}</div>
                <div class="label">Recovery Score</div>
                <div class="status {health_data.get('recovery_status_class', 'status-warning')}">{health_data.get('recovery_status', '一般')}</div>
            </div>
            <div class="score-card">
                <div class="value">{health_data.get('sleep_score', 0)}</div>
                <div class="label">睡眠质量</div>
                <div class="status {health_data.get('sleep_status_class', 'status-bad')}">{health_data.get('sleep_status_text', '不足')}</div>
            </div>
            <div class="score-card">
                <div class="value">{health_data.get('exercise_score', 0)}%</div>
                <div class="label">运动完成</div>
                <div class="status {health_data.get('exercise_status_class', 'status-warning')}">{health_data.get('exercise_status_text', '中等')}</div>
            </div>
        </div>
        
        <div class="content">
            <!-- 关键指标 -->
            <div class="section">
                <div class="section-title"><span class="icon">📊</span>关键指标</div>
                <div class="metrics-grid">
                    <div class="metric-item">
                        <div class="number">{health_data.get('steps', 0):,}</div>
                        <div class="unit">步</div>
                        <div class="label">今日步数</div>
                    </div>
                    <div class="metric-item">
                        <div class="number">{health_data.get('sleep_hours', 0)}</div>
                        <div class="unit">小时</div>
                        <div class="label">睡眠时长</div>
                    </div>
                    <div class="metric-item">
                        <div class="number">{health_data.get('hrv', 0)}</div>
                        <div class="unit">ms</div>
                        <div class="label">HRV</div>
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
                        <div class="number">{health_data.get('floors', 0)}</div>
                        <div class="unit">层</div>
                        <div class="label">爬楼层数</div>
                    </div>
                </div>
            </div>
            
            <!-- 结论 -->
            <div class="conclusions">
                <h3>📋 今日结论</h3>
                {generate_conclusions(health_data)}
            </div>
            
            <!-- 建议 -->
            <div class="recommendations">
                <h3>💡 明日建议</h3>
                {generate_recommendations(health_data)}
            </div>
            
            <!-- 饮食记录 -->
            <div class="section">
                <div class="section-title"><span class="icon">🍽️</span>饮食记录</div>
                <div class="user-input">
                    {health_data.get('diet_content') or '<div class="placeholder">（未记录 - 请私发补充）</div>'}
                </div>
            </div>
            
            <!-- 备注 -->
            <div class="section">
                <div class="section-title"><span class="icon">📝</span>身体备注</div>
                <div class="user-input">
                    {health_data.get('notes_content') or '<div class="placeholder">（未记录 - 请私发补充：精力、情绪、皮肤状态等）</div>'}
                </div>
            </div>
            
        </div>
        
        <div class="footer">
            由 Health Agent 自动生成 | 数据来源: Apple Health + Google Fit
        </div>
    </div>
</body>
</html>'''
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)
    
    return output_file

def generate_conclusions(data):
    """生成结论 HTML"""
    conclusions = []
    
    # 睡眠结论
    sleep_hours = data.get('sleep_hours', 0)
    if sleep_hours < 6:
        conclusions.append(('🔴 睡眠严重不足', 'badge-bad', f'仅睡 {sleep_hours} 小时，远低于 7-8 小时目标，影响恢复'))
    elif sleep_hours < 7:
        conclusions.append(('🟡 睡眠偏短', 'badge-warning', f'睡眠 {sleep_hours} 小时，建议今晚提早入睡'))
    else:
        conclusions.append(('🟢 睡眠充足', 'badge-good', f'睡眠 {sleep_hours} 小时，恢复良好'))
    
    # HRV 结论
    hrv = data.get('hrv', 0)
    if hrv >= 50:
        conclusions.append(('🟢 HRV 优秀', 'badge-good', f'HRV {hrv}ms，自主神经恢复良好'))
    elif hrv >= 40:
        conclusions.append(('🟡 HRV 正常', 'badge-warning', f'HRV {hrv}ms，恢复中'))
    else:
        conclusions.append(('🔴 HRV 偏低', 'badge-bad', f'HRV {hrv}ms，身体压力较大'))
    
    # 运动结论
    steps = data.get('steps', 0)
    if steps >= 10000:
        conclusions.append(('🟢 运动量充足', 'badge-good', f'{steps:,} 步，超额完成目标'))
    elif steps >= 8000:
        conclusions.append(('🟡 运动量良好', 'badge-warning', f'{steps:,} 步，接近目标'))
    else:
        conclusions.append(('🔴 运动量不足', 'badge-bad', f'{steps:,} 步，需增加日常活动'))
    
    html = ''
    for title, badge_class, desc in conclusions:
        html += f'<div class="conclusion-item"><span class="badge {badge_class}">{title}</span><span>{desc}</span></div>'
    
    return html

def generate_recommendations(data):
    """生成建议 HTML"""
    recs = []
    
    sleep_hours = data.get('sleep_hours', 0)
    if sleep_hours < 6:
        recs.append(('<span class="priority priority-high">[最高]</span>', '今晚 22:30 前必须入睡，保证 7+ 小时睡眠'))
    
    steps = data.get('steps', 0)
    if steps < 8000:
        recs.append(('<span class="priority priority-medium">[建议]</span>', f'今日目标 {10000-steps:,} 步补足，建议爬楼梯 30 分钟'))
    
    hrv = data.get('hrv', 0)
    if hrv >= 50:
        recs.append(('<span class="priority priority-low">[可选]</span>', '恢复良好，可进行中等强度训练'))
    
    html = ''
    for priority, text in recs:
        html += f'<div class="rec-item">{priority}<span>{text}</span></div>'
    
    return html

if __name__ == '__main__':
    # 示例数据
    sample_data = {
        'date': '2026-02-18',
        'weekday': '三',
        'recovery_score': 7,
        'recovery_status': '良好',
        'recovery_status_class': 'status-warning',
        'sleep_score': 5,
        'sleep_status_text': '不足',
        'sleep_status_class': 'status-bad',
        'exercise_score': 86,
        'exercise_status_text': '中等',
        'exercise_status_class': 'status-warning',
        'steps': 6852,
        'sleep_hours': 5.4,
        'hrv': 52,
        'resting_hr': 57,
        'exercise_min': 40,
        'floors': 108,
        'diet_content': '',
        'notes_content': ''
    }
    
    output = sys.argv[1] if len(sys.argv) > 1 else '/tmp/visual-report.html'
    generate_visual_report(sample_data, output)
    print(f"✅ 报告已生成: {output}")
