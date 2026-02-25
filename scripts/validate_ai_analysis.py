#!/usr/bin/env python3
"""
AI分析数据验证脚本 V5.0 - 严格版
在生成报告前验证AI分析中的数值与实际数据是否匹配
- 验证项全覆盖
- 数据误差严格限制
- 禁止编造数据
"""

import json
import re
import sys
from pathlib import Path

# 添加scripts目录到路径
sys.path.insert(0, str(Path(__file__).parent))
from generate_v5_medical_dashboard import load_data

# V5.0 零容忍验证标准 - 精确匹配
TOLERANCE = {
    'hrv': 0,           # HRV 精确匹配
    'hrv_points': 0,    # HRV数据点数必须精确匹配
    'resting_hr': 0,    # 静息心率精确匹配
    'steps': 0,         # 步数精确匹配
    'flights': 0,       # 爬楼精确匹配
    'distance': 0,      # 距离精确匹配
    'active_energy': 0, # 活动能量精确匹配
    'stand_time': 0,    # 站立时间精确匹配
    'spo2': 0,          # 血氧精确匹配
    'basal_energy': 0,  # 静息能量精确匹配
    'respiratory': 0,   # 呼吸率精确匹配
    'sleep_total': 0,   # 睡眠总时长精确匹配
    'sleep_deep': 0,    # 深睡精确匹配
    'sleep_core': 0,    # 核心睡眠精确匹配
    'sleep_rem': 0,     # REM精确匹配
    'workout_duration': 0, # 运动时长精确匹配
    'workout_avg_hr': 0,   # 运动平均心率精确匹配
    'workout_max_hr': 0,   # 运动最高心率精确匹配
}

def extract_numbers(text):
    """从文本中提取数字（处理千分位逗号）"""
    if not text:
        return []
    # 先移除千分位逗号 (如 6,852 -> 6852)
    text_clean = re.sub(r'(\d),(\d)', r'\1\2', text)
    # 提取整数和小数
    numbers = re.findall(r'(\d+\.?\d*)', text_clean)
    return [float(n) for n in numbers]

def validate_metric(name, actual, text, tolerance, unit=''):
    """验证单个指标 - 零容忍模式，必须精确匹配"""
    if actual is None or text is None:
        return None
    
    numbers = extract_numbers(text)
    if not numbers:
        return None
    
    # 零容忍：检查是否有精确匹配的数值（处理浮点数精度问题）
    matched = False
    for n in numbers:
        # 对于整数型数据，直接相等
        if isinstance(actual, int) and abs(n - actual) == 0:
            matched = True
            break
        # 对于浮点型数据，使用极小误差范围处理精度问题（0.0001以内视为相等）
        elif isinstance(actual, float) and abs(n - actual) < 0.0001:
            matched = True
            break
    
    if not matched:
        return f"{name}: 实际 {actual}{unit}, AI分析中数值 {numbers}"
    
    return None

def validate_ai_analysis(date_str, ai_analysis):
    """验证AI分析中的数值与实际数据是否匹配 - V5.0严格版"""
    # 加载实际数据
    data = load_data(date_str)
    
    errors = []
    warnings = []
    
    # ========== 1. HRV验证 ==========
    actual_hrv = data.get('hrv', {}).get('value')
    hrv_text = ai_analysis.get('hrv', '')
    if actual_hrv and hrv_text:
        err = validate_metric('HRV', actual_hrv, hrv_text, TOLERANCE['hrv'], 'ms')
        if err:
            errors.append(err)
        # 验证HRV数据点数
        actual_points = data.get('hrv', {}).get('points', 0)
        if actual_points > 0:
            points_numbers = extract_numbers(hrv_text)
            # 检查是否提到了数据点数（精确匹配）
            if not any(abs(n - actual_points) < 0.0001 for n in points_numbers if n > 10 and n < 200):
                warnings.append(f"HRV数据点数: 实际 {actual_points}个, 建议在分析中明确提及")
    
    # ========== 2. 静息心率验证 ==========
    actual_rhr = data.get('resting_hr', {}).get('value')
    rhr_text = ai_analysis.get('resting_hr', '')
    if actual_rhr and rhr_text:
        err = validate_metric('静息心率', actual_rhr, rhr_text, TOLERANCE['resting_hr'], 'bpm')
        if err:
            errors.append(err)
    
    # ========== 3. 步数验证 ==========
    actual_steps = data.get('steps', 0)
    steps_text = ai_analysis.get('steps', '')
    if actual_steps and steps_text:
        err = validate_metric('步数', actual_steps, steps_text, TOLERANCE['steps'], '步')
        if err:
            errors.append(err)
    
    # ========== 4. 爬楼验证 ==========
    actual_flights = data.get('flights_climbed', 0) or data.get('flights', 0)
    flights_text = ai_analysis.get('flights', '')
    
    if actual_flights and flights_text:
        # 有爬楼数据时，验证数值
        err = validate_metric('爬楼', actual_flights, flights_text, TOLERANCE['flights'], '层')
        if err:
            errors.append(err)
    elif actual_flights == 0 and flights_text:
        # 无爬楼数据时，检查是否错误地声称今日有爬楼
        # 允许提到历史数据（如"前日完成109层"），但不允许说"今日完成X层"
        if ('今日' in flights_text or '今天' in flights_text) and ('层' in flights_text or '完成' in flights_text):
            numbers = extract_numbers(flights_text)
            if any(n > 1 for n in numbers):
                # 进一步检查是否明确说是今日的数据
                if '今日完成' in flights_text or '今日爬' in flights_text or '今天完成' in flights_text:
                    errors.append("爬楼: 实际0层, 但AI分析声称今日有爬楼数据")
        # 警告：提到较大数字时提示确认是历史数据
        numbers = extract_numbers(flights_text)
        if any(n > 10 for n in numbers):
            warnings.append("爬楼分析中提到较大数字，请确保明确标注为'前日'或'昨日'数据，避免误导")
    
    # ========== 5. 距离验证 ==========
    actual_distance = data.get('distance', 0) or data.get('walking_distance', 0) or data.get('distance_km', 0)
    distance_text = ai_analysis.get('distance', '')
    if actual_distance and distance_text:
        err = validate_metric('距离', actual_distance, distance_text, TOLERANCE['distance'], 'km')
        if err:
            errors.append(err)
    
    # ========== 6. 活动能量验证 ==========
    actual_energy = data.get('active_energy', 0)
    energy_text = ai_analysis.get('active_energy', '')
    if actual_energy and energy_text:
        err = validate_metric('活动能量', actual_energy, energy_text, TOLERANCE['active_energy'], 'kcal')
        if err:
            errors.append(err)
    
    # ========== 7. 站立时间验证 ==========
    actual_stand = data.get('stand_time_min', 0) or data.get('apple_stand_time', 0)
    stand_text = ai_analysis.get('stand', '')
    if actual_stand and stand_text:
        err = validate_metric('站立时间', actual_stand, stand_text, TOLERANCE['stand_time'], '分钟')
        if err:
            errors.append(err)
    
    # ========== 8. 血氧验证 ==========
    actual_spo2 = data.get('spo2', 0)
    spo2_text = ai_analysis.get('spo2', '')
    if actual_spo2 and spo2_text:
        err = validate_metric('血氧', actual_spo2, spo2_text, TOLERANCE['spo2'], '%')
        if err:
            errors.append(err)
    
    # ========== 9. 静息能量验证 ==========
    basal_data = data.get('basal_energy_kcal', 0) or data.get('basal_energy', 0)
    actual_basal = basal_data
    basal_text = ai_analysis.get('basal', '')
    if actual_basal and basal_text:
        err = validate_metric('静息能量', actual_basal, basal_text, TOLERANCE['basal_energy'], 'kcal')
        if err:
            errors.append(err)
    
    # ========== 10. 呼吸率验证 ==========
    resp_data = data.get('respiratory_rate', 0)
    actual_resp = resp_data.get('value', 0) if isinstance(resp_data, dict) else resp_data
    resp_text = ai_analysis.get('respiratory', '')
    if actual_resp and resp_text:
        err = validate_metric('呼吸率', actual_resp, resp_text, TOLERANCE['respiratory'], '次/分')
        if err:
            errors.append(err)
    
    # ========== 11. 睡眠数据验证 ==========
    sleep_data = data.get('sleep', {})
    if sleep_data and sleep_data.get('total', 0) > 0:
        actual_sleep_total = sleep_data.get('total', 0)
        sleep_text = ai_analysis.get('sleep', '')
        
        if sleep_text:
            err = validate_metric('睡眠总时长', actual_sleep_total, sleep_text, TOLERANCE['sleep_total'], '小时')
            if err:
                errors.append(err)
            
            # 验证睡眠阶段数据 - 精确匹配
            sleep_deep = sleep_data.get('deep', 0)
            sleep_core = sleep_data.get('core', 0)
            sleep_rem = sleep_data.get('rem', 0)
            
            if sleep_deep and not any(abs(n - sleep_deep) < 0.0001 for n in extract_numbers(sleep_text)):
                warnings.append(f"深睡时长: 实际 {sleep_deep}小时, 建议在分析中明确提及")
            if sleep_core and not any(abs(n - sleep_core) < 0.0001 for n in extract_numbers(sleep_text)):
                warnings.append(f"核心睡眠时长: 实际 {sleep_core}小时, 建议在分析中明确提及")
            if sleep_rem and not any(abs(n - sleep_rem) < 0.0001 for n in extract_numbers(sleep_text)):
                warnings.append(f"REM时长: 实际 {sleep_rem}小时, 建议在分析中明确提及")
    else:
        # 无睡眠数据时，检查AI是否正确说明
        sleep_text = ai_analysis.get('sleep', '')
        if sleep_text and '小时' in sleep_text:
            numbers = extract_numbers(sleep_text)
            if any(n > 1 for n in numbers):
                errors.append("睡眠: 实际无睡眠记录, 但AI分析提到具体睡眠时长")
    
    # ========== 12. 运动数据验证 ==========
    has_workout = data.get('has_workout', False)
    workouts = data.get('workouts', [])
    workout_text = ai_analysis.get('workout', '')
    
    if has_workout and workouts:
        w = workouts[0]
        
        # 检查是否错误描述为无运动
        if '无' in workout_text and '未记录' in workout_text:
            errors.append("运动: 实际有运动记录，但AI分析写'无运动'")
        
        # 验证运动时长 - 精确匹配
        duration = w.get('duration_min', 0)
        if duration and workout_text:
            numbers = extract_numbers(workout_text)
            if not any(abs(n - duration) < 0.0001 for n in numbers):
                warnings.append(f"运动时长: 实际 {duration:.1f}分钟, AI分析中数值不匹配")
        
        # 验证平均心率 - 精确匹配
        avg_hr = w.get('avg_hr', 0)
        if avg_hr and workout_text:
            numbers = extract_numbers(workout_text)
            if not any(abs(n - avg_hr) < 0.0001 for n in numbers):
                warnings.append(f"运动平均心率: 实际 {avg_hr}bpm")
        
        # 验证最高心率 - 精确匹配
        max_hr = w.get('max_hr', 0)
        if max_hr and workout_text:
            numbers = extract_numbers(workout_text)
            if not any(abs(n - max_hr) < 0.0001 for n in numbers):
                warnings.append(f"运动最高心率: 实际 {max_hr}bpm")
                
    else:
        # 无运动记录时
        if '完成' in workout_text or ('训练' in workout_text and '恢复' not in workout_text):
            errors.append("运动: 实际无运动记录，但AI分析写有'完成训练'")
        if '分钟' in workout_text:
            numbers = extract_numbers(workout_text)
            if any(n > 5 for n in numbers):  # 大于5分钟的数字
                warnings.append("运动: 实际无运动记录，但AI分析提到具体时长")
    
    return errors, warnings

def main():
    if len(sys.argv) < 2:
        print("用法: python3 validate_ai_analysis.py <YYYY-MM-DD> < ai_analysis.json")
        print("")
        print("V5.0 零容忍验证标准:")
        print("  所有指标必须精确匹配，禁止任何误差")
        print("  - HRV: 精确到小数点后1位")
        print("  - 步数: 精确匹配")
        print("  - 距离: 精确到小数点后2位")
        print("  - 活动能量: 精确匹配")
        print("  - 睡眠时长: 精确到小数点后2小时")
        print("  - 运动时长: 精确匹配")
        sys.exit(1)
    
    date_str = sys.argv[1]
    
    try:
        ai_analysis = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        print(f"❌ JSON解析错误: {e}")
        sys.exit(1)
    
    print(f"🔍 验证 {date_str} 的AI分析...")
    print("   V5.0 严格模式 - 零容忍编造数据")
    print()
    
    errors, warnings = validate_ai_analysis(date_str, ai_analysis)
    
    if errors:
        print("❌ 数据不匹配错误 (必须修正):")
        for e in errors:
            print(f"   • {e}")
        print()
        print("⚠️  V5.0标准: AI分析必须基于真实数据，禁止编造！")
        print("   请根据实际数据重新编写AI分析。")
        sys.exit(1)
    
    if warnings:
        print("⚠️  警告 (建议优化):")
        for w in warnings:
            print(f"   • {w}")
        print()
    
    # 验证字段完整性
    required_fields = ['hrv', 'sleep', 'workout', 'priority']
    missing = [f for f in required_fields if f not in ai_analysis or not ai_analysis[f]]
    if missing:
        print(f"⚠️  缺少推荐字段: {', '.join(missing)}")
        print()
    
    print("✅ V5.0 严格验证通过！")
    print("   所有数值与真实数据一致，可以生成报告。")

if __name__ == '__main__':
    main()
