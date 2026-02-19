#!/usr/bin/env python3
"""
每日健康报告生成器 - 简化版
直接读取 JSON 数据并生成可视化报告
"""

import json
import sys
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
    
    # 状态
    if recovery_score >= 8:
        recovery_status = "良好"
        recovery_class = "status-good"
    elif recovery_score >= 5:
        recovery_status = "一般"
        recovery_class = "status-warning"
    else:
        recovery_status = "需改善"
        recovery_class = "status-bad"
    
    # 构建数据字典
    report_data = {
        'date': yesterday,
        'weekday': ['日', '一', '二', '三', '四', '五', '六'][datetime.strptime(yesterday, '%Y-%m-%d').weekday() + 1],
        'recovery_score': recovery_score,
        'recovery_status': recovery_status,
        'recovery_status_class': recovery_class,
        'sleep_score': int(sleep_hours * 10 / 8),
        'sleep_status_text': '不足' if sleep_hours < 6 else '偏短' if sleep_hours < 7 else '充足',
        'sleep_status_class': 'status-bad' if sleep_hours < 6 else 'status-warning' if sleep_hours < 7 else 'status-good',
        'exercise_score': min(int(steps * 100 / 8000), 100),
        'exercise_status_text': '优秀' if steps >= 10000 else '良好' if steps >= 8000 else '不足',
        'exercise_status_class': 'status-good' if steps >= 10000 else 'status-warning' if steps >= 8000 else 'status-bad',
        'steps': steps,
        'sleep_hours': round(sleep_hours, 1),
        'hrv': hrv,
        'resting_hr': rhr,
        'exercise_min': exercise,
        'floors': floors,
        'diet_content': diet_content,
        'notes_content': notes_content
    }
    
    # 生成报告 (使用英文版避免字体问题)
    from generate_simple_report_en import generate_simple_report
    
    output_dir = Path.home() / '.openclaw/workspace/shared/health-reports'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    html_file = output_dir / f'{yesterday}-visual-report.html'
    generate_simple_report(report_data, str(html_file))
    
    print(f"✅ 报告已生成: {html_file}")
    
    # 生成 PDF
    pdf_file = output_dir / 'pdf' / f'{yesterday}-health-report.pdf'
    pdf_file.parent.mkdir(exist_ok=True)
    
    import subprocess
    result = subprocess.run(
        ['weasyprint', str(html_file), str(pdf_file)],
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        print(f"✅ PDF 已生成: {pdf_file}")
        return str(pdf_file)
    else:
        print(f"⚠️  PDF 生成警告: {result.stderr}")
        return str(html_file)

if __name__ == '__main__':
    pdf_path = main()
    print(pdf_path)  # 输出路径供其他脚本使用
