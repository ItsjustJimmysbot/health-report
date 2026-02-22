#!/usr/bin/env python3
"""
V5.0 Weekly/Monthly Report Generator - Complete Version
周报月报生成脚本 - 完整版，处理所有模板变量
"""
import json
from pathlib import Path
from datetime import datetime

def generate_daily_rows(daily_data):
    """生成每日明细表格行"""
    rows = []
    for day in daily_data:
        date = day.get('date', '')
        weekday = datetime.strptime(date, '%Y-%m-%d').strftime('%a')
        hrv = day.get('hrv', '--')
        steps = day.get('steps', '--')
        sleep = day.get('sleep', '--')
        energy = day.get('active_energy', '--')
        workout = '✓' if day.get('has_workout') else '-'
        recovery = '良好' if day.get('hrv', 0) > 50 else '一般'
        
        row = f"""
      <tr>
        <td>{date}</td>
        <td>{weekday}</td>
        <td>{hrv}</td>
        <td>{steps:,}</td>
        <td>{sleep}h</td>
        <td>{energy}</td>
        <td>{workout}</td>
        <td><span class='trend-stable'>{recovery}</span></td>
      </tr>"""
        rows.append(row)
    return '\n'.join(rows)

def generate_weekly_report(data, template_path, output_path):
    """生成周报 - 完整变量替换"""
    with open(template_path, 'r', encoding='utf-8') as f:
        html = f.read()
    
    ai = data.get('ai_analysis', {})
    stats = data.get('statistics', {})
    daily_data = data.get('daily_data', [])
    
    # 计算额外统计
    rest_days = data.get('data_days', 0) - data.get('workout_days', 0)
    total_energy = sum(d.get('active_energy', 0) for d in daily_data)
    avg_steps = data.get('total_steps', 0) // max(data.get('data_days', 1), 1)
    
    # 获取趋势分析（AI生成或模板）
    hrv_analysis = ai.get('hrv_analysis', ai.get('trend_summary', '基于本周数据分析，HRV呈现波动趋势。'))
    sleep_analysis = ai.get('sleep_analysis', '本周睡眠数据显示改善趋势。')
    activity_analysis = ai.get('activity_analysis', '本周活动量存在一定波动。')
    workout_pattern = '本周运动频率较低，建议增加规律运动。' if data.get('workout_days', 0) < 3 else '本周保持较好运动习惯。'
    
    # 构建替换字典
    replacements = {
        '{{START_DATE}}': data.get('start_date', ''),
        '{{END_DATE}}': data.get('end_date', ''),
        '{{DATA_STATUS}}': data.get('data_status', ''),
        '{{DATA_PROGRESS}}': data.get('data_progress', ''),
        '{{ALERT_CLASS}}': 'complete' if data.get('data_days', 0) >= 6 else '',
        '{{DATA_NOTICE}}': data.get('data_notice', f"基于{data.get('data_days', 0)}天数据生成"),
        '{{DATA_COUNT}}': str(data.get('data_days', 0)),
        '{{GENERATED_AT}}': datetime.now().strftime('%Y-%m-%d %H:%M'),
        
        # 统计概览
        '{{AVG_HRV}}': str(data.get('avg_hrv', '--')),
        '{{AVG_SLEEP}}': str(data.get('avg_sleep', '--')),
        '{{AVG_STEPS}}': str(avg_steps),
        '{{TOTAL_STEPS}}': f"{data.get('total_steps', 0):,}",
        '{{TOTAL_ENERGY}}': str(round(total_energy)),
        '{{WORKOUT_DAYS}}': str(data.get('workout_days', 0)),
        '{{REST_DAYS}}': str(rest_days),
        
        # 趋势标签
        '{{HRV_TREND}}': data.get('hrv_trend', '稳定'),
        '{{HRV_TREND_CLASS}}': 'badge-good' if '改善' in data.get('hrv_trend', '') or '稳定' in data.get('hrv_trend', '') else 'badge-average',
        '{{STEPS_TREND}}': data.get('steps_trend', '波动'),
        '{{STEPS_TREND_CLASS}}': 'badge-good' if '改善' in data.get('steps_trend', '') else 'badge-average',
        '{{SLEEP_TREND}}': data.get('sleep_trend', '改善中'),
        '{{SLEEP_TREND_CLASS}}': 'badge-good' if '改善' in data.get('sleep_trend', '') else 'badge-average',
        
        # 详细统计
        '{{HRV_MAX}}': str(stats.get('hrv_max', '--')),
        '{{HRV_MIN}}': str(stats.get('hrv_min', '--')),
        '{{HRV_STD}}': str(stats.get('hrv_std', '--')),
        '{{STEPS_MAX}}': str(stats.get('steps_max', '--')),
        '{{STEPS_MIN}}': str(stats.get('steps_min', '--')),
        '{{SLEEP_MAX}}': str(stats.get('sleep_max', '--')),
        '{{SLEEP_MIN}}': str(stats.get('sleep_min', '--')),
        
        # AI分析内容
        '{{HRV_TREND_ANALYSIS}}': hrv_analysis,
        '{{SLEEP_TREND_ANALYSIS}}': sleep_analysis,
        '{{ACTIVITY_TREND_ANALYSIS}}': activity_analysis,
        '{{WORKOUT_PATTERN_ANALYSIS}}': workout_pattern,
        
        # 表格行
        '{{DAILY_ROWS}}': generate_daily_rows(daily_data),
        '{{WEEKLY_COMPARISON_ROWS}}': '<tr><td colspan="8" style="text-align:center;">历史对比数据需读取缓存文件</td></tr>',
        
        # AI建议 - 从recommendations读取
        '{{AI1_TITLE}}': ai.get('recommendations', {}).get('high_priority', {}).get('title', '暂无'),
        '{{AI1_PROBLEM}}': ai.get('recommendations', {}).get('high_priority', {}).get('problem', ai.get('recommendations', {}).get('high_priority', {}).get('content', '暂无')),
        '{{AI1_ACTION}}': ai.get('recommendations', {}).get('high_priority', {}).get('action', '暂无'),
        '{{AI1_EXPECTATION}}': ai.get('recommendations', {}).get('high_priority', {}).get('expected', '暂无'),
        
        '{{AI2_TITLE}}': ai.get('recommendations', {}).get('medium_priority', {}).get('title', '暂无'),
        '{{AI2_PROBLEM}}': ai.get('recommendations', {}).get('medium_priority', {}).get('problem', ai.get('recommendations', {}).get('medium_priority', {}).get('content', '暂无')),
        '{{AI2_ACTION}}': ai.get('recommendations', {}).get('medium_priority', {}).get('action', '暂无'),
        '{{AI2_EXPECTATION}}': ai.get('recommendations', {}).get('medium_priority', {}).get('expected', '暂无'),
        
        '{{AI3_TITLE}}': ai.get('recommendations', {}).get('routine', {}).get('title', '暂无'),
        '{{AI3_DIET}}': ai.get('recommendations', {}).get('routine', {}).get('diet', '暂无'),
        '{{AI3_ROUTINE}}': ai.get('recommendations', {}).get('routine', {}).get('schedule', ai.get('recommendations', {}).get('routine', {}).get('content', '暂无')),
        
        '{{AI4_TITLE}}': ai.get('recommendations', {}).get('long_term', {}).get('title', ai.get('recommendations', {}).get('summary', {}).get('title', '综合健康评估')),
        '{{AI4_ADVANTAGES}}': ai.get('recommendations', {}).get('long_term', {}).get('advantages', ai.get('recommendations', {}).get('summary', {}).get('advantages', '暂无')),
        '{{AI4_RISKS}}': ai.get('recommendations', {}).get('long_term', {}).get('risks', ai.get('recommendations', {}).get('summary', {}).get('risks', '暂无')),
        '{{AI4_CONCLUSION}}': ai.get('recommendations', {}).get('long_term', {}).get('conclusion', ai.get('recommendations', {}).get('summary', {}).get('conclusion', '暂无')),
        '{{AI4_PLAN}}': ai.get('recommendations', {}).get('long_term', {}).get('plan', ai.get('recommendations', {}).get('summary', {}).get('plan', '暂无')),
    }
    
    # 替换所有变量
    for key, value in replacements.items():
        html = html.replace(key, str(value))
    
    # 检查未替换变量
    import re
    unreplaced = re.findall(r'\{\{[^}]+\}\}', html)
    if unreplaced:
        print(f"⚠️ 未替换变量: {unreplaced}")
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    return output_path

def generate_monthly_report(data, template_path, output_path):
    """生成月报"""
    with open(template_path, 'r', encoding='utf-8') as f:
        html = f.read()
    
    ai = data.get('ai_analysis', {})
    
    replacements = {
        '{{YEAR}}': str(data.get('year', '')),
        '{{MONTH}}': str(data.get('month', '')),
        '{{DATA_STATUS}}': data.get('data_status', ''),
        '{{DATA_PROGRESS}}': data.get('data_progress', ''),
        '{{ALERT_CLASS}}': 'complete' if data.get('data_days', 0) >= 25 else '',
        '{{DATA_NOTICE}}': data.get('data_notice', ''),
        '{{GENERATED_AT}}': datetime.now().strftime('%Y-%m-%d %H:%M'),
        
        '{{AVG_HRV}}': str(data.get('avg_hrv', '--')),
        '{{AVG_STEPS}}': str(data.get('avg_steps', '--')),
        '{{AVG_SLEEP}}': str(data.get('avg_sleep', '--')),
        '{{WORKOUT_DAYS}}': str(data.get('workout_days', 0)),
        '{{DATA_COUNT}}': str(data.get('data_days', 0)),
        
        '{{TOTAL_STEPS}}': f"{data.get('total_steps', 0):,}",
        '{{ACTIVE_ENERGY_TOTAL}}': str(data.get('total_active_energy', 0)),
        
        # AI内容
        '{{SUMMARY}}': ai.get('summary', '本月健康数据待补充'),
        '{{ACHIEVEMENTS}}': ai.get('achievements', '暂无'),
        '{{CHALLENGES}}': ai.get('challenges', '暂无'),
    }
    
    for key, value in replacements.items():
        html = html.replace(key, str(value))
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    return output_path

if __name__ == '__main__':
    import sys
    
    report_type = sys.argv[1] if len(sys.argv) > 1 else 'weekly'
    data_file = sys.argv[2] if len(sys.argv) > 2 else 'data.json'
    output_file = sys.argv[3] if len(sys.argv) > 3 else 'report.html'
    
    with open(data_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    if report_type == 'weekly':
        template = 'templates/WEEKLY_TEMPLATE_V2.html'
        result = generate_weekly_report(data, template, output_file)
    else:
        template = 'templates/MONTHLY_TEMPLATE_V2.html'
        result = generate_monthly_report(data, template, output_file)
    
    print(f"报告已生成: {result}")
