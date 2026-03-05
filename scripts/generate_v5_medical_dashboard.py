#!/usr/bin/env python3
"""
V5.9.0 AI分析报告生成器 - Medical Dashboard 模板版
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
from html import escape as html_escape
from playwright.sync_api import sync_playwright

# V5.9.0: 使用共用工具函数
sys.path.insert(0, str(Path(__file__).parent))
from utils import load_config, safe_member_name, pick_member_ai_analysis, MAX_MEMBERS, KJ_TO_KCAL

# ==================== 全局配置（从 config.json 加载）====================
CONFIG = load_config()
LANGUAGE = str(CONFIG.get("language", "CN")).strip().upper()
if LANGUAGE not in ("CN", "EN"):
    LANGUAGE = "CN"
MEMBERS = CONFIG.get("members", [])
ANALYSIS_LIMITS = CONFIG.get("analysis_limits", {})

# 成员数量（最多3人）
MEMBER_COUNT = min(len(MEMBERS), MAX_MEMBERS)

# ==================== report_metrics 配置（V5.9.0 新增）====================
REPORT_METRICS_CFG = CONFIG.get("report_metrics", {})
REPORT_SELECTED_METRICS = REPORT_METRICS_CFG.get("selected", [])
REPORT_SHOW_EMPTY_CATEGORIES = bool(REPORT_METRICS_CFG.get("show_empty_categories", True))
REPORT_SORT_BY_IMPORTANCE = bool(REPORT_METRICS_CFG.get("sort_by_importance", True))
REPORT_HIDE_NO_DATA_METRICS = bool(REPORT_METRICS_CFG.get("hide_no_data_metrics", True))
REPORT_REQUIRE_AI_FOR_SELECTED = bool(REPORT_METRICS_CFG.get("require_ai_for_selected", False))

# 新字段优先，旧字段兼容
if "show_sleep_in_metrics_table" in REPORT_METRICS_CFG:
    REPORT_INCLUDE_SLEEP_METRICS_IN_TABLE = bool(REPORT_METRICS_CFG.get("show_sleep_in_metrics_table", False))
else:
    REPORT_INCLUDE_SLEEP_METRICS_IN_TABLE = bool(REPORT_METRICS_CFG.get("include_sleep_metrics_in_table", False))

CATEGORY_ORDER_OVERRIDE = REPORT_METRICS_CFG.get("category_order", [])
IMPORTANCE_OVERRIDES = REPORT_METRICS_CFG.get("importance_overrides", {})

DEFAULT_SELECTED_METRICS = [
    'hrv', 'resting_hr', 'steps', 'distance', 'active_energy', 'spo2',
    'flights_climbed', 'apple_stand_time', 'basal_energy_burned', 'respiratory_rate',
    'vo2_max', 'apple_exercise_time'
]

# ==================== 多语言错误消息 ====================
ERROR_MESSAGES = {
    "CN": {
        "missing_hrv": "❌ 错误: 缺少HRV分析 - 必须在当前AI对话中生成",
        "missing_resting_hr": "❌ 错误: 缺少静息心率分析 - 必须在当前AI对话中生成",
        "missing_steps": "❌ 错误: 缺少步数分析 - 必须在当前AI对话中生成",
        "missing_distance": "❌ 错误: 缺少距离分析 - 必须在当前AI对话中生成",
        "missing_active_energy": "❌ 错误: 缺少活动能量分析 - 必须在当前AI对话中生成",
        "missing_spo2": "❌ 错误: 缺少血氧分析 - 必须在当前AI对话中生成",
        "missing_flights": "❌ 错误: 缺少爬楼分析 - 必须在当前AI对话中生成",
        "missing_stand": "❌ 错误: 缺少站立时间分析 - 必须在当前AI对话中生成",
        "missing_basal": "❌ 错误: 缺少基础代谢分析 - 必须在当前AI对话中生成",
        "missing_respiratory": "❌ 错误: 缺少呼吸率分析 - 必须在当前AI对话中生成",
        "missing_sleep": "❌ 错误: 缺少睡眠分析 - 必须在当前AI对话中生成",
        "missing_workout": "❌ 错误: 缺少运动分析 - 必须在当前AI对话中生成（即使无运动也需分析）",
        "missing_fields": "❌ 错误: AI分析缺少以下字段，必须在当前AI对话中生成",
        "template_check_pass": "✅ 模板文件检查通过",
        "template_check_fail": "❌ 模板文件检查失败:",
    },
    "EN": {
        "missing_hrv": "❌ Error: Missing HRV analysis - must be generated in current AI session",
        "missing_resting_hr": "❌ Error: Missing Resting HR analysis - must be generated in current AI session",
        "missing_steps": "❌ Error: Missing Steps analysis - must be generated in current AI session",
        "missing_distance": "❌ Error: Missing Distance analysis - must be generated in current AI session",
        "missing_active_energy": "❌ Error: Missing Active Energy analysis - must be generated in current AI session",
        "missing_spo2": "❌ Error: Missing SpO2 analysis - must be generated in current AI session",
        "missing_flights": "❌ Error: Missing Flights Climbed analysis - must be generated in current AI session",
        "missing_stand": "❌ Error: Missing Stand Time analysis - must be generated in current AI session",
        "missing_basal": "❌ Error: Missing Basal Energy analysis - must be generated in current AI session",
        "missing_respiratory": "❌ Error: Missing Respiratory Rate analysis - must be generated in current AI session",
        "missing_sleep": "❌ Error: Missing Sleep analysis - must be generated in current AI session",
        "missing_workout": "❌ Error: Missing Workout analysis - must be generated in current AI session (even if no workout)",
        "missing_fields": "❌ Error: AI analysis missing required fields, must be generated in current AI session",
        "template_check_pass": "✅ Template files check passed",
        "template_check_fail": "❌ Template files check failed:",
    }
}

def get_error_msg(key: str) -> str:
    """获取当前语言的错误消息"""
    return ERROR_MESSAGES.get(LANGUAGE, ERROR_MESSAGES["EN"]).get(key, key)


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
MAX_LENGTH_METRIC = ANALYSIS_LIMITS.get("metric_max_words", 200)

# 优先级建议字数限制
MIN_LENGTH_PRIORITY_TITLE = 1
MIN_LENGTH_PRIORITY_PROBLEM = 1
MIN_LENGTH_PRIORITY_ACTION = ANALYSIS_LIMITS.get("action_min_words", 250)
MAX_LENGTH_PRIORITY_ACTION = ANALYSIS_LIMITS.get("action_max_words", 300)
MIN_LENGTH_PRIORITY_EXPECTATION = 1
MIN_LENGTH_AI2_TITLE = 1
MIN_LENGTH_AI2_PROBLEM = 1
MIN_LENGTH_AI2_ACTION = 1
MIN_LENGTH_AI2_EXPECTATION = 1
MIN_LENGTH_AI3_TITLE = 1
MIN_LENGTH_AI3_PROBLEM = 1
MIN_LENGTH_AI3_ACTION = 1
MIN_LENGTH_AI3_EXPECTATION = 1

# 饮食方案字数限制
MIN_LENGTH_BREAKFAST = 1      # 早餐最低字数
MIN_LENGTH_LUNCH = 1          # 午餐最低字数
MIN_LENGTH_DINNER = 1         # 晚餐最低字数
MIN_LENGTH_SNACK = 1          # 加餐最低字数

# 每日分析总字数下限
DAILY_MIN_WORDS = ANALYSIS_LIMITS.get("daily_min_words", 500)

# 验证模式：strict=严格模式(不满足则报错), warn=警告模式(只提示)
VALIDATION_MODE = CONFIG.get("validation_mode", "strict")  # 可选值: "strict", "warn"
# =====================================================

# ==================== 动态指标表配置（V5.9.0 新增）====================
CATEGORY_ORDER = [
    "core_health", "cardio_fitness", "sleep_recovery", "activity_mobility",
    "running_advanced", "walking_gait", "stairs_strength", "environment_audio"
]

CATEGORY_LABELS = {
    "CN": {
        "core_health": "核心健康",
        "cardio_fitness": "心肺能力",
        "sleep_recovery": "睡眠恢复",
        "activity_mobility": "活动与机能",
        "running_advanced": "高级跑步指标",
        "walking_gait": "步行步态",
        "stairs_strength": "爬楼与下肢",
        "environment_audio": "环境与暴露",
    },
    "EN": {
        "core_health": "Core Health",
        "cardio_fitness": "Cardio Fitness",
        "sleep_recovery": "Sleep & Recovery",
        "activity_mobility": "Activity & Mobility",
        "running_advanced": "Advanced Running",
        "walking_gait": "Walking & Gait",
        "stairs_strength": "Stairs & Lower Body",
        "environment_audio": "Environment & Exposure",
    }
}

# 32项指标定义
METRIC_DEFS = {
    # 核心健康（10）
    "hrv": {"category": "core_health", "importance": 10, "ai_key": "hrv", "label_cn": "HRV", "label_en": "HRV"},
    "resting_hr": {"category": "core_health", "importance": 10, "ai_key": "resting_hr", "label_cn": "静息心率", "label_en": "Resting HR"},
    "heart_rate_avg": {"category": "core_health", "importance": 8, "ai_key": None, "label_cn": "平均心率", "label_en": "Avg Heart Rate"},
    "steps": {"category": "core_health", "importance": 9, "ai_key": "steps", "label_cn": "步数", "label_en": "Steps"},
    "distance": {"category": "core_health", "importance": 8, "ai_key": "distance", "label_cn": "行走距离", "label_en": "Walking Distance"},
    "active_energy": {"category": "core_health", "importance": 9, "ai_key": "active_energy", "label_cn": "活动能量", "label_en": "Active Energy"},
    "spo2": {"category": "core_health", "importance": 8, "ai_key": "spo2", "label_cn": "血氧饱和度", "label_en": "SpO2"},
    "respiratory_rate": {"category": "core_health", "importance": 7, "ai_key": "respiratory", "label_cn": "呼吸率", "label_en": "Respiratory Rate"},
    "apple_stand_time": {"category": "core_health", "importance": 6, "ai_key": "stand", "label_cn": "站立时间", "label_en": "Stand Time"},
    "basal_energy_burned": {"category": "core_health", "importance": 5, "ai_key": "basal", "label_cn": "基础代谢", "label_en": "Basal Energy"},

    # 心肺能力（2）
    "vo2_max": {"category": "cardio_fitness", "importance": 9, "ai_key": None, "label_cn": "VO₂ Max", "label_en": "VO2 Max"},
    "physical_effort": {"category": "cardio_fitness", "importance": 7, "ai_key": None, "label_cn": "体力消耗率", "label_en": "Physical Effort"},

    # 睡眠恢复（4）
    "sleep_total_hours": {"category": "sleep_recovery", "importance": 10, "ai_key": "sleep", "label_cn": "总睡眠时长", "label_en": "Total Sleep"},
    "sleep_deep_hours": {"category": "sleep_recovery", "importance": 8, "ai_key": None, "label_cn": "深睡时长", "label_en": "Deep Sleep"},
    "sleep_rem_hours": {"category": "sleep_recovery", "importance": 8, "ai_key": None, "label_cn": "REM时长", "label_en": "REM Sleep"},
    "breathing_disturbances": {"category": "sleep_recovery", "importance": 7, "ai_key": None, "label_cn": "呼吸紊乱", "label_en": "Breathing Disturbances"},

    # 活动与机能（4）
    "apple_exercise_time": {"category": "activity_mobility", "importance": 8, "ai_key": None, "label_cn": "锻炼时间", "label_en": "Exercise Time"},
    "flights_climbed": {"category": "stairs_strength", "importance": 6, "ai_key": "flights", "label_cn": "爬楼层数", "label_en": "Flights Climbed"},
    "apple_stand_hour": {"category": "activity_mobility", "importance": 5, "ai_key": None, "label_cn": "站立小时数", "label_en": "Stand Hours"},
    "stair_speed_up": {"category": "stairs_strength", "importance": 5, "ai_key": None, "label_cn": "上楼速度", "label_en": "Stair Speed Up"},

    # 高级跑步（5）
    "running_speed": {"category": "running_advanced", "importance": 8, "ai_key": None, "label_cn": "跑步速度", "label_en": "Running Speed"},
    "running_power": {"category": "running_advanced", "importance": 8, "ai_key": None, "label_cn": "跑步功率", "label_en": "Running Power"},
    "running_stride_length": {"category": "running_advanced", "importance": 7, "ai_key": None, "label_cn": "跑步步幅", "label_en": "Running Stride Length"},
    "running_ground_contact_time": {"category": "running_advanced", "importance": 7, "ai_key": None, "label_cn": "触地时间", "label_en": "Ground Contact Time"},
    "running_vertical_oscillation": {"category": "running_advanced", "importance": 6, "ai_key": None, "label_cn": "垂直振幅", "label_en": "Vertical Oscillation"},

    # 步行步态（5）
    "walking_speed": {"category": "walking_gait", "importance": 6, "ai_key": None, "label_cn": "步行速度", "label_en": "Walking Speed"},
    "walking_step_length": {"category": "walking_gait", "importance": 6, "ai_key": None, "label_cn": "步行步长", "label_en": "Walking Step Length"},
    "walking_heart_rate_average": {"category": "walking_gait", "importance": 5, "ai_key": None, "label_cn": "步行心率", "label_en": "Walking HR Avg"},
    "walking_asymmetry_percentage": {"category": "walking_gait", "importance": 5, "ai_key": None, "label_cn": "步行不对称性", "label_en": "Walking Asymmetry"},
    "walking_double_support_percentage": {"category": "walking_gait", "importance": 4, "ai_key": None, "label_cn": "双支撑时间占比", "label_en": "Double Support %"},

    # 环境暴露（2）
    "headphone_audio_exposure": {"category": "environment_audio", "importance": 5, "ai_key": None, "label_cn": "耳机音频暴露", "label_en": "Headphone Exposure"},
    "environmental_audio_exposure": {"category": "environment_audio", "importance": 3, "ai_key": None, "label_cn": "环境音频暴露", "label_en": "Environmental Exposure"},
}
# =====================================================

# ==================== 单位处理函数（V5.9.0 新增）====================
def _metric_unit(metrics, name: str) -> str:
    """从 metrics 中提取指定指标的单位"""
    if isinstance(metrics, dict):
        m = metrics.get(name, {})
        if isinstance(m, dict):
            return str(m.get('units', '')).strip().lower()
        return ''
    if isinstance(metrics, list):
        for m in metrics:
            if isinstance(m, dict) and m.get('name') == name:
                return str(m.get('units', '')).strip().lower()
    return ''


def _convert_length_to_cm(v: float, unit: str) -> float:
    """长度单位转换为厘米"""
    if v is None:
        return None
    if unit in ('m', 'meter', 'meters'):
        return v * 100.0
    return v


def _convert_speed_to_kmh(v: float, unit: str) -> float:
    """速度单位转换为 km/h"""
    if v is None:
        return None
    if unit in ('m/s', 'meter/s', 'meters/s'):
        return v * 3.6
    return v


def _display_unit(data: dict, metric_key: str, fallback: str = '') -> str:
    """从 data['_metric_units'] 中获取单位"""
    units_map = data.get('_metric_units', {})
    if not isinstance(units_map, dict):
        return fallback
    unit = units_map.get(metric_key)
    return unit if unit else fallback


def _parse_datetime_flexible(value):
    """解析多种时间格式（秒/毫秒时间戳、ISO、常见日期字符串）。"""
    if value is None or value == '':
        return None

    # 1) 数值类型时间戳
    if isinstance(value, (int, float)):
        ts = float(value)
        if ts > 1e12:  # 毫秒
            ts /= 1000.0
        try:
            return datetime.fromtimestamp(ts)
        except Exception:
            return None

    # 2) 字符串
    text = str(value).strip()
    if not text:
        return None

    # 2.1 纯数字字符串
    try:
        ts = float(text)
        if ts > 1e12:
            ts /= 1000.0
        return datetime.fromtimestamp(ts)
    except Exception:
        pass

    # 2.2 ISO / 带时区
    iso_text = text.replace('Z', '+00:00')
    match = re.match(r'(.+?)\s+([+-]\d{4})$', iso_text)
    if match:
        dt_part, tz_part = match.groups()
        iso_text = f"{dt_part}{tz_part[:3]}:{tz_part[3:]}"
    try:
        return datetime.fromisoformat(iso_text)
    except Exception:
        pass

    # 2.3 常见格式兜底
    for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%Y/%m/%d %H:%M:%S', '%Y/%m/%d %H:%M'):
        try:
            return datetime.strptime(text, fmt)
        except Exception:
            continue

    return None
# =====================================================

HOME = Path.home()
TEMPLATE_DIR = Path(__file__).parent.parent / 'templates'
OUTPUT_DIR = Path(CONFIG.get("output_dir", str(Path.home() / '.openclaw' / 'workspace' / 'shared' / 'health-reports' / 'upload'))).expanduser()
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
            "email": member.get("email", ""),
            "age": member.get("age"),
            "gender": member.get("gender"),
            "height_cm": member.get("height_cm"),
            "weight_kg": member.get("weight_kg")
        }

    # 默认配置
    return {
        "name": f"成员{index+1}",
        "health_dir": DEFAULT_HEALTH_DIR,
        "workout_dir": DEFAULT_WORKOUT_DIR,
        "email": "",
        "age": 30,
        "gender": "male",
        "height_cm": 175,
        "weight_kg": 70
    }


def verify_ai_analysis(ai_analysis: dict, selected_metric_keys: list = None) -> list:
    """
    验证AI分析字数是否符合要求（V5.9.0 支持动态指标）
    返回错误列表（为空表示验证通过）
    """
    errors = []
    seen = set()

    def add_err(msg: str):
        if msg not in seen:
            seen.add(msg)
            errors.append(msg)

    total_text_len = 0

    # 1) 核心字段字数校验（完整保留）
    validations = [
        ('hrv', MIN_LENGTH_HRV, MAX_LENGTH_METRIC, 'HRV分析'),
        ('resting_hr', MIN_LENGTH_RESTING_HR, MAX_LENGTH_METRIC, '静息心率分析'),
        ('steps', MIN_LENGTH_STEPS, MAX_LENGTH_METRIC, '步数分析'),
        ('distance', MIN_LENGTH_DISTANCE, MAX_LENGTH_METRIC, '距离分析'),
        ('active_energy', MIN_LENGTH_ACTIVE_ENERGY, MAX_LENGTH_METRIC, '活动能量分析'),
        ('spo2', MIN_LENGTH_SPO2, MAX_LENGTH_METRIC, '血氧分析'),
        ('flights', MIN_LENGTH_FLIGHTS, MAX_LENGTH_METRIC, '爬楼分析'),
        ('stand', MIN_LENGTH_STAND, MAX_LENGTH_METRIC, '站立分析'),
        ('basal', MIN_LENGTH_BASAL, MAX_LENGTH_METRIC, '基础代谢分析'),
        ('respiratory', MIN_LENGTH_RESPIRATORY, MAX_LENGTH_METRIC, '呼吸率分析'),
        ('sleep', MIN_LENGTH_SLEEP, MAX_LENGTH_METRIC, '睡眠分析'),
        ('workout', MIN_LENGTH_WORKOUT, MAX_LENGTH_METRIC, '运动分析'),
    ]

    for key, min_len, max_len, name in validations:
        text = ai_analysis.get(key, '')
        if text:
            total_text_len += len(text)
            if len(text) < min_len:
                add_err(f"❌ {name} 字数不足: {len(text)}字 (要求至少{min_len}字)")
            if len(text) > max_len:
                add_err(f"❌ {name} 字数超限: {len(text)}字 (要求最多{max_len}字)")

    # 最高优先级建议
    priority = ai_analysis.get('priority', {})
    title = priority.get('title', '')
    problem = priority.get('problem', '')
    action = priority.get('action', '')
    expectation = priority.get('expectation', '')

    if title:
        total_text_len += len(title)
        if len(title) < MIN_LENGTH_PRIORITY_TITLE:
            add_err(f"❌ 最高优先级标题 字数不足: {len(title)}字 (要求至少{MIN_LENGTH_PRIORITY_TITLE}字)")

    if problem:
        total_text_len += len(problem)
        if len(problem) < MIN_LENGTH_PRIORITY_PROBLEM:
            add_err(f"❌ 问题识别 字数不足: {len(problem)}字 (要求至少{MIN_LENGTH_PRIORITY_PROBLEM}字)")

    if action:
        total_text_len += len(action)
        if len(action) < MIN_LENGTH_PRIORITY_ACTION:
            add_err(f"❌ 行动计划 字数不足: {len(action)}字 (要求至少{MIN_LENGTH_PRIORITY_ACTION}字)")
        if len(action) > MAX_LENGTH_PRIORITY_ACTION:
            add_err(f"❌ 行动计划 字数超限: {len(action)}字 (要求最多{MAX_LENGTH_PRIORITY_ACTION}字)")

    if expectation:
        total_text_len += len(expectation)
        if len(expectation) < MIN_LENGTH_PRIORITY_EXPECTATION:
            add_err(f"❌ 预期效果 字数不足: {len(expectation)}字 (要求至少{MIN_LENGTH_PRIORITY_EXPECTATION}字)")

    # 验证次级建议
    for prefix, label in [('ai2', '第二优先级'), ('ai3', '第三优先级')]:
        title = ai_analysis.get(f'{prefix}_title', '')
        problem = ai_analysis.get(f'{prefix}_problem', '')
        action = ai_analysis.get(f'{prefix}_action', '')
        expectation = ai_analysis.get(f'{prefix}_expectation', '')

        if title:
            total_text_len += len(title)
            if len(title) < MIN_LENGTH_AI2_TITLE:
                add_err(f"❌ {label}标题 字数不足: {len(title)}字 (要求至少{MIN_LENGTH_AI2_TITLE}字)")
        if problem:
            total_text_len += len(problem)
            if len(problem) < MIN_LENGTH_AI2_PROBLEM:
                add_err(f"❌ {label}问题 字数不足: {len(problem)}字 (要求至少{MIN_LENGTH_AI2_PROBLEM}字)")
        if action:
            total_text_len += len(action)
            if len(action) < MIN_LENGTH_AI2_ACTION:
                add_err(f"❌ {label}行动 字数不足: {len(action)}字 (要求至少{MIN_LENGTH_AI2_ACTION}字)")
        if expectation:
            total_text_len += len(expectation)
            if len(expectation) < MIN_LENGTH_AI2_EXPECTATION:
                add_err(f"❌ {label}效果 字数不足: {len(expectation)}字 (要求至少{MIN_LENGTH_AI2_EXPECTATION}字)")

    # 饮食方案（必填字段）
    diet_checks = [
        ('breakfast', MIN_LENGTH_BREAKFAST, '早餐'),
        ('lunch', MIN_LENGTH_LUNCH, '午餐'),
        ('dinner', MIN_LENGTH_DINNER, '晚餐'),
        ('snack', MIN_LENGTH_SNACK, '加餐'),
    ]
    for key, min_len, name in diet_checks:
        text = ai_analysis.get(key, '')
        if not text:
            add_err(f"❌ {name} 缺失: 必须提供{name}内容")
        else:
            total_text_len += len(text)
            if len(text) < min_len:
                add_err(f"❌ {name} 字数不足: {len(text)}字 (要求至少{min_len}字)")

    # 每日总字数下限（来自 analysis_limits.daily_min_words）
    if total_text_len < DAILY_MIN_WORDS:
        add_err(f"❌ 日报AI总字数不足: {total_text_len}字 (要求至少{DAILY_MIN_WORDS}字)")

    # 语言一致性
    from utils import detect_language_mismatch
    lang_errors = detect_language_mismatch(
        ai_analysis,
        LANGUAGE,
        strict_mode=(VALIDATION_MODE == "strict")
    )
    for error in lang_errors:
        add_err(f"❌ {error}")

    # 3) selected 指标 AI 必填（可选严格模式）
    if selected_metric_keys is None:
        selected_metric_keys = get_selected_metric_keys()

    if REPORT_REQUIRE_AI_FOR_SELECTED:
        for mk in selected_metric_keys:
            ai_key = METRIC_DEFS.get(mk, {}).get('ai_key')
            if ai_key and not ai_analysis.get(ai_key):
                add_err(f"❌ 已选指标缺少AI分析: {mk} -> {ai_key}")

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

    # V5.9.0: 睡眠数据严格时间窗口过滤，防止次日数据污染当日指标
    if target_date:
        filtered_arr = []
        for x in arr:
            st = x.get('startDate') or x.get('date')
            if st is None:
                continue
            st_str = str(st)
            if st_str.startswith(target_date):
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

    # V5.8.1: 活动数据读取当日文件，严格过滤当日时间戳
    metrics = _parse_metrics(date_str, health_dir)
    if not metrics:
        raise FileNotFoundError(f'未找到源数据: {health_dir}/HealthAutoExport-{date_str}.json')

    hrv_vals = _values(metrics, 'heart_rate_variability', date_str)
    rhr_vals = _values(metrics, 'resting_heart_rate', date_str)
    steps_vals = _values(metrics, 'step_count', date_str)
    dist_vals = _values(metrics, 'walking_running_distance', date_str)
    active_vals = _values(metrics, 'active_energy', date_str)
    spo2_vals = _values(metrics, 'blood_oxygen_saturation', date_str)
    flights_vals = _values(metrics, 'flights_climbed', date_str)
    stand_vals = _values(metrics, 'apple_stand_time', date_str)
    basal_vals = _values(metrics, 'basal_energy_burned', date_str)
    resp_vals = _values(metrics, 'respiratory_rate', date_str)

    # V5.9.0: 新增指标读取
    heart_vals = _values(metrics, 'heart_rate', date_str)
    vo2_vals = _values(metrics, 'vo2_max', date_str)
    exercise_vals = _values(metrics, 'apple_exercise_time', date_str)
    stand_hour_vals = _values(metrics, 'apple_stand_hour', date_str)
    physical_effort_vals = _values(metrics, 'physical_effort', date_str)

    walking_step_length_vals = _values(metrics, 'walking_step_length', date_str)
    walking_hr_avg_vals = _values(metrics, 'walking_heart_rate_average', date_str)
    walking_asym_vals = _values(metrics, 'walking_asymmetry_percentage', date_str)
    walking_double_support_vals = _values(metrics, 'walking_double_support_percentage', date_str)
    walking_speed_vals = _values(metrics, 'walking_speed', date_str)

    running_stride_vals = _values(metrics, 'running_stride_length', date_str)
    running_vertical_vals = _values(metrics, 'running_vertical_oscillation', date_str)
    running_ground_vals = _values(metrics, 'running_ground_contact_time', date_str)
    running_power_vals = _values(metrics, 'running_power', date_str)
    running_speed_vals = _values(metrics, 'running_speed', date_str)

    stair_speed_vals = _values(metrics, 'stair_speed_up', date_str)
    breathing_disturb_vals = _values(metrics, 'breathing_disturbances', date_str)

    headphone_audio_vals = _values(metrics, 'headphone_audio_exposure', date_str)
    environmental_audio_vals = _values(metrics, 'environmental_audio_exposure', date_str)

    # 能量通常是kJ，转kcal
    active_kcal = (_sum(active_vals) / KJ_TO_KCAL) if active_vals else None
    basal_kcal = (_sum(basal_vals) / KJ_TO_KCAL) if basal_vals else None

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
    if wp and wp.exists():
        try:
            wd = json.loads(wp.read_text(encoding='utf-8'))
        except Exception as e:
            print(f"⚠️ 解析运动文件失败: {wp} - {e}")
            wd = {}
        workout_raw = wd.get('data', {}).get('workouts', [])
        if isinstance(workout_raw, dict):
            workout_list = workout_raw.get('data', [])
        elif isinstance(workout_raw, list):
            workout_list = workout_raw
        else:
            workout_list = wd.get('workouts', [])

        if not isinstance(workout_list, list):
            workout_list = []

        for w in workout_list:
            timeline = []
            hr_source = w.get('heartRateData') or w.get('hrData') or []
            for h in hr_source:
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

            # duration 使用智能单位推断
            dur_raw = w.get('duration')
            if isinstance(dur_raw, (int, float)) and dur_raw > 0:
                from utils import infer_duration_unit
                duration_min, _ = infer_duration_unit(dur_raw, w)
            else:
                duration_min = 0.0

            # 能量兼容多字段名；源数据通常是 kJ，转换为 kcal
            from utils import get_workout_field
            energy_raw = get_workout_field(
                w,
                ['energy', 'activeEnergyBurned', 'totalEnergyBurned', 'activeEnergy'],
                0
            )
            energy_kcal = (float(energy_raw) / KJ_TO_KCAL) if isinstance(energy_raw, (int, float)) and energy_raw else 0

            # 处理开始和结束时间（兼容 start/startDate 和 end/endDate）
            start_raw = w.get('start') or w.get('startDate')
            end_raw = w.get('end') or w.get('endDate')
            start_dt = _parse_datetime_flexible(start_raw)
            end_dt = _parse_datetime_flexible(end_raw)
            start_str = start_dt.strftime('%Y-%m-%d %H:%M') if start_dt else ''
            end_str = end_dt.strftime('%Y-%m-%d %H:%M') if end_dt else ''

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

    # V5.8.1: 计算总活动能量（日常活动 + 运动能量）
    workout_energy_total = sum(w.get('energy_kcal', 0) for w in workouts)
    if active_kcal is not None and active_kcal > 0:
        # active_energy 已代表当日活动能量，避免与 workout 重复累加
        total_active_kcal = active_kcal
    else:
        # 回退：当 active_energy 缺失时，使用 workout 能量
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

    # V5.9.0: 睡眠数据精确处理（B3 修正）
    sleep_total_raw = None
    sleep_deep_raw = None
    sleep_rem_raw = None
    if isinstance(sleep_result, dict):
        total_candidate = sleep_result.get('total_hours', 0)
        if isinstance(total_candidate, (int, float)) and total_candidate > 0:
            sleep_total_raw = total_candidate
            deep_candidate = sleep_result.get('deep_hours', 0)
            rem_candidate = sleep_result.get('rem_hours', 0)
            sleep_deep_raw = deep_candidate if isinstance(deep_candidate, (int, float)) else None
            sleep_rem_raw = rem_candidate if isinstance(rem_candidate, (int, float)) else None

    # V5.9.0: 单位转换
    walking_step_length_unit = _metric_unit(metrics, 'walking_step_length')
    walking_speed_unit = _metric_unit(metrics, 'walking_speed')
    running_speed_unit = _metric_unit(metrics, 'running_speed')

    bd_unit = _metric_unit(metrics, 'breathing_disturbances')
    pe_unit = _metric_unit(metrics, 'physical_effort')
    if bd_unit not in ('count', 'count/min', '', 'index'):
        print(f"⚠️ breathing_disturbances 非预期单位: {bd_unit}")
    if pe_unit not in ('kcal/hr·kg', 'kcal/hr*kg', ''):
        print(f"⚠️ physical_effort 非预期单位: {pe_unit}")

    data = {
        'date': date_str,
        'hrv': {
            'value': round(_avg(hrv_vals), 1) if hrv_vals else None,
            'measurement_count': len(hrv_vals),
            'points': len(hrv_vals),  # 兼容旧字段
        },
        'resting_hr': {'value': round(_avg(rhr_vals)) if rhr_vals else None},
        'steps': int(_sum(steps_vals)) if steps_vals else None,
        'distance': round(_sum(dist_vals), 2) if dist_vals else None,
        'active_energy': int(round(total_active_kcal)) if total_active_kcal is not None else None,
        'spo2': round(spo2, 1) if spo2 is not None else None,
        'flights_climbed': int(_sum(flights_vals)) if flights_vals else None,
        'apple_stand_time': int(_sum(stand_vals)) if stand_vals else None,
        'basal_energy_burned': int(round(basal_kcal)) if basal_kcal is not None else None,
        'respiratory_rate': round(_avg(resp_vals), 1) if resp_vals else None,

        # V5.9.0: 新增指标
        'heart_rate_avg': round(_avg(heart_vals), 1) if heart_vals else None,
        'vo2_max': round(_avg(vo2_vals), 2) if vo2_vals else None,
        'apple_exercise_time': int(round(_sum(exercise_vals))) if exercise_vals else None,
        'apple_stand_hour': int(round(_sum(stand_hour_vals))) if stand_hour_vals else None,
        'physical_effort': round(_avg(physical_effort_vals), 2) if physical_effort_vals else None,

        'walking_step_length': _convert_length_to_cm(_avg(walking_step_length_vals), walking_step_length_unit) if walking_step_length_vals else None,
        'walking_heart_rate_average': round(_avg(walking_hr_avg_vals), 1) if walking_hr_avg_vals else None,
        'walking_asymmetry_percentage': round(_avg(walking_asym_vals), 2) if walking_asym_vals else None,
        'walking_double_support_percentage': round(_avg(walking_double_support_vals), 2) if walking_double_support_vals else None,
        'walking_speed': _convert_speed_to_kmh(_avg(walking_speed_vals), walking_speed_unit) if walking_speed_vals else None,

        'running_stride_length': round(_avg(running_stride_vals), 2) if running_stride_vals else None,
        'running_vertical_oscillation': round(_avg(running_vertical_vals), 2) if running_vertical_vals else None,
        'running_ground_contact_time': round(_avg(running_ground_vals), 2) if running_ground_vals else None,
        'running_power': round(_avg(running_power_vals), 2) if running_power_vals else None,
        'running_speed': _convert_speed_to_kmh(_avg(running_speed_vals), running_speed_unit) if running_speed_vals else None,

        'stair_speed_up': round(_avg(stair_speed_vals), 3) if stair_speed_vals else None,
        'breathing_disturbances': round(_avg(breathing_disturb_vals), 2) if breathing_disturb_vals else None,

        'headphone_audio_exposure': round(_avg(headphone_audio_vals), 1) if headphone_audio_vals else None,
        'environmental_audio_exposure': round(_avg(environmental_audio_vals), 1) if environmental_audio_vals else None,

        # V5.9.0: 睡眠指标（从 sleep_result 填充）
        'sleep_total_hours': round(sleep_total_raw, 2) if sleep_total_raw is not None else None,
        'sleep_deep_hours': round(sleep_deep_raw, 2) if sleep_deep_raw is not None else None,
        'sleep_rem_hours': round(sleep_rem_raw, 2) if sleep_rem_raw is not None else None,

        'sleep': sleep_result,
        'workouts': workouts,
        'has_workout': len(workouts) > 0,

        # V5.9.0: 单位映射
        '_metric_units': {
            'running_power': _metric_unit(metrics, 'running_power') or 'W',
            'physical_effort': _metric_unit(metrics, 'physical_effort') or 'kcal/hr·kg',
            'breathing_disturbances': _metric_unit(metrics, 'breathing_disturbances') or 'index',
            'walking_speed': _metric_unit(metrics, 'walking_speed') or 'km/hr',
            'running_speed': _metric_unit(metrics, 'running_speed') or 'km/hr'
        }
    }
    return data


def real_text(v, fmt):
    return fmt(v) if v is not None else '--'


def safe_html_text(value) -> str:
    if value is None:
        return ''
    return html_escape(str(value), quote=True)


def safe_html_paragraph(value) -> str:
    return safe_html_text(value).replace('\n', '<br>')


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


# ==================== 动态指标表渲染函数（V5.9.0 新增）====================
def get_category_order():
    """获取类别顺序（支持配置覆盖）"""
    # 从 METRIC_DEFS 提取真实类别全集
    all_cats = []
    for d in METRIC_DEFS.values():
        c = d.get('category')
        if c and c not in all_cats:
            all_cats.append(c)

    ordered = []

    # 用户配置优先
    if isinstance(CATEGORY_ORDER_OVERRIDE, list):
        for c in CATEGORY_ORDER_OVERRIDE:
            if c in all_cats and c not in ordered:
                ordered.append(c)

    # 内置顺序补齐
    for c in CATEGORY_ORDER:
        if c in all_cats and c not in ordered:
            ordered.append(c)

    # 防漏兜底
    for c in all_cats:
        if c not in ordered:
            ordered.append(c)

    return ordered


def metric_importance(metric_key: str) -> int:
    """获取指标重要性（支持 override）"""
    if isinstance(IMPORTANCE_OVERRIDES, dict) and metric_key in IMPORTANCE_OVERRIDES:
        try:
            x = int(IMPORTANCE_OVERRIDES[metric_key])
            return max(0, min(10, x))
        except Exception:
            pass
    return int(METRIC_DEFS[metric_key]['importance'])


def get_selected_metric_keys():
    """获取选中的指标列表"""
    if not REPORT_SELECTED_METRICS:
        selected = DEFAULT_SELECTED_METRICS.copy()
    else:
        selected = [k for k in REPORT_SELECTED_METRICS if k in METRIC_DEFS]

    if not REPORT_INCLUDE_SLEEP_METRICS_IN_TABLE:
        sleep_keys = {'sleep_total_hours', 'sleep_deep_hours', 'sleep_rem_hours'}
        selected = [k for k in selected if k not in sleep_keys]

    # 过滤 importance=0 的指标
    selected = [k for k in selected if metric_importance(k) > 0]

    return selected


def metric_label(metric_key: str) -> str:
    """获取指标标签"""
    d = METRIC_DEFS[metric_key]
    return d['label_en'] if LANGUAGE == 'EN' else d['label_cn']


def metric_value_text(metric_key: str, data: dict) -> str:
    """格式化指标值文本"""
    v = data.get(metric_key)

    # 处理嵌套字典格式（如 hrv, resting_hr）
    if isinstance(v, dict):
        v = v.get('value')

    if v is None:
        return '--'

    # 按指标格式化
    if metric_key in ('hrv',):
        return f"{float(v):.1f} ms"
    if metric_key in ('resting_hr', 'heart_rate_avg', 'walking_heart_rate_average'):
        return f"{float(v):.1f} bpm"
    if metric_key == 'respiratory_rate':
        unit = 'breaths/min' if LANGUAGE == 'EN' else '次/分'
        return f"{float(v):.1f} {unit}"
    if metric_key in ('steps', 'flights_climbed', 'apple_stand_hour'):
        suffix = ' floors' if (LANGUAGE == 'EN' and metric_key == 'flights_climbed') else (' 层' if metric_key == 'flights_climbed' else '')
        return f"{int(round(v)):,}{suffix}"
    if metric_key == 'distance':
        return f"{float(v):.2f} km"
    if metric_key in ('active_energy', 'basal_energy_burned'):
        return f"{int(round(v))} kcal"
    if metric_key in ('apple_stand_time', 'apple_exercise_time'):
        unit = 'min' if LANGUAGE == 'EN' else '分钟'
        return f"{int(round(v))} {unit}"
    if metric_key == 'spo2':
        return f"{float(v):.1f}%"
    if metric_key == 'vo2_max':
        return f"{float(v):.2f} ml/(kg·min)"
    if metric_key == 'physical_effort':
        unit = _display_unit(data, 'physical_effort', 'kcal/hr·kg')
        return f"{float(v):.2f} {unit}"
    if metric_key == 'walking_step_length':
        return f"{float(v):.2f} cm"
    if metric_key in ('walking_asymmetry_percentage', 'walking_double_support_percentage'):
        return f"{float(v):.2f}%"
    if metric_key in ('walking_speed', 'running_speed'):
        unit = _display_unit(data, metric_key, 'km/hr')
        return f"{float(v):.2f} {unit}"
    if metric_key == 'running_stride_length':
        return f"{float(v):.2f} m"
    if metric_key == 'running_vertical_oscillation':
        return f"{float(v):.2f} cm"
    if metric_key == 'running_ground_contact_time':
        return f"{float(v):.2f} ms"
    if metric_key == 'running_power':
        unit = _display_unit(data, 'running_power', 'W')
        return f"{float(v):.2f} {unit}"
    if metric_key == 'stair_speed_up':
        return f"{float(v):.3f} m/s"
    if metric_key in ('headphone_audio_exposure', 'environmental_audio_exposure'):
        return f"{float(v):.1f} dBASPL"
    if metric_key in ('sleep_total_hours', 'sleep_deep_hours', 'sleep_rem_hours'):
        return f"{float(v):.2f} h"
    if metric_key == 'breathing_disturbances':
        unit = _display_unit(data, 'breathing_disturbances', 'index')
        return f"{float(v):.2f} {unit}"

    return str(v)


def metric_rating(metric_key: str, data: dict):
    """计算指标评级"""
    v = data.get(metric_key)

    # 处理嵌套字典格式（如 hrv, resting_hr）
    if isinstance(v, dict):
        v = v.get('value')

    if v is None:
        return ('rating-average', '--')

    # 仅核心指标给评级
    if metric_key == 'hrv':
        if LANGUAGE == 'EN':
            return ('rating-good', 'Good') if v >= 50 else ('rating-average', 'Average')
        return ('rating-good', '良好') if v >= 50 else ('rating-average', '一般')
    if metric_key == 'resting_hr':
        if LANGUAGE == 'EN':
            return ('rating-excellent', 'Excellent') if v < 60 else ('rating-good', 'Good')
        return ('rating-excellent', '优秀') if v < 60 else ('rating-good', '良好')
    if metric_key == 'spo2':
        if LANGUAGE == 'EN':
            return ('rating-good', 'Normal') if v >= 95 else ('rating-average', 'Average')
        return ('rating-good', '正常') if v >= 95 else ('rating-average', '一般')
    if metric_key == 'steps':
        if LANGUAGE == 'EN':
            return ('rating-good', 'Good') if v > 8000 else ('rating-average', 'Average')
        return ('rating-good', '良好') if v > 8000 else ('rating-average', '一般')
    if metric_key == 'sleep_total_hours':
        if LANGUAGE == 'EN':
            return ('rating-good', 'Normal') if v >= 6 else ('rating-average', 'Average')
        return ('rating-good', '正常') if v >= 6 else ('rating-average', '一般')

    # 非核心指标返回中立
    return ('rating-average', '--')


def metric_analysis_text(metric_key: str, ai_analysis: dict, data: dict):
    """获取指标AI分析文本"""
    ai_key = METRIC_DEFS[metric_key].get('ai_key')
    if ai_key and ai_analysis.get(ai_key):
        return ai_analysis.get(ai_key)

    # 无AI文本时的自动兜底
    value_text = metric_value_text(metric_key, data)
    label = metric_label(metric_key)
    if LANGUAGE == 'EN':
        return f"{label}: current value is {value_text}. No dedicated AI paragraph was provided for this metric."
    return f"{label}：当前值为 {value_text}。该指标未提供独立AI长文分析，建议结合趋势继续观察。"


def build_metrics_table_rows(data: dict, ai_analysis: dict, selected_keys: list):
    """构建指标表格HTML行"""
    rows = []
    sleep_keys = {'sleep_total_hours', 'sleep_deep_hours', 'sleep_rem_hours'}

    for cat in get_category_order():
        cat_label = CATEGORY_LABELS[LANGUAGE].get(cat, cat)
        cat_metrics = [k for k in selected_keys if METRIC_DEFS.get(k, {}).get('category') == cat]

        # 无数据过滤（睡眠表格显式开启时，睡眠项即使无值也保留）
        if REPORT_HIDE_NO_DATA_METRICS:
            filtered = []
            for k in cat_metrics:
                v = data.get(k)
                if REPORT_INCLUDE_SLEEP_METRICS_IN_TABLE and k in sleep_keys:
                    filtered.append(k)
                elif v is not None:
                    filtered.append(k)
            cat_metrics = filtered

        if REPORT_SORT_BY_IMPORTANCE:
            cat_metrics = sorted(cat_metrics, key=lambda k: metric_importance(k), reverse=True)

        # 空类别
        if not cat_metrics:
            if REPORT_SHOW_EMPTY_CATEGORIES:
                suffix = '（无数据）' if LANGUAGE == 'CN' else ' (No Data)'
                rows.append(f'<tr class="metric-category-row"><td colspan="4">{safe_html_text(cat_label)}{safe_html_text(suffix)}</td></tr>')
            continue

        rows.append(f'<tr class="metric-category-row"><td colspan="4">{safe_html_text(cat_label)}</td></tr>')

        for k in cat_metrics:
            label = metric_label(k)
            value_text = metric_value_text(k, data)
            rating_class, rating_text = metric_rating(k, data)
            analysis_text = metric_analysis_text(k, ai_analysis, data)
            imp = metric_importance(k)

            rows.append(
                f'''<tr class="metric-row">
<td><span class="metric-name">{safe_html_text(label)}</span><span class="metric-importance">P{imp}</span></td>
<td class="metric-value-cell">{safe_html_text(value_text)}</td>
<td><span class="rating {rating_class}">{safe_html_text(rating_text)}</span></td>
<td><div class="metric-analysis">{safe_html_paragraph(analysis_text)}</div></td>
</tr>'''
            )

    return '\n'.join(rows)
# =====================================================


def calculate_scores(data, member_cfg=None):
    """V5.8.1: 计算个性化评分（考虑年龄、性别、BMI）

    Returns:
        tuple: (recovery, sleep_score, exercise)
    """
    sleep_hours = data.get('sleep', {}).get('total_hours', data.get('sleep', {}).get('total', 0)) or 0
    hrv_v = data['hrv']['value'] or 0
    rhr_v = data['resting_hr']['value'] or 999
    steps_v = data['steps'] or 0
    active_v = data.get('active_energy') or 0

    # 获取成员档案信息（带缺省值保护）
    if member_cfg:
        raw_age = member_cfg.get("age")
        raw_gender = member_cfg.get("gender")
        raw_height = member_cfg.get("height_cm")
        raw_weight = member_cfg.get("weight_kg")
    else:
        raw_age = raw_gender = raw_height = raw_weight = None

    age = int(raw_age) if isinstance(raw_age, (int, float)) and raw_age > 0 else 30
    gender = raw_gender if raw_gender in ("male", "female", "other") else "male"
    height_cm = float(raw_height) if isinstance(raw_height, (int, float)) and raw_height > 0 else 175.0
    weight_kg = float(raw_weight) if isinstance(raw_weight, (int, float)) and raw_weight > 0 else 70.0

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


def generate_report(date_str, ai_analysis, template, health_dir=None, workout_dir=None, member_cfg=None, preloaded_data=None):
    data = preloaded_data if preloaded_data is not None else load_data(date_str, health_dir, workout_dir)
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

    # 基础信息 - V5.8.1: 使用统一的日期格式化
    from utils import format_date

    html = html.replace('{{DATE}}', date_str)
    html = html.replace('{{DAY}}', date_str.split('-')[2])

    month_year = format_date(date_str, "month_year", LANGUAGE)

    if LANGUAGE == 'EN':
        header_subtitle = f'{date_str} · Apple Health · AI Analysis Edition'
    else:
        header_subtitle = f'{date_str} · Apple Health · AI分析版'
    html = html.replace('{{MONTH_YEAR}}', month_year)
    html = html.replace('{{HEADER_SUBTITLE}}', header_subtitle)
    html = html.replace('{{DATA_SOURCE}}', 'Apple Health')

    # 评分 - V5.8.1: 使用提取的函数，传入 member_cfg
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

    # V5.9.0: 动态指标表渲染
    selected_metric_keys = get_selected_metric_keys()
    rows_html = build_metrics_table_rows(data, ai_analysis, selected_metric_keys)
    metric_min = ANALYSIS_LIMITS.get("metric_min_words", 150)
    metric_max = ANALYSIS_LIMITS.get("metric_max_words", 200)

    # A6: 英文单复数处理
    n_metrics = len(selected_metric_keys)
    if LANGUAGE == 'EN':
        unit_word = 'metric' if n_metrics == 1 else 'metrics'
        section_title = f"Detailed Metric Analysis ({n_metrics} {unit_word} selected)"
        col_header = f"AI Analysis ({metric_min}-{metric_max} words)"
    else:
        section_title = f"详细指标分析（已选{n_metrics}项）"
        col_header = f"AI分析（{metric_min}-{metric_max}字）"

    html = html.replace('{{METRICS_SECTION_TITLE}}', section_title)
    html = html.replace('{{METRIC_ANALYSIS_COL_HEADER}}', col_header)
    html = html.replace('{{METRICS_TABLE_ROWS}}', rows_html)

    # 睡眠 - 必须有真实AI内容
    sleep_analysis = ai_analysis.get('sleep')
    if not sleep_analysis:
        raise ValueError(get_error_msg("missing_sleep"))

    # 获取睡眠总时长
    sleep_hours = data.get('sleep', {}).get('total_hours', data.get('sleep', {}).get('total', 0)) or 0

    sleep_status_text = 'Severely Insufficient' if LANGUAGE == 'EN' else '严重不足'
    sleep_status_normal = 'Normal' if LANGUAGE == 'EN' else '正常'
    html = html.replace('{{SLEEP_STATUS}}', sleep_status_text if sleep_hours < 6 else sleep_status_normal)

    if LANGUAGE == 'EN':
        alert = f'<div class="sleep-alert warning"><div class="alert-icon">⚠️</div><div class="alert-content"><h4>Severe Sleep Deficiency</h4><p>Total sleep duration {sleep_hours:.1f} hours, far below the 7-9 hour recommended standard.</p></div></div>' if sleep_hours < 6 else ''
    else:
        alert = f'<div class="sleep-alert warning"><div class="alert-icon">⚠️</div><div class="alert-content"><h4>睡眠严重不足</h4><p>总睡眠时长{sleep_hours:.1f}小时，远低于7-9小时推荐标准。</p></div></div>' if sleep_hours < 6 else ''
    html = html.replace('{{SLEEP_ALERT}}', alert)
    html = html.replace('{{SLEEP_TOTAL}}', f"{sleep_hours:.1f}")
    html = html.replace('{{SLEEP_HOURS}}', f"{sleep_hours:.1f}")

    s = data.get('sleep', {})
    s_total = s.get('total_hours', s.get('total', 0))
    s_deep = s.get('deep_hours', s.get('deep', 0))
    s_core = s.get('core_hours', s.get('core', 0))
    s_rem = s.get('rem_hours', s.get('rem', 0))
    s_awake = s.get('awake_hours', s.get('awake', 0))

    t = max(s_total, 0.1)
    html = html.replace('{{SLEEP_DEEP}}', f"{s_deep:.1f}")
    html = html.replace('{{SLEEP_CORE}}', f"{s_core:.1f}")
    html = html.replace('{{SLEEP_REM}}', f"{s_rem:.1f}")
    html = html.replace('{{SLEEP_AWAKE}}', f"{s_awake:.1f}")
    html = html.replace('{{SLEEP_DEEP_PCT}}', str(int((s_deep / t) * 100)))
    html = html.replace('{{SLEEP_CORE_PCT}}', str(int((s_core / t) * 100)))
    html = html.replace('{{SLEEP_REM_PCT}}', str(int((s_rem / t) * 100)))
    html = html.replace('{{SLEEP_AWAKE_PCT}}', str(int((s_awake / t) * 100)))
    html = html.replace('{{SLEEP_ANALYSIS_TEXT}}', safe_html_paragraph(sleep_analysis))

    # V5.8.1: 添加入睡时间和起床时间
    html = html.replace('{{SLEEP_BEDTIME}}', s.get('bedtime', '--'))
    html = html.replace('{{SLEEP_WAKETIME}}', s.get('waketime', '--'))

    # 运动 section（有运动才画图）- 显示所有运动记录
    if data.get('has_workout') and data.get('workouts'):
        workouts = data['workouts']
        workout_analysis = ai_analysis.get('workout')
        if not workout_analysis:
            raise ValueError(get_error_msg("missing_workout"))

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
        <div class="workout-name">{idx}. {safe_html_text(w['name'])}</div>
        <div class="workout-time">{safe_html_text(time_display)}</div>
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
        count_text = f"{len(workouts)} workouts" if LANGUAGE == 'EN' else f"{len(workouts)} 次运动"
        workout_section = f'''<div class="workout-section no-break">
  <div class="section-header">
    <div class="section-title">
      <span class="section-icon">🏃</span>{workout_title} - {count_text}
    </div>
  </div>
  {''.join(workout_entries)}
  <div class="workout-analysis">
    <div class="workout-analysis-title">{ai_analysis_title}</div>
    <div class="workout-analysis-text">{safe_html_paragraph(workout_analysis)}</div>
  </div>
</div>'''
    else:
        # 无运动时也必须有workout分析字段（说明无运动的情况）
        workout_analysis = ai_analysis.get('workout')
        if not workout_analysis:
            raise ValueError(get_error_msg("missing_workout"))
        workout_title = 'Workout Records' if LANGUAGE == 'EN' else '运动记录'
        no_workout_title = 'No Structured Exercise Today' if LANGUAGE == 'EN' else '今日无结构化运动'
        workout_section = f'''<div class="workout-section no-break"><div class="section-header"><div class="section-title"><span class="section-icon">🏃</span>{workout_title}</div></div><div class="workout-analysis"><div class="workout-analysis-title">{no_workout_title}</div><div class="workout-analysis-text">{safe_html_paragraph(workout_analysis)}</div></div></div>'''
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
        raise ValueError(f"{get_error_msg('missing_fields')}: {missing_fields}")

    # 最高优先级建议
    p = ai_analysis.get('priority', {})
    html = html.replace('{{AI1_TITLE}}', safe_html_text(p.get('title', '')))
    html = html.replace('{{AI1_PROBLEM}}', safe_html_paragraph(p.get('problem', '')))
    html = html.replace('{{AI1_ACTION}}', safe_html_paragraph(p.get('action', '')))
    html = html.replace('{{AI1_EXPECTATION}}', safe_html_paragraph(p.get('expectation', '')))

    html = html.replace('{{AI2_TITLE}}', safe_html_text(ai_analysis.get('ai2_title', '')))
    html = html.replace('{{AI2_PROBLEM}}', safe_html_paragraph(ai_analysis.get('ai2_problem', '')))
    html = html.replace('{{AI2_ACTION}}', safe_html_paragraph(ai_analysis.get('ai2_action', '')))
    html = html.replace('{{AI2_EXPECTATION}}', safe_html_paragraph(ai_analysis.get('ai2_expectation', '')))

    html = html.replace('{{AI3_TITLE}}', safe_html_text(ai_analysis.get('ai3_title', '')))
    html = html.replace('{{AI3_PROBLEM}}', safe_html_paragraph(ai_analysis.get('ai3_problem', '')))
    html = html.replace('{{AI3_ACTION}}', safe_html_paragraph(ai_analysis.get('ai3_action', '')))
    html = html.replace('{{AI3_EXPECTATION}}', safe_html_paragraph(ai_analysis.get('ai3_expectation', '')))

    html = html.replace('{{AI4_BREAKFAST}}', safe_html_paragraph(ai_analysis.get('breakfast', '')))
    html = html.replace('{{AI4_LUNCH}}', safe_html_paragraph(ai_analysis.get('lunch', '')))
    html = html.replace('{{AI4_DINNER}}', safe_html_paragraph(ai_analysis.get('dinner', '')))
    html = html.replace('{{AI4_SNACK}}', safe_html_paragraph(ai_analysis.get('snack', '')))

    # V5.9.0: 占位符残留保护
    unresolved = re.findall(r'\{\{[^{}]+\}\}', html)
    if unresolved:
        raise ValueError(f"模板占位符未替换: {unresolved[:10]}")

    return html


if __name__ == '__main__':
    # ============================================
    # 自动删除旧的 ai_analysis.json 防止缓存问题
    # ============================================
    workspace_dir = Path(__file__).parent.parent
    ai_analysis_file = workspace_dir / 'ai_analysis.json'

    if ai_analysis_file.exists():
        try:
            ai_analysis_file.unlink()
            print(f"🗑️  已删除旧的 AI 分析文件: {ai_analysis_file}")
        except Exception as e:
            print(f"⚠️  无法删除旧的 AI 分析文件: {e}", file=sys.stderr)
    # ============================================

    from datetime import datetime

    if len(sys.argv) < 2:
        print('用法: python3 scripts/generate_v5_medical_dashboard.py <YYYY-MM-DD> < ai_analysis.json')
        print('       支持多成员报告生成（最多3人）')
        print('')
        print('多成员模式：')
        print('  1. 成员数量与路径全部从 config.json 读取（最多3人）')
        print('  2. AI 输入支持单对象 / members数组 / 成员名映射字典')
        print('')
        print('当前配置：')
        print(f'  MEMBER_COUNT = {MEMBER_COUNT}')
        for i in range(min(MEMBER_COUNT, MAX_MEMBERS)):
            cfg = get_member_config(i)
            print(f'  成员{i+1}: {cfg["name"]} -> {cfg["health_dir"]}')
        sys.exit(1)

    date_str = sys.argv[1]

    # V5.8.1: 预检查模板文件
    from utils import validate_templates_exist
    template_check = validate_templates_exist(TEMPLATE_DIR, LANGUAGE)
    if template_check["errors"]:
        print(get_error_msg("template_check_fail"))
        for error in template_check["errors"]:
            print(f"   - {error}")
        sys.exit(1)
    print(get_error_msg("template_check_pass"))

    # 限制成员数量在1-3之间（控制token消耗）
    if MEMBER_COUNT == 0:
        print("❌ 错误: config.json 未配置 members，无法生成报告")
        sys.exit(1)

    member_count = min(MEMBER_COUNT, MAX_MEMBERS)

    print(f"📊 多成员报告生成模式")
    print(f"   日期: {date_str}")
    print(f"   成员数: {member_count} (上限3人，控制token消耗)")
    print("")

    # 读取所有成员的AI分析（支持单对象或字典或列表）
    # V5.8.1: 使用安全解析（自动修复中文引号）
    from utils import safe_json_loads
    input_text = sys.stdin.read()
    try:
        raw_ai_analyses = safe_json_loads(input_text, context="AI分析JSON")
    except json.JSONDecodeError as e:
        print(f"❌ 错误: {e}")
        sys.exit(1)

    if isinstance(raw_ai_analyses, dict) and "members" in raw_ai_analyses:
        raw_ai_analyses = raw_ai_analyses["members"]

    # V5.8.1: 使用多成员处理器
    from utils import MultiMemberProcessor, ValidationError, DataError

    processor = MultiMemberProcessor()

    for idx in range(member_count):
        member_cfg = get_member_config(idx)
        member_name = member_cfg['name']

        def process_single_member():
            """处理单个成员的闭包函数"""
            member_health_dir = Path(member_cfg['health_dir'])
            member_workout_dir = Path(member_cfg['workout_dir'])

            # 健壮的成员匹配逻辑
            ai_analysis = pick_member_ai_analysis(raw_ai_analyses, member_name, idx, strict=True)

            if not isinstance(ai_analysis, dict) or not ai_analysis:
                print(f"⚠️  警告: 找不到成员 {member_name} 的有效分析数据")
                return None

            # 验证AI分析
            print(f"📏 验证AI分析字数...")
            validation_errors = verify_ai_analysis(ai_analysis)
            if validation_errors:
                print(f"⚠️  发现 {len(validation_errors)} 处验证问题:")
                for error in validation_errors:
                    print(f"   {error}")
                if VALIDATION_MODE == "strict":
                    raise ValidationError(f"字数验证失败: {len(validation_errors)} 处不符合要求")
                print(f"⚠️  警告模式: 继续生成")

            # 检查数据文件
            data_file = member_health_dir / f'HealthAutoExport-{date_str}.json'
            if not data_file.exists():
                raise DataError(f"数据文件不存在: {data_file}")

            # 读取模板 - V5.8.1: 使用灵活的模板选择
            from utils import get_template_path
            template_path = get_template_path("daily", LANGUAGE, TEMPLATE_DIR, version="V2")
            print(f"📄 使用模板: {template_path.name}")

            with open(template_path, 'r', encoding='utf-8') as f:
                template = f.read()

            # 重新加载该成员的数据
            data = load_data(date_str, member_health_dir, member_workout_dir)

            # 生成报告HTML
            html = generate_report(
                date_str,
                ai_analysis,
                template,
                member_health_dir,
                member_workout_dir,
                member_cfg,
                preloaded_data=data
            )

            # 保存HTML
            safe_name = safe_member_name(member_name)
            html_path = OUTPUT_DIR / f'{date_str}-daily-v5-medical-{safe_name}.html'
            pdf_path = OUTPUT_DIR / f'{date_str}-daily-v5-medical-{safe_name}.pdf'

            html_path.write_text(html, encoding='utf-8')

            # 生成PDF
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
                    break
                except Exception as e:
                    if attempt < max_retries - 1:
                        print(f'   ⚠️ PDF生成失败，第{attempt + 1}次重试...')
                        import time
                        time.sleep(1)
                    else:
                        raise Exception(f'PDF生成失败（已重试{max_retries}次）: {e}')

            print(f'✅ 报告已生成: {pdf_path}')

            # 保存缓存
            try:
                cache_data = {
                    'date': date_str,
                    'member': member_name,
                    'hrv': data['hrv'],
                    'resting_hr': data['resting_hr'],
                    'steps': data['steps'],
                    'active_energy': data.get('active_energy') or 0,
                    'apple_stand_time': data.get('apple_stand_time') or 0,
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

            return str(pdf_path)

        # 处理单个成员（错误会被捕获，不影响其他成员）
        processor.process_member(idx, member_name, process_single_member)

    # 打印摘要
    all_success = processor.print_summary()

    if not all_success:
        print("⚠️  部分成员处理失败，请检查上述错误信息")
        sys.exit(1)
