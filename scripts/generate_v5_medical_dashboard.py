#!/usr/bin/env python3
"""
V5.7.1 AI分析报告生成器 - Medical Dashboard 模板版
- 从 config.json 读取配置
- 支持多语言切换 (CN/EN)
- 严格真实值：缺失即'--'，不估算
- 仅在有运动时显示心率曲线
- 支持多成员报告生成（最多3人，控制token消耗）

用法:
  python3 scripts/generate_v5_medical_dashboard.py <YYYY-MM-DD> < ai_analysis.json

配置方法：
  1. 编辑 config.json 设置成员信息和路径
  2. 为每个成员分别提供AI分析（通过stdin传入）
"""
import json
import sys
import re
from datetime import datetime, timedelta
from pathlib import Path
from playwright.sync_api import sync_playwright

# V5.8.1: 使用共用工具函数
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).parent))
from utils import load_config, safe_member_name, pick_member_ai_analysis, is_single_analysis_dict

# ==================== 全局配置（从 config.json 加载）====================
CONFIG = load_config()
LANGUAGE = str(CONFIG.get("language", "CN")).strip().upper()
if LANGUAGE not in ("CN", "EN"):
    LANGUAGE = "CN"
MEMBERS = CONFIG.get("members", [{}])
ANALYSIS_LIMITS = CONFIG.get("analysis_limits", {})

# 语言配置 (CN=中文, EN=英文)
LANGUAGE = str(CONFIG.get("language", "CN")).strip().upper()
if LANGUAGE not in ("CN", "EN"):
    LANGUAGE = "CN"

# 成员数量（最多3人）
MAX_MEMBERS = 3
MEMBER_COUNT = min(len(MEMBERS), MAX_MEMBERS)



# ==================== AI分析字数限制配置（从 config.json 读取） ====================
# 指标分析字数限制（每项）
MIN_LENGTH_HRV = ANALYSIS_LIMITS.get("metric_min_words", 150)
MIN_LENGTH_RESTING_HR = ANALYSIS_LIMITS.get("metric_min_words", 150)
MIN_LENGTH_STEPS = ANALYSIS_LIMITS.get("metric_min_words", 150)
MIN_LENGTH_DISTANCE = ANALYSIS_LIMITS.get("metric_min_words", 150)
MIN_LENGTH_ACTIVE_ENERGY = ANALYSIS_LIMITS.get("metric_min_words", 150)
MIN_LENGTH_SPO2 = ANALYSIS_LIMITS.get("metric_min_words", 150)
MIN_LENGTH_FLIGHTS = ANALYSIS_LIMITS.get("metric_min_words", 150)
MIN_LENGTH_STAND = ANALYSIS_LIMITS.get("metric_min_words", 150)
MIN_LENGTH_BASAL = ANALYSIS_LIMITS.get("metric_min_words", 150)
MIN_LENGTH_RESPIRATORY = ANALYSIS_LIMITS.get("metric_min_words", 150)
MIN_LENGTH_SLEEP = ANALYSIS_LIMITS.get("metric_min_words", 150)
MIN_LENGTH_WORKOUT = ANALYSIS_LIMITS.get("metric_min_words", 150)

# 优先级建议字数限制
action_min = ANALYSIS_LIMITS.get("action_min_words", 250)
MIN_LENGTH_PRIORITY_TITLE = 10
MIN_LENGTH_PRIORITY_PROBLEM = 80
MIN_LENGTH_PRIORITY_ACTION = 100
MIN_LENGTH_PRIORITY_EXPECTATION = 70
MIN_LENGTH_AI2_TITLE = 10
MIN_LENGTH_AI2_PROBLEM = 80
MIN_LENGTH_AI2_ACTION = 100
MIN_LENGTH_AI2_EXPECTATION = 70
MIN_LENGTH_AI3_TITLE = 10
MIN_LENGTH_AI3_PROBLEM = 80
MIN_LENGTH_AI3_ACTION = 100
MIN_LENGTH_AI3_EXPECTATION = 70

# 饮食方案字数限制
MIN_LENGTH_BREAKFAST = 30      # 早餐最低字数
MIN_LENGTH_LUNCH = 30          # 午餐最低字数
MIN_LENGTH_DINNER = 30         # 晚餐最低字数
MIN_LENGTH_SNACK = 30          # 加餐最低字数

# 验证模式：strict=严格模式(不满足则报错), warn=警告模式(只提示)
VALIDATION_MODE = CONFIG.get("validation_mode", "strict")  # 可选值: "strict", "warn"
# =====================================================

HOME = Path.home()
TEMPLATE_DIR = Path(__file__).parent.parent / 'templates'
OUTPUT_DIR = Path(CONFIG.get("output_dir", str(Path(__file__).parent.parent / 'output'))).expanduser()
DEFAULT_HEALTH_DIR = HOME / '我的云端硬盘' / 'Health Auto Export' / 'Health Data'
DEFAULT_WORKOUT_DIR = HOME / '我的云端硬盘' / 'Health Auto Export' / 'Workout Data'

# 固定缓存路径（用于周报/月报分析）
CACHE_DIR = Path(CONFIG.get("cache_dir", str(Path(__file__).parent.parent / 'cache' / 'daily'))).expanduser()
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def get_member_config(index: int):
    """获取指定成员的配置（从 config.json 读取）"""
    members = CONFIG.get("members", [])
    
    if index < len(members):
        member = members[index]
        return {
            "name": member.get("name", f"成员{index+1}"),
            "health_dir": Path(member.get("health_dir", "~/我的云端硬盘/Health Auto Export/Health Data")).expanduser(),
            "workout_dir": Path(member.get("workout_dir", "~/我的云端硬盘/Health Auto Export/Workout Data")).expanduser(),
            "email": member.get("email", "")
        }
    
    # 默认配置
    return {
        "name": f"成员{index+1}",
        "health_dir": DEFAULT_HEALTH_DIR,
        "workout_dir": DEFAULT_WORKOUT_DIR,
        "email": ""
    }


def verify_ai_analysis(ai_analysis: dict) -> list:
    """
    验证AI分析字数是否符合要求
    返回错误列表（为空表示验证通过）
    """
    errors = []
    
    # 定义需要验证的字段及其最低字数
    validations = [
        # 指标分析
        ('hrv', MIN_LENGTH_HRV, 'HRV分析'),
        ('resting_hr', MIN_LENGTH_RESTING_HR, '静息心率分析'),
        ('steps', MIN_LENGTH_STEPS, '步数分析'),
        ('distance', MIN_LENGTH_DISTANCE, '距离分析'),
        ('active_energy', MIN_LENGTH_ACTIVE_ENERGY, '活动能量分析'),
        ('spo2', MIN_LENGTH_SPO2, '血氧分析'),
        ('flights', MIN_LENGTH_FLIGHTS, '爬楼分析'),
        ('stand', MIN_LENGTH_STAND, '站立分析'),
        ('basal', MIN_LENGTH_BASAL, '基础代谢分析'),
        ('respiratory', MIN_LENGTH_RESPIRATORY, '呼吸率分析'),
        # 睡眠分析
        ('sleep', MIN_LENGTH_SLEEP, '睡眠分析'),
        # 运动分析
        ('workout', MIN_LENGTH_WORKOUT, '运动分析'),
    ]
    
    # 验证指标分析
    for key, min_len, name in validations:
        text = ai_analysis.get(key, '')
        if text and len(text) < min_len:
            errors.append(f"❌ {name} 字数不足: {len(text)}字 (要求至少{min_len}字)")
    
    # 验证优先级建议
    priority = ai_analysis.get('priority', {})
    priority_checks = [
        ('title', MIN_LENGTH_PRIORITY_TITLE, '最高优先级标题'),
        ('problem', MIN_LENGTH_PRIORITY_PROBLEM, '问题识别'),
        ('action', MIN_LENGTH_PRIORITY_ACTION, '行动计划'),
        ('expectation', MIN_LENGTH_PRIORITY_EXPECTATION, '预期效果'),
    ]
    for key, min_len, name in priority_checks:
        text = priority.get(key, '')
        if text and len(text) < min_len:
            errors.append(f"❌ {name} 字数不足: {len(text)}字 (要求至少{min_len}字)")
    
    # 验证次级建议
    for prefix, label in [('ai2', '第二优先级'), ('ai3', '第三优先级')]:
        title = ai_analysis.get(f'{prefix}_title', '')
        problem = ai_analysis.get(f'{prefix}_problem', '')
        action = ai_analysis.get(f'{prefix}_action', '')
        expectation = ai_analysis.get(f'{prefix}_expectation', '')
        
        if title and len(title) < MIN_LENGTH_AI2_TITLE:
            errors.append(f"❌ {label}标题 字数不足: {len(title)}字 (要求至少{MIN_LENGTH_AI2_TITLE}字)")
        if problem and len(problem) < MIN_LENGTH_AI2_PROBLEM:
            errors.append(f"❌ {label}问题 字数不足: {len(problem)}字 (要求至少{MIN_LENGTH_AI2_PROBLEM}字)")
        if action and len(action) < MIN_LENGTH_AI2_ACTION:
            errors.append(f"❌ {label}行动 字数不足: {len(action)}字 (要求至少{MIN_LENGTH_AI2_ACTION}字)")
        if expectation and len(expectation) < MIN_LENGTH_AI2_EXPECTATION:
            errors.append(f"❌ {label}效果 字数不足: {len(expectation)}字 (要求至少{MIN_LENGTH_AI2_EXPECTATION}字)")
    
    # 验证饮食方案
    diet_checks = [
        ('breakfast', MIN_LENGTH_BREAKFAST, '早餐'),
        ('lunch', MIN_LENGTH_LUNCH, '午餐'),
        ('dinner', MIN_LENGTH_DINNER, '晚餐'),
        ('snack', MIN_LENGTH_SNACK, '加餐'),
    ]
    for key, min_len, name in diet_checks:
        text = ai_analysis.get(key, '')
        if text and len(text) < min_len:
            errors.append(f"❌ {name} 字数不足: {len(text)}字 (要求至少{min_len}字)")
            
    # 验证语言
    full_text = json.dumps(ai_analysis, ensure_ascii=False)
    chinese_chars = len(re.findall(r'[\u4e00-\u9fa5]', full_text))
    
    if LANGUAGE == "EN" and chinese_chars > 20:
        errors.append("❌ 语言配置不匹配: config.json 中设置为 EN(英文), 但 AI 分析结果中检测到大量中文字符。请让 AI 重新生成纯英文的 JSON。")
    elif LANGUAGE == "CN" and chinese_chars < 20:
        errors.append("❌ 语言配置不匹配: config.json 中设置为 CN(中文), 但 AI 分析结果中未检测到足够的中文字符。请让 AI 重新生成纯中文的 JSON。")
    
    return errors


def _parse_metrics(date_str: str, health_dir: Path = None):
    health_dir = health_dir or DEFAULT_HEALTH_DIR
    p = health_dir / f'HealthAutoExport-{date_str}.json'
    if not p.exists():
        return {}
    try:
        data = json.loads(p.read_text(encoding='utf-8'))
    except json.JSONDecodeError as e:
        print(f"⚠️ 解析文件失败: {p} - {e}")
        return {}
    except Exception as e:
        print(f"⚠️ 读取文件失败: {p} - {e}")
        return {}
    
    metrics = {m.get('name'): m for m in data.get('data', {}).get('metrics', [])}
    if 'sleep_analysis' in data.get('data', {}):
        metrics['sleep_analysis'] = data['data']['sleep_analysis']
    return metrics


def _values(metrics: dict, name: str, target_date: str = None):
    m = metrics.get(name, {})
    arr = m.get('data', []) if isinstance(m, dict) else []
    
    # V5.1 修正：严格时间窗口过滤，防止次日数据污染当日指标
    if target_date:
        filtered_arr = []
        for x in arr:
            st = x.get('startDate') or x.get('date')
            if st and st.startswith(target_date):
                filtered_arr.append(x)
        arr = filtered_arr

    vals = [x.get('qty') for x in arr if isinstance(x, dict) and x.get('qty') is not None]
    return vals


def _avg(vals):
    return (sum(vals) / len(vals)) if vals else None


def _sum(vals):
    return (sum(vals)) if vals else None


def load_data(date_str: str, health_dir: Path = None, workout_dir: Path = None):
    health_dir = health_dir or DEFAULT_HEALTH_DIR
    workout_dir = workout_dir or DEFAULT_WORKOUT_DIR
    
    # V5.1 修正：活动数据读取当日文件，严格过滤当日时间戳
    metrics = _parse_metrics(date_str, health_dir)
    if not metrics:
        raise FileNotFoundError(f'未找到源数据: {health_dir}/HealthAutoExport-{date_str}.json')

    hrv_vals = _values(metrics, 'heart_rate_variability', date_str)
    rhr_vals = _values(metrics, 'resting_heart_rate', date_str)
    steps_vals = _values(metrics, 'step_count', date_str)
    dist_vals = _values(metrics, 'walking_running_distance', date_str)
    active_vals = _values(metrics, 'active_energy', date_str)  # V5.1.1-fix: 正确的指标名
    spo2_vals = _values(metrics, 'blood_oxygen_saturation', date_str)
    flights_vals = _values(metrics, 'flights_climbed', date_str)
    stand_vals = _values(metrics, 'apple_stand_time', date_str)
    basal_vals = _values(metrics, 'basal_energy_burned', date_str)
    resp_vals = _values(metrics, 'respiratory_rate', date_str)

    # 能量通常是kJ，转kcal
    active_kcal = (_sum(active_vals) / 4.184) if active_vals else None
    basal_kcal = (_sum(basal_vals) / 4.184) if basal_vals else None

    # 血氧智能单位
    spo2_avg = _avg(spo2_vals)
    if spo2_avg is None:
        spo2 = None
    else:
        spo2 = spo2_avg if spo2_avg > 1 else spo2_avg * 100

    # 运动 - 按顺序尝试多种文件名格式
    workouts = []
    workout_paths = [
        workout_dir / f'HealthAutoExport-{date_str}.json',
        workout_dir / f'{date_str}.json',
        health_dir / f'HealthAutoExport-{date_str}.json',
    ]
    wp = None
    for p in workout_paths:
        if p.exists():
            wp = p
            break
    if wp.exists():
        try:
            wd = json.loads(wp.read_text(encoding='utf-8'))
        except Exception as e:
            print(f"⚠️ 解析运动文件失败: {wp} - {e}")
            wd = {}
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

            # 处理开始和结束时间（兼容 start/startDate 和 end/endDate）
            start_dt = w.get('start') or w.get('startDate') or ''
            end_dt = w.get('end') or w.get('endDate') or ''
            start_str = start_dt[:16].replace('T', ' ') if start_dt else ''
            end_str = end_dt[:16].replace('T', ' ') if end_dt else ''
            
            workouts.append({
                'name': w.get('workoutActivityType') or w.get('name') or '运动',
                'start': start_str,
                'end': end_str,
                'duration_min': duration_min,
                'energy_kcal': float(energy_kcal) if isinstance(energy_kcal, (int, float)) else 0,
                'avg_hr': int(avg_hr) if avg_hr is not None else None,
                'max_hr': int(max_hr) if max_hr is not None else None,
                'hr_timeline': [x for x in timeline if x.get('avg') is not None or x.get('max') is not None]
            })

    # V5.1.1-fix: 计算总活动能量（日常活动 + 运动能量）
    workout_energy_total = sum(w.get('energy_kcal', 0) for w in workouts)
    if active_kcal is not None:
        total_active_kcal = active_kcal + workout_energy_total
    else:
        total_active_kcal = workout_energy_total if workout_energy_total > 0 else None
    
    # 睡眠数据 - V5.8.1: 使用统一解析函数
    from utils import parse_sleep_data_unified
    sleep_config = CONFIG.get('sleep_config', {})
    sleep_result = parse_sleep_data_unified(
        date_str, health_dir,
        read_mode=sleep_config.get('read_mode', 'next_day'),
        start_hour=sleep_config.get('start_hour', 20),
        end_hour=sleep_config.get('end_hour', 12)
    )

    data = {
        'date': date_str,
        'hrv': {'value': round(_avg(hrv_vals), 1) if hrv_vals else None, 'points': len(hrv_vals)},
        'resting_hr': {'value': round(_avg(rhr_vals)) if rhr_vals else None},
        'steps': int(_sum(steps_vals)) if steps_vals else None,
        'distance': round(_sum(dist_vals), 2) if dist_vals else None,
        'active_energy': int(round(total_active_kcal)) if total_active_kcal is not None else None,
        'spo2': round(spo2, 1) if spo2 is not None else None,
        'flights_climbed': int(_sum(flights_vals)) if flights_vals else None,
        'apple_stand_time': int(_sum(stand_vals)) if stand_vals else None,  # 分钟
        'basal_energy_burned': int(round(basal_kcal)) if basal_kcal is not None else None,
        'respiratory_rate': round(_avg(resp_vals), 1) if resp_vals else None,
        'sleep': sleep_result,
        'workouts': workouts,
        'has_workout': len(workouts) > 0,
    }
    return data


def real_text(v, fmt):
    return fmt(v) if v is not None else '--'


def badge(score):
    if LANGUAGE == 'EN':
        if score >= 80: return 'badge-excellent', 'Excellent'
        if score >= 60: return 'badge-good', 'Good'
        if score >= 40: return 'badge-average', 'Average'
        return 'badge-poor', 'Needs Improvement'
    else:
        if score >= 80: return 'badge-excellent', '优秀'
        if score >= 60: return 'badge-good', '良好'
        if score >= 40: return 'badge-average', '一般'
        return 'badge-poor', '需改善'


def gen_rating_from_value(v):
    if LANGUAGE == 'EN':
        return ('rating-good', 'Normal') if v != '--' else ('rating-average', '--')
    else:
        return ('rating-good', '正常') if v != '--' else ('rating-average', '--')


def generate_hr_svg(hr_data):
    no_data_text = 'No heart rate data' if LANGUAGE == 'EN' else '无心率数据'
    if not hr_data:
        return f'<div style="color:#999;text-align:center;padding:20px;">{no_data_text}</div>'

    avg = [h['avg'] for h in hr_data if h.get('avg') is not None]
    mx = [h['max'] for h in hr_data if h.get('max') is not None]
    if not avg and not mx:
        return f'<div style="color:#999;text-align:center;padding:20px;">{no_data_text}</div>'

    vals = (avg + mx)
    y_min = int((min(vals) // 10 - 1) * 10)
    y_max = int((max(vals) // 10 + 2) * 10)
    if y_max == y_min:
        y_max = y_min + 10

    n = len(hr_data)
    chart_width = 450
    chart_height = 80
    left_margin = 40
    bottom_margin = 20
    
    pts_avg, pts_max = [], []
    time_labels = []
    
    for i, h in enumerate(hr_data):
        x = left_margin + i * (chart_width / max(n - 1, 1))
        a = h.get('avg', vals[0])
        m = h.get('max', a)
        y_a = bottom_margin + chart_height - ((a - y_min) / (y_max - y_min)) * chart_height
        y_m = bottom_margin + chart_height - ((m - y_min) / (y_max - y_min)) * chart_height
        pts_avg.append(f"{x:.1f},{y_a:.1f}")
        pts_max.append(f"{x:.1f},{y_m:.1f}")
        
        # 时间标签 - 每隔几个点显示一个，避免重叠
        if n <= 10 or i % max(1, n // 5) == 0 or i == n - 1:
            time_str = h.get('time', '')
            if time_str:
                time_labels.append(f'<text x="{x}" y="{bottom_margin + chart_height + 12}" text-anchor="middle" font-size="8" fill="#64748B">{time_str}</text>')

    # Y轴刻度标签
    y_labels = []
    y_ticks = 5
    for i in range(y_ticks + 1):
        y_val = y_min + (y_max - y_min) * i / y_ticks
        y_pos = bottom_margin + chart_height - (i / y_ticks) * chart_height
        y_labels.append(f'<text x="{left_margin - 5}" y="{y_pos + 3}" text-anchor="end" font-size="8" fill="#64748B">{int(y_val)}</text>')
        # 网格线
        if i > 0 and i < y_ticks:
            y_labels.append(f'<line x1="{left_margin}" y1="{y_pos}" x2="{left_margin + chart_width}" y2="{y_pos}" stroke="#E5E7EB" stroke-width="0.5" stroke-dasharray="2,2"/>')

    hr_title = 'Heart Rate' if LANGUAGE == 'EN' else '心率变化'
    avg_text = 'Avg' if LANGUAGE == 'EN' else '平均'
    max_text = 'Max' if LANGUAGE == 'EN' else '最高'
    time_axis = 'Time' if LANGUAGE == 'EN' else '时间'
    hr_axis = 'HR (bpm)' if LANGUAGE == 'EN' else '心率 (bpm)'
    
    return f'''<div class="hr-chart-wrapper">
<div class="hr-chart-title"><span>📈 {hr_title}</span>
<div class="hr-chart-legend">
<div class="hr-legend-item"><div class="hr-legend-dot avg"></div><span>{avg_text}</span></div>
<div class="hr-legend-item"><div class="hr-legend-dot max"></div><span>{max_text}</span></div>
</div>
</div>
<div class="hr-chart-container">
<svg class="hr-chart-svg" viewBox="0 0 520 130" preserveAspectRatio="xMidYMid meet">
<!-- Y轴 -->
<line x1="{left_margin}" y1="{bottom_margin}" x2="{left_margin}" y2="{bottom_margin + chart_height}" stroke="#94A3B8" stroke-width="1"/>
<!-- X轴 -->
<line x1="{left_margin}" y1="{bottom_margin + chart_height}" x2="{left_margin + chart_width}" y2="{bottom_margin + chart_height}" stroke="#94A3B8" stroke-width="1"/>
<!-- Y轴标签 -->
{''.join(y_labels)}
<!-- 心率曲线 -->
<polyline fill="none" stroke="#3B82F6" stroke-width="2" points="{' '.join(pts_avg)}" />
<polyline fill="none" stroke="#EF4444" stroke-width="1.5" stroke-dasharray="3,2" points="{' '.join(pts_max)}" />
<!-- 时间标签 -->
{''.join(time_labels)}
<!-- 轴标题 -->
<text x="{left_margin + chart_width / 2}" y="{bottom_margin + chart_height + 25}" text-anchor="middle" font-size="9" fill="#64748B">{time_axis}</text>
<text x="15" y="{bottom_margin + chart_height / 2}" text-anchor="middle" font-size="9" fill="#64748B" transform="rotate(-90, 15, {bottom_margin + chart_height / 2})">{hr_axis}</text>
</svg>
</div>
</div>'''


def calculate_scores(data, member_cfg=None):
    """V5.7.2: 计算个性化评分（考虑年龄、性别、BMI）
    
    Returns:
        tuple: (recovery, sleep_score, exercise)
    """
    sleep_hours = data.get('sleep', {}).get('total', 0) or 0
    hrv_v = data['hrv']['value'] or 0
    rhr_v = data['resting_hr']['value'] or 999
    steps_v = data['steps'] or 0
    active_v = data.get('active_energy') or 0
    
    # 获取成员档案信息
    if member_cfg:
        age = member_cfg.get("age", 30)
        gender = member_cfg.get("gender", "male")
        height_cm = member_cfg.get("height_cm", 175)
        weight_kg = member_cfg.get("weight_kg", 70)
    else:
        age, gender, height_cm, weight_kg = 30, "male", 175, 70
    
    # 计算BMI
    bmi = weight_kg / ((height_cm / 100) ** 2) if height_cm > 0 else 22
    
    # === 恢复度评分 (Recovery) ===
    if age <= 25:
        hrv_threshold, rhr_threshold = 55, 60
    elif age <= 35:
        hrv_threshold, rhr_threshold = 50, 65
    elif age <= 45:
        hrv_threshold, rhr_threshold = 45, 68
    else:
        hrv_threshold, rhr_threshold = 40, 70
    
    recovery_base = 60
    recovery_hrv = 15 if hrv_v > hrv_threshold + 10 else (10 if hrv_v > hrv_threshold else (5 if hrv_v > hrv_threshold - 10 else 0))
    recovery_rhr = 15 if rhr_v < rhr_threshold - 5 else (10 if rhr_v < rhr_threshold else (5 if rhr_v < rhr_threshold + 5 else 0))
    recovery_sleep = 10 if sleep_hours >= 7.5 else (7 if sleep_hours >= 7 else (4 if sleep_hours >= 6 else 0))
    recovery = min(100, recovery_base + recovery_hrv + recovery_rhr + recovery_sleep)
    
    # === 睡眠评分 (Sleep Score) ===
    if age <= 25:
        sleep_optimal, sleep_min = 8.0, 7.0
    elif age <= 35:
        sleep_optimal, sleep_min = 7.5, 6.5
    else:
        sleep_optimal, sleep_min = 7.0, 6.0
    
    if sleep_hours >= sleep_optimal:
        sleep_score = 90 + min(10, int((sleep_hours - sleep_optimal) * 5))
    elif sleep_hours >= sleep_min:
        sleep_score = 70 + int((sleep_hours - sleep_min) / (sleep_optimal - sleep_min) * 20)
    elif sleep_hours >= sleep_min - 1:
        sleep_score = 50 + int((sleep_hours - (sleep_min - 1)) * 20)
    else:
        sleep_score = max(30, int(sleep_hours * 15))
    sleep_score = min(100, sleep_score)
    
    # === 运动评分 (Exercise Score) ===
    if bmi < 18.5:
        steps_target, active_target = 7000, 350
    elif bmi < 24:
        steps_target, active_target = 8000, 450
    elif bmi < 28:
        steps_target, active_target = 10000, 550
    else:
        steps_target, active_target = 12000, 650
    
    if gender == "female":
        steps_target, active_target = int(steps_target * 0.9), int(active_target * 0.9)
    
    if age > 40:
        steps_target, active_target = int(steps_target * 0.9), int(active_target * 0.9)
    
    exercise_steps = min(40, int((steps_v / steps_target) * 40))
    exercise_active = min(30, int((active_v / active_target) * 30))
    exercise_workout = 20 if data.get('has_workout') else 0
    exercise_consistency = 10 if steps_v >= steps_target * 0.5 else 5
    exercise = min(100, exercise_steps + exercise_active + exercise_workout + exercise_consistency)
    
    return recovery, sleep_score, exercise


def generate_report(date_str, ai_analysis, template, health_dir=None, workout_dir=None, member_cfg=None):
    data = load_data(date_str, health_dir, workout_dir)
    html = template
    
    # 清理AI分析中的markdown粗体标记 **
    def clean_markdown(text):
        if isinstance(text, str):
            return text.replace('**', '')
        return text
    
    # 递归清理字典中的所有字符串
    def clean_dict(d):
        if isinstance(d, dict):
            return {k: clean_dict(v) for k, v in d.items()}
        elif isinstance(d, str):
            return clean_markdown(d)
        return d
    
    ai_analysis = clean_dict(ai_analysis)

    # 基础信息
    html = html.replace('{{DATE}}', date_str)
    html = html.replace('{{DAY}}', date_str.split('-')[2])
    year_text = date_str.split('-')[0]
    month_text = int(date_str.split('-')[1])
    if LANGUAGE == 'EN':
        month_names = ['', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        month_year = f"{month_names[month_text]} {year_text}"
        header_subtitle = f'{date_str} · Apple Health · AI Analysis Edition'
    else:
        month_year = f"{year_text}年{month_text}月"
        header_subtitle = f'{date_str} · Apple Health · AI分析版'
    html = html.replace('{{MONTH_YEAR}}', month_year)
    html = html.replace('{{HEADER_SUBTITLE}}', header_subtitle)
    html = html.replace('{{DATA_SOURCE}}', 'Apple Health')

    # 评分 - V5.7.2: 使用提取的函数，传入 member_cfg
    if member_cfg is None:
        members = CONFIG.get("members", [])
        member_cfg = members[0] if members else None
    recovery, sleep_score, exercise = calculate_scores(data, member_cfg)

    rc, rt = badge(recovery)
    sc, st = badge(sleep_score)
    ec, et = badge(exercise)

    html = html.replace('{{SCORE_RECOVERY}}', str(recovery)).replace('{{BADGE_RECOVERY_CLASS}}', rc).replace('{{BADGE_RECOVERY_TEXT}}', rt)
    html = html.replace('{{SCORE_SLEEP}}', str(sleep_score)).replace('{{BADGE_SLEEP_CLASS}}', sc).replace('{{BADGE_SLEEP_TEXT}}', st)
    html = html.replace('{{SCORE_EXERCISE}}', str(exercise)).replace('{{BADGE_EXERCISE_CLASS}}', ec).replace('{{BADGE_EXERCISE_TEXT}}', et)

    # 指标（严格真实值）
    # 指标分析 - 必须有真实AI内容，禁止为空
    m1 = real_text(data['hrv']['value'], lambda v: f"{v:.1f} ms")
    hrv_analysis = ai_analysis.get('hrv')
    if not hrv_analysis:
        raise ValueError("❌ 错误: 缺少HRV分析 - 必须在当前AI对话中生成")
    hrv_rating_text = 'Good' if LANGUAGE == 'EN' else '良好'
    hrv_rating_text2 = 'Average' if LANGUAGE == 'EN' else '一般'
    html = html.replace('{{METRIC1_VALUE}}', m1).replace('{{METRIC1_RATING_CLASS}}', 'rating-good' if data['hrv']['value'] and data['hrv']['value'] > 50 else 'rating-average').replace('{{METRIC1_RATING}}', hrv_rating_text if data['hrv']['value'] and data['hrv']['value'] > 50 else hrv_rating_text2).replace('{{METRIC1_ANALYSIS}}', hrv_analysis)

    m2 = real_text(data['resting_hr']['value'], lambda v: f"{int(v)} bpm")
    rhr_analysis = ai_analysis.get('resting_hr')
    if not rhr_analysis:
        raise ValueError("❌ 错误: 缺少静息心率分析 - 必须在当前AI对话中生成")
    rhr_rating_text = 'Excellent' if LANGUAGE == 'EN' else '优秀'
    rhr_rating_text2 = 'Good' if LANGUAGE == 'EN' else '良好'
    html = html.replace('{{METRIC2_VALUE}}', m2).replace('{{METRIC2_RATING_CLASS}}', 'rating-excellent' if data['resting_hr']['value'] and data['resting_hr']['value'] < 60 else 'rating-good').replace('{{METRIC2_RATING}}', rhr_rating_text if data['resting_hr']['value'] and data['resting_hr']['value'] < 60 else rhr_rating_text2).replace('{{METRIC2_ANALYSIS}}', rhr_analysis)

    m3 = real_text(data['steps'], lambda v: f"{int(v):,}")
    steps_analysis = ai_analysis.get('steps')
    if not steps_analysis:
        raise ValueError("❌ 错误: 缺少步数分析 - 必须在当前AI对话中生成")
    steps_rating_text = 'Good' if LANGUAGE == 'EN' else '良好'
    steps_rating_text2 = 'Average' if LANGUAGE == 'EN' else '一般'
    html = html.replace('{{METRIC3_VALUE}}', m3).replace('{{METRIC3_RATING_CLASS}}', 'rating-good' if data['steps'] and data['steps'] > 8000 else 'rating-average').replace('{{METRIC3_RATING}}', steps_rating_text if data['steps'] and data['steps'] > 8000 else steps_rating_text2).replace('{{METRIC3_ANALYSIS}}', steps_analysis)

    m4 = real_text(data['distance'], lambda v: f"{v:.1f} km")
    c4, t4 = gen_rating_from_value(m4)
    distance_analysis = ai_analysis.get('distance')
    if not distance_analysis:
        raise ValueError("❌ 错误: 缺少距离分析 - 必须在当前AI对话中生成")
    html = html.replace('{{METRIC4_VALUE}}', m4).replace('{{METRIC4_RATING_CLASS}}', c4).replace('{{METRIC4_RATING}}', t4).replace('{{METRIC4_ANALYSIS}}', distance_analysis)

    m5 = real_text(data['active_energy'], lambda v: f"{int(v)} kcal")
    c5, t5 = gen_rating_from_value(m5)
    active_analysis = ai_analysis.get('active_energy')
    if not active_analysis:
        raise ValueError("❌ 错误: 缺少活动能量分析 - 必须在当前AI对话中生成")
    html = html.replace('{{METRIC5_VALUE}}', m5).replace('{{METRIC5_RATING_CLASS}}', c5).replace('{{METRIC5_RATING}}', t5).replace('{{METRIC5_ANALYSIS}}', active_analysis)

    if LANGUAGE == 'EN':
        m6 = real_text(data['flights_climbed'], lambda v: f"{int(v)} floors")
    else:
        m6 = real_text(data['flights_climbed'], lambda v: f"{int(v)} 层")
    c6, t6 = gen_rating_from_value(m6)
    flights_analysis = ai_analysis.get('flights')
    if not flights_analysis:
        raise ValueError("❌ 错误: 缺少爬楼分析 - 必须在当前AI对话中生成")
    html = html.replace('{{METRIC6_VALUE}}', m6).replace('{{METRIC6_RATING_CLASS}}', c6).replace('{{METRIC6_RATING}}', t6).replace('{{METRIC6_ANALYSIS}}', flights_analysis)

    if LANGUAGE == 'EN':
        m7 = real_text(data['apple_stand_time'], lambda v: f"{int(v)//60}h {int(v)%60}min")
    else:
        m7 = real_text(data['apple_stand_time'], lambda v: f"{int(v)//60}h {int(v)%60}分钟")
    c7, t7 = gen_rating_from_value(m7)
    stand_analysis = ai_analysis.get('stand')
    if not stand_analysis:
        raise ValueError("❌ 错误: 缺少站立时间分析 - 必须在当前AI对话中生成")
    html = html.replace('{{METRIC7_VALUE}}', m7).replace('{{METRIC7_RATING_CLASS}}', c7).replace('{{METRIC7_RATING}}', t7).replace('{{METRIC7_ANALYSIS}}', stand_analysis)

    m8 = real_text(data['spo2'], lambda v: f"{v:.1f}%")
    c8, t8 = gen_rating_from_value(m8)
    spo2_analysis = ai_analysis.get('spo2')
    if not spo2_analysis:
        raise ValueError("❌ 错误: 缺少血氧分析 - 必须在当前AI对话中生成")
    html = html.replace('{{METRIC8_VALUE}}', m8).replace('{{METRIC8_RATING_CLASS}}', c8).replace('{{METRIC8_RATING}}', t8).replace('{{METRIC8_ANALYSIS}}', spo2_analysis)

    m9 = real_text(data['basal_energy_burned'], lambda v: f"{int(v):,} kcal")
    c9, t9 = gen_rating_from_value(m9)
    basal_analysis = ai_analysis.get('basal')
    if not basal_analysis:
        raise ValueError("❌ 错误: 缺少基础代谢分析 - 必须在当前AI对话中生成")
    html = html.replace('{{METRIC9_VALUE}}', m9).replace('{{METRIC9_RATING_CLASS}}', c9).replace('{{METRIC9_RATING}}', t9).replace('{{METRIC9_ANALYSIS}}', basal_analysis)

    m10 = real_text(data['respiratory_rate'], lambda v: f"{float(v):.1f} 次/分")
    c10, t10 = gen_rating_from_value(m10)
    resp_analysis = ai_analysis.get('respiratory')
    if not resp_analysis:
        raise ValueError("❌ 错误: 缺少呼吸率分析 - 必须在当前AI对话中生成")
    html = html.replace('{{METRIC10_VALUE}}', m10).replace('{{METRIC10_RATING_CLASS}}', c10).replace('{{METRIC10_RATING}}', t10).replace('{{METRIC10_ANALYSIS}}', resp_analysis)

    # 睡眠 - 必须有真实AI内容
    sleep_analysis = ai_analysis.get('sleep')
    if not sleep_analysis:
        raise ValueError("❌ 错误: 缺少睡眠分析 - 必须在当前AI对话中生成")
    
    # 获取睡眠总时长
    sleep_hours = data.get('sleep', {}).get('total', 0) or 0
    
    sleep_status_text = 'Severely Insufficient' if LANGUAGE == 'EN' else '严重不足'
    sleep_status_normal = 'Normal' if LANGUAGE == 'EN' else '正常'
    html = html.replace('{{SLEEP_STATUS}}', sleep_status_text if sleep_hours < 3 else sleep_status_normal)
    
    if LANGUAGE == 'EN':
        alert = f'<div class="sleep-alert warning"><div class="alert-icon">⚠️</div><div class="alert-content"><h4>Severe Sleep Deficiency</h4><p>Total sleep duration {sleep_hours:.1f} hours, far below the 7-9 hour recommended standard.</p></div></div>' if sleep_hours < 6 else ''
    else:
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
    html = html.replace('{{SLEEP_ANALYSIS_TEXT}}', sleep_analysis)
    
    # V5.1.1-fix: 添加入睡时间和起床时间
    html = html.replace('{{SLEEP_BEDTIME}}', s.get('bedtime', '--'))
    html = html.replace('{{SLEEP_WAKETIME}}', s.get('waketime', '--'))

    # 运动 section（有运动才画图）- 显示所有运动记录
    if data.get('has_workout') and data.get('workouts'):
        workouts = data['workouts']
        workout_analysis = ai_analysis.get('workout')
        if not workout_analysis:
            raise ValueError("❌ 错误: 缺少运动分析 - 必须在当前AI对话中生成（今日有运动记录）")
        
        # 构建所有运动记录的HTML
        workout_entries = []
        for idx, w in enumerate(workouts, 1):
            # 格式化时间显示
            start_time = w.get('start', '')
            end_time = w.get('end', '')
            if start_time and len(start_time) >= 16:
                start_display = start_time[11:16]
            else:
                start_display = start_time or '--:--'
            
            if end_time and len(end_time) >= 16:
                end_display = end_time[11:16]
            else:
                end_display = end_time or '--:--'
            
            time_display = f"{start_display} - {end_display}" if start_display != '--:--' or end_display != '--:--' else ("Time not recorded" if LANGUAGE == 'EN' else "时间未记录")
            
            # 为每个运动生成心率图（如果有数据）
            hr_timeline = w.get('hr_timeline', [])
            hr_chart = generate_hr_svg(hr_timeline) if hr_timeline else ""
            
            completed_text = 'Completed' if LANGUAGE == 'EN' else '已完成'
            min_text = 'min' if LANGUAGE == 'EN' else '分钟'
            kcal_text = 'kcal' if LANGUAGE == 'EN' else '千卡'
            avg_hr_text = 'Avg HR' if LANGUAGE == 'EN' else '平均心率'
            max_hr_text = 'Max HR' if LANGUAGE == 'EN' else '最高心率'
            
            entry = f'''<div class="workout-entry" style="margin-bottom: 20px; padding: 15px; background: rgba(255,255,255,0.5); border-radius: 8px;">
  <div class="workout-header" style="margin-bottom: 10px;">
    <div class="workout-type">
      <div class="workout-icon">💪</div>
      <div>
        <div class="workout-name">{idx}. {w['name']}</div>
        <div class="workout-time">{time_display}</div>
      </div>
    </div>
    <span class="badge badge-good">{completed_text}</span>
  </div>
  <div class="workout-stats">
    <div class="stat-box"><div class="stat-value">{int(w['duration_min']) if w['duration_min'] else '--'}</div><div class="stat-label">{min_text}</div></div>
    <div class="stat-box"><div class="stat-value">{int(w['energy_kcal']) if w['energy_kcal'] else '--'}</div><div class="stat-label">{kcal_text}</div></div>
    <div class="stat-box"><div class="stat-value">{w['avg_hr'] if w['avg_hr'] is not None else '--'}</div><div class="stat-label">{avg_hr_text}</div></div>
    <div class="stat-box"><div class="stat-value">{w['max_hr'] if w['max_hr'] is not None else '--'}</div><div class="stat-label">{max_hr_text}</div></div>
  </div>
  {hr_chart}
</div>'''
            workout_entries.append(entry)
        
        workout_title = 'Workout Records' if LANGUAGE == 'EN' else '运动记录'
        ai_analysis_title = 'Workout AI Analysis' if LANGUAGE == 'EN' else '运动AI综合分析'
        workout_section = f'''<div class="workout-section no-break">
  <div class="section-header">
    <div class="section-title">
      <span class="section-icon">🏃</span>{workout_title} - {len(workouts)} workouts
    </div>
  </div>
  {''.join(workout_entries)}
  <div class="workout-analysis">
    <div class="workout-analysis-title">{ai_analysis_title}</div>
    <div class="workout-analysis-text">{workout_analysis}</div>
  </div>
</div>'''
    else:
        # 无运动时也必须有workout分析字段（说明无运动的情况）
        workout_analysis = ai_analysis.get('workout')
        if not workout_analysis:
            raise ValueError("❌ 错误: 缺少运动分析 - 必须在当前AI对话中生成（即使无运动也需分析）")
        workout_title = 'Workout Records' if LANGUAGE == 'EN' else '运动记录'
        no_workout_title = 'No Structured Exercise Today' if LANGUAGE == 'EN' else '今日无结构化运动'
        workout_section = f'''<div class="workout-section no-break"><div class="section-header"><div class="section-title"><span class="section-icon">🏃</span>{workout_title}</div></div><div class="workout-analysis"><div class="workout-analysis-title">{no_workout_title}</div><div class="workout-analysis-text">{workout_analysis}</div></div></div>'''
    html = html.replace('{{WORKOUT_SECTION}}', workout_section)

    # AI建议 - 必须有真实内容，禁止模板填充
    required_ai_fields = [
        'priority', 'ai2_title', 'ai2_problem', 'ai2_action', 'ai2_expectation',
        'ai3_title', 'ai3_problem', 'ai3_action', 'ai3_expectation',
        'breakfast', 'lunch', 'dinner', 'snack'
    ]
    
    # 严格检查所有必填字段
    missing_fields = []
    for f in required_ai_fields:
        if f == 'priority':
            p = ai_analysis.get('priority', {})
            if not p or not p.get('title') or not p.get('problem') or not p.get('action') or not p.get('expectation'):
                missing_fields.append('priority (title/problem/action/expectation)')
        elif not ai_analysis.get(f):
            missing_fields.append(f)
    
    if missing_fields:
        raise ValueError(f"❌ 错误: AI分析缺少以下字段，必须在当前AI对话中生成: {missing_fields}")
    
    # 最高优先级建议
    p = ai_analysis.get('priority', {})
    html = html.replace('{{AI1_TITLE}}', p.get('title', ''))
    html = html.replace('{{AI1_PROBLEM}}', p.get('problem', ''))
    html = html.replace('{{AI1_ACTION}}', p.get('action', ''))
    html = html.replace('{{AI1_EXPECTATION}}', p.get('expectation', ''))
    
    html = html.replace('{{AI2_TITLE}}', ai_analysis.get('ai2_title', ''))
    html = html.replace('{{AI2_PROBLEM}}', ai_analysis.get('ai2_problem', ''))
    html = html.replace('{{AI2_ACTION}}', ai_analysis.get('ai2_action', ''))
    html = html.replace('{{AI2_EXPECTATION}}', ai_analysis.get('ai2_expectation', ''))

    html = html.replace('{{AI3_TITLE}}', ai_analysis.get('ai3_title', ''))
    html = html.replace('{{AI3_PROBLEM}}', ai_analysis.get('ai3_problem', ''))
    html = html.replace('{{AI3_ACTION}}', ai_analysis.get('ai3_action', ''))
    html = html.replace('{{AI3_EXPECTATION}}', ai_analysis.get('ai3_expectation', ''))

    html = html.replace('{{AI4_BREAKFAST}}', ai_analysis.get('breakfast', ''))
    html = html.replace('{{AI4_LUNCH}}', ai_analysis.get('lunch', ''))
    html = html.replace('{{AI4_DINNER}}', ai_analysis.get('dinner', ''))
    html = html.replace('{{AI4_SNACK}}', ai_analysis.get('snack', ''))

    return html


if __name__ == '__main__':
    from datetime import datetime
    
    if len(sys.argv) < 2:
        print('用法: python3 scripts/generate_v5_medical_dashboard.py <YYYY-MM-DD> < ai_analysis.json')
        print('       支持多成员报告生成（最多3人）')
        print('')
        print('多成员模式：')
        print('  1. 修改脚本开头 MEMBER_COUNT 变量（1-3）')
        print('  2. 填写对应成员的数据路径 MEMBER_X_HEALTH_DIR')
        print('  3. 按顺序为每个成员提供AI分析（通过stdin传入，用JSON数组格式）')
        print('')
        print('当前配置：')
        print(f'  MEMBER_COUNT = {MEMBER_COUNT}')
        for i in range(min(MEMBER_COUNT, MAX_MEMBERS)):
            cfg = get_member_config(i)
            print(f'  成员{i+1}: {cfg["name"]} -> {cfg["health_dir"]}')
        sys.exit(1)

    date_str = sys.argv[1]
    
    # 限制成员数量在1-3之间（控制token消耗）
    member_count = max(1, min(MEMBER_COUNT, MAX_MEMBERS))
    
    print(f"📊 多成员报告生成模式")
    print(f"   日期: {date_str}")
    print(f"   成员数: {member_count} (上限3人，控制token消耗)")
    print("")
    
    # 读取所有成员的AI分析（支持单对象或字典或列表）
    raw_ai_analyses = json.load(sys.stdin)
    
    if isinstance(raw_ai_analyses, dict) and "members" in raw_ai_analyses:
        raw_ai_analyses = raw_ai_analyses["members"]
    
    # 为每个成员生成报告
    for idx in range(member_count):
        member_cfg = get_member_config(idx)
        member_name = member_cfg['name']
        member_health_dir = Path(member_cfg['health_dir'])
        member_workout_dir = Path(member_cfg['workout_dir'])
        
        # 健壮的成员匹配逻辑 - V5.8.0: 使用 pick_member_ai_analysis
        ai_analysis = pick_member_ai_analysis(raw_ai_analyses, member_name, idx)
        
        if not isinstance(ai_analysis, dict) or not ai_analysis:
            print(f"⚠️ 警告: 找不到成员 {member_name} 的有效分析数据，跳过")
            continue
        
        print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print(f"🧑 正在为成员 {idx+1}/{member_count} 生成报告: {member_name}")
        print(f"   Health路径: {member_health_dir}")
        print(f"   Workout路径: {member_workout_dir}")
        print("")
        
        # 验证AI分析
        if ai_analysis.get('generated_date') != date_str:
            print(f"⚠️ 警告: AI分析日期标记不匹配")
            print(f"   报告日期: {date_str}")
            print(f"   AI分析日期: {ai_analysis.get('generated_date', '未标记')}")
        
        # 验证AI分析字数
        print(f"📏 验证AI分析字数...")
        validation_errors = verify_ai_analysis(ai_analysis)
        if validation_errors:
            print(f"⚠️  发现 {len(validation_errors)} 处字数不足:")
            for error in validation_errors:
                print(f"   {error}")
            if VALIDATION_MODE == "strict":
                print(f"❌ 严格模式: 字数验证失败，停止生成")
                print(f"   请重新生成符合字数要求的AI分析")
                print(f"   当前限制: HRV/睡眠等指标最低{MIN_LENGTH_HRV}字, 优先级建议最低{MIN_LENGTH_PRIORITY_PROBLEM}字")
                continue
            else:
                print(f"⚠️ 警告模式: 继续生成，但请注意内容可能不够详细")
        else:
            print(f"   ✅ 字数验证通过")
        
        # 检查数据文件是否存在
        data_file = member_health_dir / f'HealthAutoExport-{date_str}.json'
        if not data_file.exists():
            print(f"❌ 错误: 数据文件不存在: {data_file}")
            print(f"   跳过成员 {member_name}")
            continue
        
        print(f"📊 正在生成 {date_str} 健康日报...")
        print("   数据提取: 实时从Apple Health文件读取")
        print("   AI分析: 当前对话生成（已验证）")
        
        # 读取模板（根据语言选择）
        template_file = 'DAILY_TEMPLATE_MEDICAL_V2_EN.html' if LANGUAGE == 'EN' else 'DAILY_TEMPLATE_MEDICAL_V2.html'
        with open(TEMPLATE_DIR / template_file, 'r', encoding='utf-8') as f:
            template = f.read()
        
        # 生成报告（需要修改generate_report以支持自定义health_dir）
        # 临时方案：先修改全局变量再恢复
        original_health_dir = DEFAULT_HEALTH_DIR
        
        try:
            # 重新加载该成员的数据
            data = load_data(date_str, member_health_dir, member_workout_dir)
            
            # 生成报告HTML
            html = generate_report(date_str, ai_analysis, template, member_health_dir, member_workout_dir)
            
            # 计算评分 - V5.7.2: 使用提取的函数
            member_cfg = get_member_config(idx)
            recovery, sleep_score, exercise = calculate_scores(data, member_cfg)
            
            # 生成文件名（包含成员标识）
            safe_name = safe_member_name(member_name)
            html_path = OUTPUT_DIR / f'{date_str}-daily-v5-medical-{safe_name}.html'
            pdf_path = OUTPUT_DIR / f'{date_str}-daily-v5-medical-{safe_name}.pdf'
            
            html_path.write_text(html, encoding='utf-8')
            
            # V5.2.3-fix: 添加PDF生成重试机制
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    with sync_playwright() as p:
                        browser = p.chromium.launch()
                        page = browser.new_page()
                        page.goto(html_path.resolve().as_uri())
                        page.wait_for_timeout(2500)
                        page.pdf(path=str(pdf_path), format='A4', print_background=True,
                                 margin={'top': '10mm', 'bottom': '10mm', 'left': '10mm', 'right': '10mm'},
                                 display_header_footer=False)
                        browser.close()
                    break  # 成功则跳出重试循环
                except Exception as e:
                    if attempt < max_retries - 1:
                        print(f'   ⚠️ PDF生成失败，第{attempt + 1}次重试...')
                        import time
                        time.sleep(1)
                    else:
                        raise Exception(f'PDF生成失败（已重试{max_retries}次）: {e}')
            
            print(f'✅ 报告已生成: {pdf_path}')
            print(f'   大小: {pdf_path.stat().st_size / 1024:.0f} KB')
            print(f'   成员: {member_name}')
            
            # 保存缓存
            try:
                cache_data = {
                    'date': date_str,
                    'member': member_name,
                    'hrv': data['hrv'],
                    'resting_hr': data['resting_hr'],
                    'steps': data['steps'],
                    'active_energy': data.get('active_energy') or 0,  # V5.2.3-fix: 统一使用 active_energy
                    'spo2': data['spo2'],
                    'workouts': data['workouts'],
                    'has_workout': data['has_workout'],
                    'sleep': data['sleep']
                }
                cache_path = CACHE_DIR / f'{date_str}_{safe_name}.json'
                with open(cache_path, 'w', encoding='utf-8') as f:
                    json.dump(cache_data, f, ensure_ascii=False, indent=2)
                print(f'   数据缓存: {cache_path}')
            except Exception as e:
                print(f'   缓存保存失败: {e}')
                
        except Exception as e:
            print(f"❌ 生成失败: {e}")
            import traceback
            traceback.print_exc()
        
        print("")
    
    print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"✅ 所有成员报告生成完成！")
    print(f"   总计: {member_count} 份报告")
    print(f"   输出目录: {OUTPUT_DIR}")
