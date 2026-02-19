#!/usr/bin/env python3
"""
多语言健康报告生成器
支持中文(zh)和英文(en)
"""
import json
import sys
from pathlib import Path
from datetime import datetime

# 翻译字典
TRANSLATIONS = {
    'zh': {
        'title': '健康日报',
        'date_prefix': '',
        'day_prefix': '第',
        'day_suffix': '天',
        'recovery_score': '恢复度评分',
        'sleep_quality': '睡眠质量',
        'exercise_completion': '运动完成',
        'steps': '今日步数',
        'sleep_duration': '睡眠时长',
        'hrv': 'HRV 心率变异性',
        'resting_hr': '静息心率',
        'exercise_time': '锻炼时间',
        'active_calories': '活跃消耗',
        'floors': '爬楼层数',
        'distance': '行走距离',
        'blood_oxygen': '血氧饱和度',
        'heart_rate_analysis': '心率分析',
        'all_day_hr': '全天心率趋势',
        'workout_hr': '锻炼心率区间',
        'sleep_analysis': '睡眠分析',
        'sleep_structure': '睡眠结构分布',
        'sleep_efficiency': '睡眠效率',
        'deep_sleep': '深睡',
        'rem_sleep': 'REM',
        'light_sleep': '浅睡',
        'awake': '清醒',
        'bed_time': '入睡',
        'wake_time': '起床',
        'time_in_bed': '卧床',
        'exercise_records': '运动记录',
        'trend_comparison': '7日趋势对比',
        'conclusions': '今日健康结论',
        'recommendations': '明日健康建议',
        'diet_suggestions': '明日饮食建议',
        'diet_record': '今日饮食记录',
        'notes': '身体状态备注',
        'breakfast': '早餐',
        'lunch': '午餐',
        'dinner': '晚餐',
        'generated_by': '自动生成',
        'data_source': '数据来源',
        'status_excellent': '优秀',
        'status_good': '良好',
        'status_average': '一般',
        'status_poor': '需改善',
        'status_sufficient': '充足',
        'status_short': '偏短',
        'status_insufficient': '不足',
        'status_not_recorded': '未记录',
        'no_workout': '今日无锻炼记录',
        'no_hr_data': '无全天心率数据',
        'priority': '[优先]',
        'suggestion': '[建议]',
        'optional': '[可选]',
    },
    'en': {
        'title': 'Daily Health Report',
        'date_prefix': '',
        'day_prefix': 'Day',
        'day_suffix': '',
        'recovery_score': 'Recovery Score',
        'sleep_quality': 'Sleep Quality',
        'exercise_completion': 'Exercise',
        'steps': 'Steps',
        'sleep_duration': 'Sleep Duration',
        'hrv': 'HRV (ms)',
        'resting_hr': 'Resting HR',
        'exercise_time': 'Exercise Time',
        'active_calories': 'Active Calories',
        'floors': 'Floors Climbed',
        'distance': 'Distance',
        'blood_oxygen': 'Blood Oxygen',
        'heart_rate_analysis': 'Heart Rate Analysis',
        'all_day_hr': 'All-Day HR Trend',
        'workout_hr': 'Workout HR Zones',
        'sleep_analysis': 'Sleep Analysis',
        'sleep_structure': 'Sleep Structure',
        'sleep_efficiency': 'Sleep Efficiency',
        'deep_sleep': 'Deep',
        'rem_sleep': 'REM',
        'light_sleep': 'Light',
        'awake': 'Awake',
        'bed_time': 'Bedtime',
        'wake_time': 'Wake Time',
        'time_in_bed': 'Time in Bed',
        'exercise_records': 'Exercise Records',
        'trend_comparison': '7-Day Trend',
        'conclusions': 'Health Summary',
        'recommendations': 'Tomorrow\'s Recommendations',
        'diet_suggestions': 'Diet Suggestions',
        'diet_record': 'Today\'s Diet',
        'notes': 'Personal Notes',
        'breakfast': 'Breakfast',
        'lunch': 'Lunch',
        'dinner': 'Dinner',
        'generated_by': 'Auto-generated',
        'data_source': 'Data Source',
        'status_excellent': 'Excellent',
        'status_good': 'Good',
        'status_average': 'Average',
        'status_poor': 'Needs Improvement',
        'status_sufficient': 'Sufficient',
        'status_short': 'Short',
        'status_insufficient': 'Insufficient',
        'status_not_recorded': 'Not Recorded',
        'no_workout': 'No workout recorded today',
        'no_hr_data': 'No heart rate data',
        'priority': '[Priority]',
        'suggestion': '[Suggestion]',
        'optional': '[Optional]',
    }
}

def get_text(key, lang='zh'):
    """获取翻译文本"""
    return TRANSLATIONS.get(lang, TRANSLATIONS['zh']).get(key, key)

def get_score_label(score, lang='zh'):
    """获取评分标签"""
    if score >= 80:
        return get_text('status_excellent', lang)
    elif score >= 60:
        return get_text('status_good', lang)
    elif score >= 40:
        return get_text('status_average', lang)
    else:
        return get_text('status_poor', lang)

def get_sleep_status(hours, has_data, lang='zh'):
    """获取睡眠状态标签"""
    if not has_data:
        return get_text('status_not_recorded', lang)
    if hours >= 7:
        return get_text('status_sufficient', lang)
    elif hours >= 6:
        return get_text('status_short', lang)
    else:
        return get_text('status_insufficient', lang)

def get_weekday_cn(weekday_num):
    """获取中文星期"""
    weekdays = ['日', '一', '二', '三', '四', '五', '六']
    return weekdays[int(weekday_num)]

def get_weekday_en(weekday_num):
    """获取英文星期"""
    weekdays = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
    return weekdays[int(weekday_num)]