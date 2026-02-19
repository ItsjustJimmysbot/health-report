#!/usr/bin/env python3
"""
每日健康报告生成器 - 使用 Puppeteer + Chrome 生成中文 PDF
"""

import json
import sys
import subprocess
from pathlib import Path
from datetime import datetime, timedelta

def main():
    # 昨天日期
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    
    # 数据文件路径
    ah_file = Path.home() / '我的云端硬盘/Health Auto Export/Health Data' / f'HealthAutoExport-{yesterday}.json'
    
    if not ah_file.exists():
        print(f"❌ 未找到数据文件: {ah_file}")
        sys.exit(1)
    
    # 读取数据
    with open(ah_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 提取关键指标
    metrics = data.get('data', {}).get('metrics', [])
    
    def get_metric(name, field='qty', agg='avg'):
        for m in metrics:
            if m.get('name') == name:
                items = m.get('data', [])
                if not items:
                    return 0
                if field == 'qty':
                    values = [item.get('qty', 0) for item in items if item.get('qty') is not None]
                    if not values:
                        return 0
                    if agg == 'avg':
                        return sum(values) / len(values)
                    elif agg == 'sum':
                        return sum(values)
                    elif agg == 'first':
                        return values[0] if values else 0
                return 0
        return 0
    
    steps = int(get_metric('step_count', agg='sum'))
    sleep_hours = get_metric('sleep_analysis', field='totalSleep', agg='first')
    hrv = int(get_metric('heart_rate_variability'))
    rhr = int(get_metric('resting_heart_rate', agg='first'))
    exercise = int(get_metric('apple_exercise_time', agg='sum'))
    floors = int(get_metric('flights_climbed', agg='sum'))
    
    # 读取饮食/备注
    workspace = Path.home() / '.openclaw/workspace-health'
    diet_file = workspace / 'memory/health-daily' / f'{yesterday}-diet.txt'
    notes_file = workspace / 'memory/health-daily' / f'{yesterday}-notes.txt'
    
    diet_content = ''
    if diet_file.exists():
        diet_content = diet_file.read_text(encoding='utf-8').strip()
    
    notes_content = ''
    if notes_file.exists():
        notes_content = notes_file.read_text(encoding='utf-8').strip()
    
    # 计算评分
    hrv_score = 10 if hrv >= 50 else 7 if hrv >= 40 else 5
    sleep_score = 10 if sleep_hours >= 7 else 5 if sleep_hours >= 5 else 3
    step_score = 10 if steps >= 10000 else 8 if steps >= 8000 else 6 if steps >= 6000 else 4
    
    recovery_score = int((hrv_score * 35 + sleep_score * 35 + step_score * 30) / 100)
    
    # 生成 HTML 文件
    html_content = generate_html({
        'date': yesterday,
        'recovery_score': recovery_score,
        'sleep_score': int(sleep_hours * 10 / 8),
        'exercise_score': min(int(steps * 100 / 8000), 100),
        'steps': steps,
        'sleep_hours': round(sleep_hours, 1),
        'hrv': hrv,
        'resting_hr': rhr,
        'exercise_min': exercise,
        'floors': floors,
        'diet_content': diet_content,
        'notes_content': notes_content
    })
    
    # 保存 HTML
    output_dir = Path.home() / '.openclaw/workspace/shared/health-reports'
    output_dir.mkdir(parents=True, exist_ok=True)
    html_file = output_dir / f'{yesterday}-report.html'
    html_file.write_text(html_content, encoding='utf-8')
    
    # 使用 Puppeteer 生成 PDF
    pdf_file = output_dir / 'pdf' / f'{yesterday}-health-report.pdf'
    pdf_file.parent.mkdir(exist_ok=True)
    
    # 创建临时 JS 脚本
    js_script = f"""
const puppeteer = require('/tmp/node_modules/puppeteer');
(async () => {{
    const browser = await puppeteer.launch({{
        headless: 'new',
        executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
        args: ['--no-sandbox']
    }});
    const page = await browser.newPage();
    const html = `{html_content.replace('`', '\\`').replace('$', '\\$')}`;
    await page.setContent(html, {{ waitUntil: 'networkidle0' }});
    await new Promise(r => setTimeout(r, 2000));
    await page.pdf({{
        path: '{pdf_file}',
        format: 'A4',
        printBackground: true,
        margin: {{ top: '1.5cm', right: '1.5cm', bottom: '1.5cm', left: '1.5cm' }}
    }});
    await browser.close();
    console.log('PDF generated');
}})();
"""
    
    js_file = Path('/tmp/generate-pdf-temp.js')
    js_file.write_text(js_script, encoding='utf-8')
    
    # 运行生成
    result = subprocess.run(['node', str(js_file)], capture_output=True, text=True)
    
    if result.returncode == 0:
        print(f"✅ 报告已生成: {pdf_file}")
        return str(pdf_file)
    else:
        print(f"⚠️  PDF 生成警告: {result.stderr}")
        return str(html_file)

def generate_html(data):
    """生成 HTML 内容"""
    
    # 睡眠状态
    if data['sleep_hours'] < 6:
        sleep_badge = '<span class="badge bad">严重不足</span>'
        sleep_conclusion = f'<div class="conclusion"><span class="badge bad">睡眠严重不足</span> 仅睡 {data["sleep_hours"]} 小时，远低于 7-8 小时目标。建议今晚 22:30 前入睡，保证 7+ 小时睡眠。</div>'
    elif data['sleep_hours'] < 7:
        sleep_badge = '<span class="badge warning">偏短</span>'
        sleep_conclusion = f'<div class="conclusion"><span class="badge warning">睡眠偏短</span> 睡眠 {data["sleep_hours"]} 小时，建议今晚提前 30-60 分钟入睡。</div>'
    else:
        sleep_badge = '<span class="badge good">充足</span>'
        sleep_conclusion = f'<div class="conclusion"><span class="badge good">睡眠充足</span> 睡眠 {data["sleep_hours"]} 小时，有助于身体恢复和认知功能维持。</div>'
    
    # HRV 状态
    if data['hrv'] >= 50:
        hrv_badge = '<span class="badge good">优秀</span>'
        hrv_conclusion = f'<div class="conclusion"><span class="badge good">HRV 优秀</span> HRV {data["hrv"]}ms，自主神经系统恢复良好，可以进行中等强度训练。</div>'
    elif data['hrv'] >= 40:
        hrv_badge = '<span class="badge warning">正常</span>'
        hrv_conclusion = f'<div class="conclusion"><span class="badge warning">HRV 正常</span> HRV {data["hrv"]}ms，恢复中，注意适当休息。</div>'
    else:
        hrv_badge = '<span class="badge bad">偏低</span>'
        hrv_conclusion = f'<div class="conclusion"><span class="badge bad">HRV 偏低</span> HRV {data["hrv"]}ms，身体压力较大，建议优先休息。</div>'
    
    # 运动状态
    if data['steps'] >= 10000:
        step_badge = '<span class="badge good">优秀</span>'
        step_conclusion = f'<div class="conclusion"><span class="badge good">运动量充足</span> {data["steps"]:,} 步，超额完成目标，保持良好状态。</div>'
    elif data['steps'] >= 8000:
        step_badge = '<span class="badge good">良好</span>'
        step_conclusion = f'<div class="conclusion"><span class="badge good">运动量良好</span> {data["steps"]:,} 步，接近目标，可适量增加日常活动。</div>'
    else:
        step_badge = '<span class="badge warning">不足</span>'
        deficit = 8000 - data['steps']
        step_conclusion = f'<div class="conclusion"><span class="badge warning">运动量不足</span> {data["steps"]:,} 步，建议增加 {deficit:,} 步，可通过爬楼梯或快走补充。</div>'
    
    # 建议
    recommendations = []
    if data['sleep_hours'] < 6:
        recommendations.append('<div class="recommendation"><span class="priority">[最高]</span> 今晚 22:30 前必须入睡，保证 7+ 小时睡眠。21:30 开始减少屏幕使用。</div>')
    elif data['sleep_hours'] < 7:
        recommendations.append('<div class="recommendation"><span class="priority">[建议]</span> 今晚 23:00 前入睡，比平时提前 30 分钟。</div>')
    
    if data['steps'] < 8000:
        deficit = 8000 - data['steps']
        recommendations.append(f'<div class="recommendation"><span class="priority">[建议]</span> 今日目标补足 {deficit:,} 步，建议爬楼梯 30 分钟或快走 15 分钟。</div>')
    
    if data['hrv'] >= 50:
        recommendations.append('<div class="recommendation"><span class="priority">[可选]</span> 恢复良好，可进行中等强度训练（力量训练或有氧）。</div>')
    elif data['hrv'] < 40:
        recommendations.append('<div class="recommendation"><span class="priority">[建议]</span> 身体疲劳，今日建议轻度活动或休息，避免高强度训练。</div>')
    
    rec_html = '\n'.join(recommendations) if recommendations else '<div class="recommendation">保持当前生活节奏，各项指标正常。</div>'
    
    # 饮食/备注
    diet_html = data['diet_content'] if data['diet_content'] else '<span class="placeholder">（未记录 - 可私发补充）</span>'
    notes_html = data['notes_content'] if data['notes_content'] else '<span class="placeholder">（未记录 - 可私发补充：精力、情绪、皮肤状态等）</span>'
    
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>健康报告 - {data['date']}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", "Hiragino Sans GB", "STHeiti", "Heiti SC", sans-serif;
            font-size: 11pt;
            line-height: 1.6;
            color: #333;
            padding: 30px;
            max-width: 700px;
            margin: 0 auto;
        }}
        h1 {{
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
            font-size: 22pt;
        }}
        h2 {{
            color: #34495e;
            font-size: 14pt;
            margin-top: 25px;
            border-bottom: 1px solid #ddd;
            padding-bottom: 5px;
        }}
        .score-box {{
            background: #f8f9fa;
            border-left: 4px solid #3498db;
            padding: 20px;
            margin: 20px 0;
        }}
        .score-item {{
            display: inline-block;
            margin-right: 50px;
            text-align: center;
        }}
        .score-value {{
            font-size: 32pt;
            font-weight: bold;
            color: #667eea;
        }}
        .score-label {{
            font-size: 10pt;
            color: #666;
            margin-top: 5px;
        }}
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
        .conclusion {{
            background: #e8f4f8;
            padding: 15px;
            margin: 10px 0;
            border-radius: 5px;
        }}
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
        <tr><th>指标</th><th>数值</th><th>目标</th><th>状态</th></tr>
        <tr><td>步数</td><td><strong>{data['steps']:,}</strong></td><td>8,000</td><td>{step_badge}</td></tr>
        <tr><td>睡眠</td><td><strong>{data['sleep_hours']} 小时</strong></td><td>7-8 小时</td><td>{sleep_badge}</td></tr>
        <tr><td>HRV</td><td><strong>{data['hrv']} ms</strong></td><td>40-60 ms</td><td>{hrv_badge}</td></tr>
        <tr><td>静息心率</td><td><strong>{data['resting_hr']} bpm</strong></td><td>55-70 bpm</td><td><span class="badge good">正常</span></td></tr>
        <tr><td>锻炼时间</td><td><strong>{data['exercise_min']} 分钟</strong></td><td>60 分钟</td><td>{'<span class="badge good">达标</span>' if data['exercise_min'] >= 60 else '<span class="badge warning">未达标</span>'}</td></tr>
        <tr><td>爬楼层数</td><td><strong>{data['floors']} 层</strong></td><td>-</td><td><span class="badge good">完成</span></td></tr>
    </table>
    
    <h2>今日结论</h2>
    {sleep_conclusion}
    {hrv_conclusion}
    {step_conclusion}
    
    <h2>明日建议</h2>
    {rec_html}
    
    <h2>饮食记录</h2>
    <div class="user-section">{diet_html}</div>
    
    <h2>身体备注</h2>
    <div class="user-section">{notes_html}</div>
    
    <div class="footer">
        由 Health Agent 自动生成 | 数据来源: Apple Health + Google Fit
    </div>
</body>
</html>"""

if __name__ == '__main__':
    pdf_path = main()
    print(pdf_path)
