#!/usr/bin/env python3
"""
V5.0 Weekly/Monthly Report Generator
周报月报生成脚本 - 所有分析内容从JSON读取
"""
import json
from pathlib import Path
from datetime import datetime

def generate_weekly_report(data, template_path, output_path):
    """生成周报"""
    with open(template_path, 'r', encoding='utf-8') as f:
        html = f.read()
    
    ai = data.get('ai_analysis', {})
    recs = ai.get('recommendations', {})
    stats = data.get('statistics', {})
    
    replacements = {
        '{{START_DATE}}': data['start_date'],
        '{{END_DATE}}': data['end_date'],
        '{{DATA_STATUS}}': data['data_status'],
        '{{DATA_PROGRESS}}': data['data_progress'],
        '{{ALERT_CLASS}}': 'complete' if data['data_days'] >= 6 else '',
        '{{DATA_NOTICE}}': f'基于{data["data_days"]}天数据生成，部分分析可能不够全面' if data['data_days'] < 7 else '数据完整',
        
        '{{AVG_HRV}}': str(data['avg_hrv']),
        '{{HRV_TREND}}': data['hrv_trend'],
        '{{HRV_TREND_CLASS}}': 'badge-good' if '改善' in data['hrv_trend'] or '稳定' in data['hrv_trend'] else 'badge-average',
        
        '{{TOTAL_STEPS}}': f"{data['total_steps']:,}",
        '{{STEPS_TREND}}': data['steps_trend'],
        '{{STEPS_TREND_CLASS}}': 'badge-good' if '改善' in data['steps_trend'] or '稳定' in data['steps_trend'] else 'badge-average',
        
        '{{AVG_SLEEP}}': str(data['avg_sleep']),
        '{{SLEEP_TREND}}': data['sleep_trend'],
        '{{SLEEP_TREND_CLASS}}': 'badge-good' if '改善' in data['sleep_trend'] else 'badge-average',
        
        '{{WORKOUT_DAYS}}': str(data['workout_days']),
        '{{WORKOUT_FREQUENCY}}': data['workout_frequency'],
        
        '{{HRV_MAX}}': str(stats.get('hrv_max', '--')),
        '{{HRV_MIN}}': str(stats.get('hrv_min', '--')),
        '{{HRV_STD}}': str(stats.get('hrv_std', '--')),
        '{{STEPS_MAX}}': str(stats.get('steps_max', '--')),
        '{{STEPS_MIN}}': str(stats.get('steps_min', '--')),
        '{{SLEEP_MAX}}': str(stats.get('sleep_max', '--')),
        '{{SLEEP_MIN}}': str(stats.get('sleep_min', '--')),
        
        '{{TREND_SUMMARY}}': ai.get('trend_summary', '暂无分析'),
        '{{HRV_ANALYSIS}}': ai.get('hrv_analysis', '暂无分析'),
        '{{SLEEP_ANALYSIS}}': ai.get('sleep_analysis', '暂无分析'),
        '{{ACTIVITY_ANALYSIS}}': ai.get('activity_analysis', '暂无分析'),
        
        '{{AI1_TITLE}}': recs.get('high_priority', {}).get('title', '暂无'),
        '{{AI1_CONTENT}}': recs.get('high_priority', {}).get('content', '暂无'),
        '{{AI2_TITLE}}': recs.get('medium_priority', {}).get('title', '暂无'),
        '{{AI2_CONTENT}}': recs.get('medium_priority', {}).get('content', '暂无'),
        '{{AI3_TITLE}}': recs.get('long_term', {}).get('title', '暂无'),
        '{{AI3_CONTENT}}': recs.get('long_term', {}).get('content', '暂无'),
        
        '{{FOOTER_DATE}}': datetime.now().strftime('%Y-%m-%d %H:%M'),
    }
    
    for key, value in replacements.items():
        html = html.replace(key, str(value))
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    return output_path

def generate_monthly_report(data, template_path, output_path):
    """生成月报"""
    with open(template_path, 'r', encoding='utf-8') as f:
        html = f.read()
    
    ai = data.get('ai_analysis', {})
    recs = ai.get('monthly_recommendations', {})
    
    replacements = {
        '{{YEAR}}': str(data['year']),
        '{{MONTH}}': str(data['month']),
        '{{DATA_STATUS}}': data['data_status'],
        '{{DATA_PROGRESS}}': data['data_progress'],
        '{{ALERT_CLASS}}': 'complete' if data['data_days'] >= 25 else '',
        '{{DATA_NOTICE}}': data.get('data_notice', ''),
        
        '{{AVG_HRV}}': str(data['avg_hrv']),
        '{{AVG_STEPS}}': str(data['avg_steps']),
        '{{AVG_SLEEP}}': str(data['avg_sleep']),
        '{{WORKOUT_DAYS}}': str(data['workout_days']),
        '{{DATA_COUNT}}': str(data['data_days']),
        
        '{{TOTAL_STEPS}}': f"{data['total_steps']:,}",
        '{{ACTIVE_ENERGY_TOTAL}}': str(data['total_active_energy']),
        
        '{{SUMMARY}}': ai.get('summary', '暂无分析'),
        '{{ACHIEVEMENTS}}': ai.get('achievements', '暂无'),
        '{{CHALLENGES}}': ai.get('challenges', '暂无'),
        
        '{{AI1_TITLE}}': recs.get('immediate', {}).get('title', '暂无'),
        '{{AI1_CONTENT}}': recs.get('immediate', {}).get('content', '暂无'),
        '{{AI2_TITLE}}': recs.get('short_term', {}).get('title', '暂无'),
        '{{AI2_CONTENT}}': recs.get('short_term', {}).get('content', '暂无'),
        '{{AI3_TITLE}}': recs.get('long_term', {}).get('title', '暂无'),
        '{{AI3_CONTENT}}': recs.get('long_term', {}).get('content', '暂无'),
        
        '{{FOOTER_DATE}}': datetime.now().strftime('%Y-%m-%d %H:%M'),
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
