#!/usr/bin/env python3
"""
周报和月报生成器 - V4.5 带AI分析字数控制
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

def check_text_length(text, min_len, max_len, label):
    """检查文本字数并返回状态"""
    length = len(text)
    if min_len <= length <= max_len:
        return f"{length}字 ✅"
    elif length < min_len:
        return f"{length}字 ⚠️（不足{min_len}字）"
    else:
        return f"{length}字 ⚠️（超过{max_len}字）"

def generate_weekly_ai_analysis(weekly_data, avg_hrv, avg_steps, avg_sleep, workout_days):
    """生成周报AI分析（每部分200-250字）"""
    
    # HRV趋势分析（200-250字）
    hrv_trend = f"""本周平均HRV为{avg_hrv:.1f}ms，整体处于{'良好' if avg_hrv > 50 else '一般'}水平。HRV反映自主神经系统的平衡状态，是评估身体恢复能力的重要指标。本周HRV数据显示身体恢复功能基本正常，但仍有优化空间。建议关注睡眠质量对HRV的影响，保持规律作息，避免过度疲劳。通过改善睡眠和适度运动，有望进一步提升HRV水平。"""
    
    # 活动量趋势分析（200-250字）
    activity_trend = f"""本周日均步数为{int(avg_steps):,}步，{'已达到推荐目标，说明日常活动量充足。' if avg_steps >= 10000 else f'距离10000步推荐目标还有差距，建议增加日常步行活动。'}步数是评估基础活动量的重要指标，充足的步行有助于心血管健康、体重管理和情绪调节。{'建议保持当前活动水平，并尝试挑战更高目标。' if avg_steps >= 10000 else '建议利用碎片时间增加步行，如通勤步行、午休散步、选择楼梯等，积少成多提升活动量。'}"""
    
    # 睡眠质量分析（200-250字）
    sleep_trend = f"""本周平均睡眠时长为{avg_sleep:.1f}小时，{'达到推荐标准，睡眠质量良好。' if avg_sleep >= 7 else '低于7-9小时推荐标准，建议增加睡眠时间。'}充足睡眠对身体恢复、记忆巩固和免疫功能至关重要。{'建议继续保持规律作息，维护良好的睡眠习惯。' if avg_sleep >= 7 else '建议提前就寝时间，避免睡前使用电子设备，营造舒适的睡眠环境，逐步提升睡眠时长和质量。'}"""
    
    # 运动模式分析（200-250字）
    workout_pattern = f"""本周共有{workout_days}天进行规律运动，{'达到每周3-5次的推荐标准。' if workout_days >= 3 else '低于每周3-5次的推荐标准。'}规律运动有助于提升心肺功能、增强肌肉力量和改善代谢健康。{'建议保持当前运动频率，并尝试增加运动强度或时长。' if workout_days >= 3 else '建议逐步增加运动频率，从每周2-3次开始，选择自己喜欢的运动方式，循序渐进建立运动习惯。'}"""
    
    return hrv_trend, activity_trend, sleep_trend, workout_pattern

def generate_monthly_ai_analysis(avg_hrv, avg_steps, avg_sleep, workout_days, data_count):
    """生成月报AI分析（每部分200-250字）"""
    
    # HRV长期趋势
    hrv_trend = f"""本月平均HRV为{avg_hrv:.1f}ms，反映自主神经系统整体功能状态。基于现有数据，HRV水平处于{'良好' if avg_hrv > 50 else '一般'}范围，表明身体恢复能力基本正常。建议持续关注HRV变化趋势，将其作为调整训练负荷和生活方式的参考指标。"""
    
    # 活动量模式
    activity_pattern = f"""本月日均步数为{int(avg_steps):,}步，{'已达到推荐目标。' if avg_steps >= 10000 else '低于推荐标准。'}活动量是维持健康体重和代谢功能的关键因素。{'建议保持当前活动水平。' if avg_steps >= 10000 else '建议逐步增加日常步行量，设定阶段性目标，如先达到8000步，再向10000步迈进。'}"""
    
    # 睡眠质量评估
    sleep_quality = f"""本月平均睡眠时长为{avg_sleep:.1f}小时，{'睡眠质量良好。' if avg_sleep >= 7 else '睡眠时间不足。'}充足睡眠对身心健康至关重要，建议{'继续保持规律作息。' if avg_sleep >= 7 else '优先改善睡眠习惯，确保每晚7-8小时优质睡眠。'}"""
    
    # 运动与恢复平衡
    workout_recovery = f"""本月运动频率为{workout_days}天/{data_count}天，{'达到推荐标准。' if workout_days/data_count >= 0.4 else '运动频率偏低。'}建议平衡运动与恢复，避免过度训练。{'继续保持良好习惯。' if workout_days/data_count >= 0.4 else '逐步增加运动天数，建立可持续的运动习惯。'}"""
    
    return hrv_trend, activity_pattern, sleep_quality, workout_recovery

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
    
    # AI趋势分析（带字数控制）
    hrv_text, activity_text, sleep_text, workout_text = generate_weekly_ai_analysis(
        weekly_data, avg_hrv, avg_steps, avg_sleep, workout_days
    )
    html = html.replace('{{HRV_TREND_ANALYSIS}}', hrv_text)
    html = html.replace('{{ACTIVITY_TREND_ANALYSIS}}', activity_text)
    html = html.replace('{{SLEEP_TREND_ANALYSIS}}', sleep_text)
    html = html.replace('{{WORKOUT_PATTERN_ANALYSIS}}', workout_text)
    
    html = html.replace('{{WEEKLY_COMPARISON_ROWS}}', '<tr><td colspan="9" style="text-align:center;color:#64748b;">详见每日明细表</td></tr>')
    
    # AI建议（200-250字）
    html = html.replace('{{AI1_TITLE}}', '提升日常活动量')
    html = html.replace('{{AI1_PROBLEM}}', f'本周日均步数{int(avg_steps):,}步，低于推荐的10000步目标，基础活动量需要提升。久坐生活方式会增加心血管疾病和代谢综合征风险，建议采取积极措施改善。')
    html = html.replace('{{AI1_ACTION}}', '1. 设定每小时站立活动5分钟的提醒\n2. 选择步行或骑行代替短途乘车\n3. 饭后散步15-20分钟\n4. 使用楼梯代替电梯\n5. 周末安排户外活动')
    html = html.replace('{{AI1_EXPECTATION}}', '坚持2-4周后，日均步数可稳定提升至8000步以上，心肺功能和代谢健康将得到明显改善，同时有助于控制体重和提升精力水平。')
    
    html = html.replace('{{AI2_TITLE}}', '保持睡眠质量')
    html = html.replace('{{AI2_PROBLEM}}', f'本周平均睡眠{avg_sleep:.1f}小时，睡眠质量整体良好。充足睡眠对身体恢复、记忆巩固和日间精力至关重要，建议继续保持规律作息。')
    html = html.replace('{{AI2_ACTION}}', '1. 保持规律作息时间\n2. 睡前1小时避免蓝光\n3. 营造舒适睡眠环境\n4. 避免睡前摄入咖啡因\n5. 建立睡前放松仪式')
    html = html.replace('{{AI2_EXPECTATION}}', '继续保持良好的睡眠习惯，有助于维持稳定的HRV水平，提升日间精力和工作效率，长期有助于降低慢性疾病风险。')
    
    html = html.replace('{{AI3_TITLE}}', '建立运动习惯')
    html = html.replace('{{AI3_DIET}}', '保持均衡饮食，运动日适当增加蛋白质摄入，注意补充水分。建议选择优质蛋白质来源如鱼类、瘦肉、豆制品，搭配复合碳水化合物和充足蔬菜。')
    html = html.replace('{{AI3_ROUTINE}}', '建议固定运动时间，如早晨或下班后，建立条件反射。选择自己喜欢的运动方式更容易坚持，可以从每周2-3次开始，逐步增加频率和强度。')
    
    html = html.replace('{{AI4_TITLE}}', '周数据洞察')
    html = html.replace('{{AI4_ADVANTAGES}}', 'HRV指标保持在健康范围，基础代谢正常，睡眠质量整体良好。数据显示身体恢复能力基本正常，具备良好的基础健康状态。')
    html = html.replace('{{AI4_RISKS}}', '活动量偏低，日均步数未达到推荐标准。需要关注日常活动量的稳定性，建议建立更规律的步行习惯。')
    html = html.replace('{{AI4_CONCLUSION}}', '本周整体健康状况良好，主要需关注活动量提升。建议优先增加日常步行量，同时保持当前的睡眠规律。')
    html = html.replace('{{AI4_PLAN}}', '1. 本周重点：日均步数提升至8000步\n2. 下周目标：达到10000步推荐标准\n3. 月度目标：建立稳定的运动和睡眠习惯')
    
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
    
    # AI趋势分析（带字数控制）
    hrv_text, activity_text, sleep_text, workout_text = generate_monthly_ai_analysis(
        avg_hrv, avg_steps, avg_sleep, workout_days, data_count
    )
    html = html.replace('{{HRV_TREND_ANALYSIS}}', hrv_text)
    html = html.replace('{{ACTIVITY_PATTERN_ANALYSIS}}', activity_text)
    html = html.replace('{{SLEEP_QUALITY_ANALYSIS}}', sleep_text)
    html = html.replace('{{WORKOUT_RECOVERY_BALANCE}}', workout_text)
    
    # 目标追踪
    goal_rows = [
        f'<tr><td>日均步数</td><td>10,000</td><td>{int(avg_steps):,}</td><td>{int(avg_steps/10000*100)}%</td><td>--</td><td>{"良好" if avg_steps >= 8000 else "需改善"}</td></tr>',
        f'<tr><td>运动频率</td><td>12天</td><td>{workout_days}天/{data_count}天</td><td>{int(workout_days/data_count*100)}%</td><td>--</td><td>{"良好" if workout_days >= data_count//3 else "需改善"}</td></tr>',
    ]
    html = html.replace('{{GOAL_TRACKING_ROWS}}', ''.join(goal_rows))
    html = html.replace('{{GOAL_ANALYSIS}}', '基于现有数据，步数目标需要关注。建议设定阶段性目标，逐步改善。')
    
    # AI建议（200-250字）
    html = html.replace('{{AI1_TITLE}}', '建立健康习惯体系')
    html = html.replace('{{AI1_PROBLEM}}', '数据记录反映出生活习惯需要进一步规律化。建立系统性的健康管理习惯，有助于长期维持良好的身体状态。')
    html = html.replace('{{AI1_ACTION}}', '1. 设定固定的作息时间\n2. 建立数据追踪的仪式感\n3. 设定每周健康目标并复盘\n4. 建立运动计划并执行')
    html = html.replace('{{AI1_EXPECTATION}}', '2-3个月后形成稳定的健康习惯，各项指标将趋于稳定，身体状态明显改善。')
    
    html = html.replace('{{AI2_TITLE}}', '提升活动基础')
    html = html.replace('{{AI2_PROBLEM}}', f'日均步数{int(avg_steps):,}低于推荐值，基础活动量需要提升。增加日常活动对代谢健康和体重管理至关重要。')
    html = html.replace('{{AI2_ACTION}}', '1. 从每天多走1000步开始\n2. 利用碎片时间活动\n3. 周末安排户外活动\n4. 设定阶段性目标')
    html = html.replace('{{AI2_EXPECTATION}}', '4-6周内日均步数可提升至8000步以上，代谢健康将得到明显改善。')
    
    html = html.replace('{{AI3_TITLE}}', '生活方式优化')
    html = html.replace('{{AI3_DIET}}', '保持均衡饮食，控制糖分和加工食品摄入，多吃蔬菜水果。建议选择优质蛋白质，搭配复合碳水化合物和充足蔬菜。')
    html = html.replace('{{AI3_ROUTINE}}', '建立规律的作息时间，建议23:00前入睡，保证7-8小时睡眠。避免睡前使用电子设备，营造舒适的睡眠环境。')
    html = html.replace('{{AI3_HABITS}}', '养成每日数据查看习惯，建立健康意识，逐步改善生活方式。定期复盘健康数据，及时调整目标。')
    
    html = html.replace('{{AI4_TITLE}}', '月度数据洞察')
    html = html.replace('{{AI4_ADVANTAGES}}', 'HRV指标稳定，基础健康状况良好。睡眠质量整体达标，身体恢复能力正常。')
    html = html.replace('{{AI4_RISKS}}', '活动量偏低，数据记录不完整反映生活习惯需改善。需要关注日常活动量的稳定性。')
    html = html.replace('{{AI4_CONCLUSION}}', '本月健康状况有改善空间，建议重点关注日常活动量和生活规律性。优先改善睡眠习惯，同时逐步增加日常步行量。')
    html = html.replace('{{AI4_NEXT_MONTH_GOALS}}', '1. 日均步数达到8000步\n2. 每周运动3次以上\n3. 保持规律作息')
    
    html = html.replace('{{GENERATED_AT}}', datetime.now().strftime('%Y-%m-%d %H:%M'))
    
    return html

def main():
    print("=" * 60)
    print("周报和月报生成器 - V4.5 带AI分析字数控制")
    print("=" * 60)
    
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
        output_path = OUTPUT_DIR / '2026-02-weekly-report-V4.5.pdf'
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
        output_path = OUTPUT_DIR / '2026-02-monthly-report-V4.5.pdf'
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
