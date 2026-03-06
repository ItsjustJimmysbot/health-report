#!/usr/bin/env python3
"""Health Report 共用工具函数 - V5.9.1"""

import json
import re
import sys
from pathlib import Path
from typing import Optional, Dict, Any, List, Union

try:
    from langdetect import detect, LangDetectError
    LANGDETECT_AVAILABLE = True
except ImportError:
    LANGDETECT_AVAILABLE = False

import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# 创建模块级 logger
logger = logging.getLogger('health_report')

# 文件日志处理器延迟初始化标志
_file_handler_initialized = False

def _setup_file_handler():
    """设置文件日志处理器（延迟初始化）"""
    global _file_handler_initialized
    if _file_handler_initialized:
        return

    config = load_config()
    log_dir = get_log_dir(config)
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / 'health_report.log'

    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    ))
    logger.addHandler(file_handler)
    _file_handler_initialized = True
# 全局常量
MAX_MEMBERS = 3  # 支持的最大成员数

# 能量单位转换常量
KJ_TO_KCAL = 4.184

# ==================== 统一异常类 ====================

class HealthReportError(Exception):
    """健康报告基础异常类"""
    pass

class ConfigError(HealthReportError):
    """配置错误（配置文件缺失、格式错误等）"""
    pass

class DataError(HealthReportError):
    """数据错误（数据文件缺失、格式错误、指标缺失等）"""
    pass

class ValidationError(HealthReportError):
    """验证错误（AI分析字数不足、语言不匹配等）"""
    pass

class RenderError(HealthReportError):
    """渲染错误（PDF生成失败等）"""
    pass

class EmailError(HealthReportError):
    """邮件发送错误"""
    pass


def handle_error(error: Exception, context: str = "", exit_on_fatal: bool = True) -> None:
    """统一错误处理函数

    参数:
        error: 异常对象
        context: 错误上下文描述
        exit_on_fatal: 致命错误时是否退出程序

    使用示例:
        try:
            data = load_data(date_str)
        except FileNotFoundError as e:
            handle_error(DataError(f"数据文件不存在: {e}"), "加载数据")
    """
    error_type = type(error).__name__
    error_msg = str(error)

    # 打印格式化的错误信息
    print(f"\n{'='*60}", file=sys.stderr)
    print(f"❌ 错误类型: {error_type}", file=sys.stderr)
    if context:
        print(f"📍 上下文: {context}", file=sys.stderr)
    print(f"📝 错误信息: {error_msg}", file=sys.stderr)
    print(f"{'='*60}\n", file=sys.stderr)

    # 写入文件日志（尽力而为，不影响主流程）
    try:
        _setup_file_handler()
        logger.error(
            f"[{context}] {error_type}: {error_msg}" if context else f"{error_type}: {error_msg}",
            exc_info=True
        )
    except Exception:
        pass

    # 根据错误类型决定是否退出
    if exit_on_fatal and isinstance(error, (ConfigError, DataError)):
        sys.exit(1)


# ==================== 配置加载 ====================

def load_config() -> dict:
    """从 config.json 加载配置（带验证）

    搜索路径（按优先级）：
    1. 脚本所在目录的父目录/config.json
    2. ~/.openclaw/workspace-health/config.json
    """
    config_paths = [
        Path(__file__).parent.parent / "config.json",
        Path.home() / '.openclaw' / 'workspace-health' / 'config.json',
    ]

    for config_path in config_paths:
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)

            # 验证配置
            validation_errors = validate_config_schema(config)
            if validation_errors:
                print(f"\n⚠️  config.json 配置验证警告:", file=sys.stderr)
                for error in validation_errors:
                    print(f"   - {error}", file=sys.stderr)
                print(f"   配置文件位置: {config_path}\n", file=sys.stderr)

            return config

    return {}


def get_log_dir(config=None):
    """获取日志目录，优先从配置读取"""
    if config is None:
        config = load_config()
    log_dir_str = config.get('log_dir')
    if log_dir_str:
        return Path(log_dir_str).expanduser()
    # 默认路径
    return Path.home() / '.openclaw' / 'workspace-health' / 'logs'


# ==================== 成员名称处理 ====================

def safe_member_name(name: str) -> str:
    """将成员名称转换为安全的文件名格式

    替换规则：
    - 空格、/、\、:、*、?、"、<、>、| 替换为下划线
    - 连续多个下划线合并为一个
    - 移除首尾下划线
    - 限制长度不超过50字符
    """
    if not name:
        return "member"

    import re

    # 替换不安全字符为下划线
    safe = (name or "member").strip()
    unsafe_chars = r'[\s/\\:*?"<>|]+'
    safe = re.sub(unsafe_chars, '_', safe)

    # 合并连续下划线
    safe = re.sub(r'_+', '_', safe)

    # 移除首尾下划线
    safe = safe.strip('_')

    # 限制长度
    if len(safe) > 50:
        safe = safe[:50]

    # 如果结果为空，使用默认值
    if not safe:
        safe = "member"

    return safe


# ==================== AI 分析匹配 ====================

def is_single_analysis_dict(obj: Any) -> bool:
    """检查对象是否为单个成员的分析数据结构"""
    if not isinstance(obj, dict):
        return False
    signal_keys = {
        'hrv', 'resting_hr', 'steps', 'distance', 'active_energy',
        'sleep', 'workout', 'priority', 'recommendations',
        'trend_analysis', 'hrv_analysis', 'weekly_analysis', 'monthly_analysis'
    }
    return bool(signal_keys.intersection(obj.keys()))


def pick_member_ai_analysis(
    raw_ai_analyses: Union[Dict, List],
    member_name: str,
    idx: int,
    strict: bool = False
) -> Dict[str, Any]:
    """从原始 AI 分析数据中提取指定成员的分析

    参数:
        raw_ai_analyses: 原始 AI 分析数据（可能包含多成员）
        member_name: 成员名称
        idx: 成员索引
        strict: 严格模式（True=找不到时返回空，False=兜底到第一个）

    返回:
        该成员的 AI 分析字典，找不到时返回空字典

    匹配优先级：
    1. 成员名完全匹配
    2. safe_member_name 匹配
    3. 索引匹配 (member_0, member_1)
    4. strict=False 时兜底到第一个有效字典
    """
    data = raw_ai_analyses

    # 解包 {"members": [...]} 格式
    if isinstance(data, dict) and 'members' in data:
        data = data['members']

    # 情况 1：单成员单对象
    if is_single_analysis_dict(data):
        # 如果只有一个成员，直接返回（但记录警告）
        if idx == 0:
            return data
        elif strict:
            print(f"❌ 严格模式：期望成员 {idx} ({member_name})，但只有单份数据")
            return {}
        else:
            print(f"⚠️  警告：成员 {idx} ({member_name}) 使用兜底数据")
            return data

    # 情况 2：按成员名映射的字典
    if isinstance(data, dict):
        # 候选匹配键（按优先级排序）
        candidates = [
            member_name,                                    # 原始名称
            safe_member_name(member_name),                  # 安全名称
            str(idx),                                       # 数字索引
            f'member_{idx}',                                # member_0 格式
            f'member_{idx+1}',                              # member_1 格式（1-based）
        ]

        for key in candidates:
            if key in data and isinstance(data[key], dict):
                print(f"✅ 成员 {member_name} 匹配到键: {key}")
                return data[key]

        # 严格模式：找不到直接返回空
        if strict:
            available_keys = list(data.keys())
            print(f"❌ 严格模式：找不到成员 {member_name} (索引{idx}) 的分析数据")
            print(f"   可用键: {available_keys}")
            return {}

        # 非严格模式：兜底到第一个有效字典（保留原逻辑但加警告）
        print(f"⚠️  警告：成员 {member_name} 未匹配，兜底到第一个可用数据")
        for v in data.values():
            if isinstance(v, dict):
                return v
        return {}

    # 情况 3：列表格式
    if isinstance(data, list):
        if 0 <= idx < len(data) and isinstance(data[idx], dict):
            print(f"✅ 成员 {member_name} 匹配到列表索引: {idx}")
            return data[idx]

        if strict:
            print(f"❌ 严格模式：索引 {idx} 超出列表范围（长度 {len(data)}）")
            return {}

        # 兜底到第一个
        for v in data:
            if isinstance(v, dict):
                print(f"⚠️  警告：成员 {member_name} 使用兜底数据")
                return v

    return {}


# ==================== 语言检测 ====================

# ==================== 模板选择 ====================

def get_template_path(
    template_type: str, language: str, template_dir: Path, version: str = "V2"
) -> Path:
    """获取模板文件路径 - 支持多语言 - V5.8.1

    查找顺序（按优先级）：
    1. 完整版：{TYPE}_TEMPLATE_MEDICAL_{VERSION}_{LANG}.html (日报)
       或 {TYPE}_TEMPLATE_MEDICAL_{LANG}.html (周报/月报)
    2. 语言版（无版本）：{TYPE}_TEMPLATE_MEDICAL_{LANG}.html (日报回退)
    3. 版本默认：{TYPE}_TEMPLATE_MEDICAL_{VERSION}.html (日报中文)
    4. 默认：{TYPE}_TEMPLATE_MEDICAL.html (中文回退)
    """
    template_dir = Path(template_dir)
    type_upper = template_type.upper()
    lang_upper = language.upper()

    # 构建候选列表
    candidates = []

    # 区分日报和周月报的模板命名规则
    is_weekly_monthly = template_type.lower() in ['weekly', 'monthly']

    if is_weekly_monthly:
        # 周报/月报: 没有版本号，格式为 WEEKLY_TEMPLATE_MEDICAL[_EN].html
        base_name = f"{type_upper}_TEMPLATE_MEDICAL"

        # 1. 语言版（非中文）
        if lang_upper != "CN":
            candidates.append(template_dir / f"{base_name}_{lang_upper}.html")

        # 2. 默认（中文或无语言后缀）
        candidates.append(template_dir / f"{base_name}.html")
    else:
        # 日报: 有版本号，格式为 DAILY_TEMPLATE_MEDICAL_V2[_EN].html
        base_name = f"{type_upper}_TEMPLATE_MEDICAL_{version}"

        # 1. 完整版（版本+语言）
        if lang_upper != "CN":
            candidates.append(template_dir / f"{base_name}_{lang_upper}.html")

        # 2. 语言版（无版本，日报回退）
        if lang_upper != "CN":
            candidates.append(template_dir / f"{type_upper}_TEMPLATE_MEDICAL_{lang_upper}.html")

        # 3. 版本默认（中文）
        candidates.append(template_dir / f"{base_name}.html")

        # 4. 默认（中文回退）
        candidates.append(template_dir / f"{type_upper}_TEMPLATE_MEDICAL.html")

    for i, p in enumerate(candidates, 1):
        if p.exists():
            if i > 1:
                print(f"⚠️ 警告: 模板回退到 {p.name}")
            return p

    raise FileNotFoundError(
        "找不到模板文件。尝试了以下路径:\n" + "\n".join([f" - {c}" for c in candidates])
    )


def list_available_templates(template_dir: Path) -> dict:
    """列出所有可用的模板

    返回:
        {
            "daily": ["CN", "EN"],
            "weekly": ["CN", "EN"],
            "monthly": ["CN", "EN"]
        }
    """
    template_dir = Path(template_dir)
    result = {"daily": [], "weekly": [], "monthly": []}

    if not template_dir.exists():
        return result

    for template_type in ["daily", "weekly", "monthly"]:
        type_upper = template_type.upper()

        # 查找所有匹配该类型的模板
        for template_file in template_dir.glob(f"{type_upper}_TEMPLATE_MEDICAL*.html"):
            name = template_file.stem  # 不含扩展名

            # 解析语言代码
            # DAILY_TEMPLATE_MEDICAL_V2_EN -> EN
            # DAILY_TEMPLATE_MEDICAL_V2 -> default
            parts = name.split('_')

            if len(parts) >= 2 and parts[-1] in ['CN', 'EN', 'JP', 'KR', 'FR', 'DE']:
                lang = parts[-1]
                if lang not in result[template_type]:
                    result[template_type].append(lang)
            elif 'V2' in parts or 'V1' in parts or template_type in ['weekly', 'monthly']:
                # 默认模板(无语言后缀) - weekly/monthly没有版本号,直接识别基础文件名
                if 'default' not in result[template_type]:
                    result[template_type].append('default')

    return result


def validate_templates_exist(template_dir: Path, language: str = "CN") -> dict:
    """验证必需的模板文件是否存在

    返回:
        {
            "daily": bool,
            "weekly": bool,
            "monthly": bool,
            "errors": [str]
        }
    """
    result = {"daily": False, "weekly": False, "monthly": False, "errors": []}
    template_dir = Path(template_dir)

    if not template_dir.exists():
        result["errors"].append(f"模板目录不存在: {template_dir}")
        return result

    # 检查日报模板
    daily_candidates = [
        template_dir / f"DAILY_TEMPLATE_MEDICAL_V2_{language.upper()}.html",
        template_dir / f"DAILY_TEMPLATE_MEDICAL_V2.html",
    ]
    result["daily"] = any(p.exists() for p in daily_candidates)
    if not result["daily"]:
        result["errors"].append(f"缺少日报模板，尝试了: {[p.name for p in daily_candidates]}")

    # 检查周报模板
    weekly_candidates = [
        template_dir / f"WEEKLY_TEMPLATE_MEDICAL_{language.upper()}.html",
        template_dir / f"WEEKLY_TEMPLATE_MEDICAL.html",
    ]
    result["weekly"] = any(p.exists() for p in weekly_candidates)
    if not result["weekly"]:
        result["errors"].append(f"缺少周报模板，尝试了: {[p.name for p in weekly_candidates]}")

    # 检查月报模板
    monthly_candidates = [
        template_dir / f"MONTHLY_TEMPLATE_MEDICAL_{language.upper()}.html",
        template_dir / f"MONTHLY_TEMPLATE_MEDICAL.html",
    ]
    result["monthly"] = any(p.exists() for p in monthly_candidates)
    if not result["monthly"]:
        result["errors"].append(f"缺少月报模板，尝试了: {[p.name for p in monthly_candidates]}")

    return result


# ==================== 睡眠数据解析 ====================

from datetime import datetime, timedelta
from typing import List

def parse_sleep_data_unified(
    date_str: str,
    health_dir: Path,
    read_mode: str = 'next_day',
    start_hour: int = 20,
    end_hour: int = 12
) -> Dict[str, Any]:
    """统一睡眠数据解析函数 - V5.8.1

    参数:
        date_str: 目标日期 (YYYY-MM-DD)
        health_dir: Health数据目录路径
        read_mode: 读取模式
            - 'next_day': 读取次日文件，筛选当天20:00-次日12:00
            - 'same_day': 读取当天文件，筛选前一天20:00-当天12:00
        start_hour: 睡眠窗口开始小时（默认20点）
        end_hour: 睡眠窗口结束小时（默认次日12点）

    返回:
        {
            'records': [...],  # 原始睡眠记录列表
            'total_hours': float,  # 总睡眠时长
            'deep_hours': float,
            'core_hours': float,
            'rem_hours': float,
            'awake_hours': float,
            'bedtime': str,  # 入睡时间 (HH:MM)
            'waketime': str,  # 起床时间 (HH:MM)
        }
    """
    date = datetime.strptime(date_str, '%Y-%m-%d')

    # 根据模式确定要读取的文件和日期范围
    if read_mode == 'next_day':
        next_date = date + timedelta(days=1)
        sleep_file_date = next_date
        filter_start_date = date
        filter_end_date = next_date
    else:  # same_day
        prev_date = date - timedelta(days=1)
        sleep_file_date = date
        filter_start_date = prev_date
        filter_end_date = date

    # 读取文件
    health_dir = Path(health_dir).expanduser()
    sleep_file = health_dir / f'HealthAutoExport-{sleep_file_date.strftime("%Y-%m-%d")}.json'

    if not sleep_file.exists():
        return {
            'records': [],
            'total_hours': 0,
            'deep_hours': 0,
            'core_hours': 0,
            'rem_hours': 0,
            'awake_hours': 0,
            'bedtime': '--',
            'waketime': '--',
        }

    try:
        with open(sleep_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception:
        return {
            'records': [],
            'total_hours': 0,
            'deep_hours': 0,
            'core_hours': 0,
            'rem_hours': 0,
            'awake_hours': 0,
            'bedtime': '--',
            'waketime': '--',
        }

    # 提取睡眠记录（兼容两种数据结构）
    sleep_data = data.get('data', {}).get('sleep_analysis')
    if not sleep_data:
        metrics = data.get('data', {}).get('metrics', [])
        metrics_dict = {m.get('name'): m for m in metrics if 'name' in m}
        sleep_data = metrics_dict.get('sleep_analysis', {})

    if not sleep_data:
        return {
            'records': [],
            'total_hours': 0,
            'deep_hours': 0,
            'core_hours': 0,
            'rem_hours': 0,
            'awake_hours': 0,
            'bedtime': '--',
            'waketime': '--',
        }

    # 筛选符合条件的记录
    sleep_records = []
    earliest_start = None
    latest_end = None

    for record in sleep_data.get('data', []):
        start_ts = record.get('sleepStart')
        end_ts = record.get('sleepEnd')
        if not start_ts or not end_ts:
            continue

        # 解析时间（兼容秒/毫秒时间戳，以及常见字符串格式）
        def _parse_sleep_ts(ts):
            if isinstance(ts, (int, float)):
                ts_num = float(ts)
                if ts_num > 1e12:  # 毫秒
                    ts_num /= 1000.0
                return datetime.fromtimestamp(ts_num)

            ts_text = str(ts).strip()
            # 纯数字字符串（秒/毫秒）
            try:
                ts_num = float(ts_text)
                if ts_num > 1e12:
                    ts_num /= 1000.0
                return datetime.fromtimestamp(ts_num)
            except (ValueError, TypeError, OSError, OverflowError):
                pass

            # 字符串日期（保留到秒）
            return datetime.strptime(ts_text[:19], '%Y-%m-%d %H:%M:%S')

        try:
            start_dt = _parse_sleep_ts(start_ts)
            end_dt = _parse_sleep_ts(end_ts)
        except (ValueError, TypeError, OSError, OverflowError):
            continue

        # 筛选逻辑
        start_date = start_dt.strftime('%Y-%m-%d')
        record_start_hour = start_dt.hour

        if read_mode == 'next_day':
            belongs_to_date = (
                (start_date == filter_start_date.strftime('%Y-%m-%d') and record_start_hour >= start_hour) or
                (start_date == filter_end_date.strftime('%Y-%m-%d') and record_start_hour < end_hour)
            )
        else:  # same_day
            belongs_to_date = (
                (start_date == filter_start_date.strftime('%Y-%m-%d') and record_start_hour >= start_hour) or
                (start_date == filter_end_date.strftime('%Y-%m-%d') and record_start_hour < end_hour)
            )

        if belongs_to_date:
            duration_hours = (end_dt - start_dt).total_seconds() / 3600

            # 获取原始值
            deep_raw = record.get('deep', 0) or 0
            core_raw = record.get('core', 0) or 0
            rem_raw = record.get('rem', 0) or 0
            awake_raw = record.get('awake', 0) or 0

            # 统一转换为小时（假设原始值可能是分钟或小时）
            def normalize_hours(value, field_name=""):
                if not value or value <= 0:
                    return 0.0

                # 判断是否为睡眠阶段字段
                is_stage = any(x in field_name.lower() for x in ['deep', 'core', 'rem', 'awake'])

                # 更智能的单位判断逻辑
                if is_stage:
                    # 睡眠阶段正常范围：0.5-5 小时（30-300 分钟）
                    # 值 > 30 几乎肯定是分钟
                    if value > 30:
                        return round(value / 60.0, 2)
                    # 值在 10-30 之间：如果是整数可能是分钟，如果是小数可能是小时
                    elif value > 10 and float(value) == int(value):
                        return round(value / 60.0, 2)
                else:
                    # 总睡眠正常范围：3-12 小时（180-720 分钟）
                    # 值 > 100 肯定是分钟
                    if value > 100:
                        return round(value / 60.0, 2)

                return round(float(value), 2)

            deep_h = normalize_hours(deep_raw, 'deep')
            core_h = normalize_hours(core_raw, 'core')
            rem_h = normalize_hours(rem_raw, 'rem')
            awake_h = normalize_hours(awake_raw, 'awake')
            stage_total = deep_h + core_h + rem_h + awake_h

            # 若分期字段缺失，则回退到 start/end 计算出的时长，避免 total_hours 被错误算成 0
            total_h = stage_total if stage_total > 0 else max(duration_hours, 0.0)

            sleep_records.append({
                'start': start_dt.strftime('%H:%M'),
                'end': end_dt.strftime('%H:%M'),
                'total': round(total_h, 2),
                'deep': deep_h,
                'core': core_h,
                'rem': rem_h,
                'awake': awake_h,
            })

            # 记录最早入睡和最晚起床（按完整 datetime 比较）
            if earliest_start is None or start_dt < earliest_start:
                earliest_start = start_dt
            if latest_end is None or end_dt > latest_end:
                latest_end = end_dt

    # 计算总时长
    deep = sum(r['deep'] for r in sleep_records)
    core = sum(r['core'] for r in sleep_records)
    rem = sum(r['rem'] for r in sleep_records)
    awake = sum(r['awake'] for r in sleep_records)
    total = sum(r['total'] for r in sleep_records)

    return {
        'records': sleep_records,
        'total_hours': round(total, 2),
        'deep_hours': round(deep, 2),
        'core_hours': round(core, 2),
        'rem_hours': round(rem, 2),
        'awake_hours': round(awake, 2),
        'bedtime': earliest_start.strftime('%H:%M') if earliest_start else '--',
        'waketime': latest_end.strftime('%H:%M') if latest_end else '--',
    }


# ==================== 成员配置获取 ====================

def get_member_config_unified(
    config: dict,
    member_idx: int,
    strict: bool = True
) -> Dict[str, Any]:
    """统一获取成员配置

    参数:
        config: 配置字典
        member_idx: 成员索引（从0开始）
        strict: 严格模式（True=越界时报错，False=越界时回退到第一个）

    返回:
        成员配置字典

    异常:
        ConfigError: 严格模式下索引越界时抛出
    """
    members = config.get('members', [])
    MAX_MEMBERS = 3

    # 限制最大成员数
    if len(members) > MAX_MEMBERS:
        members = members[:MAX_MEMBERS]

    if not members:
        raise ConfigError("config.json 中未配置任何成员")

    # 检查索引范围
    if member_idx < 0 or member_idx >= len(members):
        if strict:
            raise ConfigError(
                f"成员索引 {member_idx} 超出范围 (有效范围: 0-{len(members)-1}, "
                f"总成员数: {len(members)})"
            )
        else:
            # 非严格模式：记录警告并回退到第一个成员
            print(f"⚠️  警告: 成员索引 {member_idx} 超出范围，回退到第一个成员")
            member_idx = 0

    member = members[member_idx]

    return {
        'name': member.get('name', f'成员{member_idx+1}'),
        'age': member.get('age'),
        'gender': member.get('gender'),
        'height_cm': member.get('height_cm'),
        'weight_kg': member.get('weight_kg'),
        'health_dir': member.get('health_dir', '~/Health Auto Export/Health Data'),
        'workout_dir': member.get('workout_dir', '~/Health Auto Export/Workout Data'),
        'email': member.get('email', ''),
    }


# ==================== 日期格式化 ====================

def get_ordinal_suffix(day: int) -> str:
    """获取英文序数后缀 (1st, 2nd, 3rd, 4th...)"""
    if 11 <= day <= 13:
        return "th"
    last_digit = day % 10
    if last_digit == 1:
        return "st"
    elif last_digit == 2:
        return "nd"
    elif last_digit == 3:
        return "rd"
    else:
        return "th"


def format_date(date_str: str, format_type: str = "full", language: str = "CN") -> str:
    """格式化日期 - V5.8.1

    参数:
        date_str: 日期字符串 (YYYY-MM-DD) 或 datetime 对象
        format_type: 格式类型
            - "full": 完整日期 (如 "2026年3月1日" / "March 1, 2026")
            - "month_year": 年月 (如 "2026年3月" / "Mar 2026")
            - "day": 仅日期数字 (如 "1" / "1st")
            - "short": 短格式 (如 "3/1" / "01/03")
        language: 语言代码

    返回:
        格式化后的日期字符串
    """
    if isinstance(date_str, str):
        date = datetime.strptime(date_str, "%Y-%m-%d")
    else:
        date = date_str

    # 多语言配置
    locales = {
        "CN": {
            "month_names": ['', '1月', '2月', '3月', '4月', '5月', '6月',
                           '7月', '8月', '9月', '10月', '11月', '12月'],
            "month_names_full": ['', '一月', '二月', '三月', '四月', '五月', '六月',
                                '七月', '八月', '九月', '十月', '十一月', '十二月'],
            "format": {
                "full": lambda d: f"{d.year}年{d.month}月{d.day}日",
                "month_year": lambda d: f"{d.year}年{d.month}月",
                "day": lambda d: str(d.day),
                "short": lambda d: f"{d.month}/{d.day}",
            }
        },
        "EN": {
            "month_names": ['', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                           'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
            "month_names_full": ['', 'January', 'February', 'March', 'April', 'May', 'June',
                                'July', 'August', 'September', 'October', 'November', 'December'],
            "format": {
                "full": lambda d: f"{locales['EN']['month_names_full'][d.month]} {d.day}, {d.year}",
                "month_year": lambda d: f"{locales['EN']['month_names'][d.month]} {d.year}",
                "day": lambda d: f"{d.day}{get_ordinal_suffix(d.day)}",
                "short": lambda d: f"{d.day:02d}/{d.month:02d}",
            }
        },
        "JP": {
            "month_names": ['', '1月', '2月', '3月', '4月', '5月', '6月',
                           '7月', '8月', '9月', '10月', '11月', '12月'],
            "format": {
                "full": lambda d: f"{d.year}年{d.month}月{d.day}日",
                "month_year": lambda d: f"{d.year}年{d.month}月",
                "day": lambda d: str(d.day),
                "short": lambda d: f"{d.month}/{d.day}",
            }
        }
    }

    # 默认使用英文
    locale = locales.get(language, locales["EN"])

    formatter = locale["format"].get(format_type, locale["format"]["full"])
    return formatter(date)


def format_week_range(start_date: str, end_date: str, language: str = "CN") -> str:
    """格式化周范围

    例如:
        CN: "第9周"
        EN: "Week 9"
    """
    start = datetime.strptime(start_date, "%Y-%m-%d")
    week_num = start.isocalendar()[1]

    if language == "CN":
        return f"第{week_num}周"
    elif language == "EN":
        return f"Week {week_num}"
    elif language == "JP":
        return f"第{week_num}週"
    else:
        return f"Week {week_num}"


# ==================== 多成员处理结果 ====================

from dataclasses import dataclass, field

@dataclass
class MemberResult:
    """单个成员的处理结果"""
    index: int
    name: str
    success: bool = False
    error_message: str = ""
    output_files: List[str] = field(default_factory=list)

    def __str__(self):
        status = "✅ 成功" if self.success else "❌ 失败"
        return f"成员 {self.index+1} ({self.name}): {status}"


class MultiMemberProcessor:
    """多成员处理器 - 确保一个成员失败不影响其他成员"""

    def __init__(self):
        self.results: List[MemberResult] = []

    def process_member(self, index: int, name: str, process_func) -> MemberResult:
        """处理单个成员，捕获所有异常

        参数:
            index: 成员索引
            name: 成员名称
            process_func: 处理函数，接收 () 参数，返回输出文件列表或 None

        返回:
            MemberResult 对象
        """
        result = MemberResult(index=index, name=name)

        try:
            print(f"\n{'='*60}")
            print(f"🧑 处理成员 {index+1}: {name}")
            print(f"{'='*60}")

            output = process_func()

            if output:
                if isinstance(output, list):
                    result.output_files = output
                else:
                    result.output_files = [output]
                result.success = True
                print(f"✅ 成员 {name} 处理成功")
            else:
                result.error_message = "处理函数返回空"
                print(f"⚠️  成员 {name} 处理返回空")

        except FileNotFoundError as e:
            result.error_message = f"数据文件不存在: {e}"
            print(f"❌ 成员 {name} 处理失败: 数据文件不存在 - {e}")
        except json.JSONDecodeError as e:
            result.error_message = f"JSON解析失败: {e}"
            print(f"❌ 成员 {name} 处理失败: JSON解析错误 - {e}")
        except ValidationError as e:
            result.error_message = f"验证失败: {e}"
            print(f"❌ 成员 {name} 处理失败: 验证错误 - {e}")
        except Exception as e:
            result.error_message = f"{type(e).__name__}: {str(e)}"
            print(f"❌ 成员 {name} 处理失败: {e}")
            import traceback
            traceback.print_exc()

        self.results.append(result)
        return result

    def print_summary(self):
        """打印处理摘要"""
        print(f"\n{'='*60}")
        print("📊 多成员处理摘要")
        print(f"{'='*60}")

        success_count = sum(1 for r in self.results if r.success)
        total_count = len(self.results)

        print(f"总计: {success_count}/{total_count} 成功\n")

        for result in self.results:
            print(f"  {result}")
            if not result.success:
                print(f"     错误: {result.error_message}")
            if result.output_files:
                for f in result.output_files:
                    print(f"     输出: {f}")

        print(f"{'='*60}\n")

        return success_count == total_count

# ==================== JSON Schema 验证 ====================

def validate_config_schema(config: dict) -> list:
    """验证配置是否符合基础约束（不依赖外部 jsonschema 库）"""
    errors = []

    # 基础类型
    if not isinstance(config, dict):
        errors.append("配置必须是 JSON 对象")
        return errors

    # 必填字段
    required = ["version", "members", "language"]
    for field in required:
        if field not in config:
            errors.append(f"缺少必填字段: {field}")

    # version - 支持 5.8.x 和 5.9.x
    version = config.get('version')
    if version is not None:
        import re
        if not re.match(r'^5\.(8|9)\.\d+$', str(version)):
            errors.append(f"version '{version}' 无效，格式应为 5.8.x 或 5.9.x")

    # members
    members = config.get('members', [])
    if not isinstance(members, list):
        errors.append("members 必须是数组")
        members = []

    if len(members) == 0:
        errors.append("至少需要配置 1 个成员")
    if len(members) > 3:
        errors.append(f"成员数量 {len(members)} 超过最大限制 3")

    for i, member in enumerate(members[:3]):
        if not isinstance(member, dict):
            errors.append(f"members[{i}] 必须是对象")
            continue

        for k in ['name', 'health_dir', 'workout_dir']:
            if not member.get(k):
                errors.append(f"members[{i}] 缺少成员必填字段: {k}")

        # 可选 email 格式校验
        email = member.get('email', '')
        if email and '@' not in str(email):
            errors.append(f"members[{i}].email 格式无效: {email}")

        # 放宽的数值范围验证（仅警告极端值，不排除边界情况）
        age = member.get('age')
        if age is not None:
            if not isinstance(age, (int, float)):
                errors.append(f"members[{i}].age 必须是数字")
            elif age < 1 or age > 130:
                errors.append(f"members[{i}].age 值 {age} 超出正常范围 (1-130)")

        height_cm = member.get('height_cm')
        if height_cm is not None:
            if not isinstance(height_cm, (int, float)):
                errors.append(f"members[{i}].height_cm 必须是数字")
            elif height_cm < 50 or height_cm > 250:
                errors.append(f"members[{i}].height_cm 值 {height_cm} 超出正常范围 (50-250 cm)")

        weight_kg = member.get('weight_kg')
        if weight_kg is not None:
            if not isinstance(weight_kg, (int, float)):
                errors.append(f"members[{i}].weight_kg 必须是数字")
            elif weight_kg < 10 or weight_kg > 400:
                errors.append(f"members[{i}].weight_kg 值 {weight_kg} 超出正常范围 (10-400 kg)")

    # 检查成员名唯一性
    member_names = []
    safe_names = []
    for i, member in enumerate(members[:3]):
        if isinstance(member, dict):
            name = member.get('name', '')
            if name:
                if name in member_names:
                    errors.append(f"members[{i}].name '{name}' 与其他成员重复")
                member_names.append(name)

                # 检查 safe_member_name 冲突，避免输出文件名互相覆盖
                safe_name = safe_member_name(name)
                if safe_name in safe_names:
                    errors.append(
                        f"members[{i}].name '{name}' 转换后的安全名 '{safe_name}' 与其他成员冲突，请修改成员名称"
                    )
                safe_names.append(safe_name)

    # language
    language = config.get('language', 'CN')
    if language not in ['CN', 'EN']:
        errors.append(f"语言设置 '{language}' 无效，必须是 'CN' 或 'EN'")

    # validation_mode
    validation_mode = config.get('validation_mode', 'strict')
    if validation_mode not in ['strict', 'warn']:
        errors.append(f"validation_mode '{validation_mode}' 无效，必须是 'strict' 或 'warn'")

    # analysis_limits
    limits = config.get('analysis_limits', {})
    if limits and not isinstance(limits, dict):
        errors.append("analysis_limits 必须是对象")
    elif isinstance(limits, dict):
        int_keys = [
            'metric_min_words', 'metric_max_words',
            'action_min_words', 'action_max_words',
            'daily_min_words', 'weekly_min_words', 'monthly_min_words',
            'monthly_trend_min_words'
        ]
        for k in int_keys:
            if k in limits:
                v = limits.get(k)
                if not isinstance(v, int) or v <= 0:
                    errors.append(f"analysis_limits.{k} 必须是正整数")

        metric_min = limits.get('metric_min_words', 150)
        metric_max = limits.get('metric_max_words', 200)
        action_min = limits.get('action_min_words', 250)
        action_max = limits.get('action_max_words', 300)
        daily_min = limits.get('daily_min_words', 500)
        weekly_min = limits.get('weekly_min_words', 800)
        monthly_min = limits.get('monthly_min_words', 1000)

        if metric_min > metric_max:
            errors.append("analysis_limits.metric_min_words 不能大于 metric_max_words")
        if action_min > action_max:
            errors.append("analysis_limits.action_min_words 不能大于 action_max_words")
        if weekly_min < daily_min:
            errors.append("analysis_limits.weekly_min_words 不能小于 daily_min_words")
        if monthly_min < weekly_min:
            errors.append("analysis_limits.monthly_min_words 不能小于 weekly_min_words")
        if metric_min > daily_min:
            errors.append("analysis_limits.metric_min_words 应小于等于 daily_min_words")
        if action_min > daily_min:
            errors.append("analysis_limits.action_min_words 应小于等于 daily_min_words")

        ratio_keys = [
            'lang_en_max_chinese_ratio_strict',
            'lang_en_max_chinese_ratio_warn',
            'lang_cn_min_chinese_ratio_strict',
            'lang_cn_min_chinese_ratio_warn',
        ]
        for k in ratio_keys:
            if k in limits:
                v = limits.get(k)
                if not isinstance(v, (int, float)):
                    errors.append(f"analysis_limits.{k} 必须是数字")
                elif v < 0 or v > 1:
                    errors.append(f"analysis_limits.{k} 必须在 0 到 1 之间")

    # sleep_config
    sleep_config = config.get('sleep_config', {})
    if sleep_config and not isinstance(sleep_config, dict):
        errors.append("sleep_config 必须是对象")
    elif isinstance(sleep_config, dict) and sleep_config:
        read_mode = sleep_config.get('read_mode', 'next_day')
        if read_mode not in ['next_day', 'same_day']:
            errors.append(f"sleep_config.read_mode '{read_mode}' 无效，必须是 next_day 或 same_day")

        start_hour = sleep_config.get('start_hour', 20)
        end_hour = sleep_config.get('end_hour', 12)
        if not isinstance(start_hour, int) or start_hour < 0 or start_hour > 23:
            errors.append("sleep_config.start_hour 必须是 0-23 的整数")
        if not isinstance(end_hour, int) or end_hour < 0 or end_hour > 23:
            errors.append("sleep_config.end_hour 必须是 0-23 的整数")

    # email_config
    email_config = config.get('email_config', {})
    if email_config and not isinstance(email_config, dict):
        errors.append("email_config 必须是对象")
    elif isinstance(email_config, dict):
        priority = email_config.get('provider_priority', [])
        valid_providers = ['oauth2', 'smtp', 'mail_app', 'local']

        if priority:
            if not isinstance(priority, list):
                errors.append("email_config.provider_priority 必须是数组")
            else:
                for provider in priority:
                    if provider not in valid_providers:
                        errors.append(f"未知的邮件 provider: {provider}")
                if len(set(priority)) != len(priority):
                    errors.append("email_config.provider_priority 不允许重复项")

        oauth2 = email_config.get('oauth2', {})
        if isinstance(oauth2, dict) and oauth2.get('enabled'):
            for k in ['client_id', 'client_secret', 'refresh_token', 'sender_email']:
                if not oauth2.get(k):
                    errors.append(f"email_config.oauth2 启用时缺少字段: {k}")

        smtp = email_config.get('smtp', {})
        if isinstance(smtp, dict) and smtp.get('enabled'):
            for k in ['sender_email', 'password']:
                if not smtp.get(k):
                    errors.append(f"email_config.smtp 启用时缺少字段: {k}")

        local_cfg = email_config.get('local', {})
        if isinstance(local_cfg, dict) and local_cfg.get('enabled'):
            if not local_cfg.get('output_dir'):
                errors.append("email_config.local 启用时缺少字段: output_dir")

    # report_metrics 校验
    report_metrics = config.get('report_metrics', {})
    if report_metrics and not isinstance(report_metrics, dict):
        errors.append("report_metrics 必须是对象")
    elif isinstance(report_metrics, dict):
        selected = report_metrics.get('selected', [])
        if selected and not isinstance(selected, list):
            errors.append("report_metrics.selected 必须是数组")
        elif isinstance(selected, list):
            allowed = set([
                "hrv","resting_hr","heart_rate_avg","steps","distance","active_energy","spo2","respiratory_rate","apple_stand_time","basal_energy_burned",
                "vo2_max","physical_effort","sleep_total_hours","sleep_deep_hours","sleep_rem_hours","breathing_disturbances",
                "apple_exercise_time","flights_climbed","apple_stand_hour","stair_speed_up",
                "running_speed","running_power","running_stride_length","running_ground_contact_time","running_vertical_oscillation",
                "walking_speed","walking_step_length","walking_heart_rate_average","walking_asymmetry_percentage","walking_double_support_percentage",
                "headphone_audio_exposure","environmental_audio_exposure"
            ])
            for k in selected:
                if k not in allowed:
                    errors.append(f"report_metrics.selected 包含未知指标: {k}")

        for b in [
            "sort_by_importance", "show_empty_categories", "show_sleep_in_metrics_table",
            "hide_no_data_metrics", "require_ai_for_selected"
        ]:
            if b in report_metrics and not isinstance(report_metrics[b], bool):
                errors.append(f"report_metrics.{b} 必须是布尔值")

        category_order = report_metrics.get('category_order', [])
        if category_order and not isinstance(category_order, list):
            errors.append("report_metrics.category_order 必须是数组")
        elif isinstance(category_order, list):
            allowed_categories = set([
                "core_health","cardio_fitness","sleep_recovery","activity_mobility",
                "running_advanced","walking_gait","stairs_strength","environment_audio"
            ])
            for c in category_order:
                if c not in allowed_categories:
                    errors.append(f"report_metrics.category_order 包含未知类别: {c}")

        importance_overrides = report_metrics.get('importance_overrides', {})
        if importance_overrides and not isinstance(importance_overrides, dict):
            errors.append("report_metrics.importance_overrides 必须是对象")
        elif isinstance(importance_overrides, dict):
            for k, v in importance_overrides.items():
                if not isinstance(v, int) or v < 0 or v > 10:
                    errors.append(f"report_metrics.importance_overrides.{k} 必须是 0-10 的整数")

    return errors


# ==================== 改进的语言检测 V3 ====================

def detect_language_advanced(text: str) -> str:
    """使用 langdetect 检测文本语言

    返回: 'zh' (中文), 'en' (英文), 或其他语言代码
    """
    if not LANGDETECT_AVAILABLE:
        return 'unknown'

    if not text or len(text.strip()) < 10:
        return 'unknown'

    try:
        sample = text[:500]
        lang = detect(sample)
        return lang
    except Exception:
        return 'unknown'


def _collect_text_values(obj: Any) -> List[str]:
    texts: List[str] = []
    if isinstance(obj, dict):
        for v in obj.values():
            texts.extend(_collect_text_values(v))
    elif isinstance(obj, list):
        for item in obj:
            texts.extend(_collect_text_values(item))
    elif isinstance(obj, str):
        texts.append(obj)
    return texts


def count_text_units(text: Any, language: str = "CN") -> int:
    """统计文本长度单位。

    - EN: 按英文单词数统计
    - CN/其他: 按非空白字符数统计（近似"字数"）
    """
    if not isinstance(text, str):
        return 0

    text = text.strip()
    if not text:
        return 0

    lang = str(language or "CN").upper()

    if lang == "EN":
        # 支持普通英文词、缩写（don't）和数字
        words = re.findall(r"[A-Za-z]+(?:'[A-Za-z]+)?|\d+(?:\.\d+)?", text)
        return len(words)

    # CN/其他语言：统计非空白字符（更符合"字数"语义，且兼容中英混排）
    return len(re.sub(r"\s+", "", text))


def _get_language_ratio_thresholds() -> dict:
    """读取语言检测阈值（支持 analysis_limits 覆盖）。"""
    defaults = {
        'lang_en_max_chinese_ratio_strict': 0.15,
        'lang_en_max_chinese_ratio_warn': 0.20,
        'lang_cn_min_chinese_ratio_strict': 0.30,
        'lang_cn_min_chinese_ratio_warn': 0.20,
    }

    try:
        cfg = load_config()
        limits = cfg.get('analysis_limits', {}) if isinstance(cfg, dict) else {}
        if not isinstance(limits, dict):
            return defaults

        result = defaults.copy()
        for k in defaults:
            v = limits.get(k)
            if isinstance(v, (int, float)) and 0 <= float(v) <= 1:
                result[k] = float(v)
        return result
    except Exception:
        return defaults


def detect_language_mismatch_v3(
    ai_analysis: dict,
    expected_language: str,
    strict_mode: bool = False
) -> list:
    """改进的语言检测 V3 - 基于字符统计和langdetect

    参数:
        ai_analysis: AI分析结果字典
        expected_language: 期望语言 ("CN" 或 "EN")
        strict_mode: 严格模式（False时允许少量其他语言字符）

    返回:
        错误列表，为空表示检测通过
    """
    errors = []
    if expected_language not in ("CN", "EN"):
        return errors

    # 提取所有文本内容（仅值，忽略key，减少误判）
    text_values = _collect_text_values(ai_analysis)
    full_text = "\n".join([t for t in text_values if t and isinstance(t, str)])

    # 默认指标名白名单（这些词不计入语言统计）
    default_cn_metrics = [
        "心率", "HRV", "静息心率", "步数", "距离", "活动能量",
        "血氧", "爬楼", "站立", "基础代谢", "呼吸率", "睡眠", "运动",
        "千卡", "公里", "小时", "分钟", "次", "层", "步", "毫秒",
        "bpm", "ms", "深睡", "核心睡眠", "REM", "清醒"
    ]
    default_en_metrics = [
        "HRV", "Resting HR", "Steps", "Distance", "Active Energy",
        "SpO2", "Flights", "Stand", "Basal", "Respiratory", "Sleep", "Workout",
        "kcal", "km", "hours", "minutes", "bpm", "ms", "floors",
        "Deep", "Core", "REM", "Awake"
    ]

    # 移除指标名
    text_for_check = full_text
    for metric in default_cn_metrics + default_en_metrics:
        text_for_check = text_for_check.replace(metric, "")

    # 统计中文字符
    chinese_chars = len(re.findall(r'[\u4e00-\u9fa5]', text_for_check))
    total_chars = len(text_for_check.strip())

    if total_chars == 0:
        return errors

    # 计算中文比例
    chinese_ratio = chinese_chars / total_chars

    # 读取可配置阈值
    thresholds = _get_language_ratio_thresholds()

    if expected_language == "EN":
        # EN模式：中文比例应低于阈值
        threshold = thresholds['lang_en_max_chinese_ratio_strict'] if strict_mode else thresholds['lang_en_max_chinese_ratio_warn']
        if chinese_ratio > threshold:
            errors.append(
                f"语言配置不匹配: 设置为 EN(英文), "
                f"但检测到 {chinese_chars} 个中文汉字 (占比 {chinese_ratio:.1%}, 阈值 {threshold:.0%})"
            )
    elif expected_language == "CN":
        # CN模式：中文比例应高于阈值
        threshold = thresholds['lang_cn_min_chinese_ratio_strict'] if strict_mode else thresholds['lang_cn_min_chinese_ratio_warn']
        if chinese_ratio < threshold:
            errors.append(
                f"语言配置不匹配: 设置为 CN(中文), "
                f"但只检测到 {chinese_chars} 个中文汉字 (占比 {chinese_ratio:.1%}, 阈值 {threshold:.0%})"
            )

    return errors

# 保留旧函数名兼容
detect_language_mismatch = detect_language_mismatch_v3


# ==================== 日志包装函数 ====================

def log_info(message: str) -> None:
    """记录信息日志"""
    _setup_file_handler()
    logger.info(message)


def log_warning(message: str) -> None:
    """记录警告日志"""
    _setup_file_handler()
    logger.warning(message)


def log_error(message: str, exc_info: bool = False) -> None:
    """记录错误日志"""
    _setup_file_handler()
    logger.error(message, exc_info=exc_info)


def log_debug(message: str) -> None:
    """记录调试日志"""
    _setup_file_handler()
    logger.debug(message)


def fix_json_quotes(json_text: str) -> str:
    """
    修复 JSON 中的弯引号/全角引号为标准英文引号
    """
    quote_mapping = {
        '\u201c': '"',  # 左弯双引号 "
        '\u201d': '"',  # 右弯双引号 "
        '\u2018': "'",  # 左弯单引号 '
        '\u2019': "'",  # 右弯单引号 '
        '\u300c': '"',  # 日式左引号 「
        '\u300d': '"',  # 日式右引号 」
        '\u300e': '"',  # 日式左双引号 『
        '\u300f': '"',  # 日式右双引号 』
        '\uff02': '"',  # 全角双引号 ＂
        '\uff07': "'",  # 全角单引号 ＇
    }

    for ch_quote, en_quote in quote_mapping.items():
        json_text = json_text.replace(ch_quote, en_quote)

    return json_text


def safe_json_loads(json_text: str, context: str = "") -> dict:
    """
    安全地解析 JSON，自动修复常见问题

    Args:
        json_text: JSON 字符串
        context: 上下文描述（用于错误报告）

    Returns:
        解析后的字典

    Raises:
        json.JSONDecodeError: 如果修复后仍无法解析
    """
    import json

    # 首先尝试直接解析
    try:
        return json.loads(json_text)
    except json.JSONDecodeError:
        pass

    # 尝试修复中文引号
    fixed_text = fix_json_quotes(json_text)

    try:
        result = json.loads(fixed_text)
        print(f"⚠️  {context}: JSON 已自动修复中文引号")
        return result
    except json.JSONDecodeError as e:
        # 修复失败，抛出原始错误
        raise json.JSONDecodeError(
            f"{context}: JSON 解析失败（已尝试修复中文引号）: {e}",
            e.doc if hasattr(e, 'doc') else json_text,
            e.pos if hasattr(e, 'pos') else 0
        )


def infer_duration_unit(duration_raw: float, workout: dict) -> tuple:
    """Infer duration unit (seconds or minutes).
    Returns: (duration_minutes, unit_inferred)
    """
    unit = str(workout.get('durationUnit') or workout.get('duration_unit') or '').lower()
    if unit in ('s', 'sec', 'second', 'seconds'):
        return duration_raw / 60.0, 'seconds'
    if unit in ('m', 'min', 'minute', 'minutes'):
        return float(duration_raw), 'minutes'

    if duration_raw > 1440:
        return duration_raw / 60.0, 'seconds'

    energy_raw = workout.get('energy', 0) or workout.get('activeEnergyBurned', 0) or workout.get('totalEnergyBurned', 0)
    if isinstance(energy_raw, dict):
        energy = energy_raw.get('qty', 0)
    else:
        energy = energy_raw
    if energy > 0 and duration_raw > 0:
        kcal = energy / 4.184
        kcal_per_min_if_minutes = kcal / duration_raw
        if kcal_per_min_if_minutes < 1.0:
            return duration_raw / 60.0, 'seconds'
        if kcal_per_min_if_minutes > 30.0:
            return duration_raw / 60.0, 'seconds'

    hr_data = workout.get('heartRateData', []) or workout.get('hrData', [])
    if len(hr_data) > 0:
        expected_mins_from_hr = len(hr_data)
        diff_if_minutes = abs(expected_mins_from_hr - duration_raw)
        diff_if_seconds = abs(expected_mins_from_hr - (duration_raw / 60.0))
        if diff_if_seconds < diff_if_minutes:
            return duration_raw / 60.0, 'seconds'
        return float(duration_raw), 'minutes'

    if duration_raw > 300:
        return duration_raw / 60.0, 'seconds'
    return float(duration_raw), 'minutes'


def get_workout_field(workout: dict, field_names: list, default=None):
    """
    兼容多种字段名获取workout数据
    按优先级尝试多个字段名
    """
    for name in field_names:
        if name in workout and workout[name] is not None:
            value = workout[name]
            # 处理字典格式（如 {"qty": 100, "units": "kJ"}）
            if isinstance(value, dict):
                # 如果是 heartRate 这种嵌套结构，提取 avg/max
                if 'avg' in value and isinstance(value['avg'], dict) and 'qty' in value['avg']:
                    return value['avg']['qty']
                if 'qty' in value:
                    return value.get('qty', default)
            return value
    return default
