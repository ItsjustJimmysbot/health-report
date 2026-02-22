#!/usr/bin/env python3
"""
V5.0 Report Generator (single standard entry)
- 源数据读取：HealthAutoExport/Workout Data
- 严格真实值：缺失即 '--'，不估算
- 仅有运动时显示心率曲线

兼容两种用法：
1) 旧模式（传入data.json）
   python3 scripts/generate_report_v5_ai.py data.json [template.html] [out.html]
2) 新模式（传入日期，AI分析从stdin JSON读取）
   python3 scripts/generate_report_v5_ai.py 2026-02-18 [template.html] [out.html] < ai_analysis.json
"""
import json
import os
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

# GUARD: Date mode requires AI analysis from stdin (no tty, no /tmp)
if len(sys.argv) > 1 and re.match(r'^\d{4}-\d{2}-\d{2}$', sys.argv[1]):
    if sys.stdin.isatty():
        print("ERROR: Date mode requires AI analysis JSON from stdin", file=sys.stderr)
        sys.exit(1)

HOME = Path.home()
HEALTH_DIR = HOME / '我的云端硬盘' / 'Health Auto Export' / 'Health Data'
WORKOUT_DIR = HOME / '我的云端硬盘' / 'Health Auto Export' / 'Workout Data'


def calc_recovery_score(hrv, resting_hr, sleep_hours):
    score = 70
    if hrv is not None and hrv > 50: score += 10
    if resting_hr is not None and resting_hr < 65: score += 10
    if sleep_hours is not None and sleep_hours >= 7: score += 10
    return min(100, score)


def calc_sleep_score(sleep_hours):
    if not sleep_hours: return 0
    if sleep_hours < 6: return 30
    if sleep_hours < 7: return 50
    if sleep_hours < 8: return 70
    return 80


def calc_exercise_score(steps, has_workout, energy_kcal):
    score = 50
    if steps and steps > 5000: score += 10
    if steps and steps > 8000: score += 10
    if steps and steps > 10000: score += 10
    if has_workout: score += 15
    if energy_kcal and energy_kcal > 500: score += 10
    return min(100, score)


def get_rating_class(score):
    if score >= 80: return 'rating-excellent', 'badge-excellent', '优秀'
    if score >= 60: return 'rating-good', 'badge-good', '良好'
    if score >= 40: return 'rating-average', 'badge-average', '一般'
    return 'rating-poor', 'badge-poor', '需改善'


def format_workout_time_range(start_str, duration_min):
    """Return HH:MM-HH:MM if possible."""
    try:
        from datetime import datetime, timedelta
        if not start_str:
            return '--'
        # supports 'YYYY-MM-DD HH:MM'
        dt=datetime.strptime(start_str[:16], '%Y-%m-%d %H:%M')
        end=dt + timedelta(minutes=float(duration_min or 0))
        return f"{dt.strftime('%H:%M')}-{end.strftime('%H:%M')}"
    except Exception:
        return (start_str.split(' ')[1][:5] if isinstance(start_str,str) and ' ' in start_str else '--')


def _parse_metrics(date_str: str):
    fp = HEALTH_DIR / f'HealthAutoExport-{date_str}.json'
    if not fp.exists():
        return {}
    d = json.loads(fp.read_text())
    return {m.get('name'): m for m in d.get('data', {}).get('metrics', [])}


def _vals(metrics, name):
    m = metrics.get(name, {})
    arr = m.get('data', []) if isinstance(m, dict) else []
    return [x.get('qty') for x in arr if isinstance(x, dict) and x.get('qty') is not None]


def _avg(v):
    return (sum(v) / len(v)) if v else None


def _sum(v):
    return sum(v) if v else None


def _sleep_from_source(date_str: str):
    date = datetime.strptime(date_str, '%Y-%m-%d')
    next_date = (date + timedelta(days=1)).strftime('%Y-%m-%d')
    m1 = _parse_metrics(date_str)
    m2 = _parse_metrics(next_date)

    deep = core = rem = awake = asleep = 0.0

    def consume(metrics):
        nonlocal deep, core, rem, awake, asleep
        recs = metrics.get('sleep_analysis', {}).get('data', []) if metrics else []
        for r in recs:
            st = r.get('sleepStart') or r.get('startDate')
            if not st:
                continue
            try:
                dt = datetime.strptime(st[:19], '%Y-%m-%d %H:%M:%S')
            except Exception:
                continue
            if not (dt >= date.replace(hour=20, minute=0, second=0) and dt <= (date + timedelta(days=1)).replace(hour=12, minute=0, second=0)):
                continue
            # units=hr, use explicit fields (no qty)
            deep += float(r.get('deep') or 0)
            core += float(r.get('core') or 0)
            rem += float(r.get('rem') or 0)
            awake += float(r.get('awake') or 0)
            asleep += float(r.get('asleep') or r.get('totalSleep') or 0)

    consume(m1)
    consume(m2)
    total = asleep if asleep > 0 else (deep + core + rem + awake)
    return {
        'total_hours': round(total, 2) if total > 0 else 0,
        'deep_hours': round(deep, 2) if deep > 0 else 0,
        'core_hours': round(core, 2) if core > 0 else 0,
        'rem_hours': round(rem, 2) if rem > 0 else 0,
        'awake_hours': round(awake, 2) if awake > 0 else 0,
    }


def _workout_from_source(date_str: str):
    fp = WORKOUT_DIR / f'HealthAutoExport-{date_str}.json'
    if not fp.exists():
        return []
    d = json.loads(fp.read_text())
    out = []
    for w in d.get('data', {}).get('workouts', []):
        timeline = []
        for h in (w.get('heartRateData') or []):
            a = h.get('avg') if h.get('avg') is not None else h.get('Avg')
            m = h.get('max') if h.get('max') is not None else h.get('Max')
            timeline.append({
                'date': h.get('date', ''),
                'Avg': float(a) if a is not None else None,
                'Max': float(m) if m is not None else None,
            })
        avgs = [x['Avg'] for x in timeline if x.get('Avg') is not None]
        maxs = [x['Max'] for x in timeline if x.get('Max') is not None]
        avg_hr = round(sum(avgs) / len(avgs)) if avgs else None
        max_hr = int(max(maxs)) if maxs else None

        e = w.get('activeEnergyBurned')
        if isinstance(e, dict):
            qty = e.get('qty') or 0
            unit = (e.get('units') or '').lower()
            energy_kcal = qty / 4.184 if 'kj' in unit else qty
        else:
            energy_kcal = e or 0

        dur_raw = w.get('duration')
        if isinstance(dur_raw, (int, float)):
            duration_min = (dur_raw / 60.0) if dur_raw > 200 else float(dur_raw)
        else:
            duration_min = 0

        out.append({
            'name': w.get('workoutActivityType') or w.get('name') or '运动',
            'start': ((w.get('start') or w.get('startDate') or '')[:16].replace('T', ' ')),
            'duration_min': duration_min,
            'energy_kcal': round(float(energy_kcal), 1),
            'avg_hr': avg_hr,
            'max_hr': max_hr,
            'hr_data': timeline,
            'analysis': ''
        })
    return out


def build_data_from_source(date_str: str, ai: dict):
    m = _parse_metrics(date_str)
    if not m:
        raise FileNotFoundError(f'未找到源数据: HealthAutoExport-{date_str}.json')

    active_kj = _sum(_vals(m, 'active_energy'))
    basal_kj = _sum(_vals(m, 'basal_energy_burned'))
    spo2_raw = _avg(_vals(m, 'blood_oxygen_saturation'))
    spo2 = None if spo2_raw is None else (spo2_raw if spo2_raw > 1 else spo2_raw * 100)

    data = {
        'date': date_str,
        'data_source': 'Apple Health',
        'hrv': {
            'value': round(_avg(_vals(m, 'heart_rate_variability')), 1) if _vals(m, 'heart_rate_variability') else None,
            'points': len(_vals(m, 'heart_rate_variability')),
            'analysis': ai.get('hrv', '')
        },
        'resting_hr': {
            'value': round(_avg(_vals(m, 'resting_heart_rate'))) if _vals(m, 'resting_heart_rate') else None,
            'analysis': ai.get('resting_hr', '')
        },
        'steps': {
            'value': int(_sum(_vals(m, 'step_count')) or 0),
            'analysis': ai.get('steps', '')
        },
        'walking_distance': {
            'value': round(_sum(_vals(m, 'walking_running_distance')), 2) if _vals(m, 'walking_running_distance') else None,
            'points': len(_vals(m, 'walking_running_distance')),
            'analysis': ai.get('distance', '')
        },
        'active_energy': {
            'value': round(active_kj / 4.184, 1) if active_kj is not None else None,
            'analysis': ai.get('active_energy', '')
        },
        'flights_climbed': {
            'value': int(_sum(_vals(m, 'flights_climbed'))) if _vals(m, 'flights_climbed') else None,
            'analysis': ai.get('flights', '')
        },
        'stand_time': {
            'value': int(_sum(_vals(m, 'apple_stand_time'))) if _vals(m, 'apple_stand_time') else None,
            'analysis': ai.get('stand', '')
        },
        'spo2': {
            'value': round(spo2, 1) if spo2 is not None else None,
            'analysis': ai.get('spo2', '')
        },
        'basal_energy': {
            'value': round(basal_kj / 4.184, 1) if basal_kj is not None else None,
            'analysis': ai.get('basal', '')
        },
        'respiratory_rate': {
            'value': round(_avg(_vals(m, 'respiratory_rate')), 1) if _vals(m, 'respiratory_rate') else None,
            'analysis': ai.get('respiratory', '')
        },
        'sleep': _sleep_from_source(date_str) | {'analysis': ai.get('sleep', '')},
        'workouts': _workout_from_source(date_str),
        'ai_recommendations': {
            'high_priority': {
                'title': ai.get('priority', {}).get('title', ''),
                'problem': ai.get('priority', {}).get('problem', ''),
                'action': ai.get('priority', {}).get('action', ''),
                'expected': ai.get('priority', {}).get('expectation', ''),
            },
            'medium_priority': {
                'title': ai.get('ai2_title', ''),
                'problem': ai.get('ai2_problem', ''),
                'action': ai.get('ai2_action', ''),
                'expected': ai.get('ai2_expectation', ''),
            },
            'routine': {
                'title': ai.get('ai3_title', ''),
                'diet': ai.get('ai3_action', ''),
                'schedule': ai.get('ai3_expectation', ''),
            },
            'summary': {
                'title': '个性化饮食方案',
                'advantages': ai.get('breakfast', ''),
                'risks': ai.get('lunch', ''),
                'conclusion': ai.get('dinner', ''),
                'plan': ai.get('snack', ''),
            }
        }
    }

    # 给 workout 注入分析
    if data['workouts']:
        data['workouts'][0]['analysis'] = ai.get('workout', '')

    # MANDATORY VALIDATION: Check all analyses reference actual data
    # Map data keys to AI JSON keys (they may differ)
    key_mapping = {
        'hrv': 'hrv',
        'resting_hr': 'resting_hr', 
        'steps': 'steps',
        'distance': 'distance',
        'active_energy': 'active_energy',
        'spo2': 'spo2',
        'respiratory_rate': 'respiratory',  # JSON uses 'respiratory'
        'sleep': 'sleep',
    }
    errors = []
    checks = [
        ('hrv', data['hrv']['value'], 'ms'),
        ('resting_hr', data['resting_hr']['value'], 'bpm'),
        ('steps', data['steps']['value'], '步'),
        ('distance', data['walking_distance']['value'], 'km'),
        ('active_energy', data['active_energy']['value'], 'kcal'),
        ('spo2', data['spo2']['value'], '%'),
        ('respiratory_rate', data['respiratory_rate']['value'], '次/分'),
        ('sleep', data['sleep']['total_hours'], '小时'),
    ]
    for data_key, value, unit in checks:
        ai_key = key_mapping.get(data_key, data_key)
        analysis = str(ai.get(ai_key, ''))
        if value is None:
            continue
        # Check raw value, formatted value (with comma), and 1-decimal format
        str_val = str(value)
        fmt_val = f"{value:,}" if isinstance(value, int) else str_val
        dec_val = f"{value:.1f}" if isinstance(value, float) else str_val
        
        if str_val not in analysis and fmt_val not in analysis and dec_val not in analysis:
            errors.append(f"{ai_key} analysis missing data reference: expected {value}{unit}")
    
    # Check recommendation structure
    rec = ai.get('priority', {})
    if not all([rec.get('title'), rec.get('problem'), rec.get('action')]):
        errors.append("high_priority recommendation incomplete (need title, problem, action)")
    if not ai.get('ai2_title'):
        errors.append("medium_priority (ai2) missing")
    if not ai.get('ai3_title'):
        errors.append("routine (ai3) missing")
    if not all([ai.get('breakfast'), ai.get('lunch'), ai.get('dinner')]):
        errors.append("diet plan incomplete (need breakfast, lunch, dinner)")
    
    # CRITICAL: Verify no "data missing" claims when data exists (or vice versa)
    # Map AI JSON keys to data keys
    missing_data_checks = [
        ('flights', 'flights_climbed', '爬楼层数'),
        ('stand', 'stand_time', '站立时间'),
        ('basal', 'basal_energy', '静息能量'),
    ]
    for ai_key, data_key, chinese_name in missing_data_checks:
        value = data[data_key]['value']
        analysis = str(ai.get(ai_key, ''))
        has_data = value is not None and value > 0
        claims_missing = '缺失' in analysis or ('无' in analysis and '无爬楼' not in analysis and '无运动' not in analysis) or '没有' in analysis or '不存在' in analysis
        
        if has_data and claims_missing:
            errors.append(f"CRITICAL: {chinese_name}分析说'数据缺失'，但实际有数据: {value}")
        if not has_data and not claims_missing and analysis and len(analysis) > 10 and '无' not in analysis:
            errors.append(f"CRITICAL: {chinese_name}实际无数据，但分析未说明缺失")
    
    if errors:
        print("VALIDATION FAILED:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        print("\nAI analysis must reference actual data values and include all sections.", file=sys.stderr)
        sys.exit(1)

    return data


def generate_hr_chart(workout):
    if not workout:
        return ''
    hr_data = workout.get('hr_data', [])
    if not hr_data:
        return ''

    times, avg_hrs, max_hrs = [], [], []
    for hr in hr_data:
        time_str = hr.get('date', '').split(' ')[1][:5] if hr.get('date') else ''
        a = hr.get('Avg')
        m = hr.get('Max')
        if time_str and a is not None and m is not None:
            times.append(time_str)
            avg_hrs.append(round(a))
            max_hrs.append(round(m))

    if len(times) < 3:
        return ''

    # 边界安全：x不贴边，y留上下边距
    sampled_idx = list(range(0, len(times), 2))
    labels = [times[i] for i in sampled_idx]
    avg_vals = [avg_hrs[i] for i in sampled_idx]
    max_vals = [max_hrs[i] for i in sampled_idx]

    times_str = ', '.join([f"'{t}'" for t in labels])
    avg_str = ', '.join(map(str, avg_vals))
    max_str = ', '.join(map(str, max_vals))

    y_min = max(0, min(avg_vals + max_vals) - 10)
    y_max = max(avg_vals + max_vals) + 10

    return f'''<div style="height:150px;"><canvas id="hrChart"></canvas></div>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<script>
new Chart(document.getElementById('hrChart'), {{
  type: 'line',
  data: {{
    labels: [{times_str}],
    datasets: [
      {{label:'平均心率', data:[{avg_str}], borderColor:'#667eea', backgroundColor:'rgba(102,126,234,0.1)', tension:0.3, fill:true, pointRadius:2, clip:10}},
      {{label:'最高心率', data:[{max_str}], borderColor:'#dc2626', backgroundColor:'rgba(220,38,38,0.05)', tension:0.3, fill:false, pointRadius:2, clip:10}}
    ]
  }},
  options: {{
    responsive:true, maintainAspectRatio:false,
    plugins:{{legend:{{display:true, position:'top', labels:{{font:{{size:8}}, boxWidth:10}}}}}},
    scales:{{ y:{{min:{y_min}, max:{y_max}, ticks:{{font:{{size:7}}}}}}, x:{{ticks:{{font:{{size:7}}, maxRotation:45}}}} }}
  }}
}});
</script>'''


def _txt(v, f):
    return f(v) if v is not None else '--'


def generate_report(data, template_path, output_path):
    html = Path(template_path).read_text(encoding='utf-8')

    sleep_hours = data['sleep']['total_hours'] if data.get('sleep') else 0
    recovery_score = calc_recovery_score(data['hrv']['value'], data['resting_hr']['value'], sleep_hours)
    sleep_score = calc_sleep_score(sleep_hours)

    has_workout = len(data.get('workouts', [])) > 0
    workout_energy = data['workouts'][0]['energy_kcal'] if has_workout else 0
    exercise_score = calc_exercise_score(data['steps']['value'], has_workout, workout_energy)

    rr, rb, rt = get_rating_class(recovery_score)
    sr, sb, st = get_rating_class(sleep_score)
    er, eb, et = get_rating_class(exercise_score)

    sleep_deep = data['sleep'].get('deep_hours', 0)
    sleep_core = data['sleep'].get('core_hours', 0)
    sleep_rem = data['sleep'].get('rem_hours', 0)
    sleep_awake = data['sleep'].get('awake_hours', 0)

    workout = data['workouts'][0] if has_workout else None
    hr_chart = generate_hr_chart(workout)

    rec = data.get('ai_recommendations', {})
    high = rec.get('high_priority', {})
    medium = rec.get('medium_priority', {})
    routine = rec.get('routine', {})
    summary = rec.get('summary', {})

    replacements = {
        '{{DATE}}': data['date'],
        '{{HEADER_SUBTITLE}}': f"{data['date']} 健康数据分析报告",

        '{{SCORE_RECOVERY}}': str(recovery_score), '{{BADGE_RECOVERY_CLASS}}': rb, '{{BADGE_RECOVERY_TEXT}}': rt,
        '{{SCORE_SLEEP}}': str(sleep_score), '{{BADGE_SLEEP_CLASS}}': sb, '{{BADGE_SLEEP_TEXT}}': st,
        '{{SCORE_EXERCISE}}': str(exercise_score), '{{BADGE_EXERCISE_CLASS}}': eb, '{{BADGE_EXERCISE_TEXT}}': et,

        '{{METRIC1_VALUE}}': _txt(data['hrv']['value'], lambda v: f"{v:.1f}ms ({data['hrv']['points']}点)"),
        '{{METRIC1_RATING_CLASS}}': 'rating-good' if (data['hrv']['value'] or 0) > 50 else 'rating-average',
        '{{METRIC1_RATING}}': '良好' if (data['hrv']['value'] or 0) > 50 else '一般',
        '{{METRIC1_ANALYSIS}}': data['hrv'].get('analysis', '暂无分析'),

        '{{METRIC2_VALUE}}': _txt(data['resting_hr']['value'], lambda v: f"{int(v)}bpm"),
        '{{METRIC2_RATING_CLASS}}': 'rating-excellent' if (data['resting_hr']['value'] or 999) < 60 else 'rating-good',
        '{{METRIC2_RATING}}': '优秀' if (data['resting_hr']['value'] or 999) < 60 else '良好',
        '{{METRIC2_ANALYSIS}}': data['resting_hr'].get('analysis', '暂无分析'),

        '{{METRIC3_VALUE}}': f"{data['steps']['value']:,}步",
        '{{METRIC3_RATING_CLASS}}': 'rating-good' if data['steps']['value'] > 8000 else 'rating-average' if data['steps']['value'] > 5000 else 'rating-poor',
        '{{METRIC3_RATING}}': '良好' if data['steps']['value'] > 8000 else '一般' if data['steps']['value'] > 5000 else '需改善',
        '{{METRIC3_ANALYSIS}}': data['steps'].get('analysis', '暂无分析'),

        '{{METRIC4_VALUE}}': _txt(data['walking_distance']['value'], lambda v: f"{v:.2f}km ({data['walking_distance']['points']}点)"),
        '{{METRIC4_RATING_CLASS}}': 'rating-good' if data['walking_distance']['value'] is not None else 'rating-average',
        '{{METRIC4_RATING}}': '良好' if data['walking_distance']['value'] is not None else '--',
        '{{METRIC4_ANALYSIS}}': data['walking_distance'].get('analysis', '暂无分析'),

        '{{METRIC5_VALUE}}': _txt(data['active_energy']['value'], lambda v: f"{v:.1f}kcal"),
        '{{METRIC5_RATING_CLASS}}': 'rating-good' if (data['active_energy']['value'] or 0) > 200 else 'rating-average',
        '{{METRIC5_RATING}}': '良好' if (data['active_energy']['value'] or 0) > 200 else '一般',
        '{{METRIC5_ANALYSIS}}': data['active_energy'].get('analysis', '暂无分析'),

        '{{METRIC6_VALUE}}': _txt(data['flights_climbed']['value'], lambda v: f"{v:.0f}层"),
        '{{METRIC6_RATING_CLASS}}': 'rating-good' if data['flights_climbed']['value'] is not None else 'rating-average',
        '{{METRIC6_RATING}}': '正常' if data['flights_climbed']['value'] is not None else '--',
        '{{METRIC6_ANALYSIS}}': data['flights_climbed'].get('analysis', '暂无分析'),

        '{{METRIC7_VALUE}}': _txt(data['stand_time']['value'], lambda v: f"{v:.0f}min"),
        '{{METRIC7_RATING_CLASS}}': 'rating-good' if data['stand_time']['value'] is not None else 'rating-average',
        '{{METRIC7_RATING}}': '正常' if data['stand_time']['value'] is not None else '--',
        '{{METRIC7_ANALYSIS}}': data['stand_time'].get('analysis', '暂无分析'),

        '{{METRIC8_VALUE}}': _txt(data['spo2']['value'], lambda v: f"{v:.1f}%"),
        '{{METRIC8_RATING_CLASS}}': 'rating-excellent' if (data['spo2']['value'] or 0) >= 95 else 'rating-good',
        '{{METRIC8_RATING}}': '正常',
        '{{METRIC8_ANALYSIS}}': data['spo2'].get('analysis', '暂无分析'),

        '{{METRIC9_VALUE}}': _txt(data['basal_energy']['value'], lambda v: f"{v:.1f}kcal"),
        '{{METRIC9_RATING_CLASS}}': 'rating-good' if data['basal_energy']['value'] is not None else 'rating-average',
        '{{METRIC9_RATING}}': '正常' if data['basal_energy']['value'] is not None else '--',
        '{{METRIC9_ANALYSIS}}': data['basal_energy'].get('analysis', '暂无分析'),

        '{{METRIC10_VALUE}}': _txt(data['respiratory_rate']['value'], lambda v: f"{v:.1f}次/分"),
        '{{METRIC10_RATING_CLASS}}': 'rating-good' if data['respiratory_rate']['value'] is not None else 'rating-average',
        '{{METRIC10_RATING}}': '正常' if data['respiratory_rate']['value'] is not None else '--',
        '{{METRIC10_ANALYSIS}}': data['respiratory_rate'].get('analysis', '暂无分析'),

        '{{SLEEP_STATUS}}': '严重不足' if sleep_hours < 6 else '偏少' if sleep_hours < 7 else '正常',
        '{{SLEEP_ALERT_BG}}': '#fee2e2' if sleep_hours < 6 else '#fef3c7' if sleep_hours < 7 else '#dcfce7',
        '{{SLEEP_ALERT_BORDER}}': '#ef4444' if sleep_hours < 6 else '#f59e0b' if sleep_hours < 7 else '#22c55e',
        '{{SLEEP_ALERT_COLOR}}': '#991b1b' if sleep_hours < 6 else '#92400e' if sleep_hours < 7 else '#166534',
        '{{SLEEP_ALERT_SUBCOLOR}}': '#7f1d1d' if sleep_hours < 6 else '#78350f' if sleep_hours < 7 else '#14532d',
        '{{SLEEP_ALERT_TITLE}}': '⚠️ 睡眠时长严重不足' if sleep_hours < 6 else '⚡ 睡眠时长偏少' if sleep_hours < 7 else '✅ 睡眠时长正常',
        '{{SLEEP_ALERT_DETAIL}}': f'实际睡眠{sleep_hours:.1f}小时，远低于7-9小时推荐标准' if sleep_hours < 6 else f'实际睡眠{sleep_hours:.1f}小时，建议增加至7-8小时' if sleep_hours < 7 else f'实际睡眠{sleep_hours:.1f}小时，处于推荐范围内',
        '{{SLEEP_TOTAL}}': f"{sleep_hours:.1f}",
        '{{SLEEP_DEEP}}': f"{sleep_deep:.1f}" if sleep_deep > 0 else '--',
        '{{SLEEP_CORE}}': f"{sleep_core:.1f}" if sleep_core > 0 else '--',
        '{{SLEEP_REM}}': f"{sleep_rem:.1f}" if sleep_rem > 0 else '--',
        '{{SLEEP_AWAKE}}': f"{sleep_awake:.1f}" if sleep_awake > 0 else '--',
        '{{SLEEP_DEEP_PCT}}': str(round(sleep_deep / sleep_hours * 100)) if sleep_deep > 0 and sleep_hours > 0 else '--',
        '{{SLEEP_CORE_PCT}}': str(round(sleep_core / sleep_hours * 100)) if sleep_core > 0 and sleep_hours > 0 else '--',
        '{{SLEEP_REM_PCT}}': str(round(sleep_rem / sleep_hours * 100)) if sleep_rem > 0 and sleep_hours > 0 else '--',
        '{{SLEEP_AWAKE_PCT}}': str(round(sleep_awake / sleep_hours * 100)) if sleep_awake > 0 and sleep_hours > 0 else '--',
        '{{SLEEP_ANALYSIS_BORDER}}': '#ef4444' if sleep_hours < 6 else '#f59e0b' if sleep_hours < 7 else '#22c55e',
        '{{SLEEP_ANALYSIS_TEXT}}': data['sleep'].get('analysis', '暂无分析'),

        '{{WORKOUT_NAME}}': workout['name'] if workout else '无',
        '{{WORKOUT_TIME}}': format_workout_time_range(workout.get('start'), workout.get('duration_min')) if workout else '--',
        '{{WORKOUT_DURATION}}': str(round(workout['duration_min'], 1)) if workout else '--',
        '{{WORKOUT_ENERGY}}': str(round(workout['energy_kcal'], 1)) if workout else '--',
        '{{WORKOUT_AVG_HR}}': f"{workout['avg_hr']}bpm" if workout and workout.get('avg_hr') is not None else '--',
        '{{WORKOUT_MAX_HR}}': f"{workout['max_hr']}bpm" if workout and workout.get('max_hr') is not None else '--',
        '{{WORKOUT_HR_CHART}}': hr_chart if workout else '',
        '{{WORKOUT_ANALYSIS}}': workout.get('analysis', '今日无运动记录') if workout else '今日无运动记录',

        '{{AI1_TITLE}}': high.get('title', '暂无'),
        '{{AI1_PROBLEM}}': high.get('problem', '暂无'),
        '{{AI1_ACTION}}': high.get('action', '暂无'),
        '{{AI1_EXPECTATION}}': high.get('expected', '暂无'),

        '{{AI2_TITLE}}': medium.get('title', '暂无'),
        '{{AI2_PROBLEM}}': medium.get('problem', '暂无'),
        '{{AI2_ACTION}}': medium.get('action', '暂无'),
        '{{AI2_EXPECTATION}}': medium.get('expected', '暂无'),

        '{{AI3_TITLE}}': routine.get('title', '暂无'),
        '{{AI3_DIET}}': routine.get('diet', '暂无'),
        '{{AI3_ROUTINE}}': routine.get('schedule', '暂无'),

        '{{AI4_TITLE}}': summary.get('title', '暂无'),
        '{{AI4_ADVANTAGES}}': summary.get('advantages', '暂无'),
        '{{AI4_RISKS}}': summary.get('risks', '暂无'),
        '{{AI4_CONCLUSION}}': summary.get('conclusion', '暂无'),
        '{{AI4_PLAN}}': summary.get('plan', '暂无'),

        '{{FOOTER_DATA_SOURCES}}': f"数据来源: {data.get('data_source','Apple Health')}",
        '{{FOOTER_DATE}}': datetime.now().strftime('%Y-%m-%d %H:%M'),
    }


    # 兼容 Medical V2 模板新增变量
    # 基础日期变量
    replacements.update({
        '{{DAY}}': data['date'].split('-')[2],
        '{{MONTH_YEAR}}': f"{data['date'].split('-')[0]}年{int(data['date'].split('-')[1])}月",
        '{{DATA_SOURCE}}': data.get('data_source','Apple Health'),
        '{{SLEEP_HOURS}}': f"{sleep_hours:.1f}",
        '{{SLEEP_ALERT}}': (f'<div class="sleep-alert warning"><div class="alert-icon">⚠️</div><div class="alert-content"><h4>睡眠严重不足</h4><p>总睡眠时长{sleep_hours:.1f}小时，远低于7-9小时推荐标准。</p></div></div>' if sleep_hours < 6 else ''),
        '{{AI3_PROBLEM}}': routine.get('problem', '暂无'),
        '{{AI3_ACTION}}': routine.get('diet', '暂无'),
        '{{AI3_EXPECTATION}}': routine.get('schedule', '暂无'),
        '{{AI4_BREAKFAST}}': summary.get('advantages', '暂无'),
        '{{AI4_LUNCH}}': summary.get('risks', '暂无'),
        '{{AI4_DINNER}}': summary.get('conclusion', '暂无'),
        '{{AI4_SNACK}}': summary.get('plan', '暂无'),
    })

    # Workout section 占位符（无运动日不显示曲线）
    if workout:
        workout_section = f'''<div class="workout-section no-break">
  <div class="section-header"><div class="section-title"><span class="section-icon">🏃</span>运动记录 - {workout['name']}</div></div>
  <div class="workout-header"><div class="workout-type"><div class="workout-icon">💪</div><div><div class="workout-name">{workout['name']}</div><div class="workout-time">{format_workout_time_range(workout.get('start'), workout.get('duration_min'))}</div></div></div><span class="badge badge-good">已完成</span></div>
  <div class="workout-stats">
    <div class="stat-box"><div class="stat-value">{round(workout['duration_min'],1)}</div><div class="stat-label">分钟</div></div>
    <div class="stat-box"><div class="stat-value">{round(workout['energy_kcal'],1)}</div><div class="stat-label">千卡</div></div>
    <div class="stat-box"><div class="stat-value">{workout['avg_hr'] if workout.get('avg_hr') is not None else '--'}</div><div class="stat-label">平均心率</div></div>
    <div class="stat-box"><div class="stat-value">{workout['max_hr'] if workout.get('max_hr') is not None else '--'}</div><div class="stat-label">最高心率</div></div>
  </div>
  {hr_chart}
  <div class="workout-analysis"><div class="workout-analysis-title">运动AI详细分析</div><div class="workout-analysis-text">{workout.get('analysis','')}</div></div>
</div>'''
    else:
        workout_section = '<div class="workout-section no-break"><div class="section-header"><div class="section-title"><span class="section-icon">🏃</span>运动记录</div></div><div class="workout-analysis"><div class="workout-analysis-title">今日无结构化运动</div><div class="workout-analysis-text">今日未记录到结构化运动数据，因此不展示心率变化曲线。</div></div></div>'
    replacements['{{WORKOUT_SECTION}}'] = workout_section

    for k, v in replacements.items():
        html = html.replace(k, str(v))

    # 无运动时移除心率图标题块残留（模板是占位式时不会触发）
    if not workout:
        html = html.replace('📈 心率变化曲线', '（无心率曲线）')

    unreplaced = re.findall(r'\{\{[^}]+\}\}', html)
    if unreplaced:
        print(f"⚠️ 未替换变量: {unreplaced}")

    Path(output_path).write_text(html, encoding='utf-8')
    return output_path


if __name__ == '__main__':
    # args: mode1 date [template] [out]; mode2 data.json [template] [out]
    arg1 = sys.argv[1] if len(sys.argv) > 1 else 'data.json'
    template_file = sys.argv[2] if len(sys.argv) > 2 else 'templates/DAILY_TEMPLATE_MEDICAL_V2.html'
    output_file = sys.argv[3] if len(sys.argv) > 3 else 'report_v2.html'

    if re.match(r'^\d{4}-\d{2}-\d{2}$', arg1):
        # source mode: read ai json from stdin
        ai = json.load(sys.stdin) if not sys.stdin.isatty() else {}
        data = build_data_from_source(arg1, ai)
    else:
        # legacy mode
        with open(arg1, 'r', encoding='utf-8') as f:
            data = json.load(f)

    result = generate_report(data, template_file, output_file)
    print(f'报告已生成: {result}')
