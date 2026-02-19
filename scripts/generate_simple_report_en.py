#!/usr/bin/env python3
"""
简化版可视化健康报告生成器 - 修复中文显示
"""

import sys
from pathlib import Path

def generate_simple_report(data, output_file):
    """生成简化版报告，确保 PDF 兼容性"""
    
    # 使用系统支持中文的字体
    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>Health Report - {data['date']}</title>
    <style>
        body {{
            font-family: "PingFang SC", "Hiragino Sans GB", "STHeiti", "Heiti SC", "Microsoft YaHei", sans-serif;
            font-size: 11pt;
            line-height: 1.6;
            color: #333;
            max-width: 700px;
            margin: 0 auto;
            padding: 20px;
        }}
        
        h1 {{
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
            font-size: 20pt;
        }}
        
        h2 {{
            color: #34495e;
            font-size: 14pt;
            margin-top: 25px;
            border-bottom: 1px solid #ddd;
            padding-bottom: 5px;
        }}
        
        h3 {{
            color: #666;
            font-size: 12pt;
        }}
        
        /* Score section */
        .score-box {{
            background: #f8f9fa;
            border-left: 4px solid #3498db;
            padding: 15px 20px;
            margin: 15px 0;
        }}
        
        .score-item {{
            display: inline-block;
            margin-right: 40px;
            margin-bottom: 10px;
        }}
        
        .score-value {{
            font-size: 28pt;
            font-weight: bold;
            color: #667eea;
        }}
        
        .score-label {{
            font-size: 10pt;
            color: #666;
        }}
        
        /* Table */
        table {{
            border-collapse: collapse;
            width: 100%;
            margin: 15px 0;
        }}
        
        th, td {{
            border: 1px solid #ddd;
            padding: 10px;
            text-align: left;
        }}
        
        th {{
            background: #f4f4f4;
            font-weight: bold;
        }}
        
        /* Status badges */
        .badge {{
            display: inline-block;
            padding: 3px 10px;
            border-radius: 4px;
            font-size: 9pt;
            font-weight: bold;
        }}
        
        .good {{ background: #d4edda; color: #155724; }}
        .warning {{ background: #fff3cd; color: #856404; }}
        .bad {{ background: #f8d7da; color: #721c24; }}
        
        /* Conclusion */
        .conclusion {{
            background: #e8f4f8;
            padding: 15px;
            margin: 10px 0;
            border-radius: 5px;
        }}
        
        /* Recommendation */
        .recommendation {{
            background: #fff9e6;
            border: 1px solid #f39c12;
            padding: 12px 15px;
            margin: 10px 0;
            border-radius: 5px;
        }}
        
        .priority {{
            font-weight: bold;
            color: #e74c3c;
        }}
        
        /* User input area */
        .user-section {{
            background: #f0f0f0;
            border: 2px dashed #ccc;
            padding: 15px;
            margin: 10px 0;
            min-height: 60px;
        }}
        
        .placeholder {{
            color: #999;
            font-style: italic;
        }}
        
        hr {{
            border: none;
            border-top: 1px solid #ddd;
            margin: 20px 0;
        }}
        
        .footer {{
            text-align: center;
            color: #999;
            font-size: 9pt;
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
        }}
    </style>
</head>
<body>
    <h1>Health Daily Report - {data['date']}</h1>
    
    <div class="score-box">
        <div class="score-item">
            <div class="score-value">{data['recovery_score']}</div>
            <div class="score-label">Recovery Score</div>
        </div>
        <div class="score-item">
            <div class="score-value">{data['sleep_score']}</div>
            <div class="score-label">Sleep Quality</div>
        </div>
        <div class="score-item">
            <div class="score-value">{data['exercise_score']}%</div>
            <div class="score-label">Exercise</div>
        </div>
    </div>
    
    <h2>Key Metrics</h2>
    <table>
        <tr>
            <th>Metric</th>
            <th>Value</th>
            <th>Target</th>
            <th>Status</th>
        </tr>
        <tr>
            <td>Steps</td>
            <td><strong>{data['steps']:,}</strong></td>
            <td>8,000</td>
            <td><span class="badge {'good' if data['steps'] >= 8000 else 'warning' if data['steps'] >= 6000 else 'bad'}">{'Great' if data['steps'] >= 10000 else 'Good' if data['steps'] >= 8000 else 'Low'}</span></td>
        </tr>
        <tr>
            <td>Sleep</td>
            <td><strong>{data['sleep_hours']} hours</strong></td>
            <td>7-8 hours</td>
            <td><span class="badge {'good' if data['sleep_hours'] >= 7 else 'warning' if data['sleep_hours'] >= 6 else 'bad'}">{'Good' if data['sleep_hours'] >= 7 else 'Short' if data['sleep_hours'] >= 6 else 'Low'}</span></td>
        </tr>
        <tr>
            <td>HRV</td>
            <td><strong>{data['hrv']} ms</strong></td>
            <td>40-60 ms</td>
            <td><span class="badge {'good' if data['hrv'] >= 50 else 'warning' if data['hrv'] >= 40 else 'bad'}">{'Excellent' if data['hrv'] >= 50 else 'Normal' if data['hrv'] >= 40 else 'Low'}</span></td>
        </tr>
        <tr>
            <td>Resting HR</td>
            <td><strong>{data['resting_hr']} bpm</strong></td>
            <td>55-70 bpm</td>
            <td><span class="badge {'good' if 55 <= data['resting_hr'] <= 70 else 'warning'}">{'Normal' if 55 <= data['resting_hr'] <= 70 else 'Check'}</span></td>
        </tr>
        <tr>
            <td>Exercise Time</td>
            <td><strong>{data['exercise_min']} min</strong></td>
            <td>60 min</td>
            <td><span class="badge {'good' if data['exercise_min'] >= 60 else 'warning'}">{'Met' if data['exercise_min'] >= 60 else 'Low'}</span></td>
        </tr>
        <tr>
            <td>Floors Climbed</td>
            <td><strong>{data['floors']}</strong></td>
            <td>-</td>
            <td><span class="badge good">Done</span></td>
        </tr>
    </table>
    
    <h2>Today's Conclusions</h2>
    {generate_conclusions_html(data)}
    
    <h2>Tomorrow's Recommendations</h2>
    {generate_recommendations_html(data)}
    
    <h2>Diet Record</h2>
    <div class="user-section">
        {data['diet_content'] if data['diet_content'] else '<span class="placeholder">(Not recorded - you can send me later)</span>'}
    </div>
    
    <h2>Body Notes</h2>
    <div class="user-section">
        {data['notes_content'] if data['notes_content'] else '<span class="placeholder">(Not recorded - you can send me later: energy, mood, skin, etc.)</span>'}
    </div>
    
    <hr>
    
    <div class="footer">
        Generated by Health Agent | Data Source: Apple Health + Google Fit<br>
        Generated: {data['date']}
    </div>
</body>
</html>'''
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)
    
    return output_file

def generate_conclusions_html(data):
    """生成结论 HTML"""
    conclusions = []
    
    # Sleep
    if data['sleep_hours'] < 6:
        conclusions.append(f'<div class="conclusion"><span class="badge bad">Severe Sleep Deficiency</span> Only {data["sleep_hours"]} hours of sleep, far below 7-8 hour target. Recommend sleep before 22:30 tonight.</div>')
    elif data['sleep_hours'] < 7:
        conclusions.append(f'<div class="conclusion"><span class="badge warning">Short Sleep</span> {data["sleep_hours"]} hours sleep. Recommend going to bed 30-60 minutes earlier tonight.</div>')
    else:
        conclusions.append(f'<div class="conclusion"><span class="badge good">Good Sleep</span> {data["sleep_hours"]} hours sleep helps body recovery.</div>')
    
    # HRV
    if data['hrv'] >= 50:
        conclusions.append(f'<div class="conclusion"><span class="badge good">Excellent HRV</span> HRV {data["hrv"]}ms indicates good autonomic recovery. Can do moderate intensity training.</div>')
    elif data['hrv'] >= 40:
        conclusions.append(f'<div class="conclusion"><span class="badge warning">Normal HRV</span> HRV {data["hrv"]}ms, recovering. Pay attention to rest.</div>')
    else:
        conclusions.append(f'<div class="conclusion"><span class="badge bad">Low HRV</span> HRV {data["hrv"]}ms indicates high body stress. Prioritize rest.</div>')
    
    # Exercise
    if data['steps'] >= 10000:
        conclusions.append(f'<div class="conclusion"><span class="badge good">Great Exercise</span> {data["steps"]:,} steps, exceeded goal. Keep it up!</div>')
    elif data['steps'] >= 8000:
        conclusions.append(f'<div class="conclusion"><span class="badge good">Good Exercise</span> {data["steps"]:,} steps, close to goal. Can increase daily activity.</div>')
    else:
        conclusions.append(f'<div class="conclusion"><span class="badge warning">Low Exercise</span> {data["steps"]:,} steps. Recommend adding {8000-data["steps"]:,} steps via stairs or brisk walking.</div>')
    
    return '\n'.join(conclusions)

def generate_recommendations_html(data):
    """生成建议 HTML"""
    recs = []
    
    # Sleep recommendation (highest priority)
    if data['sleep_hours'] < 6:
        recs.append('<div class="recommendation"><span class="priority">[HIGHEST]</span> Must sleep before 22:30 tonight, ensure 7+ hours. Start reducing screen time at 21:30.</div>')
    elif data['sleep_hours'] < 7:
        recs.append('<div class="recommendation"><span class="priority">[RECOMMENDED]</span> Sleep before 23:00 tonight, 30 minutes earlier than usual.</div>')
    
    # Exercise recommendation
    if data['steps'] < 8000:
        deficit = 8000 - data['steps']
        recs.append(f'<div class="recommendation"><span class="priority">[RECOMMENDED]</span> Today&apos;s goal: make up {deficit:,} steps. Recommend 30 minutes stairs or 15 minutes brisk walking.</div>')
    
    # HRV recommendation
    if data['hrv'] >= 50:
        recs.append('<div class="recommendation"><span class="priority">[OPTIONAL]</span> Good recovery. Can do moderate intensity training (strength or cardio).</div>')
    elif data['hrv'] < 40:
        recs.append('<div class="recommendation"><span class="priority">[RECOMMENDED]</span> Body fatigued. Recommend light activity or rest today, avoid high intensity training.</div>')
    
    return '\n'.join(recs) if recs else '<div class="recommendation">Maintain current lifestyle. All indicators normal.</div>'

if __name__ == '__main__':
    # Example data
    sample_data = {
        'date': '2026-02-18',
        'recovery_score': 7,
        'sleep_score': 5,
        'exercise_score': 86,
        'steps': 6852,
        'sleep_hours': 5.4,
        'hrv': 52,
        'resting_hr': 57,
        'exercise_min': 40,
        'floors': 108,
        'diet_content': '',
        'notes_content': ''
    }
    
    output = sys.argv[1] if len(sys.argv) > 1 else '/tmp/simple-report.html'
    generate_simple_report(sample_data, output)
    print(f"Report generated: {output}")