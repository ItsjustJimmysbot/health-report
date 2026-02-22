#!/usr/bin/env python3
"""
V5.0 AI分析报告生成器 - Medical Dashboard 模板版
- 读取源数据（HealthAutoExport-YYYY-MM-DD.json）
- 严格真实值：缺失即'--'，不估算
- 仅在有运动时显示心率曲线
用法:
  python3 scripts/generate_v5_medical_dashboard.py <YYYY-MM-DD> < ai_analysis.json
"""
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from playwright.sync_api import sync_playwright

HOME = Path.home()
TEMPLATE_DIR = HOME / '.openclaw' / 'workspace-health' / 'templates'
OUTPUT_DIR = HOME / '.openclaw' / 'workspace' / 'shared' / 'health-reports' / 'upload'
HEALTH_DIR = HOME / '我的云端硬盘' / 'Health Auto Export' / 'Health Data'
WORKOUT_DIR = HOME / '我的云端硬盘' / 'Health Auto Export' / 'Workout Data'


def _parse_metrics(date_str: str):
    p = HEALTH_DIR / f'HealthAutoExport-{date_str}.json'
    if not p.exists():
        return {}
    data = json.loads(p.read_text())
    return {m.get('name'): m for m in data.get('data', {}).get('metrics', [])}


def _values(metrics: dict, name: str):
    m = metrics.get(name, {})
    arr = m.get('data', []) if isinstance(m, dict) else []
    vals = [x.get('qty') for x in arr if isinstance(x, dict) and x.get('qty') is not None]
    return vals


def _avg(vals):
    return (sum(vals) / len(vals)) if vals else None


def _sum(vals):
    return (sum(vals)) if vals else None


def _extract_sleep_hours(date_str: str):
    """严格按窗口取睡眠：当日20:00-次日12:00；使用 sleep_analysis 的 asleep/deep/core/rem/awake（单位 hr）。"""
    date = datetime.strptime(date_str, '%Y-%m-%d')
    next_date = (date + timedelta(days=1)).strftime('%Y-%m-%d')
    m1 = _parse_metrics(date_str)
    m2 = _parse_metrics(next_date)

    deep = core = rem = awake = total_asleep = 0.0

    def consume(metrics):
        nonlocal deep, core, rem, awake, total_asleep
        recs = metrics.get('sleep_analysis', {}).get('data', []) if metrics else []
        for row in recs:
            st = row.get('sleepStart') or row.get('startDate')
            if not st:
                continue
            try:
                dt = datetime.strptime(st[:19], '%Y-%m-%d %H:%M:%S')
            except Exception:
                continue
            if not (dt >= date.replace(hour=20, minute=0, second=0) and dt <= (date + timedelta(days=1)).replace(hour=12, minute=0, second=0)):
                continue

            # 单位 hr，严格使用真实字段
            deep += float(row.get('deep') or 0)
            core += float(row.get('core') or 0)
            rem += float(row.get('rem') or 0)
            awake += float(row.get('awake') or 0)
            total_asleep += float(row.get('asleep') or row.get('totalSleep') or 0)

    consume(m1)
    consume(m2)

    # total 优先用 asleep；若缺失再用阶段和
    total = total_asleep if total_asleep > 0 else (deep + core + rem + awake)

    return {
        'total': round(total, 2) if total > 0 else 0,
        'deep': round(deep, 2) if deep > 0 else 0,
        'core': round(core, 2) if core > 0 else 0,
        'rem': round(rem, 2) if rem > 0 else 0,
        'awake': round(awake, 2) if awake > 0 else 0,
    }


def load_data(date_str: str):
    metrics = _parse_metrics(date_str)
    if not metrics:
        raise FileNotFoundError(f'未找到源数据: {HEALTH_DIR}/HealthAutoExport-{date_str}.json')

    hrv_vals = _values(metrics, 'heart_rate_variability')
    rhr_vals = _values(metrics, 'resting_heart_rate')
    steps_vals = _values(metrics, 'step_count')
    dist_vals = _values(metrics, 'walking_running_distance')
    active_vals = _values(metrics, 'active_energy')
    spo2_vals = _values(metrics, 'blood_oxygen_saturation')
    flights_vals = _values(metrics, 'flights_climbed')
    stand_vals = _values(metrics, 'apple_stand_time')
    basal_vals = _values(metrics, 'basal_energy_burned')
    resp_vals = _values(metrics, 'respiratory_rate')

    # 能量通常是kJ，转kcal
    active_kcal = (_sum(active_vals) / 4.184) if active_vals else None
    basal_kcal = (_sum(basal_vals) / 4.184) if basal_vals else None

    # 血氧智能单位
    spo2_avg = _avg(spo2_vals)
    if spo2_avg is None:
        spo2 = None
    else:
        spo2 = spo2_avg if spo2_avg > 1 else spo2_avg * 100

    # 运动
    workouts = []
    wp = WORKOUT_DIR / f'HealthAutoExport-{date_str}.json'
    if wp.exists():
        wd = json.loads(wp.read_text())
        for w in wd.get('data', {}).get('workouts', []):
            timeline = []
            for h in (w.get('heartRateData') or []):
                a = h.get('avg') if h.get('avg') is not None else h.get('Avg')
                m = h.get('max') if h.get('max') is not None else h.get('Max')
                timeline.append({
                    'time': (h.get('date', '')[11:16] if h.get('date') else ''),
                    'avg': float(a) if a is not None else None,
                    'max': float(m) if m is not None else None,
                })

            avgs = [x['avg'] for x in timeline if x.get('avg') is not None]
            mxs = [x['max'] for x in timeline if x.get('max') is not None]
            avg_hr = round(sum(avgs) / len(avgs)) if avgs else None
            max_hr = int(max(mxs)) if mxs else None

            # duration 兼容秒/分钟
            dur_raw = w.get('duration')
            if isinstance(dur_raw, (int, float)):
                duration_min = (dur_raw / 60.0) if dur_raw > 200 else float(dur_raw)
            else:
                duration_min = 0.0

            # 能量兼容数字或对象；源数据通常是 kJ，转换为 kcal
            e = w.get('activeEnergyBurned')
            if isinstance(e, dict):
                qty = e.get('qty') or 0
                unit = (e.get('units') or '').lower()
                energy_kcal = (qty / 4.184) if 'kj' in unit else qty
            else:
                energy_kcal = e or 0

            workouts.append({
                'name': w.get('workoutActivityType') or w.get('name') or '运动',
                'start': (w.get('startDate') or '')[:16].replace('T', ' '),
                'duration_min': duration_min,
                'energy_kcal': float(energy_kcal) if isinstance(energy_kcal, (int, float)) else 0,
                'avg_hr': int(avg_hr) if avg_hr is not None else None,
                'max_hr': int(max_hr) if max_hr is not None else None,
                'hr_timeline': [x for x in timeline if x.get('avg') is not None or x.get('max') is not None]
            })

    data = {
        'date': date_str,
        'hrv': {'value': round(_avg(hrv_vals), 1) if hrv_vals else None, 'points': len(hrv_vals)},
        'resting_hr': {'value': round(_avg(rhr_vals)) if rhr_vals else None},
        'steps': int(_sum(steps_vals)) if steps_vals else None,
        'distance': round(_sum(dist_vals), 2) if dist_vals else None,
        'active_energy': int(round(active_kcal)) if active_kcal is not None else None,
        'spo2': round(spo2, 1) if spo2 is not None else None,
        'flights_climbed': int(_sum(flights_vals)) if flights_vals else None,
        'apple_stand_time': int(_sum(stand_vals)) if stand_vals else None,  # 分钟
        'basal_energy_burned': int(round(basal_kcal)) if basal_kcal is not None else None,
        'respiratory_rate': round(_avg(resp_vals), 1) if resp_vals else None,
        'sleep': _extract_sleep_hours(date_str),
        'workouts': workouts,
        'has_workout': len(workouts) > 0,
    }
    return data


def real_text(v, fmt):
    return fmt(v) if v is not None else '--'


def badge(score):
    if score >= 80: return 'badge-excellent', '优秀'
    if score >= 60: return 'badge-good', '良好'
    if score >= 40: return 'badge-average', '一般'
    return 'badge-poor', '需改善'


def gen_rating_from_value(v):
    return ('rating-good', '正常') if v != '--' else ('rating-average', '--')


def generate_hr_svg(hr_data):
    if not hr_data:
        return '<div style="color:#999;text-align:center;padding:20px;">无心率数据</div>'

    avg = [h['avg'] for h in hr_data if h.get('avg') is not None]
    mx = [h['max'] for h in hr_data if h.get('max') is not None]
    if not avg and not mx:
        return '<div style="color:#999;text-align:center;padding:20px;">无心率数据</div>'

    vals = (avg + mx)
    y_min = (min(vals) // 10 - 1) * 10
    y_max = (max(vals) // 10 + 2) * 10
    if y_max == y_min:
        y_max = y_min + 10

    n = len(hr_data)
    pts_avg, pts_max = [], []
    for i, h in enumerate(hr_data):
        x = 12 + i * (476 / max(n - 1, 1))
        a = h.get('avg', vals[0])
        m = h.get('max', a)
        y_a = 88 - ((a - y_min) / (y_max - y_min)) * 76
        y_m = 88 - ((m - y_min) / (y_max - y_min)) * 76
        pts_avg.append(f"{x:.1f},{y_a:.1f}")
        pts_max.append(f"{x:.1f},{y_m:.1f}")

    return f'''<div class="hr-chart-wrapper"><div class="hr-chart-title"><span>📈 心率变化</span><div class="hr-chart-legend"><div class="hr-legend-item"><div class="hr-legend-dot avg"></div><span>平均</span></div><div class="hr-legend-item"><div class="hr-legend-dot max"></div><span>最高</span></div></div></div><div class="hr-chart-container"><svg class="hr-chart-svg" viewBox="0 0 500 100" preserveAspectRatio="none"><polyline fill="none" stroke="#3B82F6" stroke-width="2" points="{' '.join(pts_avg)}" /><polyline fill="none" stroke="#EF4444" stroke-width="1.5" stroke-dasharray="3,2" points="{' '.join(pts_max)}" /></svg></div></div>'''


def generate_report(date_str, ai_analysis, template):
    data = load_data(date_str)
    html = template

    # 基础信息
    html = html.replace('{{DATE}}', date_str)
    html = html.replace('{{DAY}}', date_str.split('-')[2])
    html = html.replace('{{MONTH_YEAR}}', f"{date_str.split('-')[0]}年{int(date_str.split('-')[1])}月")
    html = html.replace('{{HEADER_SUBTITLE}}', f'{date_str} · Apple Health · AI分析版')
    html = html.replace('{{DATA_SOURCE}}', 'Apple Health')

    # 评分
    sleep_hours = data.get('sleep', {}).get('total', 0) or 0
    hrv_v = data['hrv']['value'] or 0
    rhr_v = data['resting_hr']['value'] or 999
    steps_v = data['steps'] or 0
    active_v = data['active_energy'] or 0

    recovery = min(100, 70 + (10 if hrv_v > 50 else 0) + (10 if rhr_v < 65 else 0) + (10 if sleep_hours > 7 else 0))
    sleep_score = 30 if sleep_hours < 6 else 50 if sleep_hours < 7 else 70 if sleep_hours < 8 else 80
    exercise = min(100, 50 + (15 if data.get('has_workout') else 0) + (10 if active_v > 500 else 0) + min(25, steps_v // 400))

    rc, rt = badge(recovery)
    sc, st = badge(sleep_score)
    ec, et = badge(exercise)

    html = html.replace('{{SCORE_RECOVERY}}', str(recovery)).replace('{{BADGE_RECOVERY_CLASS}}', rc).replace('{{BADGE_RECOVERY_TEXT}}', rt)
    html = html.replace('{{SCORE_SLEEP}}', str(sleep_score)).replace('{{BADGE_SLEEP_CLASS}}', sc).replace('{{BADGE_SLEEP_TEXT}}', st)
    html = html.replace('{{SCORE_EXERCISE}}', str(exercise)).replace('{{BADGE_EXERCISE_CLASS}}', ec).replace('{{BADGE_EXERCISE_TEXT}}', et)

    # 指标（严格真实值）
    m1 = real_text(data['hrv']['value'], lambda v: f"{v:.1f} ms")
    html = html.replace('{{METRIC1_VALUE}}', m1).replace('{{METRIC1_RATING_CLASS}}', 'rating-good' if data['hrv']['value'] and data['hrv']['value'] > 50 else 'rating-average').replace('{{METRIC1_RATING}}', '良好' if data['hrv']['value'] and data['hrv']['value'] > 50 else '一般').replace('{{METRIC1_ANALYSIS}}', ai_analysis.get('hrv', ''))

    m2 = real_text(data['resting_hr']['value'], lambda v: f"{int(v)} bpm")
    html = html.replace('{{METRIC2_VALUE}}', m2).replace('{{METRIC2_RATING_CLASS}}', 'rating-excellent' if data['resting_hr']['value'] and data['resting_hr']['value'] < 60 else 'rating-good').replace('{{METRIC2_RATING}}', '优秀' if data['resting_hr']['value'] and data['resting_hr']['value'] < 60 else '良好').replace('{{METRIC2_ANALYSIS}}', ai_analysis.get('resting_hr', ''))

    m3 = real_text(data['steps'], lambda v: f"{int(v):,}")
    html = html.replace('{{METRIC3_VALUE}}', m3).replace('{{METRIC3_RATING_CLASS}}', 'rating-good' if data['steps'] and data['steps'] > 8000 else 'rating-average').replace('{{METRIC3_RATING}}', '良好' if data['steps'] and data['steps'] > 8000 else '一般').replace('{{METRIC3_ANALYSIS}}', ai_analysis.get('steps', ''))

    m4 = real_text(data['distance'], lambda v: f"{v:.1f} km")
    c4, t4 = gen_rating_from_value(m4)
    html = html.replace('{{METRIC4_VALUE}}', m4).replace('{{METRIC4_RATING_CLASS}}', c4).replace('{{METRIC4_RATING}}', t4).replace('{{METRIC4_ANALYSIS}}', ai_analysis.get('distance', ''))

    m5 = real_text(data['active_energy'], lambda v: f"{int(v)} kcal")
    c5, t5 = gen_rating_from_value(m5)
    html = html.replace('{{METRIC5_VALUE}}', m5).replace('{{METRIC5_RATING_CLASS}}', c5).replace('{{METRIC5_RATING}}', t5).replace('{{METRIC5_ANALYSIS}}', ai_analysis.get('active_energy', ''))

    m6 = real_text(data['flights_climbed'], lambda v: f"{int(v)} 层")
    c6, t6 = gen_rating_from_value(m6)
    html = html.replace('{{METRIC6_VALUE}}', m6).replace('{{METRIC6_RATING_CLASS}}', c6).replace('{{METRIC6_RATING}}', t6).replace('{{METRIC6_ANALYSIS}}', ai_analysis.get('flights', ''))

    m7 = real_text(data['apple_stand_time'], lambda v: f"{int(v)//60}h {int(v)%60}min")
    c7, t7 = gen_rating_from_value(m7)
    html = html.replace('{{METRIC7_VALUE}}', m7).replace('{{METRIC7_RATING_CLASS}}', c7).replace('{{METRIC7_RATING}}', t7).replace('{{METRIC7_ANALYSIS}}', ai_analysis.get('stand', ''))

    m8 = real_text(data['spo2'], lambda v: f"{v:.1f}%")
    c8, t8 = gen_rating_from_value(m8)
    html = html.replace('{{METRIC8_VALUE}}', m8).replace('{{METRIC8_RATING_CLASS}}', c8).replace('{{METRIC8_RATING}}', t8).replace('{{METRIC8_ANALYSIS}}', ai_analysis.get('spo2', ''))

    m9 = real_text(data['basal_energy_burned'], lambda v: f"{int(v):,} kcal")
    c9, t9 = gen_rating_from_value(m9)
    html = html.replace('{{METRIC9_VALUE}}', m9).replace('{{METRIC9_RATING_CLASS}}', c9).replace('{{METRIC9_RATING}}', t9).replace('{{METRIC9_ANALYSIS}}', ai_analysis.get('basal', ''))

    m10 = real_text(data['respiratory_rate'], lambda v: f"{float(v):.1f} 次/分")
    c10, t10 = gen_rating_from_value(m10)
    html = html.replace('{{METRIC10_VALUE}}', m10).replace('{{METRIC10_RATING_CLASS}}', c10).replace('{{METRIC10_RATING}}', t10).replace('{{METRIC10_ANALYSIS}}', ai_analysis.get('respiratory', ''))

    # 睡眠
    html = html.replace('{{SLEEP_STATUS}}', '数据不足' if sleep_hours < 3 else '正常')
    alert = f'<div class="sleep-alert warning"><div class="alert-icon">⚠️</div><div class="alert-content"><h4>睡眠严重不足</h4><p>总睡眠时长{sleep_hours:.1f}小时，远低于7-9小时推荐标准。</p></div></div>' if sleep_hours < 6 else ''
    html = html.replace('{{SLEEP_ALERT}}', alert)
    html = html.replace('{{SLEEP_TOTAL}}', f"{sleep_hours:.1f}")
    html = html.replace('{{SLEEP_HOURS}}', f"{sleep_hours:.1f}")

    s = data.get('sleep', {})
    t = max(s.get('total', 0), 0.1)
    html = html.replace('{{SLEEP_DEEP}}', f"{s.get('deep', 0):.1f}")
    html = html.replace('{{SLEEP_CORE}}', f"{s.get('core', 0):.1f}")
    html = html.replace('{{SLEEP_REM}}', f"{s.get('rem', 0):.1f}")
    html = html.replace('{{SLEEP_AWAKE}}', f"{s.get('awake', 0):.1f}")
    html = html.replace('{{SLEEP_DEEP_PCT}}', str(int((s.get('deep', 0) / t) * 100)))
    html = html.replace('{{SLEEP_CORE_PCT}}', str(int((s.get('core', 0) / t) * 100)))
    html = html.replace('{{SLEEP_REM_PCT}}', str(int((s.get('rem', 0) / t) * 100)))
    html = html.replace('{{SLEEP_AWAKE_PCT}}', str(int((s.get('awake', 0) / t) * 100)))
    html = html.replace('{{SLEEP_ANALYSIS_TEXT}}', ai_analysis.get('sleep', ''))

    # 运动 section（有运动才画图）
    if data.get('has_workout') and data.get('workouts'):
        w = data['workouts'][0]
        workout_section = f'''<div class="workout-section no-break">
  <div class="section-header"><div class="section-title"><span class="section-icon">🏃</span>运动记录 - {w['name']}</div></div>
  <div class="workout-header"><div class="workout-type"><div class="workout-icon">💪</div><div><div class="workout-name">{w['name']}</div><div class="workout-time">{(w['start'][11:16] if len(w['start'])>16 else w['start'])}</div></div></div><span class="badge badge-good">已完成</span></div>
  <div class="workout-stats">
    <div class="stat-box"><div class="stat-value">{int(w['duration_min']) if w['duration_min'] else '--'}</div><div class="stat-label">分钟</div></div>
    <div class="stat-box"><div class="stat-value">{int(w['energy_kcal']) if w['energy_kcal'] else '--'}</div><div class="stat-label">千卡</div></div>
    <div class="stat-box"><div class="stat-value">{w['avg_hr'] if w['avg_hr'] is not None else '--'}</div><div class="stat-label">平均心率</div></div>
    <div class="stat-box"><div class="stat-value">{w['max_hr'] if w['max_hr'] is not None else '--'}</div><div class="stat-label">最高心率</div></div>
  </div>
  {generate_hr_svg(w.get('hr_timeline', []))}
  <div class="workout-analysis"><div class="workout-analysis-title">运动AI详细分析</div><div class="workout-analysis-text">{ai_analysis.get('workout','')}</div></div>
</div>'''
    else:
        workout_section = '''<div class="workout-section no-break"><div class="section-header"><div class="section-title"><span class="section-icon">🏃</span>运动记录</div></div><div class="workout-analysis"><div class="workout-analysis-title">今日无结构化运动</div><div class="workout-analysis-text">今日未记录到结构化运动数据，因此不展示心率变化曲线。</div></div></div>'''
    html = html.replace('{{WORKOUT_SECTION}}', workout_section)

    # AI建议
    p = ai_analysis.get('priority', {})
    html = html.replace('{{AI1_TITLE}}', p.get('title', ''))
    html = html.replace('{{AI1_PROBLEM}}', p.get('problem', ''))
    html = html.replace('{{AI1_ACTION}}', p.get('action', ''))
    html = html.replace('{{AI1_EXPECTATION}}', p.get('expectation', ''))

    html = html.replace('{{AI2_TITLE}}', ai_analysis.get('ai2_title', '增加日常活动'))
    html = html.replace('{{AI2_PROBLEM}}', ai_analysis.get('ai2_problem', ''))
    html = html.replace('{{AI2_ACTION}}', ai_analysis.get('ai2_action', ''))
    html = html.replace('{{AI2_EXPECTATION}}', ai_analysis.get('ai2_expectation', ''))

    html = html.replace('{{AI3_TITLE}}', ai_analysis.get('ai3_title', '饮食优化'))
    html = html.replace('{{AI3_PROBLEM}}', ai_analysis.get('ai3_problem', ''))
    html = html.replace('{{AI3_ACTION}}', ai_analysis.get('ai3_action', ''))
    html = html.replace('{{AI3_EXPECTATION}}', ai_analysis.get('ai3_expectation', ''))

    html = html.replace('{{AI4_BREAKFAST}}', ai_analysis.get('breakfast', ''))
    html = html.replace('{{AI4_LUNCH}}', ai_analysis.get('lunch', ''))
    html = html.replace('{{AI4_DINNER}}', ai_analysis.get('dinner', ''))
    html = html.replace('{{AI4_SNACK}}', ai_analysis.get('snack', ''))

    return html


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('用法: python3 scripts/generate_v5_medical_dashboard.py <YYYY-MM-DD> < ai_analysis.json')
        sys.exit(1)

    date_str = sys.argv[1]
    ai_analysis = json.load(sys.stdin)

    with open(TEMPLATE_DIR / 'DAILY_TEMPLATE_MEDICAL_V2.html', 'r', encoding='utf-8') as f:
        template = f.read()

    html = generate_report(date_str, ai_analysis, template)

    html_path = OUTPUT_DIR / f'{date_str}-daily-v5-medical.html'
    html_path.write_text(html, encoding='utf-8')

    pdf_path = OUTPUT_DIR / f'{date_str}-daily-v5-medical.pdf'
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(f'file://{html_path}')
        page.wait_for_timeout(2500)
        page.pdf(path=str(pdf_path), format='A4', print_background=True,
                 margin={'top': '10mm', 'bottom': '10mm', 'left': '10mm', 'right': '10mm'})
        browser.close()

    print(f'✅ 报告已生成: {pdf_path}')
    print(f'   大小: {pdf_path.stat().st_size / 1024:.0f} KB')
