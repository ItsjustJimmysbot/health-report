#!/usr/bin/env python3
"""健康评分算法模块 V6.0.3

核心评分：
- Strain (0-21): 日心血管负荷
- Recovery (0-100%): 晨间恢复度
- Sleep Performance (0-100%): 睡眠表现
- Body Age: 身体年龄
- Pace of Aging: 衰老速度趋势
"""

import math
import json
import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path

# ============ V6.0.4 配置常量 ============
BASELINE_DAYS = 14              # HRV/RHR/呼吸率基线天数
BODY_AGE_DAYS = 30              # Body Age 计算用天数
PACE_SHORT_TERM_DAYS = 7        # Pace of Aging 短期窗口
PACE_LONG_TERM_DAYS = 14        # Pace of Aging 长期窗口
RECOVERY_WEIGHTS = {
    'hrv': 0.50,               # HRV 权重 50%
    'rhr': 0.30,               # RHR 权重 30%
    'sleep': 0.17,             # 睡眠权重 17%
    'respiratory': 0.03        # 呼吸率权重 3%
}

# ============ 工具函数 ============

def calculate_max_hr(age: int, gender: str = 'male') -> int:
    """估算最大心率"""
    return int(208 - 0.7 * age)

def get_hr_zone(hr: int, max_hr: int) -> int:
    """心率区间 1-5（基于 WHOOP 标准）"""
    if max_hr <= 0:
        return 0
    pct = hr / max_hr
    if pct < 0.5: return 0      # 恢复区
    elif pct < 0.6: return 1    # Zone 1: 50-60%
    elif pct < 0.7: return 2    # Zone 2: 60-70%
    elif pct < 0.8: return 3    # Zone 3: 70-80%
    elif pct < 0.9: return 4    # Zone 4: 80-90%
    else: return 5              # Zone 5: 90-100%

# ============ 1. Strain 评分 (0-21) ============

@dataclass
class StrainResult:
    strain: float
    cardio_load: float
    muscle_load: float
    total_load: float
    zone_times: Dict[int, float]

def calculate_strain(hr_data: List[Tuple[datetime, int]], 
                     strength_minutes: int = 0,
                     age: int = 30, 
                     gender: str = 'male') -> StrainResult:
    """计算Strain (0-21)"""
    max_hr = calculate_max_hr(age, gender)
    zone_weights = {1: 0.3, 2: 1.0, 3: 2.5, 4: 5.0, 5: 10.0}
    zone_times = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    
    if hr_data and len(hr_data) > 1:
        for i in range(len(hr_data) - 1):
            ts1, hr1 = hr_data[i]
            ts2, hr2 = hr_data[i + 1]
            duration = (ts2 - ts1).total_seconds() / 60
            zone = get_hr_zone(hr1, max_hr)
            if zone >= 1:
                zone_times[zone] += duration
    
    cardio_load = sum(zone_times[z] * zone_weights[z] for z in zone_times)
    muscle_load = strength_minutes * 0.2
    total_load = cardio_load + muscle_load
    strain = 21 * (1 - math.exp(-total_load / 180))
    
    return StrainResult(
        strain=round(min(21, strain), 1),
        cardio_load=round(cardio_load, 1),
        muscle_load=round(muscle_load, 1),
        total_load=round(total_load, 1),
        zone_times={
            'zone_1': round(zone_times[1], 1),
            'zone_2': round(zone_times[2], 1),
            'zone_3': round(zone_times[3], 1),
            'zone_4': round(zone_times[4], 1),
            'zone_5': round(zone_times[5], 1)
        }
    )

def calculate_strain_simple(active_energy: float, steps: int, 
                           workouts: List[Dict], age: int = 30,
                           hr_data: List[Dict] = None) -> Tuple[float, Dict]:
    """
    简化版Strain计算 V6.0.3（没有全天HR数据时使用）
    基于活动能量、步数、运动记录和心率数据估算
    
    返回: (strain, zone_times_dict)
    """
    # 基于活动能量估算
    energy_load = min(10, active_energy / 100) if active_energy else 0
    
    # 基于步数估算
    steps_load = min(5, steps / 2000) if steps else 0
    
    # 基于运动记录估算
    workout_load = 0
    for w in workouts:
        duration = w.get('duration_min', 0)
        intensity = 2.0 if 'run' in w.get('name', '').lower() else 1.5 if 'strength' in w.get('name', '').lower() else 1.0
        workout_load += duration / 60 * intensity
    
    total_load = energy_load + steps_load + workout_load
    
    # 缩放到0-21
    strain = min(21, total_load * 0.8)
    
    # V6.0.3: 如果有心率数据，从心率数据计算真实zone_times
    if hr_data and len(hr_data) > 0:
        zone_times = calculate_zone_times_from_hr_data(hr_data, age)
    else:
        # 没有心率数据时，基于步数估算（仅作为fallback）
        zone_times = estimate_zone_times_from_steps(steps)
    
    return round(strain, 1), zone_times

def estimate_zone_times_from_steps(steps: int) -> Dict:
    """V6.0.3: 基于步数估算zone时间（无workout时使用）"""
    if steps < 3000:
        return {'zone_1': 30, 'zone_2': 0, 'zone_3': 0, 'zone_4': 0, 'zone_5': 0}
    elif steps < 8000:
        return {'zone_1': 30, 'zone_2': 20, 'zone_3': 0, 'zone_4': 0, 'zone_5': 0}
    elif steps < 12000:
        return {'zone_1': 30, 'zone_2': 40, 'zone_3': 20, 'zone_4': 0, 'zone_5': 0}
    else:
        return {'zone_1': 30, 'zone_2': 50, 'zone_3': 30, 'zone_4': 10, 'zone_5': 0}


def _parse_timestamp_seconds(value) -> Optional[float]:
    """兼容秒/毫秒时间戳、ISO 字符串、YYYY-MM-DD HH:MM:SS、HH:MM。"""
    if value is None:
        return None

    if isinstance(value, (int, float)):
        ts = float(value)
        return ts / 1000.0 if ts > 1e12 else ts

    text = str(value).strip()
    if not text:
        return None

    try:
        ts = float(text)
        return ts / 1000.0 if ts > 1e12 else ts
    except (TypeError, ValueError):
        pass

    # 仅有 HH:MM 时，返回"分钟数"，调用方只用于相邻差值
    if re.match(r'^\d{2}:\d{2}$', text):
        hh, mm = text.split(':')
        return float(int(hh) * 60 + int(mm))

    iso_text = text.replace('Z', '+00:00')
    m = re.match(r'(.+?)\s+([+-]\d{4})$', iso_text)
    if m:
        dt_text, tz_text = m.groups()
        iso_text = dt_text + tz_text[:3] + ':' + tz_text[3:]

    try:
        return datetime.fromisoformat(iso_text).timestamp()
    except ValueError:
        pass

    try:
        return datetime.strptime(text[:19], '%Y-%m-%d %H:%M:%S').timestamp()
    except ValueError:
        return None


def _sum_zone_minutes(zone_times: Dict) -> float:
    total = 0.0
    for key in ('zone_1', 'zone_2', 'zone_3', 'zone_4', 'zone_5'):
        value = zone_times.get(key, 0)
        if isinstance(value, (int, float)):
            total += float(value)
    return total


def calculate_zone_times_from_workouts(workouts: List[Dict], age: int) -> Dict:
    """从 workout 列表尽可能恢复真实的心率区间时间。"""
    max_hr = calculate_max_hr(age)
    zone_times = {'zone_1': 0.0, 'zone_2': 0.0, 'zone_3': 0.0, 'zone_4': 0.0, 'zone_5': 0.0}

    for workout in workouts or []:
        duration_min = float(workout.get('duration_min') or 0)
        hr_timeline = workout.get('hr_timeline') or []

        if hr_timeline:
            for i in range(len(hr_timeline)):
                point = hr_timeline[i]
                hr = point.get('hr')
                if hr is None:
                    hr = point.get('avg')
                if hr is None:
                    hr = point.get('max')
                if not isinstance(hr, (int, float)):
                    continue

                duration = 1.0
                if i < len(hr_timeline) - 1:
                    current_ts = point.get('timestamp') or point.get('date') or point.get('time')
                    next_ts = hr_timeline[i + 1].get('timestamp') or hr_timeline[i + 1].get('date') or hr_timeline[i + 1].get('time')
                    ts1 = _parse_timestamp_seconds(current_ts)
                    ts2 = _parse_timestamp_seconds(next_ts)
                    if ts1 is not None and ts2 is not None and ts2 > ts1:
                        # 如果是 HH:MM，会得到分钟差；如果是 epoch，会得到秒差
                        raw_gap = ts2 - ts1
                        duration = raw_gap if raw_gap <= 30 else raw_gap / 60.0
                        duration = max(0.5, min(duration, 10.0))

                zone = get_hr_zone(int(hr), max_hr)
                if zone >= 1:
                    zone_times[f'zone_{zone}'] += duration
            continue

        avg_hr = workout.get('avg_hr')
        if isinstance(avg_hr, (int, float)) and duration_min > 0:
            zone = get_hr_zone(int(avg_hr), max_hr)
            if zone >= 1:
                zone_times[f'zone_{zone}'] += duration_min

    return {k: round(v, 1) for k, v in zone_times.items()}


def calculate_strain_from_zone_times(zone_times: Dict, strength_minutes: float = 0) -> float:
    """优先根据真实 zone_times 计算 Strain。"""
    zone_weights = {
        'zone_1': 0.3,
        'zone_2': 1.0,
        'zone_3': 2.5,
        'zone_4': 5.0,
        'zone_5': 10.0,
    }
    cardio_load = 0.0
    for zone, weight in zone_weights.items():
        minutes = zone_times.get(zone, 0)
        if isinstance(minutes, (int, float)) and minutes > 0:
            cardio_load += float(minutes) * weight

    muscle_load = max(0.0, float(strength_minutes or 0)) * 0.2
    total_load = cardio_load + muscle_load
    strain = 21 * (1 - math.exp(-total_load / 180.0))
    return round(min(21, strain), 1)


def calculate_zone_times_from_hr_data(hr_data: List[Dict], age: int) -> Dict:
    """从全天心率数据计算真实心率区间时间，支持数字/字符串时间戳。"""
    max_hr = calculate_max_hr(age)
    zone_times = {1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0, 5: 0.0}

    if not hr_data or len(hr_data) < 2:
        return {'zone_1': 0, 'zone_2': 0, 'zone_3': 0, 'zone_4': 0, 'zone_5': 0}

    sortable = []
    for item in hr_data:
        ts_raw = item.get('timestamp')
        ts = _parse_timestamp_seconds(ts_raw)
        hr = item.get('hr')
        if ts is None or not isinstance(hr, (int, float)):
            continue
        sortable.append((ts, float(hr)))

    if len(sortable) < 2:
        return {'zone_1': 0, 'zone_2': 0, 'zone_3': 0, 'zone_4': 0, 'zone_5': 0}

    sortable.sort(key=lambda x: x[0])

    for i in range(len(sortable) - 1):
        ts1, hr = sortable[i]
        ts2, _ = sortable[i + 1]
        if ts2 <= ts1:
            continue

        duration_min = (ts2 - ts1) / 60.0
        duration_min = max(0.5, min(duration_min, 10.0))

        zone = get_hr_zone(int(hr), max_hr)
        if zone >= 1:
            zone_times[zone] += duration_min

    return {
        'zone_1': round(zone_times[1], 1),
        'zone_2': round(zone_times[2], 1),
        'zone_3': round(zone_times[3], 1),
        'zone_4': round(zone_times[4], 1),
        'zone_5': round(zone_times[5], 1),
    }

# ============ 2. Recovery 评分 (0-100%) ============

@dataclass
class RecoveryResult:
    recovery: int
    hrv_score: float
    rhr_score: float
    sleep_score: float
    respiratory_score: float
    status: str  # 'green', 'yellow', 'red'

def get_baseline(values: list, days: int = BASELINE_DAYS) -> float:
    """计算基线值（使用截尾均值，剔除异常值）"""
    if not values:
        return 0.0
    
    # 转换为浮点数列表
    float_values = [float(v) for v in values if isinstance(v, (int, float)) and v > 0 and math.isfinite(v)]
    if not float_values:
        return 0.0
    
    # 如果数据不足，直接返回平均值
    if len(float_values) < days:
        return sum(float_values) / len(float_values)
    
    # 取最近 days 天的数据
    recent = float_values[-days:]
    
    # 使用截尾均值（剔除最高/最低各 10%）
    recent_sorted = sorted(recent)
    trim = max(1, int(len(recent) * 0.1))
    if len(recent) > 3:
        trimmed = recent_sorted[trim:-trim]
    else:
        trimmed = recent
    
    return sum(trimmed) / len(trimmed) if trimmed else sum(recent) / len(recent)

def calculate_recovery(
    hrv_rmssd: float,
    rhr: float,
    sleep_performance: float,
    respiratory_rate: float,
    hrv_history: list,            # HRV 历史数据
    rhr_history: list,            # RHR 历史数据
    respiratory_history: list,    # 呼吸率历史数据
    gender: str = 'male'
) -> RecoveryResult:
    """
    计算 Recovery (0-100%)
    V6.0.4 更新：使用 14 天滚动基线，WHOOP 官方权重
    """
    # 输入验证
    if not isinstance(hrv_rmssd, (int, float)) or not math.isfinite(hrv_rmssd) or hrv_rmssd <= 0:
        hrv_rmssd = 50.0
    if not isinstance(rhr, (int, float)) or not math.isfinite(rhr) or rhr <= 0:
        rhr = 65.0 if gender == 'male' else 68.0
    if not isinstance(sleep_performance, (int, float)) or not math.isfinite(sleep_performance):
        sleep_performance = 70.0
    if not isinstance(respiratory_rate, (int, float)) or not math.isfinite(respiratory_rate) or respiratory_rate <= 0:
        respiratory_rate = 14.0
    
    # 计算基线
    hrv_baseline = get_baseline(hrv_history) if hrv_history else hrv_rmssd
    rhr_baseline = get_baseline(rhr_history) if rhr_history else rhr
    resp_baseline = get_baseline(respiratory_history) if respiratory_history else respiratory_rate
    
    # HRV 分数（基于个人基线）
    if hrv_baseline > 0:
        hrv_score = min(100, max(0, 100 * (hrv_rmssd / hrv_baseline)))
    else:
        hrv_score = 50.0
    
    # RHR 分数（与基线比较，越低越好）
    if rhr_baseline > 0:
        rhr_ratio = rhr / rhr_baseline
        # rhr_ratio = 1.0 时得 100 分，每增加 10% 扣 30 分
        rhr_score = min(100, max(0, 100 * (2.0 - rhr_ratio) * 0.5))
    else:
        rhr_score = 50.0
    
    # 睡眠表现分数（直接使用百分比）
    sleep_score = min(100, max(0, sleep_performance))
    
    # 呼吸率分数（与基线偏差越小越好）
    if resp_baseline > 0:
        resp_ratio = respiratory_rate / resp_baseline
        resp_score = min(100, max(0, 100 * (2.0 - resp_ratio) * 0.8))
    else:
        resp_score = 50.0
    
    # WHOOP 官方近似权重计算
    recovery = int(round(
        RECOVERY_WEIGHTS['hrv'] * hrv_score +
        RECOVERY_WEIGHTS['rhr'] * rhr_score +
        RECOVERY_WEIGHTS['sleep'] * sleep_score +
        RECOVERY_WEIGHTS['respiratory'] * resp_score
    ))
    
    recovery = max(1, min(100, recovery))
    status = 'green' if recovery >= 67 else 'yellow' if recovery >= 34 else 'red'
    
    return RecoveryResult(
        recovery=recovery,
        hrv_score=round(hrv_score, 1),
        rhr_score=round(rhr_score, 1),
        sleep_score=round(sleep_score, 1),
        respiratory_score=round(resp_score, 1),
        status=status
    )

# ============ 3. Sleep Performance (0-100%) ============

@dataclass
class SleepPerformanceResult:
    performance: int
    sleep_need: float
    sufficiency: float
    quality_score: float

def calculate_sleep_performance(actual_hours: float, previous_strain: float,
                               consistency: float, disturbances_min: float,
                               sleep_latency_min: float,
                               baseline_need: float = 7.8,  # 基于成年人平均睡眠需求 (7-9小时中位数)
                               age: int = 30) -> SleepPerformanceResult:
    """计算Sleep Performance (0-100%)"""
    # Sleep Need自适应
    load_adjustment = 0.08 * max(-5, previous_strain - 10)
    sleep_need = max(6.0, min(10.0, baseline_need + load_adjustment))
    
    # Sufficiency
    sufficiency = min(1.2, actual_hours / sleep_need)
    
    # Quality Score
    consistency_score = consistency / 100
    disturbance_score = max(0, 1 - (disturbances_min / 60 / max(1, actual_hours)))
    efficiency = 1.0 if sleep_latency_min <= 15 else 0.9 if sleep_latency_min <= 30 else 0.75 if sleep_latency_min <= 60 else 0.6
    quality_score = 0.4 * consistency_score + 0.3 * disturbance_score + 0.3 * efficiency
    
    performance = int(round(min(100, sufficiency * quality_score * 100)))
    
    return SleepPerformanceResult(performance, round(sleep_need, 1), 
                                  round(sufficiency * 100, 1), round(quality_score * 100, 1))

# ============ 4. Body Age ============

def get_age_impact(metric: str, value: float, chrono_age: int, gender: str = 'male') -> float:
    """
    计算单个指标对年龄的影响
    返回：正值 = 加速衰老，负值 = 减缓衰老
    """
    if value is None or value <= 0:
        return 0.0
    
    # 根据年龄调整目标值
    if chrono_age <= 30:
        sleep_target, steps_target, rhr_target = 7.5, 8000, 62
    elif chrono_age <= 50:
        sleep_target, steps_target, rhr_target = 7.0, 7000, 65
    else:
        sleep_target, steps_target, rhr_target = 6.5, 6000, 68
    
    if gender == 'female':
        rhr_target += 4  # 女性心率通常高 3-5 bpm
    
    if metric == 'sleep_hours':
        if value >= sleep_target:
            return -0.5  # 睡眠充足，减龄
        elif value >= 6:
            return 0.5   # 轻度不足
        else:
            return 1.5   # 严重不足
    
    elif metric == 'steps':
        if value >= steps_target:
            return -0.3
        else:
            # 按比例计算，上限 2 岁
            deficit = (steps_target - value) / steps_target
            return min(2.0, deficit * 2.0)
    
    elif metric == 'rhr':
        if value < rhr_target:
            return -0.2
        elif value < rhr_target + 10:
            return 0
        else:
            # 每高 10 bpm，增加 1 岁，上限 3 岁
            return min(3.0, (value - rhr_target) / 10 * 1.0)
    
    elif metric == 'hrv':
        # HRV 与年龄相关，年轻人通常 50-80ms
        if chrono_age <= 30:
            expected_hrv = 55
        elif chrono_age <= 50:
            expected_hrv = 45
        else:
            expected_hrv = 35
        
        if value >= expected_hrv:
            return -0.3
        else:
            deficit = (expected_hrv - value) / expected_hrv
            return min(1.0, deficit * 1.0)
    
    elif metric == 'respiratory_rate':
        # 正常 12-20 次/分
        if 12 <= value <= 20:
            return 0
        else:
            return 0.5
    
    return 0.0

@dataclass
class BodyAgeResult:
    body_age: float
    chronological_age: int
    age_impact: float
    breakdown: Dict[str, float]
    risk_ratios: Dict[str, float] = None

def calculate_body_age(
    daily_data: list,
    chronological_age: int,
    gender: str = 'male',
    days: int = BODY_AGE_DAYS
) -> BodyAgeResult:
    """
    计算 Body Age
    V6.0.4 更新：使用 30 天平均，多指标综合评估
    
    Args:
        daily_data: 每日数据列表
        chronological_age: 实际年龄
        gender: 性别
        days: 计算窗口天数（默认 30）
    """
    if not daily_data or len(daily_data) < 3:
        return BodyAgeResult(
            body_age=float(chronological_age),
            chronological_age=chronological_age,
            age_impact=0.0,
            breakdown={'note': '数据不足，需要至少 3 天数据'},
            risk_ratios={}
        )
    
    # 取最近 days 天的数据
    recent_data = daily_data[-days:] if len(daily_data) >= days else daily_data
    
    # 计算各指标平均值
    metrics = {}
    metric_names = ['sleep_hours', 'steps', 'rhr', 'hrv', 'respiratory_rate']
    
    for metric in metric_names:
        values = []
        for d in recent_data:
            if isinstance(d, dict):
                # 处理嵌套结构（如 hrv.value）
                if metric in ['hrv', 'rhr'] and isinstance(d.get(metric), dict):
                    val = d[metric].get('value')
                else:
                    val = d.get(metric)
                
                if isinstance(val, (int, float)) and val > 0 and math.isfinite(val):
                    values.append(float(val))
        
        if values:
            metrics[metric] = sum(values) / len(values)
    
    # 计算各指标对年龄的影响
    impacts = {}
    for metric, value in metrics.items():
        impacts[metric] = get_age_impact(metric, value, chronological_age, gender)
    
    total_impact = sum(impacts.values())
    body_age = chronological_age + total_impact
    
    # 确保 Body Age 在合理范围内（实际年龄 ± 10 岁）
    body_age = max(chronological_age - 10, min(chronological_age + 10, body_age))
    
    breakdown_detail = {k: round(v, 2) for k, v in impacts.items()}
    breakdown_detail['_config'] = {
        'days_used': len(recent_data),
        'metrics_available': list(metrics.keys())
    }
    
    return BodyAgeResult(
        body_age=round(body_age, 1),
        chronological_age=chronological_age,
        age_impact=round(total_impact, 1),
        breakdown=breakdown_detail,
        risk_ratios={}
    )

# ============ 5. Pace of Aging ============

def calculate_pace_of_aging(
    daily_data: list,
    chronological_age: int,
    gender: str = 'male',
    short_term_days: int = PACE_SHORT_TERM_DAYS,
    long_term_days: int = PACE_LONG_TERM_DAYS
) -> float:
    """
    计算 Pace of Aging（年化衰老速度）
    V6.0.4 更新：基于短期 Body Age 趋势投影
    
    逻辑：
    - 1.0 = 与实际年龄同步（正常）
    - < 1.0 = 慢于实际年龄（逆龄）
    - > 1.0 = 快于实际年龄（加速）
    
    Args:
        daily_data: 每日数据列表
        chronological_age: 实际年龄
        gender: 性别
        short_term_days: 短期窗口（默认 7 天）
        long_term_days: 长期窗口（默认 14 天）
    
    Returns:
        pace: 年化衰老速度（0.0-3.0），None 表示数据不足
    """
    # 数据完整性检查
    if not daily_data or len(daily_data) < long_term_days:
        return None
    
    # 分成两段：最近短期 vs 前一段长期
    recent_short = daily_data[-short_term_days:]
    previous_long = daily_data[-long_term_days:]
    
    # 计算两段各自的 Body Age
    recent_age = calculate_body_age(recent_short, chronological_age, gender)
    previous_age = calculate_body_age(previous_long, chronological_age, gender)
    
    # 计算年龄变化
    age_change = recent_age.body_age - previous_age.body_age
    
    # 将变化率年化
    # short_term_days 天的变化 → 年化到 365 天
    if short_term_days > 0:
        daily_change = age_change / short_term_days
        annual_change = daily_change * 365
        
        # Pace = 1.0 表示与实际年龄同步
        # Pace < 1.0 表示比实际年龄增长慢（逆龄）
        # Pace > 1.0 表示比实际年龄增长快（加速）
        if annual_change < 0:
            # 逆龄：Body Age 在减少
            pace = max(0.0, 1.0 + annual_change)
        else:
            # 正常或加速衰老
            pace = min(3.0, 1.0 + annual_change)
    else:
        pace = 1.0
    
    return round(pace, 2)

# ============ 6. 历史数据管理 ============

class HealthScoreHistory:
    """管理健康评分历史数据"""
    
    def __init__(self, cache_dir: Path):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def get_scores(self, date_str: str, member_name: str) -> Optional[Dict]:
        """获取某天的评分"""
        from utils import safe_member_name
        safe_name = safe_member_name(member_name)
        cache_file = self.cache_dir / f"{date_str}_{safe_name}.json"
        
        if cache_file.exists():
            with open(cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('health_scores')
        return None

    def get_average_range(self, end_date: str, member_name: str, days: int = 7, skip_days: int = 0) -> Dict:
        """获取一段时间窗口的平均值。end_date 为窗口锚点（含），skip_days 表示向前跳过的天数。"""
        end = datetime.strptime(end_date, '%Y-%m-%d')
        scores = []

        for i in range(skip_days, skip_days + days):
            date_str = (end - timedelta(days=i)).strftime('%Y-%m-%d')
            day_scores = self.get_scores(date_str, member_name)
            if day_scores:
                scores.append(day_scores)

        if not scores:
            return {
                'days_count': 0,
                'strain': 10,
                'recovery': 50,
                'sleep_performance': 70,
                'hrv_rmssd': None,
                'rhr': None,
                'respiratory_rate': None,
            }

        def _avg_numeric(key: str, default=None):
            values = []
            for item in scores:
                value = item.get(key)
                if isinstance(value, (int, float)):
                    values.append(float(value))
            if values:
                return sum(values) / len(values)
            return default

        return {
            'days_count': len(scores),
            'strain': _avg_numeric('strain', 10),
            'recovery': _avg_numeric('recovery', 50),
            'sleep_performance': _avg_numeric('sleep_performance', 70),
            'hrv_rmssd': _avg_numeric('hrv_rmssd', None),
            'rhr': _avg_numeric('rhr', None),
            'respiratory_rate': _avg_numeric('respiratory_rate', None),
        }

    def get_7day_average(self, end_date: str, member_name: str) -> Dict:
        """兼容旧调用：返回最近 7 天平均值。"""
        return self.get_average_range(end_date, member_name, days=7, skip_days=0)
    
    def get_sleep_debt(self, date_str: str, member_name: str) -> float:
        """获取某天的累积睡眠债。注意：sleep_debt_accumulated 在缓存顶层，不在 health_scores 内。"""
        cache = self._get_raw_cache(date_str, member_name)
        if cache:
            value = cache.get('sleep_debt_accumulated', 0)
            return float(value) if isinstance(value, (int, float)) else 0.0
        return 0.0
    
    def get_bedtime_waketime(self, date_str: str, member_name: str) -> Tuple[str, str]:
        """获取就寝和起床时间"""
        cache = self._get_raw_cache(date_str, member_name)
        if cache:
            return cache.get('bedtime', '--'), cache.get('waketime', '--')
        return '--', '--'
    
    def _get_raw_cache(self, date_str: str, member_name: str) -> Optional[Dict]:
        """获取完整缓存数据"""
        from utils import safe_member_name
        safe_name = safe_member_name(member_name)
        cache_file = self.cache_dir / f"{date_str}_{safe_name}.json"
        
        if cache_file.exists():
            with open(cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None


# ============ 7. 一键计算 ============

def calculate_all_scores(data: Dict, profile: Dict, history: HealthScoreHistory,
                         zone_times: Dict = None) -> Dict:
    """一键计算所有健康评分（V6.0.3 修正版）"""
    raw_age = profile.get('age')
    age = int(raw_age) if isinstance(raw_age, (int, float)) and raw_age > 0 else 30
    gender = profile.get('gender', 'male')
    date_str = data.get('date', datetime.now().strftime('%Y-%m-%d'))
    member_name = profile.get('name', '默认用户')

    workouts = data.get('workouts') or []
    steps = int(data.get('steps') or 0)
    active_energy = data.get('active_energy')
    if active_energy is None:
        active_energy = data.get('active_energy_kcal')
    active_energy = float(active_energy or 0)

    sleep = data.get('sleep') or {}
    sleep_total = float(sleep.get('total_hours', 0) or 0)
    awake_hours = float(sleep.get('awake_hours', 0) or 0)

    strength_time = sum(
        float(w.get('duration_min') or 0)
        for w in workouts
        if any(k in str(w.get('name', '')).lower() for k in ['strength', '力量', '举重', 'weight'])
    )

    # 1) Strain：优先使用真实 zone_times
    resolved_zone_times = zone_times or data.get('zone_times') or {}
    if _sum_zone_minutes(resolved_zone_times) <= 0:
        resolved_zone_times = calculate_zone_times_from_workouts(workouts, age)

    if _sum_zone_minutes(resolved_zone_times) > 0:
        strain = calculate_strain_from_zone_times(resolved_zone_times, strength_time)
    else:
        strain, resolved_zone_times = calculate_strain_simple(
            active_energy,
            steps,
            workouts,
            age,
            data.get('heart_rate_data') or []
        )

    # 2) Sleep Performance
    yesterday = (datetime.strptime(date_str, '%Y-%m-%d') - timedelta(days=1)).strftime('%Y-%m-%d')
    previous_day_scores = history.get_scores(yesterday, member_name) or {}
    prev_strain = float(previous_day_scores.get('strain', 10) or 10)

    sleep_consistency = data.get('sleep_consistency')
    if not isinstance(sleep_consistency, (int, float)):
        sleep_consistency = 75

    sleep_latency_min = data.get('sleep_latency_min')
    if not isinstance(sleep_latency_min, (int, float)):
        sleep_latency_min = 20

    sleep_result = calculate_sleep_performance(
        sleep_total,
        prev_strain,
        float(sleep_consistency),
        awake_hours * 60.0,
        float(sleep_latency_min),
    )

    # 3) Recovery：V6.0.4 使用 14 天历史数据计算基线
    hrv = data.get('hrv', {}).get('value')
    rhr = data.get('resting_hr', {}).get('value')
    respiratory = data.get('respiratory_rate')

    if not isinstance(hrv, (int, float)):
        hrv = 50.0
    if not isinstance(rhr, (int, float)):
        rhr = 70.0 if gender == 'male' else 74.0
    if not isinstance(respiratory, (int, float)):
        respiratory = 14.0

    # 收集 14 天历史数据
    hrv_history = []
    rhr_history = []
    resp_history = []
    for i in range(14):
        past_date = (datetime.strptime(date_str, '%Y-%m-%d') - timedelta(days=i)).strftime('%Y-%m-%d')
        day_scores = history.get_scores(past_date, member_name)
        if day_scores:
            if day_scores.get('hrv_rmssd'):
                hrv_history.append(day_scores['hrv_rmssd'])
            if day_scores.get('rhr'):
                rhr_history.append(day_scores['rhr'])
            if day_scores.get('respiratory_rate'):
                resp_history.append(day_scores['respiratory_rate'])

    recovery_result = calculate_recovery(
        hrv_rmssd=float(hrv),
        rhr=float(rhr),
        sleep_performance=sleep_result.performance,
        respiratory_rate=float(respiratory),
        hrv_history=hrv_history,
        rhr_history=rhr_history,
        respiratory_history=resp_history,
        gender=gender,
    )

    # 4) Body Age：V6.0.4 使用 30 天历史数据
    body_age_history = []
    for i in range(30):
        past_date = (datetime.strptime(date_str, '%Y-%m-%d') - timedelta(days=i)).strftime('%Y-%m-%d')
        day_data = history.get_scores(past_date, member_name)
        if day_data:
            body_age_history.append(day_data)
    
    # 添加当日数据到历史
    today_data = {
        'sleep_hours': sleep_total,
        'steps': steps,
        'rhr': float(rhr),
        'hrv': float(hrv) if hrv else 0,
        'respiratory_rate': float(respiratory) if respiratory else 0,
    }
    body_age_history.insert(0, today_data)
    
    body_age_result = calculate_body_age(body_age_history, age, gender)

    # 5) Pace of Aging：V6.0.4 使用 30 天历史数据
    pace_history = []
    for i in range(30):
        past_date = (datetime.strptime(date_str, '%Y-%m-%d') - timedelta(days=i)).strftime('%Y-%m-%d')
        day_data = history.get_scores(past_date, member_name)
        if day_data:
            pace_history.append(day_data)
    
    # 添加当日数据
    pace_history.insert(0, today_data)
    
    pace = calculate_pace_of_aging(pace_history, age, gender)
    if pace is None:
        pace = 1.0  # 默认正常速度
        current_7day = {
            'recovery': float(recovery_result.recovery),
            'sleep_performance': float(sleep_result.performance),
        }

    previous_7day = history.get_average_range(yesterday, member_name, days=7, skip_days=6)
    if int(previous_7day.get('days_count', 0) or 0) > 0:
        pace = calculate_pace_of_aging(current_7day, previous_7day)
    else:
        pace = 0.0

    return {
        'strain': strain,
        'recovery': recovery_result.recovery,
        'recovery_status': recovery_result.status,
        'sleep_performance': sleep_result.performance,
        'sleep_need': sleep_result.sleep_need,
        'body_age': body_age_result.body_age,
        'chronological_age': body_age_result.chronological_age,
        'age_impact': body_age_result.age_impact,
        'pace_of_aging': pace,
        'zone_times': resolved_zone_times,
        'breakdown': {
            'recovery_detail': asdict(recovery_result),
            'sleep_detail': asdict(sleep_result),
            'body_age_detail': asdict(body_age_result),
        },
    }
