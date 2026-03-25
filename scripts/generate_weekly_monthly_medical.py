#!/usr/bin/env python3
"""
周报和月报生成器 - V6.0.5 Medical Dashboard版 (支持多语言 CN/EN)
使用新模板 WEEKLY_TEMPLATE_MEDICAL.html / MONTHLY_TEMPLATE_MEDICAL.html
用法:
  python3 scripts/generate_weekly_monthly_medical.py weekly START_DATE END_DATE < ai_analysis.json
  python3 scripts/generate_weekly_monthly_medical.py monthly YEAR MONTH < ai_analysis.json
"""
import json
import math
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path
from html import escape as html_escape
from playwright.sync_api import sync_playwright

# V6.0.0: 使用共用工具函数
sys.path.insert(0, str(Path(__file__).parent))
from utils import load_config, safe_member_name, pick_member_ai_analysis, detect_language_mismatch, MAX_MEMBERS, count_text_units
from health_score import calculate_body_age, calculate_pace_of_aging

HOME = Path.home()
TEMPLATE_DIR = Path(__file__).parent.parent / 'templates'

# ==================== 配置加载 ====================
CONFIG = load_config()
LANGUAGE = str(CONFIG.get("language", "CN")).strip().upper()
if LANGUAGE not in ("CN", "EN"):
    LANGUAGE = "CN"
VALIDATION_MODE = CONFIG.get("validation_mode", "strict")
ANALYSIS_LIMITS = CONFIG.get("analysis_limits", {})
WEEKLY_MIN_WORDS = ANALYSIS_LIMITS.get("weekly_min_words", 800)
MONTHLY_MIN_WORDS = ANALYSIS_LIMITS.get("monthly_min_words", 1000)
MONTHLY_TREND_MIN_WORDS = ANALYSIS_LIMITS.get("monthly_trend_min_words", 150)

# 安全获取嵌套字典值的辅助函数
def safe_get(obj: dict, *keys, default=None):
    """安全获取嵌套字典值"""
    current = obj
    for key in keys:
        if not isinstance(current, dict):
            return default
        current = current.get(key)
        if current is None:
            return default
    return current

OUTPUT_DIR = Path(
    CONFIG.get(
        "output_dir",
        str(Path.home() / '.openclaw' / 'workspace' / 'shared' / 'health-reports' / 'upload')
    )
).expanduser()
CACHE_DIR = Path(CONFIG.get("cache_dir", str(Path(__file__).parent.parent / 'cache' / 'daily'))).expanduser()
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# ==================== 多语言错误文本 ====================
ERROR_TEXTS = {
    "CN": {
        "weekly_label": "周报",
        "monthly_label": "月报",
        "weekly_monthly_label": "周/月报",
        "recommendations_must_list": "❌ {context} recommendations 必须是数组(list)，当前类型: {type_name}",
        "recommendations_item_must_dict": "❌ {context} recommendations[{idx}] 必须是对象(dict)，当前类型: {type_name}",
        "recommendations_missing_title": "❌ {context} recommendations[{idx}] 缺少 title",
        "recommendations_missing_content": "❌ {context} recommendations[{idx}] 缺少 content",
        "weekly_total_short": "❌ 周报总长度不足: {current}{unit} (要求≥{minimum}{unit})",
        "monthly_total_short": "❌ 月报总长度不足: {current}{unit} (要求≥{minimum}{unit})",
        "monthly_trend_short": "❌ 月报趋势评估长度不足: {current}{unit} (要求≥{minimum}{unit})",
        "validation_found": "⚠️  发现 {count} 处校验问题:",
        "strict_stop": "❌ 严格模式: 校验失败，停止生成",
        "warn_continue": "⚠️ 警告模式: 继续生成，但请注意内容可能不够详细",
        "missing_weekly_trend": "❌ 错误: 缺少周报AI趋势分析 - 必须在当前AI对话中生成",
        "invalid_weekly_recommendations": "❌ 错误: 周报 recommendations 结构无效: {details}",
        "missing_monthly_hrv": "❌ 错误: 缺少月报HRV分析 - 必须在当前AI对话中生成",
        "missing_monthly_sleep": "❌ 错误: 缺少月报睡眠质量分析 - 必须在当前AI对话中生成",
        "missing_monthly_activity": "❌ 错误: 缺少月报活动量分析 - 必须在当前AI对话中生成",
        "missing_monthly_trend": "❌ 错误: 缺少月报整体趋势评估 - 必须在当前AI对话中生成",
        "monthly_trend_short_msg": "月报趋势评估长度不足（当前{current}{unit}，要求≥{minimum}{unit}）",
        "monthly_trend_short_strict": "❌ 错误: {msg} - 请在当前AI对话中重新生成完整分析，必须包含具体数据点引用和指标间关联分析",
        "monthly_trend_short_warn": "⚠️ 警告模式: {msg}，继续生成",
        "invalid_monthly_recommendations": "❌ 错误: 月报 recommendations 结构无效: {details}",
        "json_parse_error": "❌ 错误: {error}",
        "no_members": "❌ 错误: config.json 未配置 members，无法生成周报/月报",
        "weekly_args_error": "错误: 周报模式需要 start_date 和 end_date",
        "monthly_args_error": "错误: 月报模式需要 year 和 month",
        "year_month_parse_error": "错误: year/month 必须是整数，例如: monthly 2026 3",
        "month_range_error": "错误: month 超出范围: {month}（应为 1-12）",
        "unknown_report_type": "错误: 未知报告类型 {report_type}",
    },
    "EN": {
        "weekly_label": "weekly report",
        "monthly_label": "monthly report",
        "weekly_monthly_label": "weekly/monthly report",
        "recommendations_must_list": "❌ {context} recommendations must be a list, got: {type_name}",
        "recommendations_item_must_dict": "❌ {context} recommendations[{idx}] must be an object(dict), got: {type_name}",
        "recommendations_missing_title": "❌ {context} recommendations[{idx}] missing title",
        "recommendations_missing_content": "❌ {context} recommendations[{idx}] missing content",
        "weekly_total_short": "❌ Weekly total length too short: {current}{unit} (required ≥{minimum}{unit})",
        "monthly_total_short": "❌ Monthly total length too short: {current}{unit} (required ≥{minimum}{unit})",
        "monthly_trend_short": "❌ Monthly trend assessment too short: {current}{unit} (required ≥{minimum}{unit})",
        "validation_found": "⚠️  Found {count} validation issue(s):",
        "strict_stop": "❌ Strict mode: validation failed, stop generating",
        "warn_continue": "⚠️ Warn mode: continue generating, but content may be insufficient",
        "missing_weekly_trend": "❌ Error: missing weekly trend analysis - must be generated in current AI session",
        "invalid_weekly_recommendations": "❌ Error: invalid weekly recommendations structure: {details}",
        "missing_monthly_hrv": "❌ Error: missing monthly HRV analysis - must be generated in current AI session",
        "missing_monthly_sleep": "❌ Error: missing monthly sleep analysis - must be generated in current AI session",
        "missing_monthly_activity": "❌ Error: missing monthly activity analysis - must be generated in current AI session",
        "missing_monthly_trend": "❌ Error: missing monthly trend assessment - must be generated in current AI session",
        "monthly_trend_short_msg": "Monthly trend assessment too short (current {current}{unit}, required ≥{minimum}{unit})",
        "monthly_trend_short_strict": "❌ Error: {msg} - regenerate in current AI session with concrete metric references and cross-metric analysis",
        "monthly_trend_short_warn": "⚠️ Warn mode: {msg}, continue generating",
        "invalid_monthly_recommendations": "❌ Error: invalid monthly recommendations structure: {details}",
        "json_parse_error": "❌ Error: {error}",
        "no_members": "❌ Error: config.json has no members; cannot generate weekly/monthly report",
        "weekly_args_error": "Error: Weekly report requires start and end dates",
        "monthly_args_error": "Error: Monthly report requires year and month",
        "year_month_parse_error": "Error: year/month must be integers, e.g. monthly 2026 3",
        "month_range_error": "Error: month out of range: {month} (expected 1-12)",
        "unknown_report_type": "Error: unknown report type {report_type}",
    }
}


def _err(key: str, **kwargs) -> str:
    template = ERROR_TEXTS.get(LANGUAGE, ERROR_TEXTS["CN"]).get(key, key)
    try:
        return template.format(**kwargs)
    except Exception:
        return template


# ==================== 验证函数 ====================
def _validate_recommendations(recommendations, context=None):
    """验证 recommendations 结构，避免输入异常导致 AttributeError。"""
    errors = []
    context = context or _err('weekly_monthly_label')

    if not isinstance(recommendations, list):
        return [_err('recommendations_must_list', context=context, type_name=type(recommendations).__name__)]

    for idx, rec in enumerate(recommendations):
        if not isinstance(rec, dict):
            errors.append(_err('recommendations_item_must_dict', context=context, idx=idx, type_name=type(rec).__name__))
            continue
        if not rec.get('title'):
            errors.append(_err('recommendations_missing_title', context=context, idx=idx))
        if not rec.get('content'):
            errors.append(_err('recommendations_missing_content', context=context, idx=idx))

    return errors


def verify_ai_analysis_weekly(ai_analysis):
    """验证周报AI分析长度"""
    errors = []
    total_units = 0
    unit_label = 'words' if LANGUAGE == 'EN' else '字'

    # 收集所有文本
    trend_analysis = ai_analysis.get('trend_analysis') or ai_analysis.get('weekly_analysis', '')
    total_units += count_text_units(trend_analysis, LANGUAGE)

    recommendations = ai_analysis.get('recommendations', [])
    rec_errors = _validate_recommendations(recommendations, context=_err('weekly_label'))
    errors.extend(rec_errors)

    if not rec_errors:
        for rec in recommendations:
            total_units += count_text_units(rec.get('title', ''), LANGUAGE)
            total_units += count_text_units(rec.get('content', ''), LANGUAGE)

    # 检查周报总长度（要求≥WEEKLY_MIN_WORDS）
    if total_units < WEEKLY_MIN_WORDS:
        errors.append(_err('weekly_total_short', current=total_units, unit=unit_label, minimum=WEEKLY_MIN_WORDS))

    # 语言一致性校验
    lang_errors = detect_language_mismatch(
        ai_analysis,
        LANGUAGE,
        strict_mode=(VALIDATION_MODE == "strict")
    )
    for err in lang_errors:
        errors.append(f"❌ {err}")

    return errors


def verify_ai_analysis_monthly(ai_analysis):
    """验证月报AI分析长度"""
    errors = []
    total_units = 0
    unit_label = 'words' if LANGUAGE == 'EN' else '字'

    # 收集所有文本
    hrv_analysis = ai_analysis.get('hrv_analysis') or ai_analysis.get('monthly_analysis', '')
    sleep_analysis = ai_analysis.get('sleep_analysis', '')
    activity_analysis = ai_analysis.get('activity_analysis') or ai_analysis.get('key_findings', '')
    trend_assessment = ai_analysis.get('trend_assessment') or ai_analysis.get('trend_forecast', '')

    total_units += count_text_units(hrv_analysis, LANGUAGE)
    total_units += count_text_units(sleep_analysis, LANGUAGE)
    total_units += count_text_units(activity_analysis, LANGUAGE)
    total_units += count_text_units(trend_assessment, LANGUAGE)

    recommendations = ai_analysis.get('recommendations', [])
    rec_errors = _validate_recommendations(recommendations, context=_err('monthly_label'))
    errors.extend(rec_errors)

    if not rec_errors:
        for rec in recommendations:
            total_units += count_text_units(rec.get('title', ''), LANGUAGE)
            total_units += count_text_units(rec.get('content', ''), LANGUAGE)

    # 检查月报总长度（要求≥MONTHLY_MIN_WORDS）
    if total_units < MONTHLY_MIN_WORDS:
        errors.append(_err('monthly_total_short', current=total_units, unit=unit_label, minimum=MONTHLY_MIN_WORDS))

    # 同时检查 trend_assessment 单独长度（默认150，可由 analysis_limits.monthly_trend_min_words 覆盖）
    trend_text_clean = trend_assessment.replace('<strong>', '').replace('</strong>', '').replace('<br>', '').replace('\n', '')
    trend_units = count_text_units(trend_text_clean, LANGUAGE)
    if trend_units < MONTHLY_TREND_MIN_WORDS:
        errors.append(_err('monthly_trend_short', current=trend_units, unit=unit_label, minimum=MONTHLY_TREND_MIN_WORDS))

    # 语言一致性校验
    lang_errors = detect_language_mismatch(
        ai_analysis,
        LANGUAGE,
        strict_mode=(VALIDATION_MODE == "strict")
    )
    for err in lang_errors:
        errors.append(f"❌ {err}")

    return errors

# ==================== 趋势计算函数 ====================
def load_previous_week_data(current_dates, member_name="默认用户"):
    """加载上一周完整数据（周一至周日）- V5.8.1

    正确的趋势对比逻辑：
    - 当前周：本周一至本周日（7天）
    - 对比周：上周一至上周日（7天）
    - 计算两周平均值的环比变化

    参数:
        current_dates: 当前周的日期列表，如 ['2026-03-01', '2026-03-02', ...]
        member_name: 成员名称
    """
    if not current_dates:
        return []

    # 找到当前周的起始日（周一）
    current_dates_sorted = sorted(current_dates)
    current_start = datetime.strptime(current_dates_sorted[0], '%Y-%m-%d')

    # 计算上周的起始日（再往前推7天）
    prev_week_start = current_start - timedelta(days=7)

    # 生成上周的7天日期（周一至周日）
    previous_dates = [
        (prev_week_start + timedelta(days=i)).strftime('%Y-%m-%d')
        for i in range(7)
    ]

    print(f"📊 趋势对比: 本周 {current_dates_sorted[0]} 至 {current_dates_sorted[-1]}")
    print(f"   对比上周 {previous_dates[0]} 至 {previous_dates[-1]}")

    # 加载上周数据
    previous_data = []
    for date in previous_dates:
        data = load_cache(date, member_name)
        if data:
            previous_data.append(data)

    return previous_data

def calculate_trend(current_values, previous_values):
    """计算趋势变化（环比）"""
    # 过滤掉 None 和非数字值
    current_values = [v for v in current_values if isinstance(v, (int, float)) and v is not None]
    previous_values = [v for v in previous_values if isinstance(v, (int, float)) and v is not None]
    
    # 确保列表不为空且长度足够
    if not current_values or not previous_values:
        return 0, 'stable'
    
    # 确保有足够的数据点（至少各1个）
    if len(current_values) < 1 or len(previous_values) < 1:
        return 0, 'stable'

    current_avg = sum(current_values) / len(current_values)
    previous_avg = sum(previous_values) / len(previous_values)

    # 增强的除零检查：previous_avg 为 0 或接近 0 都视为无效
    if previous_avg == 0 or abs(previous_avg) < 0.0001 or current_avg == 0:
        return 0, 'stable'
    
    # 检查数值是否有效（非 NaN, Inf）
    if not (math.isfinite(current_avg) and math.isfinite(previous_avg)):
        return 0, 'stable'
    
    change_pct = ((current_avg - previous_avg) / previous_avg) * 100
    
    # 检查结果有效性
    if not math.isfinite(change_pct):
        return 0, 'stable'

    if change_pct > 5:
        return change_pct, 'increase'
    elif change_pct < -5:
        return change_pct, 'decrease'
    else:
        return change_pct, 'stable'

def get_trend_html(change_pct, trend_type):
    """生成趋势变化HTML"""
    if trend_type == 'increase':
        return f"↑ {change_pct:+.1f}%", 'change-up'
    elif trend_type == 'decrease':
        return f"↓ {change_pct:+.1f}%", 'change-down'
    else:
        if LANGUAGE == 'EN':
            return "→ Stable", 'change-stable'
        else:
            return "→ 持平", 'change-stable'

# 多语言文本
def get_text(key):
    """获取多语言文本"""
    texts = {
        "CN": {
            "no_trend_data": "暂无趋势数据",
            "no_monthly_data": "暂无月度趋势数据",
            "date": "日期",
            "hrv": "HRV",
            "steps": "步数",
            "sleep": "睡眠",
            "active_energy": "活动能量",
            "workout": "运动",
            "recovery": "恢复度",
            "week": "周",
            "high_priority": "🔴 高优先级",
            "medium_priority": "🟡 中优先级",
            "low_priority": "🔵 低优先级",
            "good": "良好",
            "days": "天",
        },
        "EN": {
            "no_trend_data": "No trend data available",
            "no_monthly_data": "No monthly trend data available",
            "date": "Date",
            "hrv": "HRV",
            "steps": "Steps",
            "sleep": "Sleep",
            "active_energy": "Active Energy",
            "workout": "Workout",
            "recovery": "Recovery",
            "week": "Week",
            "high_priority": "🔴 High Priority",
            "medium_priority": "🟡 Medium Priority",
            "low_priority": "🔵 Low Priority",
            "good": "Good",
            "days": "days",
        }
    }
    return texts.get(LANGUAGE, texts["CN"]).get(key, key)


def safe_html_text(value) -> str:
    if value is None:
        return ''
    return html_escape(str(value), quote=True)


def safe_html_paragraph(value) -> str:
    return safe_html_text(value).replace('\n', '<br>')


def load_cache(date_str, member_name="默认用户"):
    """加载单日缓存数据 - V5.8.1: 支持 safe_name 命名规则"""
    safe_name = safe_member_name(member_name)

    # 三级读取顺序：safe_name -> 原始name -> 旧格式
    cache_paths = [
        CACHE_DIR / f'{date_str}_{safe_name}.json',
        CACHE_DIR / f'{date_str}_{member_name}.json',
        CACHE_DIR / f'{date_str}.json',  # 旧格式兜底
    ]

    for cache_path in cache_paths:
        if cache_path.exists():
            with open(cache_path, 'r', encoding='utf-8') as f:
                return json.load(f)
    return None

def _sleep_total(sleep_obj: dict) -> float:
    """兼容新旧睡眠字段：total_hours / total"""
    if not isinstance(sleep_obj, dict):
        return 0.0
    value = sleep_obj.get('total_hours', sleep_obj.get('total', 0))
    if value is None:
        return 0.0
    try:
        return float(value)
    except (ValueError, TypeError):
        return 0.0


def _active_energy_kcal(day_obj: dict):
    """兼容活动能量字段：active_energy（新）/ active_energy_kcal（旧）"""
    if not isinstance(day_obj, dict):
        return 0.0
    v = day_obj.get('active_energy')
    if isinstance(v, (int, float)):
        return float(v)
    v = day_obj.get('active_energy_kcal')
    if isinstance(v, (int, float)):
        return float(v)
    return 0.0


def _stand_hours(day_obj: dict):
    """兼容站立时长字段：apple_stand_hour（小时）/ apple_stand_time（分钟）/ stand_time_min（分钟）"""
    if not isinstance(day_obj, dict):
        return 0.0

    stand_hour_raw = day_obj.get('apple_stand_hour')
    if isinstance(stand_hour_raw, (int, float)):
        return float(stand_hour_raw)

    stand_min_raw = day_obj.get('apple_stand_time')
    if isinstance(stand_min_raw, (int, float)):
        return float(stand_min_raw) / 60.0

    stand_min_legacy = day_obj.get('stand_time_min')
    if isinstance(stand_min_legacy, (int, float)):
        return float(stand_min_legacy) / 60.0

    return 0.0


def _build_triple_chartjs_template(canvas_id_prefix, display_dates, hrv_values, steps_values, sleep_values, lang_labels, height_px_per_chart=160):
    """V6.0.5: 构建三个上下排列的图表 - HRV、步数、睡眠各一个"""
    from html import escape as html_escape
    
    # 转义标签防止 XSS
    hrv_label = html_escape(lang_labels["hrv"])
    steps_label = html_escape(lang_labels["steps"])
    sleep_label = html_escape(lang_labels["sleep"])
    
    def calc_range(values, min_default, max_default, padding=0.1):
        valid = [v for v in values if isinstance(v, (int, float))]
        if not valid:
            return min_default, max_default
        min_val = min(valid)
        max_val = max(valid)
        range_val = max_val - min_val
        if range_val == 0:
            range_val = max(abs(max_val), 1.0) * 0.1
        padding_val = range_val * padding
        return max(0, min_val - padding_val), max_val + padding_val

    def js_array(values, transform=None):
        arr = []
        for v in values:
            if isinstance(v, (int, float)):
                val = transform(v) if transform else v
                arr.append(f"{float(val):.6g}")
            else:
                arr.append('null')
        return ','.join(arr)

    hrv_min, hrv_max = calc_range(hrv_values, 30, 100)
    sleep_min, sleep_max = calc_range(sleep_values, 0, 10)
    steps_normalized = [s / 1000 for s in steps_values if isinstance(s, (int, float))]
    steps_min, steps_max = calc_range(steps_normalized, 0, 15)

    hrv_js = js_array(hrv_values)
    steps_js = js_array(steps_values, transform=lambda x: x / 1000)
    sleep_js = js_array(sleep_values)
    
    total_height = height_px_per_chart * 3 + 40
    
    return f'''<div style="height: {total_height}px; width: 88%; padding-right: 100px; margin: 0 auto; box-sizing: border-box;">
  <div style="height: {height_px_per_chart}px; margin-bottom: 20px; width: 100%;">
    <canvas id="{canvas_id_prefix}_hrv"></canvas>
  </div>
  <div style="height: {height_px_per_chart}px; margin-bottom: 20px; width: 100%;">
    <canvas id="{canvas_id_prefix}_steps"></canvas>
  </div>
  <div style="height: {height_px_per_chart}px; width: 100%;">
    <canvas id="{canvas_id_prefix}_sleep"></canvas>
  </div>
</div>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<script>
  (function() {{
    new Chart(document.getElementById('{canvas_id_prefix}_hrv').getContext('2d'), {{
      type: 'line',
      data: {{
        labels: {display_dates},
        datasets: [{{
          label: '{hrv_label}',
          data: [{hrv_js}],
          borderColor: '#22C55E',
          backgroundColor: 'rgba(34, 197, 94, 0.1)',
          tension: 0.3,
          fill: true,
          pointRadius: 4,
          clip: false
        }}]
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: false,
        layout: {{ padding: {{ right: 80 }} }},
        plugins: {{
          legend: {{ display: false }},
          title: {{ display: true, text: '{hrv_label}', font: {{ size: 12 }}, align: 'start' }}
        }},
        scales: {{
          x: {{ offset: false, grid: {{ display: true }}, ticks: {{ font: {{ size: 10 }} }} }},
          y: {{
            type: 'linear', display: true, position: 'left',
            title: {{ display: true, text: 'ms', font: {{ size: 10 }} }},
            min: {int(hrv_min)}, max: {int(hrv_max)},
            ticks: {{ font: {{ size: 10 }} }}
          }}
        }}
      }}
    }});
    
    new Chart(document.getElementById('{canvas_id_prefix}_steps').getContext('2d'), {{
      type: 'line',
      data: {{
        labels: {display_dates},
        datasets: [{{
          label: '{steps_label}',
          data: [{steps_js}],
          borderColor: '#3B82F6',
          backgroundColor: 'rgba(59, 130, 246, 0.1)',
          tension: 0.3,
          fill: true,
          pointRadius: 4,
          clip: false
        }}]
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: false,
        layout: {{ padding: {{ right: 80 }} }},
        plugins: {{
          legend: {{ display: false }},
          title: {{ display: true, text: '{steps_label}', font: {{ size: 12 }}, align: 'start' }}
        }},
        scales: {{
          x: {{ offset: false, grid: {{ display: true }}, ticks: {{ font: {{ size: 10 }} }} }},
          y: {{
            type: 'linear', display: true, position: 'left',
            title: {{ display: true, text: 'k', font: {{ size: 10 }} }},
            min: {int(steps_min)}, max: {int(steps_max)},
            ticks: {{ font: {{ size: 10 }} }}
          }}
        }}
      }}
    }});
    
    new Chart(document.getElementById('{canvas_id_prefix}_sleep').getContext('2d'), {{
      type: 'line',
      data: {{
        labels: {display_dates},
        datasets: [{{
          label: '{sleep_label}',
          data: [{sleep_js}],
          borderColor: '#A855F7',
          backgroundColor: 'rgba(168, 85, 247, 0.1)',
          tension: 0.3,
          fill: true,
          pointRadius: 4,
          clip: false
        }}]
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: false,
        layout: {{ padding: {{ right: 80 }} }},
        plugins: {{
          legend: {{ display: false }},
          title: {{ display: true, text: '{sleep_label}', font: {{ size: 12 }}, align: 'start' }}
        }},
        scales: {{
          x: {{ offset: false, grid: {{ display: true }}, ticks: {{ font: {{ size: 10 }} }} }},
          y: {{
            type: 'linear', display: true, position: 'left',
            title: {{ display: true, text: 'h', font: {{ size: 10 }} }},
            min: {sleep_min:.1f}, max: {sleep_max:.1f},
            ticks: {{ font: {{ size: 10 }} }}
          }}
        }}
      }}
    }});
  }})();
</script>'''

def generate_trend_chart(dates, hrv_values, steps_values, sleep_values, chart_type='weekly'):
    """V6.0.5: 生成三个上下排列的Chart.js趋势图表"""
    valid_hrv = [v for v in hrv_values if isinstance(v, (int, float))]
    if not dates or not valid_hrv:
        return f'<div style="text-align:center;color:#999;padding:40px;">{get_text("no_trend_data")}</div>'

    display_dates = [d[5:] if len(d) > 5 else d for d in dates]

    labels = {
        "CN": {"hrv": "HRV (ms)", "steps": "步数 (÷1000)", "sleep": "睡眠 (小时)"},
        "EN": {"hrv": "HRV (ms)", "steps": "Steps (÷1000)", "sleep": "Sleep (hours)"}
    }
    lang_labels = labels.get(LANGUAGE, labels["CN"])

    return _build_triple_chartjs_template('trendChart', display_dates, hrv_values, steps_values, sleep_values, lang_labels, 160)

def generate_monthly_chart(dates, hrv_values, steps_values, sleep_values):
    """V6.0.5: 生成月度三Chart.js趋势图表"""
    valid_hrv = [v for v in hrv_values if isinstance(v, (int, float))]
    if not dates or not valid_hrv:
        return f'<div style="text-align:center;color:#999;padding:40px;">{get_text("no_monthly_data")}</div>'

    if LANGUAGE == "CN":
        display_dates = [d[8:10] + '日' if len(d) >= 10 else d for d in dates]
    else:
        display_dates = [d[8:10] if len(d) >= 10 else d for d in dates]

    labels = {
        "CN": {"hrv": "HRV (ms)", "steps": "步数 (÷1000)", "sleep": "睡眠 (小时)"},
        "EN": {"hrv": "HRV (ms)", "steps": "Steps (÷1000)", "sleep": "Sleep (hours)"}
    }
    lang_labels = labels.get(LANGUAGE, labels["CN"])

    return _build_triple_chartjs_template('monthlyChart', display_dates, hrv_values, steps_values, sleep_values, lang_labels, 160)

def generate_weekly_report(start_date, end_date, ai_analysis, template, member_name="默认用户"):
    """生成周报 - 使用Medical Dashboard模板"""

    # 计算日期范围
    start = datetime.strptime(start_date, '%Y-%m-%d')
    end = datetime.strptime(end_date, '%Y-%m-%d')
    week_dates = []
    current = start
    while current <= end:
        week_dates.append(current.strftime('%Y-%m-%d'))
        current += timedelta(days=1)

    # 加载每日数据
    weekly_data = []
    for date in week_dates:
        data = load_cache(date, member_name)
        if data:
            weekly_data.append(data)

    if not weekly_data:
        print(f"⚠️ 警告: 未找到 {start_date} 至 {end_date} 的缓存数据")
        return None

    # 计算统计数据（按完整日期对齐，缺失天补 None，避免图表错位）
    daily_map = {d.get('date'): d for d in weekly_data if d.get('date')}

    hrv_series = []
    steps_series = []
    sleep_series = []
    for date in week_dates:
        item = daily_map.get(date, {})

        hrv_val = item.get('hrv', {}).get('value') if isinstance(item.get('hrv'), dict) else None
        hrv_series.append(hrv_val if isinstance(hrv_val, (int, float)) else None)

        steps_val = item.get('steps')
        steps_series.append(steps_val if isinstance(steps_val, (int, float)) else None)

        sleep_val = _sleep_total(item.get('sleep'))
        sleep_series.append(sleep_val if sleep_val > 0 else None)

    hrv_values = [v for v in hrv_series if isinstance(v, (int, float))]
    steps_values = [v for v in steps_series if isinstance(v, (int, float))]
    sleep_values = [v for v in sleep_series if isinstance(v, (int, float))]

    workout_days = sum(1 for d in weekly_data if d.get('has_workout'))

    avg_hrv = sum(hrv_values) / len(hrv_values) if hrv_values else 0
    avg_steps = sum(steps_values) / len(steps_values) if steps_values else 0
    avg_sleep = sum(sleep_values) / len(sleep_values) if sleep_values else 0

    # 生成每日明细行
    daily_rows = []
    for date in week_dates:
        data = load_cache(date, member_name)
        if data:
            workout_mark = '✓' if data.get('has_workout') else '-'

            hrv_val = data.get('hrv', {}).get('value') if isinstance(data.get('hrv'), dict) else None
            hrv_text = f"{hrv_val:.1f}" if isinstance(hrv_val, (int, float)) else '--'

            steps_val = data.get('steps')
            steps_text = f"{int(steps_val):,}" if isinstance(steps_val, (int, float)) else '--'

            sleep_val = _sleep_total(data.get('sleep'))
            sleep_text = f"{sleep_val:.1f}h" if sleep_val > 0 else '--'

            active_energy_val = _active_energy_kcal(data)
            active_energy_text = f"{int(active_energy_val)}kcal" if isinstance(active_energy_val, (int, float)) else '--'

            row = f"""<tr>
                <td>{date[5:]}</td>
                <td class="cell-primary">{hrv_text}</td>
                <td class="cell-primary">{steps_text}</td>
                <td class="cell-primary">{sleep_text}</td>
                <td>{active_energy_text}</td>
                <td>{workout_mark}</td>
                <td><span class="rating rating-good">{get_text('good')}</span></td>
            </tr>"""
            daily_rows.append(row)

    # 填充模板
    html = template
    html = html.replace('{{START_DATE}}', start_date)
    html = html.replace('{{END_DATE}}', end_date)

    # V5.8.1: 使用统一的周范围格式化
    week_range_text = format_week_range(start_date, end_date, LANGUAGE)
    html = html.replace('{{WEEK_RANGE}}', week_range_text)

    html = html.replace('{{DAYS_COUNT}}', str(len(weekly_data)))

    # 概览数据
    html = html.replace('{{AVG_HRV}}', f"{avg_hrv:.1f}")
    html = html.replace('{{AVG_STEPS}}', f"{int(avg_steps):,}")
    html = html.replace('{{AVG_SLEEP}}', f"{avg_sleep:.1f}")
    html = html.replace('{{WORKOUT_DAYS}}', str(workout_days))
    html = html.replace('{{WORKOUT_RATIO}}', f"{workout_days}/{len(weekly_data)} {get_text('days')}")

    # V6.0.0: 计算周报 Body Age (直接使用 weekly_data 列表)
    
    # 获取成员配置
    members = CONFIG.get('members', [])
    member_cfg = None
    for m in members:
        if m.get('name') == member_name or safe_member_name(m.get('name', '')) == safe_member_name(member_name):
            member_cfg = m
            break
    
    if member_cfg:
        body_age_result = calculate_body_age(weekly_data, member_cfg.get('age', 30), member_cfg.get('gender', 'male'))
        html = html.replace('{{WEEKLY_BODY_AGE}}', str(body_age_result.body_age))
        html = html.replace('{{WEEKLY_AGE_IMPACT}}', f"{body_age_result.age_impact:+.1f}")
    else:
        html = html.replace('{{WEEKLY_BODY_AGE}}', '--')
        html = html.replace('{{WEEKLY_AGE_IMPACT}}', '--')

    # V6.0.2: 计算本周心率区间分布
    weekly_zone_times = {'zone_1': 0, 'zone_2': 0, 'zone_3': 0, 'zone_4': 0, 'zone_5': 0}
    for day in weekly_data:
        hs = day.get('health_scores', {})
        zt = hs.get('zone_times', {})
        for zone in ['zone_1', 'zone_2', 'zone_3', 'zone_4', 'zone_5']:
            weekly_zone_times[zone] += zt.get(zone, 0)

    # 转换为小时
    weekly_zone_hours = {}
    for zone in weekly_zone_times:
        weekly_zone_hours[zone] = round(weekly_zone_times[zone] / 60, 1)

    # 计算总时间和百分比
    total_zone_minutes = sum(weekly_zone_times.values())
    total_zone_hours = round(total_zone_minutes / 60, 1)

    if total_zone_minutes > 0:
        zone_percentages = {}
        for zone in weekly_zone_times:
            zone_percentages[zone] = round(weekly_zone_times[zone] / total_zone_minutes * 100, 1)
    else:
        zone_percentages = {z: 0 for z in weekly_zone_times}

    # 确定主要训练区间
    max_zone = max(weekly_zone_hours, key=weekly_zone_hours.get)
    zone_names = {
        'zone_1': 'Zone 1 (恢复/热身)',
        'zone_2': 'Zone 2 (有氧燃脂)',
        'zone_3': 'Zone 3 (有氧耐力)',
        'zone_4': 'Zone 4 (乳酸阈值)',
        'zone_5': 'Zone 5 (无氧极限)'
    }
    primary_zone = zone_names.get(max_zone, 'Zone 1')

    # 模板替换
    html = html.replace('{{WEEKLY_ZONE_1}}', str(weekly_zone_hours['zone_1']))
    html = html.replace('{{WEEKLY_ZONE_2}}', str(weekly_zone_hours['zone_2']))
    html = html.replace('{{WEEKLY_ZONE_3}}', str(weekly_zone_hours['zone_3']))
    html = html.replace('{{WEEKLY_ZONE_4}}', str(weekly_zone_hours['zone_4']))
    html = html.replace('{{WEEKLY_ZONE_5}}', str(weekly_zone_hours['zone_5']))
    html = html.replace('{{WEEKLY_ZONE_1_PCT}}', str(zone_percentages['zone_1']))
    html = html.replace('{{WEEKLY_ZONE_2_PCT}}', str(zone_percentages['zone_2']))
    html = html.replace('{{WEEKLY_ZONE_3_PCT}}', str(zone_percentages['zone_3']))
    html = html.replace('{{WEEKLY_ZONE_4_PCT}}', str(zone_percentages['zone_4']))
    html = html.replace('{{WEEKLY_ZONE_5_PCT}}', str(zone_percentages['zone_5']))
    html = html.replace('{{WEEKLY_TOTAL_ZONE_TIME}}', str(total_zone_hours))
    html = html.replace('{{WEEKLY_PRIMARY_ZONE}}', primary_zone)

    # V6.0.5: 统一使用 health_score.py 的 Body Age / Pace of Aging 语义
    body_ages = []
    age_impacts = []
    pace_values = []

    for day in weekly_data:
        hs = day.get('health_scores', {})
        body_age = hs.get('body_age')
        if isinstance(body_age, (int, float)):
            body_ages.append(float(body_age))

        age_impact = hs.get('age_impact')
        if isinstance(age_impact, (int, float)):
            age_impacts.append(float(age_impact))

        pace_value = hs.get('pace_of_aging')
        if isinstance(pace_value, (int, float)) and math.isfinite(pace_value):
            pace_values.append(float(pace_value))

    # 计算数据完整度
    data_completeness = len(weekly_data) / 7.0  # 假设一周7天

    # 加载上一周期数据用于趋势对比
    print(f"📊 计算趋势变化...")
    previous_data = load_previous_week_data(week_dates, member_name)

    # Pace 优先使用日报已缓存结果；不足时使用 simple 版本（周报只有7天数据）
    if len(pace_values) >= 3:
        avg_pace = sum(pace_values) / len(pace_values)
    elif member_cfg:
        # 周报只有7天数据，使用 simple 版本
        from health_score import calculate_pace_of_aging_simple
        current_7day = {'recovery': sum(d.get('health_scores', {}).get('recovery', 50) for d in weekly_data) / len(weekly_data)}
        # 加载前一周数据
        prev_week_dates = [(datetime.strptime(end_date, '%Y-%m-%d') - timedelta(days=7+i)).strftime('%Y-%m-%d') for i in range(7)]
        prev_data = [load_cache(d, member_name) for d in prev_week_dates]
        prev_data = [d for d in prev_data if d]
        if prev_data:
            prev_7day = {'recovery': sum(d.get('health_scores', {}).get('recovery', 50) for d in prev_data) / len(prev_data)}
        else:
            prev_7day = {'recovery': 50}
        avg_pace = calculate_pace_of_aging_simple(current_7day, prev_7day)
    else:
        avg_pace = None

    if avg_pace is None:
        avg_pace = 1.0

    # 安全计算平均值
    avg_body_age = sum(body_ages) / len(body_ages) if body_ages else (member_cfg.get('age', 30) if member_cfg else 30)
    avg_age_impact = sum(age_impacts) / len(age_impacts) if age_impacts else 0.0

    display_pace = max(0.5, min(2.0, float(avg_pace)))

    html = html.replace('{{AVERAGE_PACE_OF_AGING}}', f'{display_pace:.2f}')
    html = html.replace('{{AVERAGE_BODY_AGE}}', f'{avg_body_age:.1f}')
    html = html.replace('{{AVERAGE_AGE_IMPACT}}', f"{avg_age_impact:+.1f}")
    html = html.replace('{{CHRONOLOGICAL_AGE}}', str(member_cfg.get('age', 30) if member_cfg else 30))

    if avg_age_impact < 0:
        age_box_class = "younger"
        age_diff_color = "#55efc4"
    elif avg_age_impact > 0:
        age_box_class = "older"
        age_diff_color = "#ff7675"
    else:
        age_box_class = ""
        age_diff_color = "#dfe6e9"

    if data_completeness < 0.7:
        pace_desc = "数据不足 ⚪ - 需要更多天数计算趋势" if LANGUAGE == "CN" else "Insufficient Data ⚪ - More days needed"
        pace_class = "stable"
        pace_color = "#b2bec3"
    elif display_pace < 0.85:
        pace_desc = "逆龄中 🟢 - 最近趋势优于实际年龄" if LANGUAGE == "CN" else "Reverse Aging 🟢 - Trending younger"
        pace_class = "reverse"
        pace_color = "#55efc4"
    elif display_pace <= 1.15:
        pace_desc = "正常速度 ⚪ - 与实际年龄基本同步" if LANGUAGE == "CN" else "Normal Pace ⚪ - Roughly age-matched"
        pace_class = "stable"
        pace_color = "#74b9ff"
    elif display_pace <= 1.35:
        pace_desc = "略快于正常 🟡 - 建议关注恢复与睡眠" if LANGUAGE == "CN" else "Slightly Fast 🟡 - Watch recovery and sleep"
        pace_class = "normal"
        pace_color = "#fdcb6e"
    else:
        pace_desc = "加速衰老 🔴 - 近期趋势偏差较明显" if LANGUAGE == "CN" else "Accelerated 🔴 - Clear recent deterioration"
        pace_class = "accelerated"
        pace_color = "#ff7675"

    html = html.replace('{{AGE_BOX_CLASS}}', age_box_class)
    html = html.replace('{{AGE_DIFF_COLOR}}', age_diff_color)
    html = html.replace('{{PACE_CLASS}}', pace_class)
    html = html.replace('{{PACE_COLOR}}', pace_color)
    html = html.replace('{{PACE_DESC}}', pace_desc)

    # 验证AI分析长度
    print(f"📏 验证AI分析长度...")
    validation_errors = verify_ai_analysis_weekly(ai_analysis)
    if validation_errors:
        print(_err('validation_found', count=len(validation_errors)))
        for error in validation_errors:
            print(f"   {error}")
        if VALIDATION_MODE == "strict":
            print(_err('strict_stop'))
            return None
        else:
            print(_err('warn_continue'))
    else:
        print(f"   ✅ 长度验证通过")

    # 计算趋势变化 (previous_data 已在 pace 计算时加载)
    print(f"📊 计算趋势变化...")
    if previous_data:
        prev_hrv = [d['hrv']['value'] for d in previous_data if d.get('hrv', {}).get('value')]
        prev_steps = [d['steps'] for d in previous_data if d.get('steps')]
        prev_sleep = [_sleep_total(d.get('sleep')) for d in previous_data if _sleep_total(d.get('sleep')) > 0]

        hrv_change_pct, hrv_trend = calculate_trend(hrv_values, prev_hrv)
        steps_change_pct, steps_trend = calculate_trend(steps_values, prev_steps)
        sleep_change_pct, sleep_trend = calculate_trend(sleep_values, prev_sleep)

        hrv_change_html, hrv_class = get_trend_html(hrv_change_pct, hrv_trend)
        steps_change_html, steps_class = get_trend_html(steps_change_pct, steps_trend)
        sleep_change_html, sleep_class = get_trend_html(sleep_change_pct, sleep_trend)

        print(f"   HRV: {hrv_change_html}, 步数: {steps_change_html}, 睡眠: {sleep_change_html}")
    else:
        print(f"   ⚠️  未找到上一周期数据，趋势显示为持平")
        hrv_change_html, hrv_class = get_trend_html(0, 'stable')
        steps_change_html, steps_class = get_trend_html(0, 'stable')
        sleep_change_html, sleep_class = get_trend_html(0, 'stable')

    # 趋势变化
    html = html.replace('{{HRV_CHANGE}}', hrv_change_html)
    html = html.replace('{{STEPS_CHANGE}}', steps_change_html)
    html = html.replace('{{SLEEP_CHANGE}}', sleep_change_html)
    html = html.replace('{{HRV_TREND_CLASS}}', hrv_class)
    html = html.replace('{{STEPS_TREND_CLASS}}', steps_class)
    html = html.replace('{{SLEEP_TREND_CLASS}}', sleep_class)

    # 表格和AI分析
    html = html.replace('{{DAILY_ROWS}}', '\n'.join(daily_rows))

    # 生成真实趋势图表
    trend_chart = generate_trend_chart(week_dates, hrv_series, steps_series, sleep_series, 'weekly')
    html = html.replace('{{TREND_CHART}}', trend_chart)

    # AI趋势分析 - 严格检查，必须在当前session生成
    trend_analysis = ai_analysis.get('trend_analysis') or ai_analysis.get('weekly_analysis')
    if not trend_analysis:
        raise ValueError(_err('missing_weekly_trend'))
    html = html.replace('{{TREND_ANALYSIS}}', safe_html_paragraph(trend_analysis))

    # 下周建议 - 严格检查，必须在当前session生成
    recommendations = ai_analysis.get('recommendations', [])
    rec_errors = _validate_recommendations(recommendations, context=_err('weekly_label'))
    if rec_errors:
        raise ValueError(_err('invalid_weekly_recommendations', details='; '.join(rec_errors)))

    html = html.replace('{{RECOMMENDATIONS}}', generate_recommendations_html(recommendations))
    html = html.replace('{{DATA_SOURCE}}', 'Apple Health')

    unresolved = re.findall(r'\{\{[^{}]+\}\}', html)
    if unresolved:
        raise ValueError(f"模板占位符未替换: {unresolved[:10]}")

    return html

def generate_monthly_report(year, month, ai_analysis, template, member_name="默认用户"):
    """生成月报 - 使用Medical Dashboard模板"""

    # 计算月份天数
    if month == 12:
        next_month = datetime(year + 1, 1, 1)
    else:
        next_month = datetime(year, month + 1, 1)
    last_day = (next_month - timedelta(days=1)).day

    # 加载整月数据
    month_dates = [f"{year}-{month:02d}-{day:02d}" for day in range(1, last_day + 1)]
    monthly_data = []
    for date in month_dates:
        data = load_cache(date, member_name)
        if data:
            monthly_data.append(data)

    if not monthly_data:
        print(f"⚠️ 警告: 未找到 {year}-{month:02d} 的缓存数据")
        return None

    # 按周汇总
    weeks = {}
    for data in monthly_data:
        date = datetime.strptime(data['date'], '%Y-%m-%d')
        week_num = date.isocalendar()[1]
        if week_num not in weeks:
            weeks[week_num] = []
        weeks[week_num].append(data)

    # 计算每周统计
    weekly_rows = []
    for week_num, week_data in sorted(weeks.items()):
        hrv_values = []
        steps_values = []
        sleep_values = []

        for d in week_data:
            hrv_raw = d.get('hrv', {}).get('value') if isinstance(d.get('hrv'), dict) else None
            if isinstance(hrv_raw, (int, float)):
                hrv_values.append(float(hrv_raw))

            steps_raw = d.get('steps')
            if isinstance(steps_raw, (int, float)):
                steps_values.append(float(steps_raw))

            sleep_raw = _sleep_total(d.get('sleep'))
            if sleep_raw > 0:
                sleep_values.append(float(sleep_raw))

        workout_days = sum(1 for d in week_data if d.get('has_workout'))

        avg_hrv = sum(hrv_values) / len(hrv_values) if hrv_values else 0
        avg_steps = sum(steps_values) / len(steps_values) if steps_values else 0
        avg_sleep = sum(sleep_values) / len(sleep_values) if sleep_values else 0

        row = f"""<tr>
            <td>{get_text('week')} {week_num}</td>
            <td class="cell-primary">{avg_hrv:.1f}</td>
            <td class="cell-primary">{int(avg_steps):,}</td>
            <td class="cell-primary">{avg_sleep:.1f}h</td>
            <td>{workout_days} {get_text('days')}</td>
            <td><span class="rating rating-good">{get_text('good')}</span></td>
        </tr>"""
        weekly_rows.append(row)

    # 计算全月统计（图表序列按日期一一对齐）
    actual_dates = [d['date'] for d in monthly_data]
    hrv_series = []
    steps_series = []
    sleep_series = []
    active_energy_series = []
    stand_time_series = []

    for d in monthly_data:
        hrv_raw = d.get('hrv', {}).get('value') if isinstance(d.get('hrv'), dict) else None
        hrv_series.append(float(hrv_raw) if isinstance(hrv_raw, (int, float)) else None)

        steps_raw = d.get('steps')
        steps_series.append(float(steps_raw) if isinstance(steps_raw, (int, float)) else None)

        sleep_raw = _sleep_total(d.get('sleep'))
        sleep_series.append(float(sleep_raw) if sleep_raw > 0 else None)

        active_energy_raw = _active_energy_kcal(d)
        if isinstance(active_energy_raw, (int, float)):
            active_energy_series.append(float(active_energy_raw))

        stand_hours = _stand_hours(d)
        if isinstance(stand_hours, (int, float)):
            stand_time_series.append(float(stand_hours))

    # 计算平均值时过滤 None（但保留 0）
    hrv_values = [v for v in hrv_series if isinstance(v, (int, float))]
    steps_values = [v for v in steps_series if isinstance(v, (int, float))]
    sleep_values = [v for v in sleep_series if isinstance(v, (int, float))]
    active_energy_values = active_energy_series
    stand_time_values = stand_time_series
    workout_days = sum(1 for d in monthly_data if d.get('has_workout'))

    avg_hrv = sum(hrv_values) / len(hrv_values) if hrv_values else 0
    avg_steps = sum(steps_values) / len(steps_values) if steps_values else 0
    avg_sleep = sum(sleep_values) / len(sleep_values) if sleep_values else 0
    avg_calories = sum(active_energy_values) / len(active_energy_values) if active_energy_values else 0
    avg_stand = sum(stand_time_values) / len(stand_time_values) if stand_time_values else 0

    # 填充模板
    html = template
    html = html.replace('{{YEAR}}', str(year))
    html = html.replace('{{MONTH}}', str(month))
    html = html.replace('{{DAYS_COUNT}}', str(len(monthly_data)))
    html = html.replace('{{WEEKS_COUNT}}', str(len(weeks)))

    # 概览数据
    html = html.replace('{{AVG_HRV}}', f"{avg_hrv:.1f}")
    html = html.replace('{{AVG_STEPS}}', f"{int(avg_steps):,}")
    html = html.replace('{{AVG_SLEEP}}', f"{avg_sleep:.1f}")
    html = html.replace('{{WORKOUT_DAYS}}', str(workout_days))
    html = html.replace('{{WORKOUT_RATIO}}', f"{workout_days}/{len(monthly_data)} {get_text('days')}")
    html = html.replace('{{AVG_CALORIES}}', f"{int(avg_calories):,}")
    html = html.replace('{{AVG_STAND}}', f"{avg_stand:.1f}")
    
    # V6.0.0: 计算月报Body Age (直接使用 monthly_data 列表)
    
    # 获取成员配置
    members = CONFIG.get("members", [])
    member_cfg = None
    for m in members:
        if safe_member_name(m.get("name", "")) == safe_member_name(member_name):
            member_cfg = m
            break
    
    if member_cfg:
        body_age_result = calculate_body_age(monthly_data, member_cfg.get('age', 30), member_cfg.get('gender', 'male'))
        html = html.replace('{{MONTHLY_BODY_AGE}}', str(body_age_result.body_age))
        html = html.replace('{{MONTHLY_AGE_IMPACT}}', f"{body_age_result.age_impact:+.1f}")
    else:
        html = html.replace('{{MONTHLY_BODY_AGE}}', '--')
        html = html.replace('{{MONTHLY_AGE_IMPACT}}', '--')

    # 验证AI分析长度
    print(f"📏 验证AI分析长度...")
    validation_errors = verify_ai_analysis_monthly(ai_analysis)
    if validation_errors:
        print(_err('validation_found', count=len(validation_errors)))
        for error in validation_errors:
            print(f"   {error}")
        if VALIDATION_MODE == "strict":
            print(_err('strict_stop'))
            return None
        else:
            print(_err('warn_continue'))
    else:
        print(f"   ✅ 长度验证通过")

    # V5.8.1: 加载上一周期数据用于趋势对比（对比整月平均值）
    print(f"📊 计算趋势变化（对比整月平均值）...")

    # 计算上月日期范围
    if month == 1:
        prev_month = 12
        prev_year = year - 1
    else:
        prev_month = month - 1
        prev_year = year

    # 获取上月总天数
    if prev_month == 12:
        next_month_date = datetime(prev_year + 1, 1, 1)
    else:
        next_month_date = datetime(prev_year, prev_month + 1, 1)
    prev_month_last_day = (next_month_date - timedelta(days=1)).day

    # 生成上月所有日期
    prev_month_dates = [
        f"{prev_year}-{prev_month:02d}-{day:02d}"
        for day in range(1, prev_month_last_day + 1)
    ]

    # 加载上月所有可用数据
    previous_data = []
    for date in prev_month_dates:
        data = load_cache(date, member_name)
        if data:
            previous_data.append(data)

    if previous_data:
        print(f"   上月数据: {len(previous_data)}/{len(prev_month_dates)} 天")

    # 计算趋势变化（使用整月平均值，至少15天数据才计算趋势）
    if previous_data and len(previous_data) >= 15:
        prev_hrv = []
        prev_steps = []
        prev_sleep = []
        prev_calories = []
        prev_stand = []

        for d in previous_data:
            hrv_raw = d.get('hrv', {}).get('value') if isinstance(d.get('hrv'), dict) else None
            if isinstance(hrv_raw, (int, float)):
                prev_hrv.append(float(hrv_raw))

            steps_raw = d.get('steps')
            if isinstance(steps_raw, (int, float)):
                prev_steps.append(float(steps_raw))

            sleep_raw = _sleep_total(d.get('sleep'))
            if sleep_raw > 0:
                prev_sleep.append(float(sleep_raw))

            active_energy_raw = _active_energy_kcal(d)
            if isinstance(active_energy_raw, (int, float)):
                prev_calories.append(float(active_energy_raw))

            stand_hours = _stand_hours(d)
            if isinstance(stand_hours, (int, float)):
                prev_stand.append(float(stand_hours))

        hrv_change_pct, hrv_trend = calculate_trend(hrv_values, prev_hrv)
        steps_change_pct, steps_trend = calculate_trend(steps_values, prev_steps)
        sleep_change_pct, sleep_trend = calculate_trend(sleep_values, prev_sleep)
        calories_change_pct, calories_trend = calculate_trend(active_energy_values, prev_calories)
        stand_change_pct, stand_trend = calculate_trend(stand_time_values, prev_stand)

        print(f"   HRV: {hrv_change_pct:+.1f}%, 步数: {steps_change_pct:+.1f}%, 睡眠: {sleep_change_pct:+.1f}%")
    else:
        if previous_data:
            print(f"   ⚠️  上月数据不足（仅{len(previous_data)}天），不计算趋势")
        # 未找到数据的情况已在上方处理，此处不再重复打印
        # 设置为持平
        hrv_change_pct, hrv_trend = 0, 'stable'
        steps_change_pct, steps_trend = 0, 'stable'
        sleep_change_pct, sleep_trend = 0, 'stable'
        calories_change_pct, calories_trend = 0, 'stable'
        stand_change_pct, stand_trend = 0, 'stable'

    # 生成趋势 HTML
    hrv_change_html, hrv_class = get_trend_html(hrv_change_pct, hrv_trend)
    steps_change_html, steps_class = get_trend_html(steps_change_pct, steps_trend)
    sleep_change_html, sleep_class = get_trend_html(sleep_change_pct, sleep_trend)
    calories_change_html, calories_class = get_trend_html(calories_change_pct, calories_trend)
    stand_change_html, stand_class = get_trend_html(stand_change_pct, stand_trend)

    # 趋势变化
    html = html.replace('{{HRV_CHANGE}}', hrv_change_html)
    html = html.replace('{{STEPS_CHANGE}}', steps_change_html)
    html = html.replace('{{SLEEP_CHANGE}}', sleep_change_html)
    html = html.replace('{{CALORIES_CHANGE}}', calories_change_html)
    html = html.replace('{{STAND_CHANGE}}', stand_change_html)
    html = html.replace('{{HRV_TREND_CLASS}}', hrv_class)
    html = html.replace('{{STEPS_TREND_CLASS}}', steps_class)
    html = html.replace('{{SLEEP_TREND_CLASS}}', sleep_class)
    html = html.replace('{{CALORIES_TREND_CLASS}}', calories_class)
    html = html.replace('{{STAND_TREND_CLASS}}', stand_class)

    # 表格和AI分析
    html = html.replace('{{WEEKLY_ROWS}}', '\n'.join(weekly_rows))

    # 生成真实月度趋势图表 - 使用实际有数据的日期
    monthly_chart = generate_monthly_chart(actual_dates, hrv_series, steps_series, sleep_series)
    html = html.replace('{{MONTHLY_CHART}}', monthly_chart)

    # AI深度分析 - 严格检查，必须在当前session生成
    hrv_analysis = ai_analysis.get('hrv_analysis') or ai_analysis.get('monthly_analysis')
    if not hrv_analysis:
        raise ValueError(_err('missing_monthly_hrv'))

    sleep_analysis = ai_analysis.get('sleep_analysis')
    if not sleep_analysis:
        raise ValueError(_err('missing_monthly_sleep'))

    activity_analysis = ai_analysis.get('activity_analysis') or ai_analysis.get('key_findings')
    if not activity_analysis:
        raise ValueError(_err('missing_monthly_activity'))

    trend_assessment = ai_analysis.get('trend_assessment') or ai_analysis.get('trend_forecast')
    if not trend_assessment:
        raise ValueError(_err('missing_monthly_trend'))

    # trend_assessment 长度在 verify_ai_analysis_monthly() 中已统一校验，避免重复提示

    html = html.replace('{{HRV_ANALYSIS}}', safe_html_paragraph(hrv_analysis))
    html = html.replace('{{SLEEP_ANALYSIS}}', safe_html_paragraph(sleep_analysis))
    html = html.replace('{{ACTIVITY_ANALYSIS}}', safe_html_paragraph(activity_analysis))
    html = html.replace('{{TREND_ASSESSMENT}}', safe_html_paragraph(trend_assessment))

    # 下月建议 - 严格检查，必须在当前session生成，直接使用recommendations数组
    recommendations = ai_analysis.get('recommendations', [])
    rec_errors = _validate_recommendations(recommendations, context=_err('monthly_label'))
    if rec_errors:
        raise ValueError(_err('invalid_monthly_recommendations', details='; '.join(rec_errors)))

    html = html.replace('{{RECOMMENDATIONS}}', generate_recommendations_html(recommendations))
    html = html.replace('{{DATA_SOURCE}}', 'Apple Health')

    unresolved = re.findall(r'\{\{[^{}]+\}\}', html)
    if unresolved:
        raise ValueError(f"模板占位符未替换: {unresolved[:10]}")

    return html

def generate_recommendations_html(recommendations):
    """生成建议HTML - 将\n替换为<br>"""
    html_parts = []
    priority_classes = {'high': 'rec-high', 'medium': 'rec-medium', 'low': 'rec-low'}
    priority_labels = {
        'high': get_text('high_priority'),
        'medium': get_text('medium_priority'),
        'low': get_text('low_priority')
    }

    for rec in recommendations:
        p_class = priority_classes.get(rec.get('priority', 'medium'), 'rec-medium')
        p_label = priority_labels.get(rec.get('priority', 'medium'), get_text('medium_priority'))
        # 将\n替换为<br>以正确显示换行
        title = safe_html_text(rec.get('title', ''))
        content = safe_html_paragraph(rec.get('content', ''))

        html = f"""<div class="rec-card {p_class}">
            <div class="rec-priority">{safe_html_text(p_label)}</div>
            <div class="rec-title">{title}</div>
            <div class="rec-content">{content}</div>
        </div>"""
        html_parts.append(html)

    return '\n'.join(html_parts)

# 成员数量（最多3人）
MEMBERS = CONFIG.get("members", [])
MEMBER_COUNT = min(len(MEMBERS), MAX_MEMBERS)

def get_member_config(index: int):
    """获取指定成员的配置"""
    if index < len(MEMBERS):
        member = MEMBERS[index]
        return {
            "name": member.get("name", f"成员{index+1}"),
            "health_dir": Path(member.get("health_dir", "~/Health Auto Export/Health Data")).expanduser(),
            "workout_dir": Path(member.get("workout_dir", "~/Health Auto Export/Workout Data")).expanduser(),
            "email": member.get("email", "")
        }
    return {
        "name": f"成员{index+1}",
        "health_dir": Path('~/Health Auto Export/Health Data').expanduser(),
        "workout_dir": Path('~/Health Auto Export/Workout Data').expanduser(),
        "email": ""
    }

def main():
    # 自动删除旧的 ai_analysis.json 防止缓存问题
    from pathlib import Path
    workspace_dir = Path(__file__).parent.parent
    ai_analysis_file = workspace_dir / 'ai_analysis.json'

    if ai_analysis_file.exists():
        try:
            ai_analysis_file.unlink()
            print(f"🗑️  已删除旧的 AI 分析文件: {ai_analysis_file}")
        except Exception as e:
            print(f"⚠️  无法删除旧的 AI 分析文件: {e}", file=sys.stderr)

    if len(sys.argv) < 2:
        print('用法:')
        print('  周报: python3 scripts/generate_weekly_monthly_medical.py weekly <start_date> <end_date> < ai_analysis.json')
        print('  月报: python3 scripts/generate_weekly_monthly_medical.py monthly <year> <month> < ai_analysis.json')
        sys.exit(1)

    report_type = sys.argv[1]

    # 读取AI分析（使用安全解析）
    from utils import safe_json_loads
    input_text = sys.stdin.read()
    try:
        raw_ai_analyses = safe_json_loads(input_text, context="周报/月报AI分析JSON")
    except json.JSONDecodeError as e:
        print(_err('json_parse_error', error=e))
        sys.exit(1)

    if MEMBER_COUNT == 0:
        print(_err('no_members'))
        sys.exit(1)

    member_count = min(MEMBER_COUNT, MAX_MEMBERS)

    if isinstance(raw_ai_analyses, dict) and "members" in raw_ai_analyses:
        raw_ai_analyses = raw_ai_analyses["members"]

    if report_type == 'weekly':
        if len(sys.argv) < 4:
            print(_err('weekly_args_error'))
            sys.exit(1)

        start_date = sys.argv[2]
        end_date = sys.argv[3]

        # 加载模板 - V5.8.1: 使用灵活的模板选择
        from utils import get_template_path
        template_path = get_template_path("weekly", LANGUAGE, TEMPLATE_DIR)
        print(f"📄 使用模板: {template_path.name}")

        # 初始化计数器
        success_count = 0
        fail_count = 0
        skip_count = 0

        with open(template_path, 'r', encoding='utf-8') as f:
            template = f.read()

        for idx in range(member_count):
            member_cfg = get_member_config(idx)
            member_name = member_cfg['name']

            try:
                # 健壮的成员匹配逻辑 - V5.8.1: 使用 pick_member_ai_analysis
                ai_analysis = pick_member_ai_analysis(raw_ai_analyses, member_name, idx, strict=True)
                if not isinstance(ai_analysis, dict) or not ai_analysis:
                    print(f"⚠️ 未找到成员 {member_name} 的有效周报分析，跳过")
                    skip_count += 1
                    continue

                print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
                print(f"🧑 正在为成员 {idx+1}/{member_count} 生成周报: {member_name}")

                # 生成报告
                html = generate_weekly_report(start_date, end_date, ai_analysis, template, member_name)
                if not html:
                    fail_count += 1
                    continue

                safe_name = safe_member_name(member_name)

                # 保存HTML
                html_path = OUTPUT_DIR / f'{start_date}_to_{end_date}-weekly-medical-{safe_name}.html'
                html_path.write_text(html, encoding='utf-8')

                # 生成PDF
                pdf_path = OUTPUT_DIR / f'{start_date}_to_{end_date}-weekly-medical-{safe_name}.pdf'
                browser = None
                try:
                    with sync_playwright() as p:
                        browser = p.chromium.launch()
                        page = browser.new_page()
                        page.goto(html_path.resolve().as_uri())
                        page.wait_for_timeout(2500)
                        page.pdf(path=str(pdf_path), format='A4', print_background=True,
                                 margin={'top': '10mm', 'bottom': '10mm', 'left': '10mm', 'right': '10mm'})
                        browser.close()
                        browser = None
                except Exception as e:
                    if browser:
                        try:
                            browser.close()
                        except:
                            pass
                    raise

                if LANGUAGE == "EN":
                    print(f'✅ Weekly report generated: {pdf_path}')
                    print(f'   Period: {start_date} to {end_date}')
                else:
                    print(f'✅ 周报已生成: {pdf_path}')
                success_count += 1
                print(f'   周期: {start_date} 至 {end_date}')
            except Exception as e:
                print(f"❌ 成员 {member_name} 处理失败: {e}")
                import traceback
                traceback.print_exc()
                fail_count += 1
                continue

        # 周报摘要
        print(f"\n📊 周报生成摘要: 成功 {success_count}, 失败 {fail_count}, 跳过 {skip_count}")

    elif report_type == 'monthly':
        if len(sys.argv) < 4:
            print(_err('monthly_args_error'))
            sys.exit(1)

        try:
            year = int(sys.argv[2])
            month = int(sys.argv[3])
        except ValueError:
            print(_err('year_month_parse_error'))
            sys.exit(1)

        if month < 1 or month > 12:
            print(_err('month_range_error', month=month))
            sys.exit(1)

        # 加载模板 - V5.8.1: 使用灵活的模板选择
        from utils import get_template_path
        template_path = get_template_path("monthly", LANGUAGE, TEMPLATE_DIR)
        print(f"📄 使用模板: {template_path.name}")

        # 初始化计数器
        success_count = 0
        fail_count = 0
        skip_count = 0

        with open(template_path, 'r', encoding='utf-8') as f:
            template = f.read()

        for idx in range(member_count):
            member_cfg = get_member_config(idx)
            member_name = member_cfg['name']

            try:
                # 健壮的成员匹配逻辑 - V5.8.1: 使用 pick_member_ai_analysis
                ai_analysis = pick_member_ai_analysis(raw_ai_analyses, member_name, idx, strict=True)
                if not isinstance(ai_analysis, dict) or not ai_analysis:
                    print(f"⚠️ 未找到成员 {member_name} 的有效月报分析，跳过")
                    skip_count += 1
                    continue

                print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
                print(f"🧑 正在为成员 {idx+1}/{member_count} 生成月报: {member_name}")

                # 生成报告
                html = generate_monthly_report(year, month, ai_analysis, template, member_name)
                if not html:
                    fail_count += 1
                    continue

                safe_name = safe_member_name(member_name)

                # 保存HTML
                html_path = OUTPUT_DIR / f'{year}-{month:02d}-monthly-medical-{safe_name}.html'
                html_path.write_text(html, encoding='utf-8')

                # 生成PDF
                pdf_path = OUTPUT_DIR / f'{year}-{month:02d}-monthly-medical-{safe_name}.pdf'
                browser = None
                try:
                    with sync_playwright() as p:
                        browser = p.chromium.launch()
                        page = browser.new_page()
                        page.goto(html_path.resolve().as_uri())
                        page.wait_for_timeout(2500)
                        page.pdf(path=str(pdf_path), format='A4', print_background=True,
                                 margin={'top': '10mm', 'bottom': '10mm', 'left': '10mm', 'right': '10mm'})
                        browser.close()
                        browser = None
                except Exception as e:
                    if browser:
                        try:
                            browser.close()
                        except:
                            pass
                    raise

                success_count += 1

                if LANGUAGE == "EN":
                    print(f'✅ Monthly report generated: {pdf_path}')
                    print(f'   Month: {year}-{month:02d}')
                else:
                    print(f'✅ 月报已生成: {pdf_path}')
                    print(f'   月份: {year}年{month}月')
            except Exception as e:
                print(f"❌ 成员 {member_name} 处理失败: {e}")
                import traceback
                traceback.print_exc()
                fail_count += 1
                continue

        # 月报摘要
        print(f"\n📊 月报生成摘要: 成功 {success_count}, 失败 {fail_count}, 跳过 {skip_count}")

    else:
        print(_err('unknown_report_type', report_type=report_type))
        sys.exit(1)

    # 打印摘要并确定退出码
    print(f"\n{'='*60}")
    print(f"📊 生成摘要: 成功={success_count}, 失败={fail_count}, 跳过={skip_count}")
    print(f"{'='*60}")

    if success_count == 0 or fail_count > 0:
        sys.exit(1)
    sys.exit(0)

if __name__ == '__main__':
    main()
