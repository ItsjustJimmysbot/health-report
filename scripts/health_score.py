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

# ============ 工具函数 ============

def calculate_max_hr(age: int, gender: str = 'male') -> int:
    """估算最大心率"""
    return int(208 - 0.7 * age)

def get_hr_zone(hr: int, max_hr: int) -> int:
    """心率区间 1-5"""
    pct = hr / max_hr
    if pct < 0.5: return 0
    elif pct < 0.6: return 1
    elif pct < 0.7: return 2
    elif pct < 0.8: return 3
    elif pct < 0.9: return 4
    else: return 5

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
    sleep_contribution: float
    status: str  # 'green', 'yellow', 'red'

def calculate_recovery(hrv_rmssd: float, rhr: float, 
                      sleep_performance: float, respiratory_rate: float,
                      sleep_consistency: float,
                      baseline_hrv: float, baseline_rhr: float,
                      baseline_respiratory: float,
                      gender: str = 'male') -> RecoveryResult:
    """计算Recovery (0-100%)"""
    target_rhr = 60 if gender == 'male' else 64
    
    # HRV分数 (70%权重)
    hrv_ratio = hrv_rmssd / max(1, baseline_hrv)
    rhr_penalty = 0
    if rhr > target_rhr:
        rhr_penalty = 0.3 * (rhr - target_rhr) / target_rhr
    hrv_score = 100 * hrv_ratio * max(0.5, 1 - rhr_penalty)
    hrv_score = min(100, max(0, hrv_score))
    
    # RHR分数
    rhr_score = 100
    if rhr > target_rhr:
        rhr_score -= (rhr - target_rhr) * 2
    rhr_score = max(0, rhr_score)
    
    # 睡眠贡献 (15%)
    sleep_contribution = sleep_performance
    
    # 呼吸率调整 (10%)
    resp_diff = abs(respiratory_rate - baseline_respiratory) / max(1, baseline_respiratory)
    respiratory_score = 100 if resp_diff <= 0.05 else max(0, 100 - (resp_diff - 0.05) * 200)
    
    # 一致性奖励 (5%)
    consistency_bonus = 100 if sleep_consistency >= 80 else 50 if sleep_consistency >= 60 else 0
    
    recovery = int(round(min(100, max(1, 
        0.70 * hrv_score + 0.15 * sleep_contribution + 
        0.10 * respiratory_score + 0.05 * consistency_bonus))))
    
    status = 'green' if recovery >= 67 else 'yellow' if recovery >= 34 else 'red'
    
    return RecoveryResult(recovery, round(hrv_score, 1), round(rhr_score, 1),
                         round(sleep_contribution, 1), status)

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

@dataclass
class BodyAgeResult:
    body_age: float
    chronological_age: int
    age_impact: float
    breakdown: Dict[str, float]
    risk_ratios: Dict[str, float] = None

def calculate_body_age(metrics: Dict, chronological_age: int, gender: str = 'male') -> BodyAgeResult:
    """计算Body Age - V6.0.3改进版（带数据有效性检查和可配置阈值）"""
    impacts = {}
    
    # 获取实际数据（带默认值保护）
    sleep_hours = metrics.get('sleep_hours', 0)
    steps = metrics.get('steps', 0)
    rhr = metrics.get('rhr', 0)
    
    # 数据有效性检查 - 如果没有真实数据，返回实际年龄
    has_real_data = (sleep_hours > 0 or steps > 0 or rhr > 0)
    if not has_real_data:
        return BodyAgeResult(
            body_age=float(chronological_age),
            chronological_age=chronological_age,
            age_impact=0.0,
            breakdown={'note': '数据不足，无法计算'},
            risk_ratios={}
        )
    
    # === 可配置阈值（基于年龄段的推荐值）===
    # 步数目标：基于 WHO 推荐和年龄调整
    if chronological_age <= 30:
        steps_target = 8000
    elif chronological_age <= 50:
        steps_target = 7000
    else:
        steps_target = 5600
    
    # 静息心率目标：基于性别（运动员可能更低，但这里使用一般健康标准）
    target_rhr = 60 if gender == 'male' else 64
    
    # === 睡眠影响计算 ===
    # 逻辑：7-9小时为最佳，6-7小时轻微负面影响，<6小时明显负面影响
    if sleep_hours > 0:
        if 7 <= sleep_hours <= 9:
            impacts['sleep'] = 0  # 最佳范围，无影响
        elif sleep_hours >= 6:
            impacts['sleep'] = 1.2  # 轻微睡眠不足，+1.2岁
        else:
            impacts['sleep'] = 2.5  # 明显睡眠不足，+2.5岁
    
    # === 步数影响计算 ===
    # 逻辑：达到目标减龄，未达标根据差距增加身体年龄（对数缩放避免极端值）
    if steps > 0:
        if steps >= steps_target:
            impacts['steps'] = -1.0  # 达标减龄1岁
        else:
            deficit_ratio = (steps_target - steps) / steps_target
            # 使用对数缩放：差距越大，边际影响递减
            impacts['steps'] = min(5.0, deficit_ratio * 5)
    
    # === RHR影响计算 ===
    # 逻辑：低于目标减龄，高于目标根据程度增加身体年龄
    if rhr > 0:
        if rhr < target_rhr:
            impacts['cardio'] = -0.5  # 心肺功能优秀，减龄0.5岁
        elif rhr < target_rhr + 10:
            impacts['cardio'] = 0  # 正常范围，无影响
        else:
            # 偏高心率：每高10bpm，增加约0.9岁（上限3岁）
            impacts['cardio'] = min(3.0, (rhr - target_rhr) / 10 * 0.9)
    
    total_impact = sum(impacts.values())
    body_age = chronological_age + total_impact
    
    # 添加调试信息到 breakdown（帮助理解计算过程）
    breakdown_detail = {k: round(v, 2) for k, v in impacts.items()}
    breakdown_detail['_config'] = {
        'steps_target': steps_target,
        'target_rhr': target_rhr,
        'gender': gender
    }
    
    return BodyAgeResult(
        body_age=round(body_age, 1),
        chronological_age=chronological_age,
        age_impact=round(total_impact, 1),
        breakdown=breakdown_detail,
        risk_ratios={}
    )

# ============ 5. Pace of Aging ============

def calculate_pace_of_aging(current_scores: Dict, previous_scores: Dict, days_span: int = 7, data_completeness: float = 1.0) -> float:
    """
    计算 Pace of Aging（保持当前模板兼容：负数=逆龄，0=稳定，正数=衰老加快）。

    这里不再做夸张的 30 天年化放大，避免结果经常被打满到 3.00 / 0.00。
    
    Args:
        data_completeness: 数据完整度 (0.0-1.0)，低于 0.7 返回 None 表示数据不足
    """
    # 数据完整性检查
    if data_completeness < 0.7:
        return None  # 返回 None 表示数据不足，而非计算为 0
    
    current_recovery = current_scores.get('recovery')
    previous_recovery = previous_scores.get('recovery')
    current_sleep = current_scores.get('sleep_performance')
    previous_sleep = previous_scores.get('sleep_performance')

    if not all(isinstance(v, (int, float)) for v in [current_recovery, previous_recovery, current_sleep, previous_sleep]):
        return None  # 数据缺失时返回 None，不是 0.0

    recovery_improvement = float(current_recovery) - float(previous_recovery)
    sleep_improvement = float(current_sleep) - float(previous_sleep)

    # 改善越大，pace 越应该偏负；恶化越大，pace 越应该偏正。
    improvement_score = recovery_improvement * 0.6 + sleep_improvement * 0.4
    pace = -(improvement_score / max(1.0, float(days_span))) * 0.25

    # 限幅，避免极端跳变
    pace = max(-1.5, min(1.5, pace))

    if abs(pace) < 0.01:
        pace = 0.0

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

    # 3) Recovery：baseline 使用真实 7 天缓存，不再用 recovery 分数估 HRV
    hrv = data.get('hrv', {}).get('value')
    rhr = data.get('resting_hr', {}).get('value')
    respiratory = data.get('respiratory_rate')

    if not isinstance(hrv, (int, float)):
        hrv = 50.0
    if not isinstance(rhr, (int, float)):
        rhr = 70.0 if gender == 'male' else 74.0
    if not isinstance(respiratory, (int, float)):
        respiratory = 14.0

    baseline = history.get_average_range(yesterday, member_name, days=7, skip_days=0)
    baseline_hrv = baseline.get('hrv_rmssd')
    baseline_rhr = baseline.get('rhr')
    baseline_respiratory = baseline.get('respiratory_rate')

    if not isinstance(baseline_hrv, (int, float)) or baseline_hrv <= 0:
        baseline_hrv = float(hrv)
    if not isinstance(baseline_rhr, (int, float)) or baseline_rhr <= 0:
        baseline_rhr = float(rhr)
    if not isinstance(baseline_respiratory, (int, float)) or baseline_respiratory <= 0:
        baseline_respiratory = float(respiratory)

    recovery_result = calculate_recovery(
        float(hrv),
        float(rhr),
        sleep_result.performance,
        float(respiratory),
        float(sleep_consistency),
        float(baseline_hrv),
        float(baseline_rhr),
        float(baseline_respiratory),
        gender,
    )

    # 4) Body Age：只吃真实数据，不再用 7h / 8000 之类假默认
    body_metrics = {
        'sleep_hours': sleep_total,
        'steps': steps,
        'rhr': float(rhr),
    }
    body_age_result = calculate_body_age(body_metrics, age, gender)

    # 5) Pace of Aging：当前 7 天 vs 前 7 天
    recent_6day = history.get_average_range(yesterday, member_name, days=6, skip_days=0)
    recent_count = int(recent_6day.get('days_count', 0) or 0)
    if recent_count > 0:
        current_7day = {
            'recovery': (
                float(recent_6day.get('recovery', 50)) * recent_count + recovery_result.recovery
            ) / (recent_count + 1),
            'sleep_performance': (
                float(recent_6day.get('sleep_performance', 70)) * recent_count + sleep_result.performance
            ) / (recent_count + 1),
        }
    else:
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
