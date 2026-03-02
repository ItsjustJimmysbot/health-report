#!/usr/bin/env python3
"""Health Report 共用工具函数 - V5.8.1"""

import json
import re
import sys
from pathlib import Path
from typing import Optional, Dict, Any, List, Union

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
    
    # 根据错误类型决定是否退出
    if exit_on_fatal and isinstance(error, (ConfigError, DataError)):
        sys.exit(1)


# ==================== 配置加载 ====================

def load_config() -> dict:
    """从 config.json 加载配置
    
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
                return json.load(f)
    
    return {}


# ==================== 成员名称处理 ====================

def safe_member_name(name: str) -> str:
    """将成员名称转换为安全的文件名格式
    
    替换规则：
    - 空格 -> 下划线
    - / -> 下划线
    - \\ -> 下划线
    """
    if not name:
        return "member"
    return (name or "member").strip().replace(' ', '_').replace('/', '_').replace('\\', '_')


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
    strict: bool = True
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

def detect_language_mismatch(ai_analysis: Dict, expected_language: str, 
                              whitelist: Optional[List[str]] = None) -> Optional[str]:
    """检测 AI 分析语言是否与配置匹配
    
    参数:
        ai_analysis: AI 分析数据
        expected_language: 期望的语言 ("CN" 或 "EN")
        whitelist: 允许的中文字符白名单（如指标名）
    
    返回:
        错误信息（不匹配时），匹配时返回 None
    """
    if expected_language not in ("CN", "EN"):
        return None
    
    full_text = json.dumps(ai_analysis, ensure_ascii=False)
    
    # 移除白名单中的词汇
    if whitelist:
        for word in whitelist:
            full_text = full_text.replace(word, "")
    
    # 统计中文字符
    chinese_chars = len(re.findall(r'[\u4e00-\u9fa5]', full_text))
    
    if expected_language == "EN" and chinese_chars > 20:
        return f"语言配置不匹配: 设置为 EN(英文), 但检测到 {chinese_chars} 个中文字符"
    elif expected_language == "CN" and chinese_chars < 20:
        return f"语言配置不匹配: 设置为 CN(中文), 但未检测到足够中文字符"
    
    return None


def detect_language_mismatch_v2(
    ai_analysis: dict, 
    expected_language: str,
    metric_names_cn: list = None,
    metric_names_en: list = None
) -> list:
    """改进的语言检测 - 排除指标名后检测 - V5.8.1
    
    参数:
        ai_analysis: AI分析数据字典
        expected_language: 期望语言 ("CN" 或 "EN")
        metric_names_cn: 中文指标名白名单（这些词不计入中文统计）
        metric_names_en: 英文指标名白名单（这些词不计入英文统计）
    
    返回:
        错误信息列表（为空表示通过检测）
    """
    errors = []
    
    if expected_language not in ("CN", "EN"):
        return errors
    
    # 默认指标名白名单
    default_cn_metrics = [
        "心率", "HRV", "静息心率", "步数", "距离", "活动能量", "血氧",
        "爬楼", "站立", "基础代谢", "呼吸率", "睡眠", "运动", "千卡",
        "公里", "小时", "分钟", "次", "层", "步", "毫秒", "bpm", "ms",
        "深睡", "核心睡眠", "REM", "清醒", "优秀", "良好", "一般", "需改善",
        "早餐", "午餐", "晚餐", "加餐", "苹果健康", "健康数据"
    ]
    
    default_en_metrics = [
        "HRV", "Resting HR", "Steps", "Distance", "Active Energy", "SpO2",
        "Flights", "Stand", "Basal", "Respiratory", "Sleep", "Workout",
        "kcal", "km", "hours", "minutes", "bpm", "ms", "floors",
        "Deep", "Core", "REM", "Awake", "Excellent", "Good", "Average", "Poor",
        "Breakfast", "Lunch", "Dinner", "Snack", "Apple Health"
    ]
    
    metric_names_cn = metric_names_cn or default_cn_metrics
    metric_names_en = metric_names_en or default_en_metrics
    
    # 提取所有文本内容
    full_text = json.dumps(ai_analysis, ensure_ascii=False)
    
    if expected_language == "EN":
        # 期望英文：移除英文指标名后，检测中文字符
        text_for_check = full_text
        for metric in metric_names_en:
            text_for_check = text_for_check.replace(metric, "")
        
        # 也移除常见的中文指标名（这些是正常的）
        for metric in metric_names_cn:
            text_for_check = text_for_check.replace(metric, "")
        
        chinese_chars = len(re.findall(r'[\u4e00-\u9fa5]', text_for_check))
        
        # 阈值提高到50个字符（允许少量中文引用）
        if chinese_chars > 50:
            # 提取违规的中文片段作为示例
            chinese_segments = re.findall(r'[\u4e00-\u9fa5]{5,}', text_for_check)
            examples = chinese_segments[:2] if chinese_segments else []
            
            error_msg = f"语言配置不匹配: 设置为 EN(英文), 但检测到 {chinese_chars} 个中文汉字"
            if examples:
                error_msg += f"（如: {'... '.join(examples)}...）"
            error_msg += "。请确保AI分析使用纯英文输出。"
            errors.append(error_msg)
    
    elif expected_language == "CN":
        # 期望中文：检测中文字符数量是否足够
        text_for_check = full_text
        
        # 移除英文指标名
        for metric in metric_names_en:
            text_for_check = text_for_check.replace(metric, "")
        
        chinese_chars = len(re.findall(r'[\u4e00-\u9fa5]', text_for_check))
        
        # 要求至少100个中文字符（排除指标名后）
        if chinese_chars < 100:
            errors.append(
                f"语言配置不匹配: 设置为 CN(中文), 但只检测到 {chinese_chars} 个中文字符 "
                f"(要求至少100字，不含指标名)。请确保AI分析使用纯中文输出。"
            )
    
    return errors


# ==================== 模板选择 ====================

def get_template_path(
    template_type: str,
    language: str,
    template_dir: Path,
    version: str = "V2"
) -> Path:
    """获取模板文件路径 - 支持多语言 - V5.8.1
    
    参数:
        template_type: 模板类型 ("daily", "weekly", "monthly")
        language: 语言代码 ("CN", "EN", "JP", etc.)
        template_dir: 模板目录路径
        version: 模板版本 (默认 "V2")
    
    返回:
        模板文件的完整路径
    
    异常:
        FileNotFoundError: 找不到模板文件时抛出
    
    模板命名约定:
        {TYPE}_TEMPLATE_MEDICAL_{VERSION}_{LANG}.html
        例如: DAILY_TEMPLATE_MEDICAL_V2_EN.html
        
        如果特定语言模板不存在，回退到默认模板（不带语言后缀）
    """
    template_dir = Path(template_dir)
    
    # 构建文件名（大写）
    type_upper = template_type.upper()
    lang_upper = language.upper()
    
    # 尝试特定语言模板
    template_name = f"{type_upper}_TEMPLATE_MEDICAL_{version}_{lang_upper}.html"
    template_path = template_dir / template_name
    
    if template_path.exists():
        return template_path
    
    # 回退到默认模板（不带语言后缀）
    default_name = f"{type_upper}_TEMPLATE_MEDICAL_{version}.html"
    default_path = template_dir / default_name
    
    if default_path.exists():
        print(f"⚠️  警告: 未找到 {language} 语言模板，使用默认模板")
        return default_path
    
    # 再尝试不带版本的旧格式
    legacy_name = f"{type_upper}_TEMPLATE_MEDICAL.html"
    legacy_path = template_dir / legacy_name
    
    if legacy_path.exists():
        print(f"⚠️  警告: 使用旧版模板 {legacy_name}")
        return legacy_path
    
    raise FileNotFoundError(
        f"找不到模板文件。尝试了以下路径:\n"
        f"  1. {template_path}\n"
        f"  2. {default_path}\n"
        f"  3. {legacy_path}"
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
            elif 'V2' in parts or 'V1' in parts:
                # 默认模板（无语言后缀）
                if 'default' not in result[template_type]:
                    result[template_type].append('default')
    
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
    bedtime = None
    waketime = None
    
    for record in sleep_data.get('data', []):
        start_ts = record.get('sleepStart')
        end_ts = record.get('sleepEnd')
        if not start_ts or not end_ts:
            continue
        
        # 解析时间
        try:
            if isinstance(start_ts, (int, float)):
                start_dt = datetime.fromtimestamp(start_ts / 1000)
                end_dt = datetime.fromtimestamp(end_ts / 1000)
            else:
                start_str = start_ts[:19]  # '2026-03-02 02:23:55'
                end_str = end_ts[:19]
                start_dt = datetime.strptime(start_str, '%Y-%m-%d %H:%M:%S')
                end_dt = datetime.strptime(end_str, '%Y-%m-%d %H:%M:%S')
        except (ValueError, TypeError):
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
            sleep_records.append({
                'start': start_dt.strftime('%H:%M'),
                'end': end_dt.strftime('%H:%M'),
                'total': duration_hours,
                'deep': record.get('deep', 0) or 0,
                'core': record.get('core', 0) or 0,
                'rem': record.get('rem', 0) or 0,
                'awake': record.get('awake', 0) or 0,
            })
            
            # 记录入睡和起床时间
            if bedtime is None or start_dt.hour < int(bedtime.split(':')[0]):
                bedtime = start_dt.strftime('%H:%M')
            if waketime is None or end_dt.hour > int(waketime.split(':')[0]):
                waketime = end_dt.strftime('%H:%M')
    
    # 计算总时长
    deep = sum(r['deep'] for r in sleep_records)
    core = sum(r['core'] for r in sleep_records)
    rem = sum(r['rem'] for r in sleep_records)
    awake = sum(r['awake'] for r in sleep_records)
    total = deep + core + rem + awake
    
    return {
        'records': sleep_records,
        'total_hours': round(total, 2),
        'deep_hours': round(deep, 2),
        'core_hours': round(core, 2),
        'rem_hours': round(rem, 2),
        'awake_hours': round(awake, 2),
        'bedtime': bedtime or '--',
        'waketime': waketime or '--',
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
        'health_dir': member.get('health_dir', '~/我的云端硬盘/Health Auto Export/Health Data'),
        'workout_dir': member.get('workout_dir', '~/我的云端硬盘/Health Auto Export/Workout Data'),
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
                
        except Exception as e:
            result.error_message = str(e)
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