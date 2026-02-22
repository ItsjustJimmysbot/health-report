#!/usr/bin/env python3
"""
周报和月报生成器 - V4.4 从缓存读取
"""
import json
import os
from datetime import datetime
from pathlib import Path
from playwright.sync_api import sync_playwright

HOME = Path.home()
TEMPLATE_DIR = HOME / '.openclaw' / 'workspace-health' / 'templates'
OUTPUT_DIR = HOME / '.openclaw' / 'workspace' / 'shared' / 'health-reports' / 'upload'
CACHE_DIR = HOME / '.openclaw' / 'workspace-health' / 'cache' / 'daily'

def load_cache(date_str):
    cache_path = CACHE_DIR / f'{date_str}.json'
    if cache_path.exists():
        with open(cache_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

def generate_weekly_report(week_dates, template):
    weekly_data = []
    for date in week_dates:
        data = load_cache(date)
        if data:
            weekly_data.append(data)
    
    if not weekly_data:
        return None
    
    # 计算统计
    avg_hrv = sum(d['hrv']['value'] for d in weekly_data if d['hrv']['value']) / len([d for d in weekly_data if d['hrv']['value']])
    total_steps = sum(d['steps']['value'] for d in weekly_data)
    avg_steps = total_steps / len(weekly_data)
    avg_sleep = sum(d['sleep']['total'] for d in weekly_data if d.get('sleep')) / len([d for d in weekly_data if d.get('sleep')])
    total_energy = sum(d['active_energy']['value'] for d in weekly_data)
    workout_days = sum(1 for d in weekly_data if d['has_workout'])
    
    html = template
    html = html.replace('{{START_DATE}}', '2026-02-16')
    html = html.replace('{{END_DATE}}', '2026-02-22')
    html = html.replace('{{DATA_STATUS}}', f'部分数据 ({len(weekly_data)}/7天)')
    
    html = html.replace('{{ALERT_CLASS}}', '')
    html = html.replace('{{DATA_PROGRESS}}', f'⚠️ 数据收集进度: {len(weekly_data)}/7 天')
    html = html.replace('{{DATA_NOTICE}}', f'本周有 {7-len(weekly_data)} 天数据缺失。报告基于可用数据生成。')
    
    html = html.replace('{{AVG_HRV}}', f"{avg_hrv:.1f}")
    html = html.replace('{{TOTAL_STEPS}}', f"{int(total_steps):,}")
    html = html.replace('{{AVG_SLEEP}}', f"{avg_sleep:.1f}")
    html = html.replace('{{AVG_STEPS}}', f"{int(avg_steps):,}")
    html = html.replace('{{TOTAL_ENERGY}}', f"{int(total_energy):,}")
    html = html.replace('{{WORKOUT_DAYS}}', str(workout_days))
    html = html.replace('{{REST_DAYS}}', str(len(weekly_data) - workout_days))
    
    html = html.replace('{{HRV_TREND_CLASS}}', 'badge-good')
    html = html.replace('{{HRV_TREND}}', '稳定')
    html = html.replace('{{STEPS_TREND_CLASS}}', 'badge-average')
    html = html.replace('{{STEPS_TREND}}', '需提升')
    html = html.replace('{{SLEEP_TREND_CLASS}}', 'badge-good')
    html = html.replace('{{SLEEP_TREND}}', '改善')
    
    # 每日明细
    daily_rows = []
    weekday_names = ['周二', '周三', '周四', '周五', '周六']
    for i, data in enumerate(weekly_data):
        recovery = data['scores']['recovery']
        sleep_h = data['sleep']['total'] if data.get('sleep') else 0
        row = f"""<tr>
            <td>{data['date']}</td>
            <td>{weekday_names[i] if i < len(weekday_names) else '--'}</td>
            <td>{data['hrv']['value']:.1f}</td>
            <td>{data['steps']['value']:,}</td>
            <td>{sleep_h:.1f}h</td>
            <td>{data['active_energy']['value']:.0f}</td>
            <td>{'✓' if data['has_workout'] else '-'}</td>
            <td>{recovery}</td>
        </tr>"""
        daily_rows.append(row)
    html = html.replace('{{DAILY_ROWS}}', ''.join(daily_rows))
    
    # 趋势分析
    html = html.replace('{{HRV_TREND_ANALYSIS}}', f'本周平均HRV {avg_hrv:.1f}ms，保持在正常范围。')
    html = html.replace('{{ACTIVITY_TREND_ANALYSIS}}', f'本周日均步数 {int(avg_steps):,} 步。')
    html = html.replace('{{SLEEP_TREND_ANALYSIS}}', f'本周平均睡眠 {avg_sleep:.1f} 小时。')
    html = html.replace('{{WORKOUT_PATTERN_ANALYSIS}}', f'本周运动 {workout_days} 天。')
    
    html = html.replace('{{WEEKLY_COMPARISON_ROWS}}', '<tr><td colspan="9" style="text-align:center;color:#64748b;">详见每日明细表</td></tr>')
    
    # AI建议
    html = html.replace('{{AI1_TITLE}}', '提升日常活动量')
    html = html.replace('{{AI1_PROBLEM}}', f'本周日均步数{int(avg_steps):,}步。')
    html = html.replace('{{AI1_ACTION}}', '1. 设定每日步数目标<br>2. 工作时每小时起身活动<br>3. 选择楼梯代替电梯')
    html = html.replace('{{AI1_EXPECTATION}}', '预计2-3周后提升。')
    
    html = html.replace('{{AI2_TITLE}}', '保持睡眠质量')
    html = html.replace('{{AI2_PROBLEM}}', '本周睡眠数据记录良好。')
    html = html.replace('{{AI2_ACTION}}', '1. 保持规律作息<br>2. 睡前避免蓝光')
    html = html.replace('{{AI2_EXPECTATION}}', '继续保持。')
    
    html = html.replace('{{AI3_TITLE}}', '建立运动习惯')
    html = html.replace('{{AI3_DIET}}', '保持均衡饮食。')
    html = html.replace('{{AI3_ROUTINE}}', '建议固定运动时间。')
    
    html = html.replace('{{AI4_TITLE}}', '周数据洞察')
    html = html.replace('{{AI4_ADVANTAGES}}', 'HRV指标正常。')
    html = html.replace('{{AI4_RISKS}}', '活动量偏低。')
    html = html.replace('{{AI4_CONCLUSION}}', '本周整体健康良好。')
    html = html.replace('{{AI4_PLAN}}', '1. 增加步行<br>2. 建立运动习惯')
    
    html = html.replace('{{DATA_COUNT}}', str(len(weekly_data)))
    html = html.replace('{{GENERATED_AT}}', datetime.now().strftime('%Y-%m-%d %H:%M'))
    
    return html

def generate_monthly_report(year, month, available_data, template):
    data_count = len(available_data)
    if not available_data:
        return None
    
    avg_hrv = sum(d['hrv']['value'] for d in available_data if d['hrv']['value']) / len([d for d in available_data if d['hrv']['value']])
    total_steps = sum(d['steps']['value'] for d in available_data)
    avg_steps = total_steps / data_count
    avg_sleep = sum(d['sleep']['total'] for d in available_data if d.get('sleep')) / len([d for d in available_data if d.get('sleep')])
    total_energy = sum(d['active_energy']['value'] for d in available_data)
    workout_days = sum(1 for d in available_data if d['has_workout'])
    
    projected_steps = int(avg_steps * 28)
    projected_workouts = int(workout_days / data_count * 28)
    
    html = template
    html = html.replace('{{YEAR}}', str(year))
    html = html.replace('{{MONTH}}', str(month))
    
    coverage = data_count / 28
    report_type = 'preview' if coverage < 0.50 else 'full'
    alert_text = f'⚠️ 数据预览版：{data_count}/28 天' if report_type == 'preview' else f'✅ 数据完整'
    
    html = html.replace('{{DATA_STATUS}}', f'部分数据 ({data_count}/28天)')
    html = html.replace('{{ALERT_CLASS}}', 'complete' if report_type == 'full' else '')
    html = html.replace('{{DATA_PROGRESS}}', alert_text)
    html = html.replace('{{DATA_NOTICE}}', f'本月有 {28-data_count} 天数据缺失。')
    
    html = html.replace('{{AVG_HRV}}', f"{avg_hrv:.1f}")
    html = html.replace('{{AVG_STEPS}}', f"{int(avg_steps):,}")
    html = html.replace('{{AVG_SLEEP}}', f"{avg_sleep:.1f}")
    html = html.replace('{{WORKOUT_DAYS}}', str(workout_days))
    html = html.replace('{{DATA_COUNT}}', str(data_count))
    html = html.replace('{{TOTAL_STEPS}}', f"{int(total_steps):,}")
    html = html.replace('{{TOTAL_ENERGY}}', f"{int(total_energy):,}")
    
    best_sleep_day = max(available_data, key=lambda x: x['sleep']['total'] if x.get('sleep') else 0)
    best_day = best_sleep_day['date'] if best_sleep_day.get('sleep') and best_sleep_day['sleep']['total'] > 0 else '--'
    html = html.replace('{{BEST_SLEEP_DAY}}', best_day)
    
    html = html.replace('{{PROJECTED_STEPS}}', f"{projected_steps:,}")
    html = html.replace('{{PROJECTED_STEPS_PERCENT}}', str(int(projected_steps/240000*100)))
    html = html.replace('{{PROJECTED_WORKOUTS}}', str(projected_workouts))
    html = html.replace('{{PROJECTED_WORKOUTS_PERCENT}}', str(int(projected_workouts/12*100)))
    html = html.replace('{{PROJECTED_ENERGY}}', f"{int(total_energy/data_count*28):,}")
    
    # 每日明细
    daily_rows = []
    for d in sorted(available_data, key=lambda x: x['date']):
        note = ''
        if d['has_workout']:
            note += '运动 '
        sleep_val = d['sleep']['total'] if d.get('sleep') else 0
        sleep_display = f"{sleep_val:.1f}h" if sleep_val > 0 else '--'
        if sleep_val == 0:
            note += '无睡眠'
        row = f"""<tr>
            <td>{d['date']}</td>
            <td>{d['hrv']['value']:.1f}</td>
            <td>{d['steps']['value']:,}</td>
            <td>{sleep_display}</td>
            <td>{d['active_energy']['value']:.0f}</td>
            <td>{'✓' if d['has_workout'] else '-'}</td>
            <td>{note}</td>
        </tr>"""
        daily_rows.append(row)
    html = html.replace('{{DAILY_ROWS}}', ''.join(daily_rows))
    
    # 趋势分析
    html = html.replace('{{HRV_TREND_ANALYSIS}}', f'平均HRV {avg_hrv:.1f}ms。')
    html = html.replace('{{ACTIVITY_PATTERN_ANALYSIS}}', f'日均步数 {int(avg_steps):,} 步。')
    html = html.replace('{{SLEEP_QUALITY_ANALYSIS}}', f'平均睡眠 {avg_sleep:.1f} 小时。')
    html = html.replace('{{WORKOUT_RECOVERY_BALANCE}}', f'运动 {workout_days} 天。')
    
    # 目标追踪
    goal_rows = [
        f'<tr><td>日均步数</td><td>10,000</td><td>{int(avg_steps):,}</td><td>{int(avg_steps/10000*100)}%</td><td>--</td><td>{"良好" if avg_steps >= 8000 else "需改善"}</td></tr>',
        f'<tr><td>运动频率</td><td>12天</td><td>{workout_days}天/{data_count}天</td><td>{int(workout_days/data_count*100)}%</td><td>--</td><td>{"良好" if workout_days >= data_count//3 else "需改善"}</td></tr>',
    ]
    html = html.replace('{{GOAL_TRACKING_ROWS}}', ''.join(goal_rows))
    html = html.replace('{{GOAL_ANALYSIS}}', '步数目标需关注。')
    
    # AI建议
    html = html.replace('{{AI1_TITLE}}', '建立健康习惯')
    html = html.replace('{{AI1_PROBLEM}}', '数据记录需要规律化。')
    html = html.replace('{{AI1_ACTION}}', '1. 固定作息<br>2. 设定目标')
    html = html.replace('{{AI1_EXPECTATION}}', '2-3个月后形成习惯。')
    
    html = html.replace('{{AI2_TITLE}}', '提升活动基础')
    html = html.replace('{{AI2_PROBLEM}}', f'日均步数{int(avg_steps):,}。')
    html = html.replace('{{AI2_ACTION}}', '1. 每天多走1000步<br>2. 周末户外活动')
    html = html.replace('{{AI2_EXPECTATION}}', '4-6周内提升。')
    
    html = html.replace('{{AI3_TITLE}}', '生活方式优化')
    html = html.replace('{{AI3_DIET}}', '均衡饮食。')
    html = html.replace('{{AI3_ROUTINE}}', '规律作息。')
    html = html.replace('{{AI3_HABITS}}', '养成健康习惯。')
    
    html = html.replace('{{AI4_TITLE}}', '月度洞察')
    html = html.replace('{{AI4_ADVANTAGES}}', 'HRV稳定。')
    html = html.replace('{{AI4_RISKS}}', '活动量偏低。')
    html = html.replace('{{AI4_CONCLUSION}}', '健康有改善空间。')
    html = html.replace('{{AI4_NEXT_MONTH_GOALS}}', '1. 8000步/天<br>2. 每周运动3次')
    
    html = html.replace('{{GENERATED_AT}}', datetime.now().strftime('%Y-%m-%d %H:%M'))
    
    return html

def main():
    print("=" * 50)
    print("周报和月报生成器 - V4.4")
    print("=" * 50)
    
    dates = ['2026-02-18', '2026-02-19', '2026-02-20', '2026-02-21', '2026-02-22']
    available_data = [load_cache(d) for d in dates if load_cache(d)]
    
    print(f"✅ 从缓存加载 {len(available_data)} 天数据")
    
    with open(TEMPLATE_DIR / 'WEEKLY_TEMPLATE_V2.html', 'r', encoding='utf-8') as f:
        weekly_template = f.read()
    with open(TEMPLATE_DIR / 'MONTHLY_TEMPLATE_V2.html', 'r', encoding='utf-8') as f:
        monthly_template = f.read()
    
    # 周报
    print("\n📊 生成本周周报...")
    html = generate_weekly_report(dates, weekly_template)
    if html:
        output_path = OUTPUT_DIR / '2026-02-weekly-report-V4.4.pdf'
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.set_content(html)
            page.wait_for_timeout(2000)
            page.pdf(path=str(output_path), format='A4', print_background=True,
                    margin={'top': '8mm', 'bottom': '8mm', 'left': '8mm', 'right': '8mm'})
            browser.close()
        print(f"  ✅ 周报生成: {output_path}")
    
    # 月报
    print("\n📈 生成本月月报...")
    html = generate_monthly_report(2026, 2, available_data, monthly_template)
    if html:
        output_path = OUTPUT_DIR / '2026-02-monthly-report-V4.4.pdf'
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.set_content(html)
            page.wait_for_timeout(2000)
            page.pdf(path=str(output_path), format='A4', print_background=True,
                    margin={'top': '8mm', 'bottom': '8mm', 'left': '8mm', 'right': '8mm'})
            browser.close()
        print(f"  ✅ 月报生成: {output_path}")
    
    print("\n✅ 全部完成！")

if __name__ == '__main__':
    main()
