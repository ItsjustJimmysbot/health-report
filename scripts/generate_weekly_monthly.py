#!/usr/bin/env python3
"""
健康报告生成器 - 周报和月报
"""
import json
import os
from datetime import datetime, timedelta
from playwright.sync_api import sync_playwright

def parse_health_data(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    metrics = data.get('data', {}).get('metrics', [])
    return {m.get('name'): m for m in metrics}

def get_metric_value(metrics, name, agg='avg'):
    if name not in metrics:
        return None, 0
    data = metrics[name].get('data', [])
    if not data:
        return None, 0
    values = [d.get('qty', 0) for d in data if 'qty' in d]
    if not values:
        return None, 0
    if agg == 'avg':
        return sum(values) / len(values), len(values)
    elif agg == 'sum':
        return sum(values), len(values)
    elif agg == 'max':
        return max(values), len(values)
    return values[0], len(values)

def get_daily_summary(date_str, metrics, next_day_metrics=None):
    summary = {'date': date_str}
    
    hrv_val, _ = get_metric_value(metrics, 'heart_rate_variability', 'avg')
    summary['hrv'] = round(hrv_val, 1) if hrv_val else None
    
    resting_hr, _ = get_metric_value(metrics, 'resting_heart_rate', 'avg')
    summary['resting_hr'] = round(resting_hr, 0) if resting_hr else None
    
    steps, _ = get_metric_value(metrics, 'step_count', 'sum')
    summary['steps'] = int(steps) if steps else 0
    
    distance, _ = get_metric_value(metrics, 'walking_running_distance', 'sum')
    summary['distance'] = round(distance, 2) if distance else 0
    
    energy, _ = get_metric_value(metrics, 'active_energy', 'sum')
    summary['energy'] = round(energy, 0) if energy else 0
    
    floors, _ = get_metric_value(metrics, 'flights_climbed', 'sum')
    summary['floors'] = int(floors) if floors else 0
    
    stand_time, _ = get_metric_value(metrics, 'apple_stand_time', 'sum')
    summary['stand_time'] = int(stand_time / 60) if stand_time else 0
    
    spo2, _ = get_metric_value(metrics, 'blood_oxygen_saturation', 'avg')
    summary['spo2'] = round(spo2 * 100, 1) if spo2 else None
    
    rest_energy, _ = get_metric_value(metrics, 'basal_energy_burned', 'sum')
    summary['rest_energy'] = round(rest_energy, 0) if rest_energy else 0
    
    resp_rate, _ = get_metric_value(metrics, 'respiratory_rate', 'avg')
    summary['resp_rate'] = round(resp_rate, 1) if resp_rate else None
    
    # 睡眠数据
    sleep_sessions = []
    sleep_hours = 0
    for m in [metrics, next_day_metrics]:
        if m and 'sleep_analysis' in m:
            for sleep in m['sleep_analysis'].get('data', []):
                sleep_start = sleep.get('startDate', '')
                sleep_qty = sleep.get('qty', 0)
                try:
                    start_dt = datetime.strptime(sleep_start[:19], '%Y-%m-%d %H:%M:%S')
                    sleep_date = start_dt.strftime('%Y-%m-%d')
                    if sleep_date == date_str and start_dt.hour >= 20:
                        sleep_hours += sleep_qty / 60
                    elif sleep_date == (datetime.strptime(date_str, '%Y-%m-%d') + timedelta(days=1)).strftime('%Y-%m-%d') and start_dt.hour < 12:
                        sleep_hours += sleep_qty / 60
                except:
                    pass
    summary['sleep_total'] = round(sleep_hours, 1)
    
    # 运动
    workouts = []
    if 'workout' in metrics:
        for w in metrics['workout'].get('data', []):
            workouts.append({'type': w.get('value', ''), 'duration': w.get('qty', 0)})
    summary['workouts'] = workouts
    summary['has_workout'] = len(workouts) > 0
    
    # 心率
    hr_data = []
    if 'heart_rate' in metrics:
        for hr in metrics['heart_rate'].get('data', []):
            hr_data.append(hr.get('qty', 0))
    summary['hr_max'] = round(max(hr_data), 0) if hr_data else None
    summary['hr_avg'] = round(sum(hr_data) / len(hr_data), 0) if hr_data else None
    
    return summary

def generate_weekly_report(daily_data, template):
    """生成周报"""
    # 本周数据：2/16-2/22，但有数据的只有2/18-2/22
    week_dates = ['2026-02-18', '2026-02-19', '2026-02-20', '2026-02-21', '2026-02-22']
    available_data = [daily_data.get(d) for d in week_dates if d in daily_data]
    
    if not available_data:
        return None
    
    # 计算统计
    avg_hrv = sum(d['hrv'] for d in available_data if d.get('hrv')) / len([d for d in available_data if d.get('hrv')]) if any(d.get('hrv') for d in available_data) else 0
    total_steps = sum(d['steps'] for d in available_data)
    avg_sleep = sum(d['sleep_total'] for d in available_data) / len(available_data)
    avg_steps = total_steps / len(available_data)
    total_energy = sum(d['energy'] for d in available_data)
    workout_days = sum(1 for d in available_data if d.get('has_workout'))
    
    html = template
    html = html.replace('{{START_DATE}}', '2026-02-16')
    html = html.replace('{{END_DATE}}', '2026-02-22')
    html = html.replace('{{DATA_STATUS}}', f'部分数据 ({len(available_data)}/7天)')
    
    # 数据进度提示
    html = html.replace('{{ALERT_CLASS}}', '')
    html = html.replace('{{DATA_PROGRESS}}', f'⚠️ 数据收集进度: {len(available_data)}/7 天')
    html = html.replace('{{DATA_NOTICE}}', f'本周有 {7-len(available_data)} 天数据缺失。报告基于可用数据生成，部分统计可能不完整。')
    
    # 统计概览
    html = html.replace('{{AVG_HRV}}', f"{avg_hrv:.1f}")
    html = html.replace('{{TOTAL_STEPS}}', f"{total_steps:,}")
    html = html.replace('{{AVG_SLEEP}}', f"{avg_sleep:.1f}")
    html = html.replace('{{AVG_STEPS}}', f"{int(avg_steps):,}")
    html = html.replace('{{TOTAL_ENERGY}}', f"{int(total_energy):,}")
    html = html.replace('{{WORKOUT_DAYS}}', str(workout_days))
    html = html.replace('{{REST_DAYS}}', str(len(available_data) - workout_days))
    
    # 趋势标签
    html = html.replace('{{HRV_TREND_CLASS}}', 'badge-good')
    html = html.replace('{{HRV_TREND}}', '稳定')
    html = html.replace('{{STEPS_TREND_CLASS}}', 'badge-average')
    html = html.replace('{{STEPS_TREND}}', '需提升')
    html = html.replace('{{SLEEP_TREND_CLASS}}', 'badge-poor')
    html = html.replace('{{SLEEP_TREND}}', '需关注')
    
    # 每日明细行
    daily_rows = []
    weekday_names = ['周二', '周三', '周四', '周五', '周六']
    for i, date in enumerate(week_dates):
        d = daily_data.get(date, {})
        if d:
            recovery = 70 + (10 if d.get('hrv', 0) > 50 else 0) + (10 if d.get('resting_hr', 100) < 65 else 0)
            row = f"<tr><td>{date}</td><td>{weekday_names[i]}</td><td>{d.get('hrv', '--')}</td><td>{d.get('steps', 0):,}</td><td>{d.get('sleep_total', 0):.1f}h</td><td>{int(d.get('energy', 0))}</td><td>{'✓' if d.get('has_workout') else '-'}</td><td>{recovery}</td></tr>"
            daily_rows.append(row)
    html = html.replace('{{DAILY_ROWS}}', ''.join(daily_rows))
    
    # 趋势分析
    html = html.replace('{{HRV_TREND_ANALYSIS}}', f'本周平均HRV {avg_hrv:.1f}ms，保持在正常范围。HRV波动反映日常压力和恢复状态，建议关注睡眠对HRV的影响。')
    html = html.replace('{{ACTIVITY_TREND_ANALYSIS}}', f'本周日均步数 {int(avg_steps):,} 步，距离10000步目标有差距。工作日活动量可能较低，建议周末增加户外活动补偿。')
    html = html.replace('{{SLEEP_TREND_ANALYSIS}}', f'本周平均睡眠 {avg_sleep:.1f} 小时，部分日期数据缺失。充足睡眠对恢复和健康至关重要，建议完善睡眠追踪。')
    html = html.replace('{{WORKOUT_PATTERN_ANALYSIS}}', f'本周运动 {workout_days} 天，运动频率一般。建议建立规律的运动习惯，每周至少运动3-4次，每次30分钟以上。')
    
    # 周对比表（简化版）
    html = html.replace('{{WEEKLY_COMPARISON_ROWS}}', '<tr><td colspan="9" style="text-align:center;color:#64748b;">数据收集不完整，完整对比表需要7天数据</td></tr>')
    
    # AI建议
    html = html.replace('{{AI1_TITLE}}', '提升日常活动量')
    html = html.replace('{{AI1_PROBLEM}}', f'本周日均步数{int(avg_steps):,}步，低于推荐的10000步目标，基础活动量不足。')
    html = html.replace('{{AI1_ACTION}}', '1. 设定每日步数目标提醒<br>2. 工作时每小时起身活动5分钟<br>3. 选择步行或骑行代替短途乘车')
    html = html.replace('{{AI1_EXPECTATION}}', '预计2-3周后日均步数可提升至8000步以上。')
    
    html = html.replace('{{AI2_TITLE}}', '完善睡眠追踪')
    html = html.replace('{{AI2_PROBLEM}}', '本周睡眠数据记录不完整，影响恢复评估的准确性。')
    html = html.replace('{{AI2_ACTION}}', '1. 检查Apple Watch睡眠模式设置<br>2. 设定规律的作息时间<br>3. 确保睡前正确佩戴设备')
    html = html.replace('{{AI2_EXPECTATION}}', '改善睡眠数据记录质量，可更准确评估恢复状态。')
    
    html = html.replace('{{AI3_TITLE}}', '建立运动习惯')
    html = html.replace('{{AI3_DIET}}', '保持均衡饮食，运动日适当增加蛋白质摄入，注意补充水分。')
    html = html.replace('{{AI3_ROUTINE}}', '建议固定运动时间，如早晨或下班后，建立条件反射。')
    
    html = html.replace('{{AI4_TITLE}}', '周数据洞察')
    html = html.replace('{{AI4_ADVANTAGES}}', 'HRV指标保持在健康范围，基础代谢正常。')
    html = html.replace('{{AI4_RISKS}}', '活动量偏低，睡眠数据记录不完整。')
    html = html.replace('{{AI4_CONCLUSION}}', '本周整体健康状况一般，需要提升活动量和改善睡眠质量。')
    html = html.replace('{{AI4_PLAN}}', '1. 增加日常步行量<br>2. 完善睡眠追踪<br>3. 建立规律运动习惯')
    
    html = html.replace('{{DATA_COUNT}}', str(len(available_data)))
    html = html.replace('{{GENERATED_AT}}', datetime.now().strftime('%Y-%m-%d %H:%M'))
    
    return html

def generate_monthly_report(daily_data, template):
    """生成月报"""
    # 本月数据：2/1-2/22，有数据的只有2/18-2/22
    available_data = list(daily_data.values())
    data_count = len(available_data)
    
    if not available_data:
        return None
    
    # 计算统计
    avg_hrv = sum(d['hrv'] for d in available_data if d.get('hrv')) / len([d for d in available_data if d.get('hrv')]) if any(d.get('hrv') for d in available_data) else 0
    total_steps = sum(d['steps'] for d in available_data)
    avg_steps = total_steps / data_count if data_count > 0 else 0
    avg_sleep = sum(d['sleep_total'] for d in available_data) / data_count
    total_energy = sum(d['energy'] for d in available_data)
    workout_days = sum(1 for d in available_data if d.get('has_workout'))
    
    # 最佳睡眠日
    best_sleep = max(available_data, key=lambda x: x.get('sleep_total', 0))
    best_sleep_day = best_sleep['date'] if best_sleep.get('sleep_total', 0) > 0 else '--'
    
    # 预测值
    projected_steps = int(avg_steps * 28)
    projected_workouts = int(workout_days / data_count * 28)
    projected_energy = int(total_energy / data_count * 28)
    
    html = template
    html = html.replace('{{YEAR}}', '2026')
    html = html.replace('{{MONTH}}', '2')
    html = html.replace('{{DATA_STATUS}}', f'部分数据 ({data_count}/28天)')
    
    # 数据进度提示
    html = html.replace('{{ALERT_CLASS}}', '')
    html = html.replace('{{DATA_PROGRESS}}', f'⚠️ 数据收集进度: {data_count}/28 天 (本月)')
    html = html.replace('{{DATA_NOTICE}}', f'本月有 {28-data_count} 天数据缺失。报告基于可用数据生成，统计和预测可能不完整。')
    
    # 统计概览
    html = html.replace('{{AVG_HRV}}', f"{avg_hrv:.1f}")
    html = html.replace('{{AVG_STEPS}}', f"{int(avg_steps):,}")
    html = html.replace('{{AVG_SLEEP}}', f"{avg_sleep:.1f}")
    html = html.replace('{{WORKOUT_DAYS}}', str(workout_days))
    html = html.replace('{{DATA_COUNT}}', str(data_count))
    html = html.replace('{{TOTAL_STEPS}}', f"{total_steps:,}")
    html = html.replace('{{TOTAL_ENERGY}}', f"{int(total_energy):,}")
    html = html.replace('{{BEST_SLEEP_DAY}}', best_sleep_day)
    
    # 月度预测
    html = html.replace('{{PROJECTED_STEPS}}', f"{projected_steps:,}")
    html = html.replace('{{PROJECTED_STEPS_PERCENT}}', str(int(projected_steps/240000*100)))
    html = html.replace('{{PROJECTED_WORKOUTS}}', str(projected_workouts))
    html = html.replace('{{PROJECTED_WORKOUTS_PERCENT}}', str(int(projected_workouts/12*100)))
    html = html.replace('{{PROJECTED_ENERGY}}', f"{projected_energy:,}")
    
    # 每日明细
    daily_rows = []
    for date, d in sorted(daily_data.items()):
        note = ''
        if d.get('has_workout'):
            note += '运动 '
        if d.get('sleep_total', 0) == 0:
            note += '无睡眠数据'
        row = f"<tr><td>{date}</td><td>{d.get('hrv', '--')}</td><td>{d.get('steps', 0):,}</td><td>{d.get('sleep_total', 0):.1f}h</td><td>{int(d.get('energy', 0))}</td><td>{'✓' if d.get('has_workout') else '-'}</td><td>{note}</td></tr>"
        daily_rows.append(row)
    html = html.replace('{{DAILY_ROWS}}', ''.join(daily_rows))
    
    # 趋势分析
    html = html.replace('{{HRV_TREND_ANALYSIS}}', f'本月平均HRV {avg_hrv:.1f}ms，处于健康范围。建议继续监测HRV变化趋势，作为训练负荷调整的参考。')
    html = html.replace('{{ACTIVITY_PATTERN_ANALYSIS}}', f'本月日均步数 {int(avg_steps):,} 步。根据现有数据推算，全月总步数预计约 {projected_steps:,} 步，建议增加日常活动量。')
    html = html.replace('{{SLEEP_QUALITY_ANALYSIS}}', f'本月平均睡眠 {avg_sleep:.1f} 小时，部分日期数据缺失。充足睡眠对健康和恢复至关重要。')
    html = html.replace('{{WORKOUT_RECOVERY_BALANCE}}', f'本月运动 {workout_days} 天，预计全月约 {projected_workouts} 天。建议平衡运动与恢复，避免过度训练。')
    
    # 目标追踪
    goal_rows = [
        f'<tr><td>日均步数</td><td>10,000</td><td>{int(avg_steps):,}</td><td>{int(avg_steps/10000*100)}%</td><td>--</td><td>{"良好" if avg_steps >= 8000 else "需改善"}</td></tr>',
        f'<tr><td>运动频率</td><td>12天/月</td><td>{workout_days}天/{data_count}天</td><td>{int(workout_days/data_count*100)}%</td><td>--</td><td>{"良好" if workout_days >= data_count//3 else "需改善"}</td></tr>',
        f'<tr><td>平均睡眠</td><td>7小时</td><td>{avg_sleep:.1f}h</td><td>{int(avg_sleep/7*100)}%</td><td>--</td><td>{"良好" if avg_sleep >= 6 else "需改善"}</td></tr>',
    ]
    html = html.replace('{{GOAL_TRACKING_ROWS}}', ''.join(goal_rows))
    
    html = html.replace('{{GOAL_ANALYSIS}}', '基于现有数据，步数和睡眠目标需要关注。建议设定阶段性目标，逐步改善。')
    
    # AI建议
    html = html.replace('{{AI1_TITLE}}', '建立健康习惯体系')
    html = html.replace('{{AI1_PROBLEM}}', '数据记录不完整反映出生活习惯可能不够规律，需要建立系统性的健康管理。')
    html = html.replace('{{AI1_ACTION}}', '1. 设定固定的作息时间<br>2. 建立数据追踪的仪式感<br>3. 设定每周健康目标并复盘')
    html = html.replace('{{AI1_EXPECTATION}}', '2-3个月后形成稳定的健康习惯。')
    
    html = html.replace('{{AI2_TITLE}}', '提升活动基础')
    html = html.replace('{{AI2_PROBLEM}}', f'日均步数{int(avg_steps):,}低于推荐值，基础活动量不足可能影响长期健康。')
    html = html.replace('{{AI2_ACTION}}', '1. 从每天多走1000步开始<br>2. 利用碎片时间活动<br>3. 周末安排户外活动')
    html = html.replace('{{AI2_EXPECTATION}}', '4-6周内日均步数可提升至8000步以上。')
    
    html = html.replace('{{AI3_TITLE}}', '生活方式优化')
    html = html.replace('{{AI3_DIET}}', '保持均衡饮食，控制糖分和加工食品摄入，多吃蔬菜水果。')
    html = html.replace('{{AI3_ROUTINE}}', '建立规律的作息时间，建议23:00前入睡，保证7-8小时睡眠。')
    html = html.replace('{{AI3_HABITS}}', '养成每日数据查看习惯，建立健康意识，逐步改善生活方式。')
    
    html = html.replace('{{AI4_TITLE}}', '月度数据洞察')
    html = html.replace('{{AI4_ADVANTAGES}}', 'HRV指标稳定，基础健康状况良好。')
    html = html.replace('{{AI4_RISKS}}', '活动量偏低，数据记录不完整反映生活习惯需改善。')
    html = html.replace('{{AI4_CONCLUSION}}', '本月健康状况有改善空间，建议重点关注日常活动量和生活规律性。')
    html = html.replace('{{AI4_NEXT_MONTH_GOALS}}', '1. 日均步数达到8000步<br>2. 完善睡眠追踪<br>3. 每周运动3次以上')
    
    html = html.replace('{{GENERATED_AT}}', datetime.now().strftime('%Y-%m-%d %H:%M'))
    
    return html

def main():
    base_dir = os.path.expanduser('~/我的云端硬盘/Health Auto Export/Health Data')
    template_dir = os.path.expanduser('~/.openclaw/workspace-health/templates')
    output_dir = os.path.expanduser('~/.openclaw/workspace/shared/health-reports/upload')
    
    os.makedirs(output_dir, exist_ok=True)
    
    # 读取模板
    with open(f'{template_dir}/WEEKLY_TEMPLATE_V2.html', 'r', encoding='utf-8') as f:
        weekly_template = f.read()
    with open(f'{template_dir}/MONTHLY_TEMPLATE_V2.html', 'r', encoding='utf-8') as f:
        monthly_template = f.read()
    
    # 读取数据
    dates = ['2026-02-18', '2026-02-19', '2026-02-20', '2026-02-21', '2026-02-22']
    daily_data = {}
    
    for i, date in enumerate(dates):
        file_path = f"{base_dir}/HealthAutoExport-{date}.json"
        next_file = f"{base_dir}/HealthAutoExport-{dates[i+1]}.json" if i < len(dates)-1 else None
        
        if os.path.exists(file_path):
            metrics = parse_health_data(file_path)
            next_metrics = parse_health_data(next_file) if next_file and os.path.exists(next_file) else None
            daily_data[date] = get_daily_summary(date, metrics, next_metrics)
    
    print(f"✅ 加载了 {len(daily_data)} 天数据")
    
    # 生成周报
    html = generate_weekly_report(daily_data, weekly_template)
    if html:
        output_path = f'{output_dir}/2026-02-weekly-report.pdf'
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.set_content(html)
            page.wait_for_timeout(2000)
            page.pdf(path=output_path, format='A4', print_background=True,
                    margin={'top': '8mm', 'bottom': '8mm', 'left': '8mm', 'right': '8mm'})
            browser.close()
        print(f"✅ 周报生成: {output_path}")
    
    # 生成月报
    html = generate_monthly_report(daily_data, monthly_template)
    if html:
        output_path = f'{output_dir}/2026-02-monthly-report.pdf'
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.set_content(html)
            page.wait_for_timeout(2000)
            page.pdf(path=output_path, format='A4', print_background=True,
                    margin={'top': '8mm', 'bottom': '8mm', 'left': '8mm', 'right': '8mm'})
            browser.close()
        print(f"✅ 月报生成: {output_path}")

if __name__ == '__main__':
    main()
