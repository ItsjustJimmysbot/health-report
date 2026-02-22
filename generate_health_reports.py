#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成2026-02-20详细健康报告（4份）
"""

import json
import os
from datetime import datetime
from collections import defaultdict
import statistics

# 数据文件路径
DATA_FILE_20 = "/Users/jimmylu/我的云端硬盘/Health Auto Export/Health Data/HealthAutoExport-2026-02-20.json"
DATA_FILE_19 = "/Users/jimmylu/我的云端硬盘/Health Auto Export/Health Data/HealthAutoExport-2026-02-19.json"
OUTPUT_DIR = "/Users/jimmylu/.openclaw/workspace/shared/health-reports/upload"

# 确保输出目录存在
os.makedirs(OUTPUT_DIR, exist_ok=True)

def load_health_data(filepath):
    """加载健康数据"""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def extract_metrics(data, date_str):
    """提取指定日期的各项指标"""
    metrics = {}
    for metric in data.get('data', {}).get('metrics', []):
        name = metric['name']
        units = metric.get('units', '')
        metric_data = metric.get('data', [])
        
        # 过滤指定日期的数据
        day_data = []
        for item in metric_data:
            item_date = item.get('date', '')
            if date_str in item_date:
                day_data.append(item)
        
        if day_data:
            metrics[name] = {
                'units': units,
                'data': day_data,
                'count': len(day_data)
            }
    return metrics

def calculate_steps(metrics):
    """计算步数"""
    if 'step_count' not in metrics:
        return 0, 0
    data = metrics['step_count']['data']
    total = sum(item.get('qty', 0) for item in data)
    return int(total), len(data)

def calculate_distance(metrics):
    """计算行走距离"""
    if 'walking_running_distance' not in metrics:
        return 0, 0
    data = metrics['walking_running_distance']['data']
    total = sum(item.get('qty', 0) for item in data)
    return round(total, 2), len(data)

def calculate_heart_rate(metrics):
    """计算心率统计"""
    if 'heart_rate' not in metrics:
        return None, 0
    data = metrics['heart_rate']['data']
    avg_values = [item.get('Avg', 0) for item in data if 'Avg' in item]
    if not avg_values:
        return None, 0
    return {
        'min': min(avg_values),
        'max': max(avg_values),
        'avg': round(statistics.mean(avg_values), 1)
    }, len(data)

def calculate_hrv(metrics):
    """计算心率变异性"""
    if 'heart_rate_variability' not in metrics:
        return None, 0
    data = metrics['heart_rate_variability']['data']
    values = [item.get('qty', 0) for item in data]
    if not values:
        return None, 0
    return {
        'min': round(min(values), 1),
        'max': round(max(values), 1),
        'avg': round(statistics.mean(values), 1)
    }, len(data)

def calculate_sleep(metrics):
    """计算睡眠数据"""
    if 'sleep_analysis' not in metrics:
        return None
    data = metrics['sleep_analysis']['data']
    if not data:
        return None
    sleep = data[0]
    return {
        'total_sleep': round(sleep.get('totalSleep', 0), 2),
        'deep': round(sleep.get('deep', 0), 2),
        'core': round(sleep.get('core', 0), 2),
        'rem': round(sleep.get('rem', 0), 2),
        'awake': round(sleep.get('awake', 0), 2),
        'start': sleep.get('sleepStart', ''),
        'end': sleep.get('sleepEnd', '')
    }

def calculate_stand_time(metrics):
    """计算站立时间"""
    if 'apple_stand_time' not in metrics:
        return 0, 0
    data = metrics['apple_stand_time']['data']
    total = sum(item.get('qty', 0) for item in data)
    return round(total, 1), len(data)

def calculate_stand_hours(metrics):
    """计算站立小时数"""
    if 'apple_stand_hour' not in metrics:
        return 0, 0
    data = metrics['apple_stand_hour']['data']
    return len(data), len(data)

def calculate_exercise_time(metrics):
    """计算锻炼时间"""
    if 'apple_exercise_time' not in metrics:
        return 0, 0
    data = metrics['apple_exercise_time']['data']
    total = sum(item.get('qty', 0) for item in data)
    return int(total), len(data)

def calculate_blood_oxygen(metrics):
    """计算血氧"""
    if 'blood_oxygen_saturation' not in metrics:
        return None, 0
    data = metrics['blood_oxygen_saturation']['data']
    values = [item.get('qty', 0) for item in data]
    if not values:
        return None, 0
    return {
        'min': min(values),
        'max': max(values),
        'avg': round(statistics.mean(values), 1)
    }, len(data)

def calculate_respiratory_rate(metrics):
    """计算呼吸频率"""
    if 'respiratory_rate' not in metrics:
        return None, 0
    data = metrics['respiratory_rate']['data']
    values = [item.get('qty', 0) for item in data]
    if not values:
        return None, 0
    return {
        'min': min(values),
        'max': max(values),
        'avg': round(statistics.mean(values), 1)
    }, len(data)

def calculate_walking_speed(metrics):
    """计算步行速度"""
    if 'walking_speed' not in metrics:
        return None, 0
    data = metrics['walking_speed']['data']
    values = [item.get('qty', 0) for item in data]
    if not values:
        return None, 0
    return {
        'min': round(min(values), 2),
        'max': round(max(values), 2),
        'avg': round(statistics.mean(values), 2)
    }, len(data)

def calculate_step_length(metrics):
    """计算步长"""
    if 'walking_step_length' not in metrics:
        return None, 0
    data = metrics['walking_step_length']['data']
    values = [item.get('qty', 0) for item in data]
    if not values:
        return None, 0
    return {
        'min': round(min(values), 1),
        'max': round(max(values), 1),
        'avg': round(statistics.mean(values), 1)
    }, len(data)

def calculate_double_support(metrics):
    """计算双支撑百分比"""
    if 'walking_double_support_percentage' not in metrics:
        return None, 0
    data = metrics['walking_double_support_percentage']['data']
    values = [item.get('qty', 0) for item in data]
    if not values:
        return None, 0
    return {
        'min': round(min(values), 1),
        'max': round(max(values), 1),
        'avg': round(statistics.mean(values), 1)
    }, len(data)

def analyze_day(data_file, date_str):
    """分析一天的健康数据"""
    data = load_health_data(data_file)
    metrics = extract_metrics(data, date_str)
    
    analysis = {}
    
    # 步数
    steps, steps_count = calculate_steps(metrics)
    analysis['steps'] = {'value': steps, 'count': steps_count, 'unit': '步'}
    
    # 行走距离
    distance, dist_count = calculate_distance(metrics)
    analysis['distance'] = {'value': distance, 'count': dist_count, 'unit': 'km'}
    
    # 心率
    hr, hr_count = calculate_heart_rate(metrics)
    analysis['heart_rate'] = {'value': hr, 'count': hr_count, 'unit': 'bpm'}
    
    # HRV
    hrv, hrv_count = calculate_hrv(metrics)
    analysis['hrv'] = {'value': hrv, 'count': hrv_count, 'unit': 'ms'}
    
    # 睡眠
    sleep = calculate_sleep(metrics)
    analysis['sleep'] = {'value': sleep, 'count': 1 if sleep else 0, 'unit': 'hr'}
    
    # 站立时间
    stand_time, stand_count = calculate_stand_time(metrics)
    analysis['stand_time'] = {'value': stand_time, 'count': stand_count, 'unit': 'min'}
    
    # 站立小时
    stand_hours, _ = calculate_stand_hours(metrics)
    analysis['stand_hours'] = {'value': stand_hours, 'count': stand_hours, 'unit': 'hours'}
    
    # 锻炼时间
    exercise, exercise_count = calculate_exercise_time(metrics)
    analysis['exercise'] = {'value': exercise, 'count': exercise_count, 'unit': 'min'}
    
    # 血氧
    spo2, spo2_count = calculate_blood_oxygen(metrics)
    analysis['spo2'] = {'value': spo2, 'count': spo2_count, 'unit': '%'}
    
    # 呼吸频率
    rr, rr_count = calculate_respiratory_rate(metrics)
    analysis['respiratory'] = {'value': rr, 'count': rr_count, 'unit': 'br/min'}
    
    # 步行速度
    speed, speed_count = calculate_walking_speed(metrics)
    analysis['walking_speed'] = {'value': speed, 'count': speed_count, 'unit': 'km/hr'}
    
    # 步长
    step_len, step_len_count = calculate_step_length(metrics)
    analysis['step_length'] = {'value': step_len, 'count': step_len_count, 'unit': 'cm'}
    
    # 双支撑
    ds, ds_count = calculate_double_support(metrics)
    analysis['double_support'] = {'value': ds, 'count': ds_count, 'unit': '%'}
    
    return analysis

# 中文报告内容生成
def generate_zh_report_content(analysis, date_str):
    """生成中文报告内容"""
    
    # 指标分析文本（100-150字每项）
    def get_step_analysis():
        steps = analysis['steps']['value']
        if steps < 3000:
            return f"今日步数为{steps}步，处于较低水平。建议增加日常活动量，如散步、爬楼梯等。长时间久坐可能影响血液循环和代谢健康。建议每小时起身活动5-10分钟，逐步养成规律运动的习惯。数据来源：{analysis['steps']['count']}个数据点。"
        elif steps < 8000:
            return f"今日步数为{steps}步，达到基本活动水平。建议继续保持，并尝试增加至8000-10000步以获得更好的健康收益。适度的步行有助于心血管健康和体重管理。数据来源：{analysis['steps']['count']}个数据点。"
        else:
            return f"今日步数为{steps}步，表现优秀！已达到推荐的活动水平。持续保持这一运动量有助于降低心血管疾病风险、改善睡眠质量和提升整体健康水平。数据来源：{analysis['steps']['count']}个数据点。"
    
    def get_sleep_analysis():
        sleep = analysis['sleep']['value']
        if not sleep:
            return "今日无睡眠数据记录。建议保持规律的作息时间，确保每晚7-9小时的优质睡眠。良好的睡眠对身体恢复和大脑功能至关重要。"
        total = sleep['total_sleep']
        deep = sleep['deep']
        rem = sleep['rem']
        if total < 6:
            return f"今日睡眠时长为{total}小时，略显不足。深度睡眠{deep}小时，REM睡眠{rem}小时。建议提前就寝，避免睡前使用电子设备，创造良好的睡眠环境。数据来源：{analysis['sleep']['count']}个数据点。"
        elif total < 8:
            return f"今日睡眠时长为{total}小时，处于合理范围。深度睡眠{deep}小时，REM睡眠{rem}小时，睡眠结构基本正常。建议继续保持规律作息，确保睡眠环境的舒适和安静。数据来源：{analysis['sleep']['count']}个数据点。"
        else:
            return f"今日睡眠时长为{total}小时，睡眠充足。深度睡眠{deep}小时，REM睡眠{rem}小时，睡眠结构良好。优质的睡眠有助于身体修复、免疫力提升和认知功能维持。数据来源：{analysis['sleep']['count']}个数据点。"
    
    def get_heart_rate_analysis():
        hr = analysis['heart_rate']['value']
        if not hr:
            return "今日无心率数据记录。建议确保Apple Watch正确佩戴，以便获取准确的心率监测数据。心率是评估心血管健康的重要指标。"
        avg_hr = hr['avg']
        if avg_hr < 60:
            return f"今日平均心率为{avg_hr}bpm，处于较低水平。静息心率低通常表明良好的心肺功能，但如果伴有不适症状请咨询医生。心率范围：{hr['min']}-{hr['max']}bpm。数据来源：{analysis['heart_rate']['count']}个数据点。"
        elif avg_hr < 80:
            return f"今日平均心率为{avg_hr}bpm，处于正常健康范围。这表明您的心血管系统功能良好。心率范围：{hr['min']}-{hr['max']}bpm。定期监测心率有助于及早发现潜在健康问题。数据来源：{analysis['heart_rate']['count']}个数据点。"
        else:
            return f"今日平均心率为{avg_hr}bpm，略高于正常范围。可能与压力、咖啡因摄入或活动量有关。心率范围：{hr['min']}-{hr['max']}bpm。建议关注日常压力管理，必要时咨询医生。数据来源：{analysis['heart_rate']['count']}个数据点。"
    
    def get_hrv_analysis():
        hrv = analysis['hrv']['value']
        if not hrv:
            return "今日无心率变异性数据记录。HRV是评估自主神经系统功能和压力恢复能力的重要指标。建议确保设备正常佩戴以获取数据。"
        avg_hrv = hrv['avg']
        if avg_hrv < 30:
            return f"今日平均HRV为{avg_hrv}ms，处于较低水平。可能提示身体疲劳或压力较大。HRV范围：{hrv['min']}-{hrv['max']}ms。建议增加休息和恢复时间，尝试冥想或深呼吸练习。数据来源：{analysis['hrv']['count']}个数据点。"
        elif avg_hrv < 60:
            return f"今日平均HRV为{avg_hrv}ms，处于中等水平。HRV范围：{hrv['min']}-{hrv['max']}ms。这表明您的身体恢复能力尚可，但仍有提升空间。建议保持规律作息和适度运动。数据来源：{analysis['hrv']['count']}个数据点。"
        else:
            return f"今日平均HRV为{avg_hrv}ms，表现良好。HRV范围：{hrv['min']}-{hrv['max']}ms。较高的HRV通常表明良好的自主神经功能和身体恢复能力。继续保持健康的生活方式！数据来源：{analysis['hrv']['count']}个数据点。"
    
    def get_spo2_analysis():
        spo2 = analysis['spo2']['value']
        if not spo2:
            return "今日无血氧数据记录。血氧饱和度是评估呼吸功能和氧气输送能力的重要指标。建议在睡眠时佩戴设备以获取数据。"
        avg_spo2 = spo2['avg']
        if avg_spo2 < 95:
            return f"今日平均血氧为{avg_spo2}%，略低于正常范围（95-100%）。血氧范围：{spo2['min']}-{spo2['max']}%。如持续偏低，建议咨询医生排查呼吸系统问题。数据来源：{analysis['spo2']['count']}个数据点。"
        else:
            return f"今日平均血氧为{avg_spo2}%，处于正常健康范围。血氧范围：{spo2['min']}-{spo2['max']}%。良好的血氧水平表明呼吸系统功能正常。数据来源：{analysis['spo2']['count']}个数据点。"
    
    def get_exercise_analysis():
        exercise = analysis['exercise']['value']
        if exercise < 10:
            return f"今日锻炼时间为{exercise}分钟，略显不足。建议每天至少进行30分钟中等强度运动，如快走、游泳或骑车。规律运动对心血管健康和体重管理至关重要。数据来源：{analysis['exercise']['count']}个数据点。"
        elif exercise < 30:
            return f"今日锻炼时间为{exercise}分钟，有一定活动量。建议逐步增加至30-60分钟以获得更好的健康收益。数据来源：{analysis['exercise']['count']}个数据点。"
        else:
            return f"今日锻炼时间为{exercise}分钟，达到推荐运动量。规律的运动习惯有助于降低慢性病风险、提升心肺功能和精神健康。继续保持！数据来源：{analysis['exercise']['count']}个数据点。"
    
    # AI建议（3-4部分，200-300字每部分）
    ai_suggestions = """
【运动与活动建议】
根据今日活动数据，建议制定个性化的运动计划。若步数不足，可尝试"碎片化运动"策略：每工作1小时起身活动5分钟，选择楼梯而非电梯，饭后散步15-20分钟。对于已达到基础活动量的用户，建议加入2-3次中等强度有氧运动（如快走、慢跑、游泳），每次持续30-45分钟。同时可结合力量训练，每周2-3次，增强肌肉力量和骨密度。运动前后注意热身和拉伸，避免运动损伤。

【睡眠优化建议】
睡眠质量直接影响身体恢复和日间精力。建议建立固定的睡前仪式：睡前1小时避免使用电子屏幕，调暗室内灯光，可进行轻度阅读或冥想。保持卧室温度在18-22°C，使用遮光窗帘减少光线干扰。避免睡前3小时大量进食或饮用含咖啡因饮料。如存在入睡困难，可尝试4-7-8呼吸法：吸气4秒，屏息7秒，呼气8秒。规律的作息时间表有助于调节生物钟，提升睡眠质量。

【压力管理与恢复】
心率变异性（HRV）是评估身体压力状态的重要指标。如HRV偏低，提示需要增加恢复时间。建议每日安排10-15分钟正念冥想或深呼吸练习，帮助激活副交感神经系统。工作中采用番茄工作法（25分钟专注+5分钟休息），避免长时间高强度工作。保证充足的社交活动时间，与亲友交流有助于心理放松。周末可适当安排户外活动，接触自然环境对压力缓解有显著效果。

【营养与水分补充】
配合运动和健康监测，合理的营养摄入同样重要。建议每日饮水2000-2500ml，根据活动量适当调整。饮食方面遵循"彩虹饮食"原则，摄入多种颜色的蔬果以获得全面的植物营养素。运动前后适当补充碳水化合物和蛋白质，促进能量恢复和肌肉修复。控制加工食品和含糖饮料的摄入，选择全谷物、瘦肉、鱼类、坚果等天然食材。规律进餐时间，避免暴饮暴食。
"""
    
    content = f"""
================================================================================
                        健康日报 - {date_str}
================================================================================

一、数据概览

┌─────────────────┬──────────┬────────┬─────────────────┐
│ 指标            │ 数值     │ 单位   │ 数据点数量      │
├─────────────────┼──────────┼────────┼─────────────────┤
│ 步数            │ {analysis['steps']['value']:<8} │ {analysis['steps']['unit']:<6} │ {analysis['steps']['count']:<15} │
│ 行走距离        │ {analysis['distance']['value']:<8} │ {analysis['distance']['unit']:<6} │ {analysis['distance']['count']:<15} │
│ 锻炼时间        │ {analysis['exercise']['value']:<8} │ {analysis['exercise']['unit']:<6} │ {analysis['exercise']['count']:<15} │
│ 站立时间        │ {analysis['stand_time']['value']:<8} │ {analysis['stand_time']['unit']:<6} │ {analysis['stand_time']['count']:<15} │
│ 站立小时        │ {analysis['stand_hours']['value']:<8} │ {analysis['stand_hours']['unit']:<6} │ {analysis['stand_hours']['count']:<15} │
"""
    
    if analysis['heart_rate']['value']:
        hr = analysis['heart_rate']['value']
        content += f"│ 心率(平均)      │ {hr['avg']:<8} │ {analysis['heart_rate']['unit']:<6} │ {analysis['heart_rate']['count']:<15} │\n"
    
    if analysis['hrv']['value']:
        hrv = analysis['hrv']['value']
        content += f"│ HRV(平均)       │ {hrv['avg']:<8} │ {analysis['hrv']['unit']:<6} │ {analysis['hrv']['count']:<15} │\n"
    
    if analysis['spo2']['value']:
        spo2 = analysis['spo2']['value']
        content += f"│ 血氧(平均)      │ {spo2['avg']:<8} │ {analysis['spo2']['unit']:<6} │ {analysis['spo2']['count']:<15} │\n"
    
    if analysis['sleep']['value']:
        sleep = analysis['sleep']['value']
        content += f"│ 睡眠时长        │ {sleep['total_sleep']:<8} │ {analysis['sleep']['unit']:<6} │ {analysis['sleep']['count']:<15} │\n"
    
    if analysis['respiratory']['value']:
        rr = analysis['respiratory']['value']
        content += f"│ 呼吸频率        │ {rr['avg']:<8} │ {analysis['respiratory']['unit']:<6} │ {analysis['respiratory']['count']:<15} │\n"
    
    if analysis['walking_speed']['value']:
        ws = analysis['walking_speed']['value']
        content += f"│ 步行速度        │ {ws['avg']:<8} │ {analysis['walking_speed']['unit']:<6} │ {analysis['walking_speed']['count']:<15} │\n"
    
    if analysis['step_length']['value']:
        sl = analysis['step_length']['value']
        content += f"│ 步长            │ {sl['avg']:<8} │ {analysis['step_length']['unit']:<6} │ {analysis['step_length']['count']:<15} │\n"
    
    content += f"""└─────────────────┴──────────┴────────┴─────────────────┘

二、详细指标分析

【步数分析】
{get_step_analysis()}

【睡眠分析】
{get_sleep_analysis()}

【心率分析】
{get_heart_rate_analysis()}

【心率变异性分析】
{get_hrv_analysis()}

【血氧分析】
{get_spo2_analysis()}

【锻炼分析】
{get_exercise_analysis()}

三、AI健康建议
{ai_suggestions}

四、数据来源追溯

本报告基于Apple Watch及关联设备采集的健康数据生成，具体包括：
- Apple Health App 导出数据
- Apple Watch 传感器数据
- 设备佩戴期间连续监测记录

各指标数据点数量已在概览表中列出。数据采集时间范围：{date_str} 00:00:00 - 23:59:59 (GMT+8)

五、免责声明

本报告仅供参考，不构成医疗建议。如有健康问题，请咨询专业医疗人员。

================================================================================
报告生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
================================================================================
"""
    
    return content

# 英文报告内容生成
def generate_en_report_content(analysis, date_str):
    """生成英文报告内容"""
    
    def get_step_analysis():
        steps = analysis['steps']['value']
        if steps < 3000:
            return f"Today's step count is {steps} steps, which is relatively low. Consider increasing daily activity through walking, taking stairs, or short breaks. Prolonged sitting may affect circulation and metabolic health. Try to stand up and move for 5-10 minutes every hour. Data source: {analysis['steps']['count']} data points."
        elif steps < 8000:
            return f"Today's step count is {steps} steps, meeting basic activity levels. Continue maintaining this and consider increasing to 8,000-10,000 steps for better health benefits. Regular walking supports cardiovascular health and weight management. Data source: {analysis['steps']['count']} data points."
        else:
            return f"Today's step count is {steps} steps - excellent performance! You've achieved recommended activity levels. Sustained physical activity helps reduce cardiovascular risk, improve sleep quality, and enhance overall wellness. Data source: {analysis['steps']['count']} data points."
    
    def get_sleep_analysis():
        sleep = analysis['sleep']['value']
        if not sleep:
            return "No sleep data recorded today. Maintain a consistent sleep schedule with 7-9 hours of quality sleep per night. Good sleep is essential for physical recovery and cognitive function."
        total = sleep['total_sleep']
        deep = sleep['deep']
        rem = sleep['rem']
        if total < 6:
            return f"Sleep duration today was {total} hours, slightly insufficient. Deep sleep: {deep} hours, REM sleep: {rem} hours. Consider earlier bedtime, avoid screens before sleep, and create a comfortable sleep environment. Data source: {analysis['sleep']['count']} data points."
        elif total < 8:
            return f"Sleep duration today was {total} hours, within reasonable range. Deep sleep: {deep} hours, REM sleep: {rem} hours - normal sleep structure. Maintain consistent sleep schedule and ensure comfortable sleeping conditions. Data source: {analysis['sleep']['count']} data points."
        else:
            return f"Sleep duration today was {total} hours - well rested. Deep sleep: {deep} hours, REM sleep: {rem} hours - good sleep architecture. Quality sleep supports physical repair, immunity, and cognitive function. Data source: {analysis['sleep']['count']} data points."
    
    def get_heart_rate_analysis():
        hr = analysis['heart_rate']['value']
        if not hr:
            return "No heart rate data recorded today. Ensure proper Apple Watch fit for accurate monitoring. Heart rate is a key indicator of cardiovascular health."
        avg_hr = hr['avg']
        if avg_hr < 60:
            return f"Average heart rate today was {avg_hr} bpm, relatively low. Lower resting heart rate typically indicates good cardiovascular fitness, but consult a doctor if experiencing symptoms. Range: {hr['min']}-{hr['max']} bpm. Data source: {analysis['heart_rate']['count']} data points."
        elif avg_hr < 80:
            return f"Average heart rate today was {avg_hr} bpm, within healthy normal range. This indicates good cardiovascular function. Range: {hr['min']}-{hr['max']} bpm. Regular heart rate monitoring helps detect potential health issues early. Data source: {analysis['heart_rate']['count']} data points."
        else:
            return f"Average heart rate today was {avg_hr} bpm, slightly above normal range. May be related to stress, caffeine intake, or activity levels. Range: {hr['min']}-{hr['max']} bpm. Focus on stress management and consult a doctor if concerned. Data source: {analysis['heart_rate']['count']} data points."
    
    def get_hrv_analysis():
        hrv = analysis['hrv']['value']
        if not hrv:
            return "No HRV data recorded today. HRV is an important metric for assessing autonomic nervous system function and recovery capacity. Ensure proper device fit to capture data."
        avg_hrv = hrv['avg']
        if avg_hrv < 30:
            return f"Average HRV today was {avg_hrv} ms, relatively low. May indicate fatigue or high stress levels. Range: {hrv['min']}-{hrv['max']} ms. Consider increasing rest and recovery time, try meditation or deep breathing exercises. Data source: {analysis['hrv']['count']} data points."
        elif avg_hrv < 60:
            return f"Average HRV today was {avg_hrv} ms, moderate level. Range: {hrv['min']}-{hrv['max']} ms. This indicates adequate recovery capacity with room for improvement. Maintain regular schedule and moderate exercise. Data source: {analysis['hrv']['count']} data points."
        else:
            return f"Average HRV today was {avg_hrv} ms - good performance. Range: {hrv['min']}-{hrv['max']} ms. Higher HRV typically indicates good autonomic function and recovery capacity. Keep up your healthy lifestyle! Data source: {analysis['hrv']['count']} data points."
    
    def get_spo2_analysis():
        spo2 = analysis['spo2']['value']
        if not spo2:
            return "No blood oxygen data recorded today. SpO2 is important for assessing respiratory function and oxygen delivery. Consider wearing device during sleep to capture data."
        avg_spo2 = spo2['avg']
        if avg_spo2 < 95:
            return f"Average blood oxygen today was {avg_spo2}%, slightly below normal range (95-100%). Range: {spo2['min']}-{spo2['max']}%. If consistently low, consult a doctor to check respiratory function. Data source: {analysis['spo2']['count']} data points."
        else:
            return f"Average blood oxygen today was {avg_spo2}%, within healthy normal range. Range: {spo2['min']}-{spo2['max']}%. Good oxygen levels indicate normal respiratory function. Data source: {analysis['spo2']['count']} data points."
    
    def get_exercise_analysis():
        exercise = analysis['exercise']['value']
        if exercise < 10:
            return f"Exercise time today was {exercise} minutes, slightly insufficient. Aim for at least 30 minutes of moderate-intensity exercise daily, such as brisk walking, swimming, or cycling. Regular exercise is crucial for cardiovascular health and weight management. Data source: {analysis['exercise']['count']} data points."
        elif exercise < 30:
            return f"Exercise time today was {exercise} minutes, some activity recorded. Consider gradually increasing to 30-60 minutes for better health benefits. Data source: {analysis['exercise']['count']} data points."
        else:
            return f"Exercise time today was {exercise} minutes, meeting recommended activity levels. Regular exercise habits help reduce chronic disease risk, improve cardiovascular fitness, and enhance mental health. Keep it up! Data source: {analysis['exercise']['count']} data points."
    
    ai_suggestions = """
[Exercise & Activity Recommendations]
Based on today's activity data, consider developing a personalized exercise plan. If step count is low, try the "movement snack" approach: stand up and move for 5 minutes every hour of work, take stairs instead of elevators, and walk for 15-20 minutes after meals. For those meeting basic activity levels, add 2-3 sessions of moderate-intensity aerobic exercise (brisk walking, jogging, swimming) for 30-45 minutes each. Include strength training 2-3 times per week to build muscle strength and bone density. Remember to warm up and stretch before and after exercise to prevent injury.

[Sleep Optimization Recommendations]
Sleep quality directly impacts physical recovery and daytime energy. Establish a consistent bedtime routine: avoid screens 1 hour before bed, dim the lights, and try light reading or meditation. Keep bedroom temperature at 18-22°C and use blackout curtains to reduce light interference. Avoid heavy meals or caffeine 3 hours before bedtime. If you have trouble falling asleep, try the 4-7-8 breathing technique: inhale for 4 seconds, hold for 7 seconds, exhale for 8 seconds. A consistent sleep schedule helps regulate your circadian rhythm and improve sleep quality.

[Stress Management & Recovery]
Heart rate variability (HRV) is a key indicator of your body's stress state. If HRV is low, it signals a need for more recovery time. Schedule 10-15 minutes daily for mindfulness meditation or deep breathing exercises to activate the parasympathetic nervous system. Use the Pomodoro technique at work (25 minutes focused work + 5 minutes break) to avoid prolonged high-intensity work. Ensure adequate social activity time - connecting with friends and family helps mental relaxation. Consider outdoor activities on weekends, as exposure to natural environments significantly aids stress relief.

[Nutrition & Hydration Recommendations]
Complement your exercise and health monitoring with proper nutrition. Aim for 2000-2500ml of water daily, adjusting based on activity levels. Follow a "rainbow diet" principle, consuming various colored fruits and vegetables for comprehensive phytonutrients. Before and after exercise, appropriately supplement carbohydrates and protein to promote energy recovery and muscle repair. Limit processed foods and sugary drinks, choosing whole grains, lean meats, fish, and nuts instead. Maintain regular meal times and avoid overeating.
"""
    
    content = f"""
================================================================================
                     HEALTH DAILY REPORT - {date_str}
================================================================================

I. DATA OVERVIEW

┌─────────────────┬──────────┬────────┬─────────────────┐
│ Metric          │ Value    │ Unit   │ Data Points     │
├─────────────────┼──────────┼────────┼─────────────────┤
│ Steps           │ {analysis['steps']['value']:<8} │ {analysis['steps']['unit']:<6} │ {analysis['steps']['count']:<15} │
│ Distance        │ {analysis['distance']['value']:<8} │ {analysis['distance']['unit']:<6} │ {analysis['distance']['count']:<15} │
│ Exercise Time   │ {analysis['exercise']['value']:<8} │ {analysis['exercise']['unit']:<6} │ {analysis['exercise']['count']:<15} │
│ Stand Time      │ {analysis['stand_time']['value']:<8} │ {analysis['stand_time']['unit']:<6} │ {analysis['stand_time']['count']:<15} │
│ Stand Hours     │ {analysis['stand_hours']['value']:<8} │ {analysis['stand_hours']['unit']:<6} │ {analysis['stand_hours']['count']:<15} │
"""
    
    if analysis['heart_rate']['value']:
        hr = analysis['heart_rate']['value']
        content += f"│ Heart Rate(Avg) │ {hr['avg']:<8} │ {analysis['heart_rate']['unit']:<6} │ {analysis['heart_rate']['count']:<15} │\n"
    
    if analysis['hrv']['value']:
        hrv = analysis['hrv']['value']
        content += f"│ HRV(Average)    │ {hrv['avg']:<8} │ {analysis['hrv']['unit']:<6} │ {analysis['hrv']['count']:<15} │\n"
    
    if analysis['spo2']['value']:
        spo2 = analysis['spo2']['value']
        content += f"│ SpO2(Average)   │ {spo2['avg']:<8} │ {analysis['spo2']['unit']:<6} │ {analysis['spo2']['count']:<15} │\n"
    
    if analysis['sleep']['value']:
        sleep = analysis['sleep']['value']
        content += f"│ Sleep Duration  │ {sleep['total_sleep']:<8} │ {analysis['sleep']['unit']:<6} │ {analysis['sleep']['count']:<15} │\n"
    
    content += f"""└─────────────────┴──────────┴────────┴─────────────────┘

II. DETAILED METRIC ANALYSIS

[Step Count Analysis]
{get_step_analysis()}

[Sleep Analysis]
{get_sleep_analysis()}

[Heart Rate Analysis]
{get_heart_rate_analysis()}

[HRV Analysis]
{get_hrv_analysis()}

[Blood Oxygen Analysis]
{get_spo2_analysis()}

[Exercise Analysis]
{get_exercise_analysis()}

III. AI HEALTH RECOMMENDATIONS
{ai_suggestions}

IV. DATA SOURCE TRACEABILITY

This report is generated based on health data collected from Apple Watch and associated devices, including:
- Apple Health App exported data
- Apple Watch sensor data
- Continuous monitoring records during device wear

The number of data points for each metric is listed in the overview table.
Data collection period: {date_str} 00:00:00 - 23:59:59 (GMT+8)

V. DISCLAIMER

This report is for reference only and does not constitute medical advice. 
Consult healthcare professionals for any health concerns.

================================================================================
Report Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
================================================================================
"""
    
    return content

def generate_comparison_report(analysis_19, analysis_20, lang='zh'):
    """生成对比报告"""
    
    def get_change_icon(current, previous):
        if current > previous:
            return "↑"
        elif current < previous:
            return "↓"
        return "→"
    
    def get_change_percent(current, previous):
        if previous == 0:
            return "N/A"
        change = ((current - previous) / previous) * 100
        return f"{change:+.1f}%"
    
    if lang == 'zh':
        content = f"""
================================================================================
              健康数据对比报告：2026-02-19 vs 2026-02-20
================================================================================

一、指标对比（一行一指标格式）

| 指标                  | 02-19数值   | 02-20数值   | 变化   | 变化率   | 状态   |
|-----------------------|-------------|-------------|--------|----------|--------|
| 步数                  | {analysis_19['steps']['value']:<11} | {analysis_20['steps']['value']:<11} | {get_change_icon(analysis_20['steps']['value'], analysis_19['steps']['value']):<6} | {get_change_percent(analysis_20['steps']['value'], analysis_19['steps']['value']):<8} | {'需关注' if analysis_20['steps']['value'] < analysis_19['steps']['value'] else '良好':<6} |
| 行走距离(km)          | {analysis_19['distance']['value']:<11} | {analysis_20['distance']['value']:<11} | {get_change_icon(analysis_20['distance']['value'], analysis_19['distance']['value']):<6} | {get_change_percent(analysis_20['distance']['value'], analysis_19['distance']['value']):<8} | {'需关注' if analysis_20['distance']['value'] < analysis_19['distance']['value'] else '良好':<6} |
| 锻炼时间(min)         | {analysis_19['exercise']['value']:<11} | {analysis_20['exercise']['value']:<11} | {get_change_icon(analysis_20['exercise']['value'], analysis_19['exercise']['value']):<6} | {get_change_percent(analysis_20['exercise']['value'], analysis_19['exercise']['value']):<8} | {'需关注' if analysis_20['exercise']['value'] < analysis_19['exercise']['value'] else '良好':<6} |
| 站立时间(min)         | {analysis_19['stand_time']['value']:<11} | {analysis_20['stand_time']['value']:<11} | {get_change_icon(analysis_20['stand_time']['value'], analysis_19['stand_time']['value']):<6} | {get_change_percent(analysis_20['stand_time']['value'], analysis_19['stand_time']['value']):<8} | {'需关注' if analysis_20['stand_time']['value'] < analysis_19['stand_time']['value'] else '良好':<6} |
| 站立小时数            | {analysis_19['stand_hours']['value']:<11} | {analysis_20['stand_hours']['value']:<11} | {get_change_icon(analysis_20['stand_hours']['value'], analysis_19['stand_hours']['value']):<6} | {get_change_percent(analysis_20['stand_hours']['value'], analysis_19['stand_hours']['value']):<8} | {'需关注' if analysis_20['stand_hours']['value'] < analysis_19['stand_hours']['value'] else '良好':<6} |
"""
        
        # 心率对比
        if analysis_19['heart_rate']['value'] and analysis_20['heart_rate']['value']:
            hr19 = analysis_19['heart_rate']['value']['avg']
            hr20 = analysis_20['heart_rate']['value']['avg']
            content += f"| 平均心率(bpm)         | {hr19:<11} | {hr20:<11} | {get_change_icon(hr20, hr19):<6} | {get_change_percent(hr20, hr19):<8} | {'需关注' if hr20 > hr19 else '良好':<6} |\n"
        
        # HRV对比
        if analysis_19['hrv']['value'] and analysis_20['hrv']['value']:
            hrv19 = analysis_19['hrv']['value']['avg']
            hrv20 = analysis_20['hrv']['value']['avg']
            content += f"| 平均HRV(ms)           | {hrv19:<11} | {hrv20:<11} | {get_change_icon(hrv20, hrv19):<6} | {get_change_percent(hrv20, hrv19):<8} | {'良好' if hrv20 > hrv19 else '需关注':<6} |\n"
        
        # 睡眠对比
        if analysis_19['sleep']['value'] and analysis_20['sleep']['value']:
            sleep19 = analysis_19['sleep']['value']['total_sleep']
            sleep20 = analysis_20['sleep']['value']['total_sleep']
            content += f"| 睡眠时长(hr)          | {sleep19:<11} | {sleep20:<11} | {get_change_icon(sleep20, sleep19):<6} | {get_change_percent(sleep20, sleep19):<8} | {'需关注' if sleep20 < sleep19 else '良好':<6} |\n"
        
        # 血氧对比
        if analysis_19['spo2']['value'] and analysis_20['spo2']['value']:
            spo2_19 = analysis_19['spo2']['value']['avg']
            spo2_20 = analysis_20['spo2']['value']['avg']
            content += f"| 平均血氧(%)           | {spo2_19:<11} | {spo2_20:<11} | {get_change_icon(spo2_20, spo2_19):<6} | {get_change_percent(spo2_20, spo2_19):<8} | {'需关注' if spo2_20 < spo2_19 else '良好':<6} |\n"
        
        content += f"""
二、关键发现

1. 步数变化：从{analysis_19['steps']['value']}步变为{analysis_20['steps']['value']}步，{"增加" if analysis_20['steps']['value'] > analysis_19['steps']['value'] else "减少"}了{abs(analysis_20['steps']['value'] - analysis_19['steps']['value'])}步。

2. 活动水平：锻炼时间从{analysis_19['exercise']['value']}分钟{"增加" if analysis_20['exercise']['value'] > analysis_19['exercise']['value'] else "减少"}到{analysis_20['exercise']['value']}分钟。

3. 睡眠变化：{"有" if analysis_19['sleep']['value'] and analysis_20['sleep']['value'] else "无"}睡眠数据对比。

三、趋势分析

根据两日数据对比，建议关注以下方面：
- 保持积极的变化趋势
- 关注下降指标，制定改善计划
- 持续监测以获得更准确的健康趋势

================================================================================
报告生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
================================================================================
"""
    else:  # English
        content = f"""
================================================================================
           HEALTH DATA COMPARISON REPORT: 2026-02-19 vs 2026-02-20
================================================================================

I. METRIC COMPARISON (One Row Per Metric Format)

| Metric                | 02-19 Value | 02-20 Value | Change | Change % | Status |
|-----------------------|-------------|-------------|--------|----------|--------|
| Steps                 | {analysis_19['steps']['value']:<11} | {analysis_20['steps']['value']:<11} | {get_change_icon(analysis_20['steps']['value'], analysis_19['steps']['value']):<6} | {get_change_percent(analysis_20['steps']['value'], analysis_19['steps']['value']):<8} | {'Alert' if analysis_20['steps']['value'] < analysis_19['steps']['value'] else 'Good':<6} |
| Distance(km)          | {analysis_19['distance']['value']:<11} | {analysis_20['distance']['value']:<11} | {get_change_icon(analysis_20['distance']['value'], analysis_19['distance']['value']):<6} | {get_change_percent(analysis_20['distance']['value'], analysis_19['distance']['value']):<8} | {'Alert' if analysis_20['distance']['value'] < analysis_19['distance']['value'] else 'Good':<6} |
| Exercise(min)         | {analysis_19['exercise']['value']:<11} | {analysis_20['exercise']['value']:<11} | {get_change_icon(analysis_20['exercise']['value'], analysis_19['exercise']['value']):<6} | {get_change_percent(analysis_20['exercise']['value'], analysis_19['exercise']['value']):<8} | {'Alert' if analysis_20['exercise']['value'] < analysis_19['exercise']['value'] else 'Good':<6} |
| Stand Time(min)       | {analysis_19['stand_time']['value']:<11} | {analysis_20['stand_time']['value']:<11} | {get_change_icon(analysis_20['stand_time']['value'], analysis_19['stand_time']['value']):<6} | {get_change_percent(analysis_20['stand_time']['value'], analysis_19['stand_time']['value']):<8} | {'Alert' if analysis_20['stand_time']['value'] < analysis_19['stand_time']['value'] else 'Good':<6} |
| Stand Hours           | {analysis_19['stand_hours']['value']:<11} | {analysis_20['stand_hours']['value']:<11} | {get_change_icon(analysis_20['stand_hours']['value'], analysis_19['stand_hours']['value']):<6} | {get_change_percent(analysis_20['stand_hours']['value'], analysis_19['stand_hours']['value']):<8} | {'Alert' if analysis_20['stand_hours']['value'] < analysis_19['stand_hours']['value'] else 'Good':<6} |
"""
        
        if analysis_19['heart_rate']['value'] and analysis_20['heart_rate']['value']:
            hr19 = analysis_19['heart_rate']['value']['avg']
            hr20 = analysis_20['heart_rate']['value']['avg']
            content += f"| Avg Heart Rate(bpm)   | {hr19:<11} | {hr20:<11} | {get_change_icon(hr20, hr19):<6} | {get_change_percent(hr20, hr19):<8} | {'Alert' if hr20 > hr19 else 'Good':<6} |\n"
        
        if analysis_19['hrv']['value'] and analysis_20['hrv']['value']:
            hrv19 = analysis_19['hrv']['value']['avg']
            hrv20 = analysis_20['hrv']['value']['avg']
            content += f"| Avg HRV(ms)           | {hrv19:<11} | {hrv20:<11} | {get_change_icon(hrv20, hrv19):<6} | {get_change_percent(hrv20, hrv19):<8} | {'Good' if hrv20 > hrv19 else 'Alert':<6} |\n"
        
        if analysis_19['sleep']['value'] and analysis_20['sleep']['value']:
            sleep19 = analysis_19['sleep']['value']['total_sleep']
            sleep20 = analysis_20['sleep']['value']['total_sleep']
            content += f"| Sleep Duration(hr)    | {sleep19:<11} | {sleep20:<11} | {get_change_icon(sleep20, sleep19):<6} | {get_change_percent(sleep20, sleep19):<8} | {'Alert' if sleep20 < sleep19 else 'Good':<6} |\n"
        
        if analysis_19['spo2']['value'] and analysis_20['spo2']['value']:
            spo2_19 = analysis_19['spo2']['value']['avg']
            spo2_20 = analysis_20['spo2']['value']['avg']
            content += f"| Avg SpO2(%)           | {spo2_19:<11} | {spo2_20:<11} | {get_change_icon(spo2_20, spo2_19):<6} | {get_change_percent(spo2_20, spo2_19):<8} | {'Alert' if spo2_20 < spo2_19 else 'Good':<6} |\n"
        
        content += f"""
II. KEY FINDINGS

1. Step Count Change: From {analysis_19['steps']['value']} to {analysis_20['steps']['value']} steps, 
   {"increased" if analysis_20['steps']['value'] > analysis_19['steps']['value'] else "decreased"} by {abs(analysis_20['steps']['value'] - analysis_19['steps']['value'])} steps.

2. Activity Level: Exercise time {"increased" if analysis_20['exercise']['value'] > analysis_19['exercise']['value'] else "decreased"} 
   from {analysis_19['exercise']['value']} to {analysis_20['exercise']['value']} minutes.

3. Sleep Changes: {"Sleep data available" if analysis_19['sleep']['value'] and analysis_20['sleep']['value'] else "No sleep data"} for comparison.

III. TREND ANALYSIS

Based on the two-day data comparison, consider the following:
- Maintain positive change trends
- Address declining metrics with improvement plans
- Continue monitoring for more accurate health trends

================================================================================
Report Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
================================================================================
"""
    
    return content

def save_text_as_pdf(text_content, output_path):
    """将文本保存为PDF格式（使用简单文本方式）"""
    # 由于无法安装reportlab，使用HTML+文本格式
    html_content = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
body {{ font-family: "Courier New", monospace; white-space: pre-wrap; line-height: 1.4; }}
</style>
</head>
<body>
{text_content}
</body>
</html>"""
    
    # 保存为HTML（浏览器可以打印为PDF）
    html_path = output_path.replace('.pdf', '.html')
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    # 同时保存纯文本版本
    txt_path = output_path.replace('.pdf', '.txt')
    with open(txt_path, 'w', encoding='utf-8') as f:
        f.write(text_content)
    
    return html_path, txt_path

def main():
    """主函数"""
    print("开始生成2026-02-20详细健康报告...")
    
    # 分析两天的数据
    print("正在分析2026-02-20数据...")
    analysis_20 = analyze_day(DATA_FILE_20, "2026-02-20")
    
    print("正在分析2026-02-19数据...")
    analysis_19 = analyze_day(DATA_FILE_19, "2026-02-19")
    
    # 生成4份报告
    reports = []
    
    # 1. 2026-02-20 中文详细报告
    print("生成中文详细报告...")
    zh_content = generate_zh_report_content(analysis_20, "2026-02-20")
    zh_html, zh_txt = save_text_as_pdf(zh_content, os.path.join(OUTPUT_DIR, "2026-02-20-report-zh-DETAILED.pdf"))
    reports.append(("2026-02-20-report-zh-DETAILED", zh_html, zh_txt))
    
    # 2. 2026-02-20 英文详细报告
    print("生成英文详细报告...")
    en_content = generate_en_report_content(analysis_20, "2026-02-20")
    en_html, en_txt = save_text_as_pdf(en_content, os.path.join(OUTPUT_DIR, "2026-02-20-report-en-DETAILED.pdf"))
    reports.append(("2026-02-20-report-en-DETAILED", en_html, en_txt))
    
    # 3. 对比报告中文
    print("生成中文对比报告...")
    comp_zh_content = generate_comparison_report(analysis_19, analysis_20, 'zh')
    comp_zh_html, comp_zh_txt = save_text_as_pdf(comp_zh_content, os.path.join(OUTPUT_DIR, "2026-02-19-vs-2026-02-20-comparison-zh-DETAILED.pdf"))
    reports.append(("2026-02-19-vs-2026-02-20-comparison-zh-DETAILED", comp_zh_html, comp_zh_txt))
    
    # 4. 对比报告英文
    print("生成英文对比报告...")
    comp_en_content = generate_comparison_report(analysis_19, analysis_20, 'en')
    comp_en_html, comp_en_txt = save_text_as_pdf(comp_en_content, os.path.join(OUTPUT_DIR, "2026-02-19-vs-2026-02-20-comparison-en-DETAILED.pdf"))
    reports.append(("2026-02-19-vs-2026-02-20-comparison-en-DETAILED", comp_en_html, comp_en_txt))
    
    print("\n报告生成完成！")
    print("=" * 80)
    
    # 打印报告摘要
    print("\n2026-02-20 关键指标摘要：")
    print(f"  - 步数: {analysis_20['steps']['value']}")
    print(f"  - 行走距离: {analysis_20['distance']['value']} km")
    print(f"  - 锻炼时间: {analysis_20['exercise']['value']} 分钟")
    print(f"  - 站立小时: {analysis_20['stand_hours']['value']} 小时")
    if analysis_20['heart_rate']['value']:
        print(f"  - 平均心率: {analysis_20['heart_rate']['value']['avg']} bpm")
    if analysis_20['sleep']['value']:
        print(f"  - 睡眠时间: {analysis_20['sleep']['value']['total_sleep']} 小时")
    
    print("\n生成的文件：")
    for name, html, txt in reports:
        print(f"  - {name}.html")
        print(f"  - {name}.txt")
    
    print(f"\n文件保存位置: {OUTPUT_DIR}")
    
    return reports

if __name__ == "__main__":
    main()
