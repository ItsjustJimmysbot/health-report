#!/usr/bin/env python3
"""
每日健康报告生成脚本 - 中文版
生成2份报告：单日报告 + 对比报告

【重要】睡眠数据逻辑（方案D - 已确认）：
- "昨晚的睡眠归今天"
- 2月20日晚上的睡眠 → 归属于2月20日的报告
- Apple Health 数据文件将睡眠记录在醒来当天的文件中
- 因此：日期X的报告，需要从文件 HealthAutoExport-(X+1).json 中提取睡眠数据
"""
import json, os, sys
from datetime import datetime, timedelta
from playwright.sync_api import sync_playwright

def get_dates():
    today = datetime.now()
    yesterday = (today - timedelta(days=1)).strftime('%Y-%m-%d')
    day_before = (today - timedelta(days=2)).strftime('%Y-%m-%d')
    return day_before, yesterday

def get_next_date(date_str):
    """获取下一天的日期字符串"""
    d = datetime.strptime(date_str, '%Y-%m-%d')
    next_d = d + timedelta(days=1)
    return next_d.strftime('%Y-%m-%d')

def extract_sleep_data(date_str):
    """
    提取睡眠数据 - 关键逻辑：从NEXT DAY的文件中提取
    因为Apple Health将睡眠记录在醒来当天的文件中
    """
    next_date = get_next_date(date_str)
    file_path = f"/Users/jimmylu/我的云端硬盘/Health Auto Export/Health Data/HealthAutoExport-{next_date}.json"
    
    if not os.path.exists(file_path):
        print(f"⚠️  找不到次日数据文件，无法获取{date_str}的睡眠数据: {file_path}")
        return None
    
    try:
        with open(file_path) as f:
            data = json.load(f)
        
        for m in data['data']['metrics']:
            if m['name'] == 'sleep_analysis' and m.get('data'):
                sleep_data = m['data'][0]
                return {
                    'total': round(sleep_data.get('totalSleep', 0), 2),
                    'deep': round(sleep_data.get('deep', 0), 2),
                    'core': round(sleep_data.get('core', 0), 2),
                    'rem': round(sleep_data.get('rem', 0), 2),
                    'awake': round(sleep_data.get('awake', 0), 2),
                    'sleep_start': sleep_data.get('sleepStart', '').split(' ')[1][:5] if sleep_data.get('sleepStart') else '--:--',
                    'sleep_end': sleep_data.get('sleepEnd', '').split(' ')[1][:5] if sleep_data.get('sleepEnd') else '--:--',
                    'source_file': next_date,  # 记录数据来源文件
                }
    except Exception as e:
        print(f"⚠️  读取睡眠数据出错: {e}")
    
    return None

def extract_data(date_str):
    """从Apple Health导出文件提取数据（除睡眠外）"""
    file_path = f"/Users/jimmylu/我的云端硬盘/Health Auto Export/Health Data/HealthAutoExport-{date_str}.json"
    
    if not os.path.exists(file_path):
        print(f"❌ 找不到数据文件: {file_path}")
        return None
    
    with open(file_path) as f:
        data = json.load(f)
    
    metrics = {m['name']: m for m in data['data']['metrics']}
    
    def get_avg(name):
        if name not in metrics or not metrics[name].get('data'):
            return 0, 0
        vals = [x['qty'] for x in metrics[name]['data'] if 'qty' in x]
        return round(sum(vals)/len(vals), 1) if vals else 0, len(vals)
    
    def get_sum(name):
        if name not in metrics or not metrics[name].get('data'):
            return 0, 0
        vals = [x['qty'] for x in metrics[name]['data'] if 'qty' in x]
        return round(sum(vals), 1), len(vals)
    
    hrv, hrv_n = get_avg('heart_rate_variability')
    resting_hr, resting_n = get_avg('resting_heart_rate')
    steps, steps_n = get_sum('step_count')
    distance, _ = get_sum('walking_running_distance')
    flights, flights_n = get_sum('flights_climbed')
    stand_hours = len(metrics.get('apple_stand_hour', {}).get('data', []))
    active_kj, active_n = get_sum('active_energy')
    active_kcal = round(active_kj / 4.184, 1) if active_kj else 0
    basal_kj, basal_n = get_sum('basal_energy_burned')
    basal_kcal = round(basal_kj / 4.184, 1) if basal_kj else 0
    blood_o2, blood_o2_n = get_avg('oxygen_saturation')
    
    result = {
        'date': date_str,
        'hrv': hrv, 'hrv_n': hrv_n,
        'resting_hr': resting_hr, 'resting_n': resting_n,
        'steps': int(steps), 'steps_n': steps_n,
        'active_kcal': active_kcal, 'active_n': active_n,
        'basal_kcal': basal_kcal, 'basal_n': basal_n,
        'distance': round(distance/1000, 2),
        'stand_hours': stand_hours,
        'flights': int(flights), 'flights_n': flights_n,
        'blood_o2': round(blood_o2*100, 1) if blood_o2 else 95, 'blood_o2_n': blood_o2_n,
        'sleep': None,  # 睡眠数据单独提取
        'sleep_source': None,
    }
    
    # 提取睡眠数据（从次日文件）
    sleep_data = extract_sleep_data(date_str)
    if sleep_data:
        result['sleep'] = sleep_data
        result['sleep_source'] = sleep_data['source_file']
        print(f"  ✅ 睡眠数据: {sleep_data['total']:.2f}h (来源: {sleep_data['source_file']}.json)")
    else:
        print(f"  ⚠️  未找到{date_str}的睡眠数据")
    
    return result

def generate_daily_report(data):
    """生成单日报告HTML"""
    if not data:
        return None
    
    d = data
    sleep_total = d['sleep']['total'] if d['sleep'] else 0
    sleep_display = f"{sleep_total:.2f}" if sleep_total > 0 else "数据缺失"
    sleep_status = "达标" if sleep_total >= 6 else "需改善" if sleep_total > 0 else "待补充"
    
    scores = {
        'recovery': min(100, int(60 + d['hrv'] * 0.5)) if d['hrv'] > 0 else 60,
        'sleep': min(100, int(sleep_total * 12.5)) if sleep_total > 0 else 50,
        'exercise': min(100, int(d['steps'] / 80)) if d['steps'] > 0 else 30,
    }
    
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>健康日报 - {d['date']}</title>
<style>
@page {{ size: A4; margin: 8mm; }}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: 'PingFang SC', sans-serif; font-size: 9pt; line-height: 1.4; color: #1f2937; }}
.container {{ max-width: 780px; margin: 0 auto; padding: 10px; }}
.header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 15px; border-radius: 10px; text-align: center; margin-bottom: 12px; }}
.score-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-bottom: 12px; }}
.score-card {{ background: #f8fafc; border-radius: 8px; padding: 12px; text-align: center; border-top: 3px solid #667eea; }}
.score-value {{ font-size: 22pt; font-weight: bold; color: #667eea; }}
.section {{ background: #f8fafc; border-radius: 8px; padding: 12px; margin-bottom: 10px; }}
.section-title {{ font-size: 11pt; font-weight: bold; color: #1e293b; margin-bottom: 10px; padding-bottom: 5px; border-bottom: 2px solid #667eea; }}
.metric-table {{ width: 100%; border-collapse: collapse; font-size: 8pt; }}
.metric-table th, .metric-table td {{ padding: 6px 8px; text-align: left; border-bottom: 1px solid #e2e8f0; }}
.metric-table th {{ background: #f1f5f9; font-weight: 600; }}
.metric-value {{ font-weight: bold; color: #1e293b; }}
.ai-text {{ font-size: 8pt; color: #475569; padding: 6px; background: white; border-radius: 4px; border-left: 3px solid #667eea; }}
.sleep-box {{ background: #f0fdf4; border-radius: 6px; padding: 10px; margin: 10px 0; }}
.sleep-box.error {{ background: #fef2f2; }}
.footer {{ text-align: center; font-size: 7pt; color: #94a3b8; padding-top: 10px; border-top: 1px solid #e2e8f0; }}
</style>
</head>
<body>
<div class="container">
<div class="header">
<h1>🏥 健康日报</h1>
<div style="font-size: 9pt; opacity: 0.9;">{d['date']} | UTC+8</div>
</div>

<div class="score-grid">
<div class="score-card"><div class="score-value">{scores['recovery']}</div><div style="font-size: 8pt; color: #64748b;">恢复度</div></div>
<div class="score-card"><div class="score-value">{scores['sleep']}</div><div style="font-size: 8pt; color: #64748b;">睡眠质量</div></div>
<div class="score-card"><div class="score-value">{scores['exercise']}</div><div style="font-size: 8pt; color: #64748b;">运动完成</div></div>
</div>

<div class="section">
<div class="section-title">📊 详细指标</div>
<table class="metric-table">
<tr><th>指标</th><th>数值</th><th>AI分析</th></tr>
<tr><td>HRV</td><td class="metric-value">{d['hrv']:.1f} ms</td><td class="ai-text">基于{d['hrv_n']}个数据点。</td></tr>
<tr><td>静息心率</td><td class="metric-value">{d['resting_hr']:.0f} bpm</td><td class="ai-text">{f'基于{d["resting_n"]}个数据点。' if d['resting_n'] > 0 else '数据待补充'}</td></tr>
<tr><td>步数</td><td class="metric-value">{d['steps']:,}</td><td class="ai-text">基于{d['steps_n']}个数据点。</td></tr>
<tr><td>活动能量</td><td class="metric-value">{d['active_kcal']:.1f} kcal</td><td class="ai-text">基于{d['active_n']}个数据点，已从kJ转换。</td></tr>
<tr><td>睡眠</td><td class="metric-value">{sleep_display} h</td><td class="ai-text">{f'来源: {d["sleep_source"]}数据文件 (入睡{d["sleep"]["sleep_start"]}→醒来{d["sleep"]["sleep_end"]})' if d['sleep'] else '数据缺失 - 未找到次日数据文件'}</td></tr>
</table>
</div>

<div class="footer">
数据来源: Apple Health | 生成: {datetime.now().strftime('%Y-%m-%d')} | UTC+8
</div>
</div>
</body>
</html>"""
    return html

def generate_comparison_report(data1, data2):
    """生成对比报告HTML"""
    if not data1 or not data2:
        return None
    
    d1, d2 = data1, data2
    
    def calc_change(v1, v2):
        if v1 == 0: return 0
        return round((v2 - v1) / v1 * 100, 1)
    
    s1 = d1['sleep']['total'] if d1['sleep'] else 0
    s2 = d2['sleep']['total'] if d2['sleep'] else 0
    
    changes = {
        'hrv': calc_change(d1['hrv'], d2['hrv']),
        'steps': calc_change(d1['steps'], d2['steps']),
        'active': calc_change(d1['active_kcal'], d2['active_kcal']),
        'sleep': calc_change(s1, s2),
    }
    
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>健康对比 - {d1['date']} vs {d2['date']}</title>
<style>
@page {{ size: A4; margin: 10mm; }}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: 'PingFang SC', sans-serif; font-size: 10pt; line-height: 1.4; color: #1f2937; }}
.container {{ max-width: 780px; margin: 0 auto; padding: 15px; }}
.header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 10px; text-align: center; margin-bottom: 15px; }}
.comp-table {{ width: 100%; border-collapse: collapse; font-size: 9pt; margin: 15px 0; }}
.comp-table th {{ background: #f1f5f9; padding: 10px; text-align: center; font-weight: bold; border-bottom: 2px solid #e2e8f0; }}
.comp-table td {{ padding: 10px; text-align: center; border-bottom: 1px solid #e2e8f0; }}
.positive {{ color: #166534; font-weight: bold; }}
.negative {{ color: #991b1b; font-weight: bold; }}
.footer {{ text-align: center; font-size: 8pt; color: #94a3b8; margin-top: 20px; padding-top: 10px; border-top: 1px solid #e2e8f0; }}
</style>
</head>
<body>
<div class="container">
<div class="header">
<h1>📊 健康对比报告</h1>
<div style="font-size: 10pt; opacity: 0.9;">{d1['date']} vs {d2['date']}</div>
</div>

<table class="comp-table">
<thead>
<tr><th>指标</th><th>{d1['date']}</th><th>{d2['date']}</th><th>变化</th><th>趋势</th></tr>
</thead>
<tbody>
<tr><td><b>睡眠</b></td><td>{s1:.2f}h</td><td>{s2:.2f}h</td><td>{'+' if changes['sleep'] > 0 else ''}{changes['sleep']}%</td><td>{'⬆️' if changes['sleep'] > 0 else '⬇️' if changes['sleep'] < 0 else '➡️'}</td></tr>
<tr><td><b>HRV</b></td><td>{d1['hrv']:.1f}ms</td><td>{d2['hrv']:.1f}ms</td><td class="{'positive' if changes['hrv'] > 0 else 'negative'}">{'+' if changes['hrv'] > 0 else ''}{changes['hrv']}%</td><td>{'⬆️' if changes['hrv'] > 0 else '⬇️' if changes['hrv'] < 0 else '➡️'}</td></tr>
<tr><td><b>步数</b></td><td>{d1['steps']:,}</td><td>{d2['steps']:,}</td><td class="{'positive' if changes['steps'] > 0 else 'negative'}">{'+' if changes['steps'] > 0 else ''}{changes['steps']}%</td><td>{'⬆️' if changes['steps'] > 0 else '⬇️' if changes['steps'] < 0 else '➡️'}</td></tr>
<tr><td><b>活动能量</b></td><td>{d1['active_kcal']:.1f}kcal</td><td>{d2['active_kcal']:.1f}kcal</td><td class="{'positive' if changes['active'] > 0 else 'negative'}">{'+' if changes['active'] > 0 else ''}{changes['active']}%</td><td>{'⬆️' if changes['active'] > 0 else '⬇️' if changes['active'] < 0 else '➡️'}</td></tr>
</tbody>
</table>

<div class="footer">
数据来源: Apple Health | 生成: {datetime.now().strftime('%Y-%m-%d')} | UTC+8
</div>
</div>
</body>
</html>"""
    return html

def html_to_pdf(html, output_path):
    """HTML转PDF"""
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.set_viewport_size({'width': 794, 'height': 1123})
        page.set_content(html)
        page.wait_for_timeout(2000)
        page.pdf(path=output_path, format='A4', print_background=True, margin={'top': '5mm', 'right': '5mm', 'bottom': '5mm', 'left': '5mm'})
        browser.close()

def main():
    day_before, yesterday = get_dates()
    print(f"生成报告: {day_before} 和 {yesterday}")
    print("\n【睡眠数据规则】从次日文件中提取（方案D：昨晚睡眠归今天）\n")
    
    # 提取数据
    print(f"提取 {day_before} 数据:")
    data1 = extract_data(day_before)
    
    print(f"\n提取 {yesterday} 数据:")
    data2 = extract_data(yesterday)
    
    if not data2:
        print(f"❌ 无法获取 {yesterday} 的数据")
        sys.exit(1)
    
    output_dir = '/Users/jimmylu/.openclaw/workspace/shared/health-reports/upload'
    os.makedirs(output_dir, exist_ok=True)
    
    # 生成单日报告
    print(f"\n生成单日报告: {yesterday}")
    html_daily = generate_daily_report(data2)
    if html_daily:
        pdf_path = f"{output_dir}/{yesterday}-report-zh.pdf"
        html_to_pdf(html_daily, pdf_path)
        print(f"✅ {pdf_path}")
    
    # 生成对比报告
    if data1:
        print(f"\n生成对比报告: {day_before} vs {yesterday}")
        html_comp = generate_comparison_report(data1, data2)
        if html_comp:
            pdf_path = f"{output_dir}/{day_before}-vs-{yesterday}-comparison-zh.pdf"
            html_to_pdf(html_comp, pdf_path)
            print(f"✅ {pdf_path}")
    
    print("\n🎉 所有报告生成完成!")

if __name__ == '__main__':
    main()
