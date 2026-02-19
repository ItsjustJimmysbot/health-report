#!/usr/bin/env python3
"""
简化版可视化健康报告生成器
兼容 weasyprint PDF 转换
"""

import sys
from pathlib import Path

def generate_simple_report(data, output_file):
    """生成简化版报告，确保 PDF 兼容性"""
    
    # 使用更简单的 HTML 结构
    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>健康报告 - {data['date']}</title>
    <style>
        body {{
            font-family: "Arial", "Helvetica", sans-serif;
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
        
        /* 评分区域 */
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
        
        /* 指标表格 */
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
        
        /* 状态标签 */
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
        
        /* 结论区域 */
        .conclusion {{
            background: #e8f4f8;
            padding: 15px;
            margin: 10px 0;
            border-radius: 5px;
        }}
        
        /* 建议 */
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
        
        /* 用户输入区域 */
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
    <h1>健康日报 - {data['date']}</h1>
    
    <div class="score-box">
        <div class="score-item">
            <div class="score-value">{data['recovery_score']}</div>
            <div class="score-label">Recovery Score</div>
        </div>
        <div class="score-item">
            <div class="score-value">{data['sleep_score']}</div>
            <div class="score-label">睡眠质量</div>
        </div>
        <div class="score-item">
            <div class="score-value">{data['exercise_score']}%</div>
            <div class="score-label">运动完成</div>
        </div>
    </div>
    
    <h2>关键指标</h2>
    <table>
        <tr>
            <th>指标</th>
            <th>数值</th>
            <th>目标</th>
            <th>状态</th>
        </tr>
        <tr>
            <td>步数</td>
            <td><strong>{data['steps']:,}</strong></td>
            <td>8,000</td>
            <td><span class="badge {'good' if data['steps'] >= 8000 else 'warning' if data['steps'] >= 6000 else 'bad'}">{'优秀' if data['steps'] >= 10000 else '良好' if data['steps'] >= 8000 else '不足'}</span></td>
        </tr>
        <tr>
            <td>睡眠</td>
            <td><strong>{data['sleep_hours']} 小时</strong></td>
            <td>7-8 小时</td>
            <td><span class="badge {'good' if data['sleep_hours'] >= 7 else 'warning' if data['sleep_hours'] >= 6 else 'bad'}">{'充足' if data['sleep_hours'] >= 7 else '偏短' if data['sleep_hours'] >= 6 else '不足'}</span></td>
        </tr>
        <tr>
            <td>HRV</td>
            <td><strong>{data['hrv']} ms</strong></td>
            <td>40-60 ms</td>
            <td><span class="badge {'good' if data['hrv'] >= 50 else 'warning' if data['hrv'] >= 40 else 'bad'}">{'优秀' if data['hrv'] >= 50 else '正常' if data['hrv'] >= 40 else '偏低'}</span></td>
        </tr>
        <tr>
            <td>静息心率</td>
            <td><strong>{data['resting_hr']} bpm</strong></td>
            <td>55-70 bpm</td>
            <td><span class="badge {'good' if 55 <= data['resting_hr'] <= 70 else 'warning'}">{'正常' if 55 <= data['resting_hr'] <= 70 else '需关注'}</span></td>
        </tr>
        <tr>
            <td>锻炼时间</td>
            <td><strong>{data['exercise_min']} 分钟</strong></td>
            <td>60 分钟</td>
            <td><span class="badge {'good' if data['exercise_min'] >= 60 else 'warning'}">{'达标' if data['exercise_min'] >= 60 else '未达标'}</span></td>
        </tr>
        <tr>
            <td>爬楼层数</td>
            <td><strong>{data['floors']} 层</strong></td>
            <td>-</td>
            <td><span class="badge good">完成</span></td>
        </tr>
    </table>
    
    <h2>今日结论</h2>
    {generate_conclusions_html(data)}
    
    <h2>明日建议</h2>
    {generate_recommendations_html(data)}
    
    <h2>饮食记录</h2>
    <div class="user-section">
        {data['diet_content'] if data['diet_content'] else '<span class="placeholder">（未记录 - 可私发补充）</span>'}
    </div>
    
    <h2>身体备注</h2>
    <div class="user-section">
        {data['notes_content'] if data['notes_content'] else '<span class="placeholder">（未记录 - 可私发补充：精力、情绪、皮肤状态等）</span>'}
    </div>
    
    <hr>
    
    <div class="footer">
        由 Health Agent 自动生成 | 数据来源: Apple Health + Google Fit<br>
        生成时间: {data['date']}
    </div>
</body>
</html>'''
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)
    
    return output_file

def generate_conclusions_html(data):
    """生成结论 HTML"""
    conclusions = []
    
    # 睡眠
    if data['sleep_hours'] < 6:
        conclusions.append(f'<div class="conclusion"><span class="badge bad">睡眠严重不足</span> 仅睡 {data["sleep_hours"]} 小时，远低于 7-8 小时目标，严重影响身体恢复。建议今晚 22:30 前入睡。</div>')
    elif data['sleep_hours'] < 7:
        conclusions.append(f'<div class="conclusion"><span class="badge warning">睡眠偏短</span> 睡眠 {data["sleep_hours"]} 小时，建议今晚提前 30-60 分钟入睡。</div>')
    else:
        conclusions.append(f'<div class="conclusion"><span class="badge good">睡眠充足</span> 睡眠 {data["sleep_hours"]} 小时，有助于身体恢复和认知功能维持。</div>')
    
    # HRV
    if data['hrv'] >= 50:
        conclusions.append(f'<div class="conclusion"><span class="badge good">HRV 优秀</span> HRV {data["hrv"]}ms，自主神经系统恢复良好，可以进行中等强度训练。</div>')
    elif data['hrv'] >= 40:
        conclusions.append(f'<div class="conclusion"><span class="badge warning">HRV 正常</span> HRV {data["hrv"]}ms，恢复中，注意适当休息。</div>')
    else:
        conclusions.append(f'<div class="conclusion"><span class="badge bad">HRV 偏低</span> HRV {data["hrv"]}ms，身体压力较大，建议优先休息。</div>')
    
    # 运动
    if data['steps'] >= 10000:
        conclusions.append(f'<div class="conclusion"><span class="badge good">运动量充足</span> {data["steps"]:,} 步，超额完成目标，保持良好状态。</div>')
    elif data['steps'] >= 8000:
        conclusions.append(f'<div class="conclusion"><span class="badge good">运动量良好</span> {data["steps"]:,} 步，接近目标，可适量增加日常活动。</div>')
    else:
        conclusions.append(f'<div class="conclusion"><span class="badge warning">运动量不足</span> {data["steps"]:,} 步，建议增加 {8000-data["steps"]:,} 步，可通过爬楼梯或快走补充。</div>')
    
    return '\n'.join(conclusions)

def generate_recommendations_html(data):
    """生成建议 HTML"""
    recs = []
    
    # 睡眠建议（最高优先级）
    if data['sleep_hours'] < 6:
        recs.append('<div class="recommendation"><span class="priority">[最高]</span> 今晚 22:30 前必须入睡，保证 7+ 小时睡眠。21:30 开始减少屏幕使用。</div>')
    elif data['sleep_hours'] < 7:
        recs.append('<div class="recommendation"><span class="priority">[建议]</span> 今晚 23:00 前入睡，比平时提前 30 分钟。</div>')
    
    # 运动建议
    if data['steps'] < 8000:
        deficit = 8000 - data['steps']
        recs.append(f'<div class="recommendation"><span class="priority">[建议]</span> 今日目标补足 {deficit:,} 步，建议爬楼梯 30 分钟或快走 15 分钟。</div>')
    
    # HRV 建议
    if data['hrv'] >= 50:
        recs.append('<div class="recommendation"><span class="priority">[可选]</span> 恢复良好，可进行中等强度训练（力量训练或有氧）。</div>')
    elif data['hrv'] < 40:
        recs.append('<div class="recommendation"><span class="priority">[建议]</span> 身体疲劳，今日建议轻度活动或休息，避免高强度训练。</div>')
    
    return '\n'.join(recs) if recs else '<div class="recommendation">保持当前生活节奏，各项指标正常。</div>'

if __name__ == '__main__':
    # 示例数据
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
    print(f"✅ 报告已生成: {output}")
