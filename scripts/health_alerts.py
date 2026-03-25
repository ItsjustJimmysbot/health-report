#!/usr/bin/env python3
"""健康风险信号检测模块 - V6.0.6

检测 10 个关键健康风险信号，分为三个级别：
🔴 紧急信号（立即就医）
🟡 早期预警（尽快检查）
🟢 长期趋势（定期关注）
"""

import json
import math
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class HealthAlert:
    """健康警告数据类"""
    level: str
    level_name: str
    title: str
    description: str
    action: str
    icon: str
    color: str


class HealthAlertDetector:
    """健康风险信号检测器"""
    
    def __init__(self, cache_dir: Path, language: str = "CN"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.language = language
        
        self.texts = {
            "CN": {
                "no_alerts": "✅ 今日无健康风险信号",
                "critical_title": "🔴 紧急信号（立即就医）",
                "warning_title": "🟡 早期预警（尽快检查）",
                "trend_title": "🟢 长期趋势（定期关注）",
                "alert_4_title": "HRV 连续暴跌",
                "alert_5_title": "静息心率持续升高",
                "alert_6_title": "静息心率异常",
                "alert_7_title": "血氧饱和度低",
                "alert_8_title": "HRV 长期趋势下行",
                "alert_9_title": "呼吸频率持续升高",
            },
            "EN": {
                "no_alerts": "✅ No health risk signals today",
                "critical_title": "🔴 Critical Signal",
                "warning_title": "🟡 Early Warning",
                "trend_title": "🟢 Long-term Trend",
                "alert_4_title": "HRV Sharp Decline",
                "alert_5_title": "Resting HR Elevated",
                "alert_6_title": "Resting HR Abnormal",
                "alert_7_title": "Low Blood Oxygen",
                "alert_8_title": "HRV Long-term Decline",
                "alert_9_title": "Respiratory Rate Elevated",
            }
        }
    
    def _t(self, key: str, **kwargs) -> str:
        text = self.texts.get(self.language, self.texts["CN"]).get(key, key)
        if kwargs:
            try:
                return text.format(**kwargs)
            except:
                return text
        return text
    
    def _get_cache(self, date_str: str, member_name: str) -> Optional[Dict]:
        from utils import safe_member_name
        safe_name = safe_member_name(member_name)
        cache_file = self.cache_dir / f"{date_str}_{safe_name}.json"
        if cache_file.exists():
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return None
        return None
    
    def _get_hrv_history(self, member_name: str, days: int = 14) -> List[Tuple[str, float]]:
        results = []
        today = datetime.now()
        for i in range(days):
            date = (today - timedelta(days=i)).strftime('%Y-%m-%d')
            cache = self._get_cache(date, member_name)
            if cache:
                hrv = cache.get('hrv', {}).get('value')
                if isinstance(hrv, (int, float)) and hrv > 0:
                    results.append((date, float(hrv)))
        return results
    
    def _get_rhr_history(self, member_name: str, days: int = 7) -> List[Tuple[str, float]]:
        results = []
        today = datetime.now()
        for i in range(days):
            date = (today - timedelta(days=i)).strftime('%Y-%m-%d')
            cache = self._get_cache(date, member_name)
            if cache:
                rhr = cache.get('resting_hr', {}).get('value')
                if isinstance(rhr, (int, float)) and rhr > 0:
                    results.append((date, float(rhr)))
        return results
    
    def detect_alert_3_exercise_hr(self, data: Dict) -> Optional[HealthAlert]:
        workouts = data.get('workouts', [])
        for workout in workouts if isinstance(workouts, list) else []:
            if not isinstance(workout, dict):
                continue
            hr_timeline = workout.get('hr_timeline', [])
            for hr_point in hr_timeline if isinstance(hr_timeline, list) else []:
                if not isinstance(hr_point, dict):
                    continue
                hr = hr_point.get('avg') or hr_point.get('max')
                if isinstance(hr, (int, float)):
                    if hr > 180 or hr < 40:
                        return HealthAlert(
                            level='critical',
                            level_name='紧急',
                            title='运动心率异常',
                            description=f'检测到心率异常: {int(hr)}bpm',
                            action='立即停止运动，坐下休息；如不缓解呼叫救护车',
                            icon='🏃',
                            color='#DC2626'
                        )
        return None
    
    def detect_alert_4_hrv_drop(self, data: Dict, member_name: str) -> Optional[HealthAlert]:
        hrv_history = self._get_hrv_history(member_name, days=5)
        if len(hrv_history) < 3:
            return None
        recent_3 = hrv_history[:3]
        hrv_today = recent_3[0][1]
        hrv_3days_ago = recent_3[2][1]
        if hrv_3days_ago > 0:
            drop_pct = (hrv_3days_ago - hrv_today) / hrv_3days_ago * 100
        else:
            return None
        if drop_pct > 30 and hrv_today < 50:
            return HealthAlert(
                level='warning',
                level_name='预警',
                title=self._t('alert_4_title'),
                description=f'HRV连续3天暴跌 {round(drop_pct)}%，从 {round(hrv_3days_ago,1)}ms 降至 {round(hrv_today,1)}ms',
                action='排除感冒/饮酒/熬夜后仍异常，尽快检查',
                icon='📉',
                color='#F59E0B'
            )
        return None
    
    def detect_alert_5_rhr_elevated(self, data: Dict, member_name: str) -> Optional[HealthAlert]:
        rhr_history = self._get_rhr_history(member_name, days=5)
        if len(rhr_history) < 3:
            return None
        recent_3 = rhr_history[:3]
        avg_rhr = sum(r[1] for r in recent_3) / len(recent_3)
        age = data.get('age', 30)
        normal_rhr = 65 if age <= 35 else (68 if age <= 55 else 70)
        if avg_rhr > normal_rhr + 10:
            return HealthAlert(
                level='warning',
                level_name='预警',
                title=self._t('alert_5_title'),
                description=f'RHR连续3天平均 {round(avg_rhr,1)}bpm（正常约 {normal_rhr}bpm）',
                action='排除感冒/饮酒/熬夜后仍高，说明心脏负荷异常',
                icon='📈',
                color='#F59E0B'
            )
        return None
    
    def detect_alert_6_rhr_abnormal(self, data: Dict) -> Optional[HealthAlert]:
        rhr = data.get('resting_hr', {}).get('value')
        if not isinstance(rhr, (int, float)):
            return None
        if rhr > 100 or rhr < 40:
            return HealthAlert(
                level='warning',
                level_name='预警',
                title=self._t('alert_6_title'),
                description=f'静息心率 {round(rhr,1)}bpm 超出正常范围（40-100bpm）',
                action='心动过速/过缓，需要就医检查',
                icon='💓',
                color='#F59E0B'
            )
        return None
    
    def detect_alert_7_spo2_low(self, data: Dict) -> Optional[HealthAlert]:
        spo2 = data.get('spo2')
        if not isinstance(spo2, (int, float)):
            return None
        if spo2 <= 1.0:
            spo2 = spo2 * 100
        if spo2 < 90:
            return HealthAlert(
                level='warning',
                level_name='预警',
                title=self._t('alert_7_title'),
                description=f'SpO2 均值 {round(spo2,1)}% 低于90%，严重缺氧',
                action='夜间心律失常风险大增，尽快就医检查',
                icon='🫁',
                color='#F59E0B'
            )
        return None
    
    def detect_alert_8_hrv_longterm_decline(self, member_name: str) -> Optional[HealthAlert]:
        hrv_history = self._get_hrv_history(member_name, days=90)
        if len(hrv_history) < 30:
            return None
        n = len(hrv_history)
        chunk_size = max(10, n // 3)
        month_1 = sum(hrv_history[i][1] for i in range(0, min(chunk_size, n))) / min(chunk_size, n)
        month_2 = sum(hrv_history[i][1] for i in range(chunk_size, min(2*chunk_size, n))) / max(1, min(chunk_size, n-chunk_size))
        month_3 = sum(hrv_history[i][1] for i in range(2*chunk_size, min(3*chunk_size, n))) / max(1, min(chunk_size, n-2*chunk_size))
        if month_1 > month_2 > month_3 and (month_1 - month_3) / month_1 > 0.2:
            return HealthAlert(
                level='trend',
                level_name='趋势',
                title=self._t('alert_8_title'),
                description=f'HRV 3个月趋势: {round(month_1)}→{round(month_2)}→{round(month_3)}ms，持续下降',
                action='自主神经功能可能退化，建议心脏全面检查',
                icon='📊',
                color='#22C55E'
            )
        return None
    
    def detect_alert_9_respiratory_elevated(self, data: Dict) -> Optional[HealthAlert]:
        respiratory = data.get('respiratory_rate')
        if not isinstance(respiratory, (int, float)):
            return None
        if respiratory > 18:
            return HealthAlert(
                level='trend',
                level_name='趋势',
                title=self._t('alert_9_title'),
                description=f'呼吸频率 {round(respiratory,1)}次/分，高于正常范围（12-16次/分）',
                action='可能提示心功能下降，定期监测并咨询医生',
                icon='🌬️',
                color='#22C55E'
            )
        return None
    
    def detect_all(self, data: Dict, member_name: str) -> Dict[str, List[HealthAlert]]:
        alerts = {'critical': [], 'warning': [], 'trend': []}
        
        alert = self.detect_alert_3_exercise_hr(data)
        if alert:
            alerts['critical'].append(alert)
        
        alert = self.detect_alert_4_hrv_drop(data, member_name)
        if alert:
            alerts['warning'].append(alert)
        
        alert = self.detect_alert_5_rhr_elevated(data, member_name)
        if alert:
            alerts['warning'].append(alert)
        
        alert = self.detect_alert_6_rhr_abnormal(data)
        if alert:
            alerts['warning'].append(alert)
        
        alert = self.detect_alert_7_spo2_low(data)
        if alert:
            alerts['warning'].append(alert)
        
        alert = self.detect_alert_8_hrv_longterm_decline(member_name)
        if alert:
            alerts['trend'].append(alert)
        
        alert = self.detect_alert_9_respiratory_elevated(data)
        if alert:
            alerts['trend'].append(alert)
        
        return alerts
    
    def generate_html(self, alerts: Dict[str, List[HealthAlert]]) -> str:
        has_any_alert = any(len(v) > 0 for v in alerts.values())
        
        if not has_any_alert:
            return f'<div class="health-alerts-section no-alerts"><div class="alerts-header">{self._t("no_alerts")}</div></div>'
        
        html_parts = ['<div class="health-alerts-section">']
        
        for level in ['critical', 'warning', 'trend']:
            if alerts[level]:
                html_parts.append(f'<div class="alerts-category {level}">')
                html_parts.append(f'<div class="alerts-category-title">{self._t(level+"_title")}</div>')
                for alert in alerts[level]:
                    html_parts.append(f'''
                    <div class="alert-item {level}" style="border-left-color: {alert.color}">
                        <div class="alert-header">
                            <span class="alert-icon">{alert.icon}</span>
                            <span class="alert-title">{alert.title}</span>
                            <span class="alert-badge" style="background: {alert.color}">{alert.level_name}</span>
                        </div>
                        <div class="alert-description">{alert.description}</div>
                        <div class="alert-action">💡 {alert.action}</div>
                    </div>
                    ''')
                html_parts.append('</div>')
        
        html_parts.append('</div>')
        return '\n'.join(html_parts)


def check_health_alerts(data: Dict, cache_dir: Path, member_name: str, language: str = "CN") -> str:
    detector = HealthAlertDetector(cache_dir, language)
    alerts = detector.detect_all(data, member_name)
    return detector.generate_html(alerts)
