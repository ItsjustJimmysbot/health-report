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

def get_hr_zone(hr: int, max_hr: int, rhr: int = None) -> int:
    """心率区间 1-5（基于 WHOOP 标准，使用 HRR 方法）
    
    WHOOP 使用 Heart Rate Reserve (HRR) 方法:
    - HRR = (HR - RHR) / (MaxHR - RHR)
    
    区间定义 (基于 HRR%):
    - Zone 0: < 30% HRR (恢复区)
    - Zone 1: 30-50% HRR (轻度活动)
    - Zone 2: 50-60% HRR (有氧基础)
    - Zone 3: 60-70% HRR (有氧强化)
    - Zone 4: 70-80% HRR (无氧阈值)
    - Zone 5: >= 80% HRR (最大强度)
    
    如果未提供 RHR，回退到简单的 %MaxHR 方法
    """
    if max_hr <= 0:
        return 0
    
    # 添加 hr 有效性检查
    if hr <= 0 or not isinstance(hr, (int, float)):
        return 0
    
    # 如果提供了静息心率，使用 HRR 方法
    if rhr is not None and rhr > 0 and max_hr > rhr:
        # 确保 hr >= rhr，否则设为恢复区
        if hr <= rhr:
            return 0
        hrr = max_hr - rhr
        hr_reserve = hr - rhr
        pct = hr_reserve / hrr if hrr > 0 else 0
        
        if pct < 0.30: return 0     # 恢复区: < 30% HRR
        elif pct < 0.50: return 1   # Zone 1: 30-50% HRR
        elif pct < 0.60: return 2   # Zone 2: 50-60% HRR
        elif pct < 0.70: return 3   # Zone 3: 60-70% HRR
        elif pct < 0.80: return 4   # Zone 4: 70-80% HRR
        else: return 5              # Zone 5: >= 80% HRR
    else:
        # 回退到简单的 %MaxHR 方法
        pct = hr / max_hr
        if pct < 0.50: return 0     # 恢复区: < 50%
        elif pct < 0.60: return 1   # Zone 1: 50-60%
        elif pct < 0.70: return 2   # Zone 2: 60-70%
        elif pct < 0.80: return 3   # Zone 3: 70-80%
        elif pct < 0.90: return 4   # Zone 4: 80-90%
        else: return 5              # Zone 5: >= 90%

# ============ 1. Strain 评分 (0-21) ============

@dataclass

def calculate_strain_simple(active_energy: float, steps: int, 
                           workouts: List[Dict], age: int = 30,
                           hr_data: List[Dict] = None, 
                           weight_kg: float = 70.0,
                           gender: str = 'male',
                           rhr: int = None) -> Tuple[float, Dict]:
    """
    简化版Strain计算 V6.0.5（没有全天HR数据时使用）
    基于活动能量、步数、运动记录和心率数据估算
    
    改进：
    - 考虑体重和性别差异
    - 个性化能量阈值
    - 运动强度基于METs估算
    - 支持HRR心率区间计算
    
    返回: (strain, zone_times_dict)
    """
    # 默认值处理
    if not weight_kg or weight_kg <= 0:
        weight_kg = 70.0
    
    # 性别调整因子（女性基础代谢较低）
    gender_factor = 0.9 if gender == 'female' else 1.0
    
    # 基于活动能量估算（考虑体重标准化）
    # 70kg男性，100kcal ≈ 1 load unit
    energy_threshold = 100 * (weight_kg / 70) * gender_factor
    energy_load = min(10, active_energy / energy_threshold) if active_energy else 0
    
    # 基于步数估算（考虑体重和性别）
    # 70kg男性，2000步 ≈ 1 load unit
    steps_threshold = 2000 * (70 / weight_kg) * (1 / gender_factor)
    steps_load = min(5, steps / steps_threshold) if steps else 0
    
    # 基于运动记录估算（使用METs估算强度）
    workout_load = 0
    for w in workouts:
        duration = w.get('duration_min', 0)
        if duration <= 0:
            continue
        
        # 根据运动类型估算METs
        workout_name = w.get('name', '').lower()
        if 'run' in workout_name or '跑步' in workout_name:
            mets = 9.0
        elif 'cycle' in workout_name or '骑行' in workout_name:
            mets = 8.0
        elif 'swim' in workout_name or '游泳' in workout_name:
            mets = 8.0
        elif 'strength' in workout_name or '力量' in workout_name or '举重' in workout_name:
            mets = 5.0
        elif 'hiit' in workout_name:
            mets = 11.0
        elif 'walk' in workout_name or '步行' in workout_name or '走路' in workout_name:
            mets = 3.5
        else:
            mets = 4.0  # 默认中等强度
        
        # METs 转换为 load（METs * 小时）
        intensity_factor = mets / 4  # 以4 METs为基准
        workout_load += (duration / 60) * intensity_factor
    
    total_load = energy_load + steps_load + workout_load
    
    # 使用对数压缩，避免高负荷日过于突出
    # 参考：21 * (1 - exp(-load / 180))
    strain = 21 * (1 - math.exp(-total_load / 180))
    strain = min(21, max(0, strain))
    
    # V6.0.5: 如果有心率数据，从心率数据计算真实zone_times
    if hr_data and len(hr_data) > 0:
        zone_times = calculate_zone_times_from_hr_data(hr_data, age, rhr)
    else:
        # 没有心率数据时，基于运动估算zone分布
        zone_times = estimate_zone_times_from_workouts(workouts, steps, rhr)
    
    return round(strain, 1), zone_times


def estimate_zone_times_from_workouts(workouts: List[Dict], steps: int, rhr: int = None) -> Dict:
    """V6.0.5: 基于运动记录和步数估算zone时间（更精确）
    
    Args:
        workouts: 运动记录列表
        steps: 步数
        rhr: 静息心率(可选)，用于HRR计算
    """
    zone_times = {'zone_1': 0, 'zone_2': 0, 'zone_3': 0, 'zone_4': 0, 'zone_5': 0}
    
    # 基于步数估算日常活动（主要在Zone 1-2）
    if steps > 0:
        # 假设每1000步 ≈ 10分钟活动
        activity_minutes = steps / 100
        zone_times['zone_1'] += activity_minutes * 0.6  # 60%在Zone 1
        zone_times['zone_2'] += activity_minutes * 0.4  # 40%在Zone 2
    
    # 基于运动记录估算
    for w in workouts:
        duration = w.get('duration_min', 0)
        if duration <= 0:
            continue
        
        avg_hr = w.get('avg_hr')
        workout_name = w.get('name', '').lower()
        
        if isinstance(avg_hr, (int, float)) and avg_hr > 0:
            # 有平均心率，估算主要zone
            max_hr = 220 - 30  # 假设平均30岁
            
            # 如果提供了RHR，使用HRR方法计算zone
            if rhr is not None and rhr > 0 and max_hr > rhr:
                hrr = max_hr - rhr
                hr_reserve = avg_hr - rhr
                hr_pct = hr_reserve / hrr if hrr > 0 else 0
            else:
                hr_pct = avg_hr / max_hr
            
            if hr_pct >= 0.90:
                zone_times['zone_5'] += duration * 0.7
                zone_times['zone_4'] += duration * 0.3
            elif hr_pct >= 0.80:
                zone_times['zone_4'] += duration * 0.6
                zone_times['zone_3'] += duration * 0.4
            elif hr_pct >= 0.70:
                zone_times['zone_3'] += duration * 0.6
                zone_times['zone_2'] += duration * 0.4
            elif hr_pct >= 0.60:
                zone_times['zone_2'] += duration * 0.7
                zone_times['zone_1'] += duration * 0.3
            else:
                zone_times['zone_1'] += duration
        else:
            # 没有心率，根据运动类型估算
            if 'run' in workout_name:
                zone_times['zone_3'] += duration * 0.5
                zone_times['zone_2'] += duration * 0.3
                zone_times['zone_4'] += duration * 0.2
            elif 'hiit' in workout_name:
                zone_times['zone_4'] += duration * 0.4
                zone_times['zone_5'] += duration * 0.3
                zone_times['zone_3'] += duration * 0.3
            elif 'strength' in workout_name:
                zone_times['zone_2'] += duration * 0.5
                zone_times['zone_3'] += duration * 0.5
            else:
                zone_times['zone_2'] += duration * 0.6
                zone_times['zone_1'] += duration * 0.4
    
    return {k: round(v, 1) for k, v in zone_times.items()}


def _parse_timestamp_seconds(value) -> Optional[float]:
    """兼容秒/毫秒时间戳、ISO 字符串、YYYY-MM-DD HH:MM:SS、HH:MM。
    
    注意：对于 HH:MM 格式，返回的是当天秒数，调用方需要处理跨天逻辑
    """
    if value is None:
        return None

    if isinstance(value, (int, float)):
        ts = float(value)
        if not math.isfinite(ts):
            return None
        return ts / 1000.0 if ts > 1e12 else ts

    text = str(value).strip()
    if not text:
        return None

    try:
        ts = float(text)
        if not math.isfinite(ts):
            return None
        return ts / 1000.0 if ts > 1e12 else ts
    except (TypeError, ValueError):
        pass

    # 处理 HH:MM:SS 或 HH:MM 格式
    time_only_match = re.match(r'^(\d{2}):(\d{2})(?::(\d{2}))?$', text)
    if time_only_match:
        # 返回当天该时间的秒数（调用方需要处理跨天）
        hh = int(time_only_match.group(1))
        mm = int(time_only_match.group(2))
        ss = int(time_only_match.group(3)) if time_only_match.group(3) else 0
        return float(hh * 3600 + mm * 60 + ss)

    # 处理 ISO 格式（带时区）
    iso_text = text.replace('Z', '+00:00')
    m = re.match(r'(.+?)\s+([+-]\d{4})$', iso_text)
    if m:
        dt_text, tz_text = m.groups()
        iso_text = dt_text + tz_text[:3] + ':' + tz_text[3:]

    try:
        return datetime.fromisoformat(iso_text).timestamp()
    except ValueError:
        pass

    # 处理常见日期时间格式
    for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%Y/%m/%d %H:%M:%S', 
                '%Y/%m/%d %H:%M', '%d/%m/%Y %H:%M:%S']:
        try:
            return datetime.strptime(text[:len(fmt)], fmt).timestamp()
        except ValueError:
            continue

    return None


def _sum_zone_minutes(zone_times: Dict) -> float:
    total = 0.0
    for key in ('zone_1', 'zone_2', 'zone_3', 'zone_4', 'zone_5'):
        value = zone_times.get(key, 0)
        if isinstance(value, (int, float)):
            total += float(value)
    return total


def calculate_zone_times_from_workouts(workouts: List[Dict], age: int, rhr: int = None) -> Dict:
    """从 workout 列表尽可能恢复真实的心率区间时间。

    Args:
        workouts: 运动记录列表
        age: 年龄
        rhr: 静息心率(可选)，用于HRR计算
    """
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
                    if ts1 is not None and ts2 is not None:
                        # 处理跨天情况：如果时间差为负（比如23:59到00:01）
                        raw_gap = ts2 - ts1
                        
                        # 检测跨天（时间差小于-20小时，说明是次日的同一时间）
                        if raw_gap < -72000:  # -20小时
                            raw_gap += 86400  # 加上一天的秒数
                        
                        # 检测异常大的时间差（可能是数据错误）
                        if raw_gap > 3600:  # 超过1小时的间隔，可能是缺失数据
                            raw_gap = 60  # 默认1分钟间隔
                        
                        if raw_gap > 0:
                            # 如果是 HH:MM（小于100000），秒数需要转换
                            if ts1 < 100000 and ts2 < 100000:  # 只有时间，没有日期
                                duration = raw_gap / 60.0  # 秒转分钟
                            else:  # 完整时间戳
                                duration = raw_gap / 60.0  # 秒转分钟
                            duration = max(0.5, min(duration, 10.0))
                        else:
                            duration = 1.0  # 默认1分钟
                    else:
                        duration = 1.0

                zone = get_hr_zone(int(hr), max_hr, rhr)  # 传入 rhr
                if zone >= 1:
                    zone_times[f'zone_{zone}'] += duration
            continue

        avg_hr = workout.get('avg_hr')
        if isinstance(avg_hr, (int, float)) and duration_min > 0:
            zone = get_hr_zone(int(avg_hr), max_hr, rhr)  # 传入 rhr
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


def calculate_zone_times_from_hr_data(hr_data: List[Dict], age: int, rhr: int = None) -> Dict:
    """从全天心率数据计算真实心率区间时间，支持数字/字符串时间戳。
    
    Args:
        hr_data: 心率数据列表
        age: 年龄
        rhr: 静息心率(可选)，用于HRR计算
    """
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

        zone = get_hr_zone(int(hr), max_hr, rhr)  # 传入 rhr
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
    """计算基线值（使用截尾均值，剔除异常值）
    
    数据不足时使用加权平滑：
    - 有数据时：使用实际数据的加权平均
    - 数据很少时（<7天）：降低截尾比例，保留更多数据
    """
    if not values:
        return 0.0
    
    # 转换为浮点数列表
    float_values = [float(v) for v in values if isinstance(v, (int, float)) and v > 0 and math.isfinite(v)]
    if not float_values:
        return 0.0
    
    # 数据不足时的平滑处理
    if len(float_values) < days:
        # 使用所有可用数据，但降低截尾比例
        recent = float_values
        # 数据越少，截尾比例越低
        trim_ratio = 0.1 * (len(float_values) / days)  # 线性降低
    else:
        # 取最近 days 天的数据
        recent = float_values[-days:]
        trim_ratio = 0.1
    
    # 使用截尾均值（剔除最高/最低）
    recent_sorted = sorted(recent)
    trim = max(0, int(len(recent) * trim_ratio))
    
    if len(recent) > 3 and trim > 0:
        trimmed = recent_sorted[trim:-trim] if trim > 0 else recent_sorted
    else:
        trimmed = recent
    
    baseline = sum(trimmed) / len(trimmed) if trimmed else sum(recent) / len(recent)
    
    # 数据不足时，使用加权平均（新数据权重更高）
    if len(float_values) < days and len(float_values) >= 3:
        # 计算加权平均：最近的数据权重更高
        weights = [i + 1 for i in range(len(float_values))]  # 1, 2, 3, ...
        weighted_sum = sum(v * w for v, w in zip(float_values, weights))
        weighted_avg = weighted_sum / sum(weights)
        
        # 混合基线值：70% 截尾均值 + 30% 加权平均
        baseline = 0.7 * baseline + 0.3 * weighted_avg
    
    return baseline

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
        # 比值 1.0 时得 100 分，每偏离 10% 扣 10 分
        deviation = abs(resp_ratio - 1.0)
        resp_score = max(0, 100 - deviation * 100)
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
    V6.0.5 更新：基于生理指标趋势的回归模型
    
    逻辑：
    - 1.0 = 与实际年龄同步（正常）
    - < 1.0 = 慢于实际年龄（逆龄）
    - > 1.0 = 快于实际年龄（加速）
    
    新方法：基于 HRV、RHR、Recovery、Sleep Performance 的趋势
    而不是简单的 Body Age 变化
    """
    # 数据完整性检查
    if not daily_data or len(daily_data) < 7:  # 至少需要7天数据
        return None
    
    # 提取关键生理指标
    hrv_values = []
    rhr_values = []
    recovery_values = []
    sleep_perf_values = []
    strain_values = []
    
    for day in daily_data:
        if not isinstance(day, dict):
            continue
        
        # HRV
        hrv = day.get('hrv', {}).get('value') if isinstance(day.get('hrv'), dict) else day.get('hrv')
        if isinstance(hrv, (int, float)) and hrv > 0:
            hrv_values.append(float(hrv))
        
        # RHR
        rhr = day.get('resting_hr', {}).get('value') if isinstance(day.get('resting_hr'), dict) else day.get('rhr')
        if isinstance(rhr, (int, float)) and rhr > 0:
            rhr_values.append(float(rhr))
        
        # Recovery (从 health_scores 或直接字段)
        hs = day.get('health_scores', {})
        recovery = hs.get('recovery') if isinstance(hs, dict) else day.get('recovery')
        if isinstance(recovery, (int, float)) and recovery > 0:
            recovery_values.append(float(recovery))
        
        # Sleep Performance
        sleep_perf = hs.get('sleep_performance') if isinstance(hs, dict) else day.get('sleep_performance')
        if isinstance(sleep_perf, (int, float)) and sleep_perf > 0:
            sleep_perf_values.append(float(sleep_perf))
        
        # Strain
        strain = hs.get('strain') if isinstance(hs, dict) else day.get('strain')
        if isinstance(strain, (int, float)) and strain >= 0:
            strain_values.append(float(strain))
    
    # 检查是否有足够的数据
    if len(hrv_values) < 5 or len(recovery_values) < 5:
        return None
    
    # 添加数据质量检查 - 至少需要3个数据点计算趋势
    if len(hrv_values) < 3:
        return None
    
    # 检查数据方差（避免所有值都一样导致趋势为0）
    if len(set(hrv_values)) == 1:  # 所有值相同
        return 1.0  # 返回稳定状态
    
    # 计算趋势（使用简单线性回归的斜率）
    def calculate_trend(values):
        """计算趋势斜率（正值=上升，负值=下降）"""
        if len(values) < 3:
            return 0
        
        n = len(values)
        x = list(range(n))
        x_mean = sum(x) / n
        y_mean = sum(values) / n
        
        numerator = sum((x[i] - x_mean) * (values[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))
        
        if denominator == 0:
            return 0
        
        return numerator / denominator
    
    # 计算各指标的趋势
    hrv_trend = calculate_trend(hrv_values)  # 正=改善，负=恶化
    rhr_trend = calculate_trend(rhr_values)  # 负=改善（RHR下降），正=恶化
    recovery_trend = calculate_trend(recovery_values)  # 正=改善
    sleep_trend = calculate_trend(sleep_perf_values) if len(sleep_perf_values) >= 5 else 0
    
    # 计算相对趋势（标准化到 -1 到 1 范围）
    def normalize_trend(trend, threshold):
        """将趋势标准化，threshold 是认为是显著变化的阈值"""
        return max(-1, min(1, trend / threshold))
    
    # 使用阈值标准化（基于经验值）
    hrv_normalized = normalize_trend(hrv_trend, 2.0)  # HRV每天变化2ms算显著
    rhr_normalized = normalize_trend(-rhr_trend, 1.0)  # RHR每天变化1bpm算显著（取负因为RHR下降是好）
    recovery_normalized = normalize_trend(recovery_trend, 3.0)  # Recovery每天变化3%算显著
    sleep_normalized = normalize_trend(sleep_trend, 2.0)  # Sleep perf每天变化2%算显著
    
    # 加权计算综合健康趋势
    # 权重：HRV 30%, RHR 25%, Recovery 30%, Sleep 15%
    health_trend = (
        0.30 * hrv_normalized +
        0.25 * rhr_normalized +
        0.30 * recovery_normalized +
        0.15 * sleep_normalized
    )
    
    # 将健康趋势转换为 Pace of Aging
    # health_trend 范围 -1 到 1
    # -1 = 快速改善（逆龄）-> Pace ~ 0.5
    # 0 = 稳定 -> Pace = 1.0
    # 1 = 快速恶化（加速衰老）-> Pace ~ 2.0
    
    # 使用非线性映射，避免极端值
    if health_trend > 0:
        # 恶化：1.0 到 2.5
        pace = 1.0 + health_trend * 1.5
    else:
        # 改善：0.5 到 1.0
        pace = 1.0 + health_trend * 0.5
    
    # 限制在合理范围
    pace = max(0.3, min(2.5, pace))
    
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

    # 1) Strain：优先使用全天心率数据计算，其次用 workout 心率
    resolved_zone_times = zone_times or data.get('zone_times') or {}
    
    # 获取静息心率用于HRR计算
    rhr = data.get('resting_hr', {}).get('value') if isinstance(data.get('resting_hr'), dict) else None
    if not isinstance(rhr, (int, float)) or rhr <= 0:
        rhr = None
    
    if _sum_zone_minutes(resolved_zone_times) <= 0:
        # 首先尝试使用全天心率数据（更精确）
        hr_data = data.get('heart_rate_data') or []
        if hr_data and len(hr_data) >= 10:  # 需要足够的数据点
            resolved_zone_times = calculate_zone_times_from_hr_data(hr_data, age, rhr)
        else:
            # 退而求其次，使用 workout 心率
            resolved_zone_times = calculate_zone_times_from_workouts(workouts, age, rhr)
    
    if _sum_zone_minutes(resolved_zone_times) > 0:
        strain = calculate_strain_from_zone_times(resolved_zone_times, strength_time)
    else:
        # 最后退回到基于活动能量的估算
        strain, resolved_zone_times = calculate_strain_simple(
            active_energy,
            steps,
            workouts,
            age,
            data.get('heart_rate_data') or [],
            rhr=rhr  # 传递静息心率用于HRR计算
        )

    # 2) Sleep Performance
    yesterday = (datetime.strptime(date_str, '%Y-%m-%d') - timedelta(days=1)).strftime('%Y-%m-%d')
    previous_day_scores = history.get_scores(yesterday, member_name) or {}
    prev_strain = float(previous_day_scores.get('strain', 10) or 10)

    # 计算睡眠规律性（基于睡眠记录的时间差异）
    sleep_records = sleep.get('records', [])
    if len(sleep_records) >= 2:
        # 计算各阶段睡眠时长的标准差变异系数作为不规律性指标
        stage_totals = []
        for record in sleep_records:
            total = record.get('total', 0)
            if total > 0:
                stage_totals.append(total)
        if stage_totals and len(stage_totals) >= 2:
            import statistics
            try:
                mean_total = statistics.mean(stage_totals)
                stdev_total = statistics.stdev(stage_totals) if len(stage_totals) > 1 else 0
                # 变异系数越小越规律，转化为 0-100 的 consistency 分数
                cv = stdev_total / mean_total if mean_total > 0 else 0
                sleep_consistency = max(0, min(100, 100 - cv * 100))
            except:
                sleep_consistency = 75
        else:
            sleep_consistency = 75
    else:
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
        # 数据不足时，基于 Recovery 变化计算简化版 Pace
        previous_7day = history.get_average_range(yesterday, member_name, days=7, skip_days=6)
        if int(previous_7day.get('days_count', 0) or 0) > 0:
            # 使用 Recovery 变化率估算 Pace
            prev_recovery = float(previous_7day.get('recovery', 50) or 50)
            curr_recovery = float(recovery_result.recovery)
            recovery_change = (curr_recovery - prev_recovery) / max(prev_recovery, 1)
            # Recovery 下降 10% → Pace 增加 0.1
            pace = max(0.5, min(2.0, 1.0 - recovery_change))
        else:
            pace = 1.0

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
