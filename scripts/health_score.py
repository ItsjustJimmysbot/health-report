#!/usr/bin/env python3
"""健康评分算法模块 V6.0.0

核心评分：
- Strain (0-21): 日心血管负荷
- Recovery (0-100%): 晨间恢复度
- Sleep Performance (0-100%): 睡眠表现
- Body Age: 身体年龄
- Pace of Aging: 衰老速度趋势
"""

import math
import json
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
        zone_times={k: round(v, 1) for k, v in zone_times.items()}
    )

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
                               baseline_need: float = 7.8) -> SleepPerformanceResult:
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

def calculate_body_age(metrics: Dict, chronological_age: int, gender: str = 'male') -> BodyAgeResult:
    """计算Body Age"""
    # 简化的身体年龄计算
    impacts = {}
    
    # 睡眠
    sleep_hours = metrics.get('sleep_hours', 7)
    if 7 <= sleep_hours <= 9:
        impacts['sleep'] = 0
    elif sleep_hours >= 6:
        impacts['sleep'] = 1.2
    else:
        impacts['sleep'] = 2.5
    
    # 步数
    steps = metrics.get('steps', 8000)
    target = 8000 if chronological_age <= 30 else 7000 if chronological_age <= 50 else 5600
    if steps >= target:
        impacts['steps'] = -1.0
    else:
        impacts['steps'] = (target - steps) / 1000 * 2.3
    
    # HRV/RHR综合
    rhr = metrics.get('rhr', 70)
    if rhr < 60:
        impacts['cardio'] = -1.5
    elif rhr < 70:
        impacts['cardio'] = 0
    else:
        impacts['cardio'] = (rhr - 70) / 10 * 0.9
    
    total_impact = sum(impacts.values())
    body_age = chronological_age + total_impact
    
    return BodyAgeResult(round(body_age, 1), chronological_age, round(total_impact, 1), 
                        {k: round(v, 2) for k, v in impacts.items()})

# ============ 5. Pace of Aging ============

def calculate_pace_of_aging(current_scores: Dict, previous_scores: Dict, days_span: int = 7) -> float:
    """
    计算Pace of Aging
    
    对比当前7天和前7天的健康评分变化
    Pace > 0: 加速衰老
    Pace = 0: 停龄
    Pace < 0: 逆龄
    """
    # 计算Recovery变化趋势
    current_recovery = current_scores.get('recovery', 50)
    previous_recovery = previous_scores.get('recovery', 50)
    recovery_change = current_recovery - previous_recovery
    
    # 计算Sleep变化趋势
    current_sleep = current_scores.get('sleep_performance', 70)
    previous_sleep = previous_scores.get('sleep_performance', 70)
    sleep_change = current_sleep - previous_sleep
    
    # 综合Pace (标准化到-1.0 ~ 3.0)
    # Recovery和Sleep都提升 -> 逆龄
    # 都下降 -> 加速衰老
    combined_change = (recovery_change * 0.6 + sleep_change * 0.4) / 10  # 归一化
    
    # 年化处理
    annualized_change = combined_change / days_span * 30  # 30天趋势
    
    pace = max(-1.0, min(3.0, annualized_change))
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
    
    def get_7day_average(self, end_date: str, member_name: str) -> Dict:
        """获取7天平均值"""
        from datetime import datetime, timedelta
        
        scores = []
        end = datetime.strptime(end_date, '%Y-%m-%d')
        
        for i in range(7):
            date = (end - timedelta(days=i)).strftime('%Y-%m-%d')
            day_scores = self.get_scores(date, member_name)
            if day_scores:
                scores.append(day_scores)
        
        if not scores:
            return {'strain': 10, 'recovery': 50, 'sleep_performance': 70}
        
        return {
            'strain': sum(s.get('strain', 10) for s in scores) / len(scores),
            'recovery': sum(s.get('recovery', 50) for s in scores) / len(scores),
            'sleep_performance': sum(s.get('sleep_performance', 70) for s in scores) / len(scores)
        }
    
    def get_sleep_debt(self, date_str: str, member_name: str) -> float:
        """获取某天的累积睡眠债"""
        scores = self.get_scores(date_str, member_name)
        if scores:
            return scores.get('sleep_debt_accumulated', 0)
        return 0
    
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

def calculate_all_scores(data: Dict, profile: Dict, history: HealthScoreHistory) -> Dict:
    """
    一键计算所有健康评分
    
    Args:
        data: 当日健康数据
        profile: 用户档案 (age, gender, height, weight)
        history: 历史数据管理器
    """
    age = profile.get('age', 30)
    gender = profile.get('gender', 'male')
    date_str = data.get('date', datetime.now().strftime('%Y-%m-%d'))
    member_name = profile.get('name', '默认用户')
    
    # 1. Strain
    # 从workouts构建心率数据（简化版）
    hr_data = []
    base_time = datetime.now().replace(hour=6, minute=0)
    for i in range(24 * 12):
        hr = 60  # 默认值
        hr_data.append((base_time + timedelta(minutes=i*5), hr))
    
    workouts = data.get('workouts', [])
    strength_time = sum(w.get('duration_minutes', 0) for w in workouts 
                       if 'strength' in w.get('name', '').lower())
    
    strain_result = calculate_strain(hr_data, strength_time, age, gender)
    
    # 2. Sleep Performance
    sleep = data.get('sleep', {})
    previous_strain = history.get_scores(
        (datetime.strptime(date_str, '%Y-%m-%d') - timedelta(days=1)).strftime('%Y-%m-%d'),
        member_name
    ) or {}
    prev_strain = previous_strain.get('strain', 10) if isinstance(previous_strain, dict) else 10
    
    sleep_result = calculate_sleep_performance(
        sleep.get('total_hours', 7),
        prev_strain,
        75,  # consistency - 需要额外计算
        sleep.get('awake_hours', 0) * 60,
        20   # latency - 需要额外计算
    )
    
    # 3. Recovery
    hrv = data.get('hrv', {}).get('value', 50)
    rhr = data.get('resting_hr', {}).get('value', 70)
    respiratory = data.get('respiratory_rate', 14)
    
    # 获取baseline（30天平均）
    baseline = history.get_7day_average(date_str, member_name)  # 简化：用7天代替30天
    
    recovery_result = calculate_recovery(
        hrv, rhr, sleep_result.performance, respiratory, 75,
        baseline.get('recovery', 50) * 0.8,  # 估算baseline_hrv
        65 if gender == 'male' else 68,
        14,
        gender
    )
    
    # 4. Body Age
    body_metrics = {
        'sleep_hours': sleep.get('total_hours', 7),
        'steps': data.get('steps', 8000),
        'rhr': rhr
    }
    body_age_result = calculate_body_age(body_metrics, age, gender)
    
    # 5. Pace of Aging
    current_7day = history.get_7day_average(date_str, member_name)
    previous_7day = {'recovery': 50, 'sleep_performance': 70}  # 简化
    pace = calculate_pace_of_aging(current_7day, previous_7day)
    
    return {
        'strain': strain_result.strain,
        'recovery': recovery_result.recovery,
        'recovery_status': recovery_result.status,
        'sleep_performance': sleep_result.performance,
        'sleep_need': sleep_result.sleep_need,
        'body_age': body_age_result.body_age,
        'chronological_age': body_age_result.chronological_age,
        'age_impact': body_age_result.age_impact,
        'pace_of_aging': pace,
        'breakdown': {
            'strain_detail': asdict(strain_result),
            'recovery_detail': asdict(recovery_result),
            'sleep_detail': asdict(sleep_result),
            'body_age_detail': asdict(body_age_result)
        }
    }
