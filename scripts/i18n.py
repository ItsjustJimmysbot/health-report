#!/usr/bin/env python3
"""
多语言支持模块 - 健康报告翻译
支持中文(zh)和英文(en)
"""

TRANSLATIONS = {
    'zh': {
        'title': '健康日报',
        'recovery_score': '恢复度评分',
        'sleep_quality': '睡眠质量',
        'exercise_completion': '运动完成',
        'steps': '今日步数',
        'sleep_duration': '睡眠时长',
        'hrv': 'HRV 心率变异性',
        'resting_hr': '静息心率',
        'exercise_time': '锻炼时间',
        'active_calories': '活跃消耗',
        'heart_rate_analysis': '心率分析',
        'sleep_analysis': '睡眠分析',
        'deep_sleep': '深睡',
        'rem_sleep': 'REM',
        'light_sleep': '浅睡',
        'awake': '清醒',
        'conclusions': '今日健康结论',
        'recommendations': '明日健康建议',
        'diet_suggestions': '明日饮食建议',
        'breakfast': '早餐',
        'lunch': '午餐',
        'dinner': '晚餐',
        'generated_by': '自动生成',
        'data_source': '数据来源',
        'status_excellent': '优秀',
        'status_good': '良好',
        'status_average': '一般',
        'status_poor': '需改善',
        'hour': '小时',
        'min': '分钟',
    },
    'en': {
        'title': 'Daily Health Report',
        'recovery_score': 'Recovery Score',
        'sleep_quality': 'Sleep Quality',
        'exercise_completion': 'Exercise',
        'steps': 'Steps',
        'sleep_duration': 'Sleep Duration',
        'hrv': 'HRV (ms)',
        'resting_hr': 'Resting HR',
        'exercise_time': 'Exercise Time',
        'active_calories': 'Active Calories',
        'heart_rate_analysis': 'Heart Rate Analysis',
        'sleep_analysis': 'Sleep Analysis',
        'deep_sleep': 'Deep',
        'rem_sleep': 'REM',
        'light_sleep': 'Light',
        'awake': 'Awake',
        'conclusions': 'Health Summary',
        'recommendations': 'Recommendations',
        'diet_suggestions': 'Diet Suggestions',
        'breakfast': 'Breakfast',
        'lunch': 'Lunch',
        'dinner': 'Dinner',
        'generated_by': 'Auto-generated',
        'data_source': 'Data Source',
        'status_excellent': 'Excellent',
        'status_good': 'Good',
        'status_average': 'Average',
        'status_poor': 'Needs Improvement',
        'hour': 'hrs',
        'min': 'min',
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

def get_weekday_cn(weekday_num):
    """获取中文星期"""
    weekdays = ['日', '一', '二', '三', '四', '五', '六']
    return weekdays[int(weekday_num)]

def get_weekday_en(weekday_num):
    """获取英文星期"""
    weekdays = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
    return weekdays[int(weekday_num)]
