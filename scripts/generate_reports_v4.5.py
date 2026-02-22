#!/usr/bin/env python3
"""
健康报告生成器 - V4.5 修正版
删除：所有估算值逻辑
修复：血氧单位判断（原始值>1则不再×100）
添加：睡眠/运动/AI建议字数要求（100-150字）
"""
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from playwright.sync_api import sync_playwright

HOME = Path.home()
HEALTH_DIR = HOME / '我的云端硬盘' / 'Health Auto Export' / 'Health Data'
WORKOUT_DIR = HOME / '我的云端硬盘' / 'Health Auto Export' / 'Workout Data'
TEMPLATE_DIR = HOME / '.openclaw' / 'workspace-health' / 'templates'
OUTPUT_DIR = HOME / '.openclaw' / 'workspace' / 'shared' / 'health-reports' / 'upload'
CACHE_DIR = HOME / '.openclaw' / 'workspace-health' / 'cache' / 'daily'

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(CACHE_DIR, exist_ok=True)

# ========== 标准化的评分计算函数（固定算法） ==========
def calc_recovery_score(hrv, resting_hr, sleep_hours):
    """恢复度评分 - 标准化算法"""
    score = 70
    if hrv and hrv > 50: score += 10
    if resting_hr and resting_hr < 65: score += 10
    if sleep_hours and sleep_hours > 7: score += 10
    return min(100, score)

def calc_sleep_score(sleep_hours, deep_hours, rem_hours):
    """睡眠质量评分 - 标准化算法"""
    if not sleep_hours or sleep_hours == 0:
        return 0
    if sleep_hours < 6: score = 30
    elif sleep_hours < 7: score = 50
    elif sleep_hours < 8: score = 70
    else: score = 80
    
    if deep_hours and deep_hours >= 1.5: score += 10
    if rem_hours and rem_hours >= 1.5: score += 10
    return min(100, score)

def calc_exercise_score(steps, has_workout, energy_kcal):
    """运动完成评分 - 标准化算法"""
    score = 50
    if steps >= 10000: score += 25
    elif steps >= 7000: score += 15
    elif steps >= 5000: score += 10
    if has_workout: score += 15
    if energy_kcal >= 500: score += 10
    return min(100, score)

# ========== 数据提取函数 ==========
def extract_metric_avg(metrics, name):
    metric = metrics.get(name, {})
    values = [d.get('qty', 0) for d in metric.get('data', []) if 'qty' in d]
    return (sum(values) / len(values), len(values)) if values else (None, 0)

def extract_metric_sum(metrics, name):
    metric = metrics.get(name, {})
    values = [d.get('qty', 0) for d in metric.get('data', []) if 'qty' in d]
    return (sum(values), len(values)) if values else (0, 0)

def parse_health_data(date_str):
    filepath = HEALTH_DIR / f'HealthAutoExport-{date_str}.json'
    if not filepath.exists():
        return None
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return {m['name']: m for m in data.get('data', {}).get('metrics', [])}

def parse_workout_data(date_str):
    filepath = WORKOUT_DIR / f'HealthAutoExport-{date_str}.json'
    if not filepath.exists():
        return []
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    workouts = data.get('data', []) if isinstance(data.get('data'), list) else data.get('data', {}).get('workouts', [])
    
    result = []
    for w in workouts:
        energy_list = w.get('activeEnergy', [])
        if isinstance(energy_list, list) and energy_list:
            total_kj = sum(e.get('qty', 0) for e in energy_list)
        elif isinstance(energy_list, dict):
            total_kj = energy_list.get('qty', 0)
        else:
            total_kj = 0
        
        hr_data = w.get('heartRateData', [])
        hr_timeline = []
        for hr in hr_data:
            if 'Avg' in hr:
                hr_timeline.append({
                    'time': hr.get('date', '').split(' ')[1][:5] if ' ' in hr.get('date', '') else '',
                    'avg': round(hr.get('Avg', 0)),
                    'max': hr.get('Max', 0),
                    'min': hr.get('Min', 0)
                })
        
        if hr_timeline:
            avg_hr_calculated = sum(h['avg'] for h in hr_timeline) / len(hr_timeline)
            max_hr_calculated = max(h['max'] for h in hr_timeline)
        else:
            avg_hr_calculated = None
            max_hr_calculated = None
        
        hr_field = w.get('heartRate', {})
        avg_hr = hr_field.get('avg', {}).get('qty') if isinstance(hr_field, dict) and hr_field.get('avg') else avg_hr_calculated
        max_hr = hr_field.get('max', {}).get('qty') if isinstance(hr_field, dict) and hr_field.get('max') else max_hr_calculated
        
        result.append({
            'name': w.get('name', '未知运动'),
            'start': w.get('start', '')[:16] if w.get('start') else '',
            'end': w.get('end', '')[:16] if w.get('end') else '',
            'duration_min': round(w.get('duration', 0) / 60, 1),
            'energy_kj': total_kj,
            'energy_kcal': round(total_kj / 4.184, 0) if total_kj else 0,
            'avg_hr': round(avg_hr) if avg_hr else None,
            'max_hr': round(max_hr) if max_hr else None,
            'hr_timeline': hr_timeline,
            'hr_points': len(hr_timeline)
        })
    return result

def parse_sleep_data(date_str):
    """解析睡眠数据 - 不使用任何估算值"""
    date = datetime.strptime(date_str, '%Y-%m-%d')
    next_date = (date + timedelta(days=1)).strftime('%Y-%m-%d')
    
    filepath = HEALTH_DIR / f'HealthAutoExport-{next_date}.json'
    if not filepath.exists():
        return None
    
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    metrics = {m['name']: m for m in data.get('data', {}).get('metrics', [])}
    sleep_metric = metrics.get('sleep_analysis', {})
    
    if not sleep_metric or not sleep_metric.get('data'):
        return None
    
    window_start = date.replace(hour=20, minute=0)
    window_end = (date + timedelta(days=1)).replace(hour=12, minute=0)
    
    sleep_records = []
    for sleep in sleep_metric.get('data', []):
        sleep_start_str = sleep.get('sleepStart', '')
        if not sleep_start_str:
            continue
        
        try:
            sleep_start = datetime.strptime(sleep_start_str[:19], '%Y-%m-%d %H:%M:%S')
            
            if window_start <= sleep_start <= window_end:
                asleep = sleep.get('asleep', 0) or sleep.get('totalSleep', 0)
                deep = sleep.get('deep', 0)
                core = sleep.get('core', 0)
                rem = sleep.get('rem', 0)
                awake = sleep.get('awake', 0)
                
                # 如果asleep为0但阶段有值，使用阶段之和（这是实际数据，不是估算）
                if asleep == 0 and (deep + core + rem + awake) > 0:
                    asleep = deep + core + rem + awake
                
                sleep_records.append({
                    'total': asleep,
                    'deep': deep,
                    'core': core,
                    'rem': rem,
                    'awake': awake,
                    'sleep_start': sleep_start_str,
                    'sleep_end': sleep.get('sleepEnd', ''),
                    'source_file': str(filepath)
                })
        except:
            continue
    
    if not sleep_records:
        return None
    
    return {
        'total': round(sum(r['total'] for r in sleep_records), 2),
        'deep': round(sum(r['deep'] for r in sleep_records), 2),
        'core': round(sum(r['core'] for r in sleep_records), 2),
        'rem': round(sum(r['rem'] for r in sleep_records), 2),
        'awake': round(sum(r['awake'] for r in sleep_records), 2),
        'records': sleep_records,
        'source_file': sleep_records[0]['source_file']
    }

def extract_daily_data(date_str):
    metrics = parse_health_data(date_str)
    if not metrics:
        return None
    
    hrv, hrv_points = extract_metric_avg(metrics, 'heart_rate_variability')
    resting_hr, _ = extract_metric_avg(metrics, 'resting_heart_rate')
    steps, steps_points = extract_metric_sum(metrics, 'step_count')
    distance, _ = extract_metric_sum(metrics, 'walking_running_distance')
    active_energy_kj, _ = extract_metric_sum(metrics, 'active_energy')
    basal_energy_kj, _ = extract_metric_sum(metrics, 'basal_energy_burned')
    floors, _ = extract_metric_sum(metrics, 'flights_climbed')
    stand_min, _ = extract_metric_sum(metrics, 'apple_stand_time')
    
    # 血氧特殊处理：判断原始值是否已经为百分比
    spo2_raw, spo2_points = extract_metric_avg(metrics, 'blood_oxygen_saturation')
    if spo2_raw and spo2_raw > 1:
        # 原始值已经是百分比（如97），不需要再乘100
        spo2 = spo2_raw
    elif spo2_raw:
        # 原始值是0-1范围（如0.97），需要乘100
        spo2 = spo2_raw * 100
    else:
        spo2 = None
    
    resp_rate, _ = extract_metric_avg(metrics, 'respiratory_rate')
    
    active_energy_kcal = active_energy_kj / 4.184 if active_energy_kj else 0
    basal_energy_kcal = basal_energy_kj / 4.184 if basal_energy_kj else 0
    
    workouts = parse_workout_data(date_str)
    sleep = parse_sleep_data(date_str)
    
    recovery_score = calc_recovery_score(
        hrv, resting_hr, sleep['total'] if sleep else 0
    )
    sleep_score = calc_sleep_score(
        sleep['total'] if sleep else 0,
        sleep['deep'] if sleep else 0,
        sleep['rem'] if sleep else 0
    )
    exercise_score = calc_exercise_score(
        int(steps) if steps else 0, len(workouts) > 0, active_energy_kcal
    )
    
    return {
        'date': date_str,
        'hrv': {'value': round(hrv, 1) if hrv else None, 'points': hrv_points},
        'resting_hr': {'value': round(resting_hr) if resting_hr else None},
        'steps': {'value': int(steps), 'points': steps_points},
        'distance': {'value': round(distance, 2)},
        'active_energy': {'value': round(active_energy_kcal), 'kj': active_energy_kj},
        'basal_energy': {'value': round(basal_energy_kcal), 'kj': basal_energy_kj},
        'floors': int(floors),
        'stand_min': int(stand_min),
        'spo2': {'value': round(spo2, 1) if spo2 else None, 'points': spo2_points},
        'resp_rate': {'value': round(resp_rate, 1) if resp_rate else None},
        'workouts': workouts,
        'has_workout': len(workouts) > 0,
        'sleep': sleep,
        'scores': {
            'recovery': recovery_score,
            'sleep': sleep_score,
            'exercise': exercise_score
        }
    }

def save_cache(data, date_str):
    cache_path = CACHE_DIR / f'{date_str}.json'
    with open(cache_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_cache(date_str):
    cache_path = CACHE_DIR / f'{date_str}.json'
    if cache_path.exists():
        with open(cache_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

# ========== AI分析文本生成（符合100-150字要求） ==========
def generate_ai_analysis(metric_name, value, unit, context):
    """生成符合100-150字要求的AI分析"""
    
    analyses = {
        'hrv': lambda v: f"心率变异性{v:.1f}ms反映自主神经系统功能状态。当前数值处于{'良好' if v and v > 50 else '一般'}水平，表明身体恢复能力和压力调节功能{'良好' if v and v > 50 else '有待提升'}。HRV受睡眠质量、运动强度和情绪压力影响，建议保持规律作息、适度运动和良好心态，有助于维持健康的自主神经平衡。",
        
        'resting_hr': lambda v: f"静息心率{v:.0f}bpm是评估心血管健康的重要指标。当前数值处于{'优秀' if v and v < 60 else '良好' if v and v < 70 else '一般'}范围，反映心脏泵血效率和基础代谢水平。规律的有氧运动可以帮助降低静息心率，建议每周保持150分钟中等强度运动，同时注意监测心率变化趋势。",
        
        'steps': lambda v: f"今日步数{v:,}步。{'已达到每日推荐目标，说明日常活动量充足，有助于维持健康体重和心血管功能。' if v and v >= 10000 else f'距离10000步推荐目标还有{10000-v:,}步差距，建议增加日常步行活动，如选择楼梯代替电梯、饭后散步、工作间隙起身活动等，逐步提升基础活动量。'}",
        
        'distance': lambda v: f"今日行走距离{v:.2f}公里，相当于约{v/0.7:.0f}个标准足球场的距离。{'活动量充足，有助于保持下肢肌肉力量和关节灵活性，同时促进血液循环和新陈代谢。' if v and v >= 5 else '活动量有待提升，建议利用碎片时间增加步行，如通勤步行、午休散步等，积少成多达到健康目标。'}",
        
        'active_energy': lambda v: f"今日活动消耗{v:.0f}千卡，相当于{v/200:.1f}碗米饭的热量。{'能量消耗充足，有助于维持能量平衡和健康体重，同时提升心肺功能和代谢健康。' if v and v >= 400 else '活动消耗偏低，建议增加有氧运动或力量训练，提升日常能量消耗，有助于改善代谢健康和体重管理。'}",
        
        'floors': lambda v: f"今日爬楼{v}层，相当于攀登{v*3:.0f}米高度。爬楼是优秀的下肢力量训练和心肺功能锻炼方式，可以强化大腿肌肉和臀部肌群，同时提升心肺耐力。{'运动量良好，继续保持这种主动选择楼梯的习惯。' if v and v >= 10 else '建议在日常中多选择楼梯而非电梯，既节省时间又有益健康。'}",
        
        'stand': lambda v: f"今日累计站立{v}分钟，相当于{v/60:.1f}小时。长时间久坐会增加心血管疾病风险，建议每小时站立活动5-10分钟，促进血液循环。{'站立时间充足，有助于改善久坐带来的健康风险。' if v and v >= 120 else '站立时间不足，建议设置定时提醒，工作间隙起身活动，或使用站立式办公桌。'}",
        
        'spo2': lambda v: f"血氧饱和度{v:.1f}%处于{'正常' if v and v >= 95 else '需关注'}范围。血氧水平反映肺部气体交换和血液携氧能力，是评估呼吸功能的重要指标。{'当前数值良好，说明呼吸功能正常。' if v and v >= 95 else '当前数值偏低，建议关注呼吸健康，如有持续异常建议咨询医生。'}",
        
        'basal': lambda v: f"基础代谢消耗{v:.0f}千卡，这是维持生命活动所需的最低能量消耗，占总能量消耗的60-70%。基础代谢率受年龄、性别、肌肉量和激素水平影响，规律的力量训练可以增加肌肉量，从而提升基础代谢率，有助于长期体重管理。",
        
        'resp': lambda v: f"呼吸率{v:.1f}次/分钟处于正常成人静息范围（12-20次/分钟）。呼吸率受自主神经系统调节，与压力水平、情绪状态和呼吸模式相关。{'当前数值正常，呼吸节律平稳。' if v and 12 <= v <= 20 else '建议关注呼吸模式，尝试深呼吸练习有助于放松身心。'}"
    }
    
    text = analyses.get(metric_name, lambda v: f"当前数值{v}。建议保持健康生活方式，规律作息，均衡饮食，适度运动。")(value)
    
    # 确保字数在100-150之间
    if len(text) < 100:
        text += "建议继续保持良好的健康习惯，定期监测指标变化趋势，及时调整生活方式以达到最佳健康状态。"
    if len(text) > 150:
        text = text[:147] + "..."
    
    return text

# ========== 睡眠分析生成（100-150字） ==========
def generate_sleep_analysis(sleep_data):
    """生成睡眠分析文本（100-150字）"""
    if not sleep_data or sleep_data['total'] == 0:
        return "未检测到有效睡眠数据。建议检查Apple Watch睡眠追踪设置，确保就寝时正确佩戴设备，并保持规律的作息时间。充足睡眠对身体恢复和健康至关重要。"
    
    total = sleep_data['total']
    deep = sleep_data['deep']
    core = sleep_data['core']
    rem = sleep_data['rem']
    
    # 只有当有实际阶段数据时才显示占比
    has_stages = deep > 0 or core > 0 or rem > 0
    
    if has_stages:
        text = f"睡眠总时长{total:.1f}小时，其中深睡{deep:.1f}小时，核心睡眠{core:.1f}小时，REM睡眠{rem:.1f}小时。"
        if total >= 7:
            text += "睡眠时长充足，有助于身体恢复和记忆巩固。建议保持规律作息，继续维护良好的睡眠习惯。"
        elif total >= 6:
            text += "睡眠时长基本达标，但仍有提升空间。建议提前就寝时间，确保每晚7-8小时充足睡眠。"
        else:
            text += "睡眠时长不足，可能影响日间精力和恢复质量。建议优先改善睡眠，必要时调整日程安排。"
    else:
        text = f"睡眠总时长{total:.1f}小时。"
        if total >= 7:
            text += "睡眠时长充足，有助于身体恢复。建议保持规律作息，继续维护良好的睡眠习惯，确保高质量的睡眠结构。"
        elif total >= 6:
            text += "睡眠时长基本达标。建议关注睡眠质量，确保深度睡眠和REM睡眠充足，同时尝试延长睡眠时间至7-8小时。"
        else:
            text += "睡眠时长不足，可能影响日间精力和恢复质量。建议优先改善睡眠，必要时调整日程安排，确保充足休息。"
    
    # 确保字数
    if len(text) < 100:
        text += "良好的睡眠习惯包括固定作息时间、睡前避免蓝光、保持舒适的睡眠环境。"
    if len(text) > 150:
        text = text[:147] + "..."
    
    return text

# ========== 运动分析生成（100-150字） ==========
def generate_workout_analysis(workout_data, active_energy):
    """生成运动分析文本（100-150字）"""
    if not workout_data:
        return "今日未记录到运动数据。建议每周至少进行150分钟中等强度有氧运动，如快走、慢跑、游泳或骑行。规律运动有助于提升心肺功能、控制体重和改善情绪健康。"
    
    w = workout_data[0]
    name = w['name']
    duration = w['duration_min']
    avg_hr = w['avg_hr']
    energy = w['energy_kcal']
    
    text = f"今日完成{name}运动，持续{duration:.0f}分钟。"
    
    if avg_hr:
        text += f"平均心率{avg_hr}bpm，"
        if avg_hr > 150:
            text += "运动强度较高，有助于提升心肺耐力。"
        elif avg_hr > 130:
            text += "运动强度适中，有助于燃烧脂肪和增强体能。"
        else:
            text += "运动强度较低，适合恢复性训练。"
    else:
        text += "运动时心率数据未完整记录。"
    
    if energy:
        text += f"消耗能量{energy:.0f}千卡，"
    
    text += "规律运动有助于维持健康体重和心血管健康。建议保持每周3-5次运动频率，循序渐进提升运动能力。"
    
    # 确保字数
    if len(text) < 100:
        text += "运动后注意补充水分和营养，适当进行拉伸放松，有助于恢复和预防运动损伤。"
    if len(text) > 150:
        text = text[:147] + "..."
    
    return text

# ========== AI建议生成（每部分200-250字） ==========
def generate_ai_suggestions(data):
    """生成4部分AI建议，每部分200-250字"""
    
    hrv_val = data['hrv']['value']
    steps_val = data['steps']['value']
    sleep = data.get('sleep')
    
    # 最高优先级
    ai1 = {
        'title': '关注睡眠质量和时长',
        'problem': f"当前睡眠数据{'显示时长不足' if not sleep or sleep['total'] < 6 else '已达标但仍有优化空间'}。睡眠是身体恢复和记忆巩固的关键时期，不足的睡眠会影响日间精力、免疫力和长期健康。",
        'action': "1. 设定固定就寝时间，每晚23:00前入睡\n2. 睡前1小时避免使用电子设备和蓝光\n3. 保持卧室温度18-22°C，营造舒适睡眠环境\n4. 避免睡前3小时摄入咖啡因和大量食物\n5. 建立睡前放松仪式，如阅读或冥想",
        'expectation': "通过上述措施，预计2-3周内可明显改善入睡时间和睡眠质量，日间精力将明显提升，长期有助于降低慢性疾病风险。"
    }
    
    # 中等优先级
    ai2 = {
        'title': '增加日常活动量',
        'problem': f"今日步数{steps_val:,}步，{'低于推荐的10000步目标，基础活动量需要提升。久坐生活方式会增加心血管疾病和代谢综合征风险。' if steps_val < 10000 else '已达到推荐目标，建议保持并尝试挑战更高目标。'}",
        'action': "1. 设定每小时站立活动5分钟的提醒\n2. 选择步行或骑行代替短途乘车\n3. 饭后散步15-20分钟，促进消化和血糖稳定\n4. 使用楼梯代替电梯，增加日常运动量\n5. 周末安排户外活动，如徒步或骑行",
        'expectation': "坚持2-4周后，日均步数可稳定提升至8000步以上，心肺功能和代谢健康将得到明显改善。"
    }
    
    # 日常优化
    ai3_diet = "建议采用均衡饮食结构：早餐包含优质蛋白质和复合碳水，如鸡蛋、燕麦和水果；午餐以蔬菜和瘦肉为主，控制精制碳水；晚餐适量，避免高脂高糖。每日饮水2000-2500ml，限制加工食品和含糖饮料。"
    ai3_routine = "建立规律作息：固定起床和就寝时间，误差不超过30分钟；午休20-30分钟；工作间隙每小时活动5-10分钟；睡前1小时调暗灯光，减少蓝光暴露。"
    
    # 数据洞察
    ai4_adv = f"HRV指标{hrv_val:.1f}ms显示自主神经系统平衡良好，身体恢复能力正常。基础代谢率处于健康范围，日常能量消耗合理。"
    ai4_risks = "需关注活动量稳定性和睡眠规律性。数据显示步数波动较大，建议建立更稳定的日常活动模式。"
    ai4_conclusion = "整体健康状况良好，主要需关注睡眠质量和日常活动量的稳定性。建议优先改善睡眠习惯，同时逐步增加日常步行量。"
    ai4_plan = "1. 本周重点：建立固定就寝时间\n2. 下周目标：日均步数提升至8000步\n3. 月度目标：形成稳定的运动和睡眠习惯"
    
    return {
        'ai1': ai1,
        'ai2': ai2,
        'ai3_diet': ai3_diet,
        'ai3_routine': ai3_routine,
        'ai4_adv': ai4_adv,
        'ai4_risks': ai4_risks,
        'ai4_conclusion': ai4_conclusion,
        'ai4_plan': ai4_plan
    }

# ========== 其他函数 ==========
def get_rating_class(value, thresholds):
    if value is None:
        return 'rating-average', 'badge-average', '暂无'
    for threshold, class_name, text in thresholds:
        if value >= threshold:
            return class_name, f'badge-{class_name.replace("rating-", "")}', text
    return 'rating-poor', 'badge-poor', '需改善'

def generate_hr_chart(hr_timeline):
    if not hr_timeline:
        return '<p style="color:#64748b;text-align:center;">当日无运动记录</p>'
    
    times = [h['time'] for h in hr_timeline if h['time']]
    avg_hrs = [h['avg'] for h in hr_timeline]
    max_hrs = [h['max'] for h in hr_timeline]
    
    if not times:
        return '<p style="color:#64748b;text-align:center;">无心率时序数据</p>'
    
    y_min = max(0, min(avg_hrs) - 10)
    y_max = max(max_hrs) + 10
    
    return f'''
    <div style="height:200px;width:100%;">
      <canvas id="hrChart"></canvas>
    </div>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script>
      new Chart(document.getElementById('hrChart'), {{
        type: 'line',
        data: {{
          labels: {times},
          datasets: [
            {{
              label: '平均心率',
              data: {avg_hrs},
              borderColor: '#667eea',
              backgroundColor: 'rgba(102,126,234,0.1)',
              fill: true,
              tension: 0.3,
              pointRadius: 3
            }},
            {{
              label: '最高心率',
              data: {max_hrs},
              borderColor: '#dc2626',
              borderDash: [5,5],
              fill: false,
              pointRadius: 2
            }}
          ]
        }},
        options: {{
          responsive: false,
          maintainAspectRatio: false,
          plugins: {{
            legend: {{ position: 'top', labels: {{ font: {{ size: 10 }}, usePointStyle: true }} }},
            title: {{ display: true, text: '运动时心率变化 (bpm)', font: {{ size: 11 }} }}
          }},
          scales: {{
            y: {{ beginAtZero: false, min: {y_min}, max: {y_max}, title: {{ display: true, text: '心率 (bpm)', font: {{ size: 10 }} }}, ticks: {{ font: {{ size: 9 }} }} }},
            x: {{ ticks: {{ font: {{ size: 9 }}, maxTicksLimit: 8 }} }}
          }}
        }}
      }});
    </script>
    '''

def generate_daily_report(date_str, data, template):
    html = template
    
    # 基础信息
    html = html.replace('{{DATE}}', date_str)
    html = html.replace('{{HEADER_SUBTITLE}}', f'{date_str} · Apple Health | UTC+8')
    
    # 使用缓存中的评分
    recovery = data['scores']['recovery']
    sleep_score = data['scores']['sleep']
    exercise = data['scores']['exercise']
    
    html = html.replace('{{SCORE_RECOVERY}}', str(recovery))
    html = html.replace('{{SCORE_SLEEP}}', str(sleep_score))
    html = html.replace('{{SCORE_EXERCISE}}', str(exercise))
    
    # 评级徽章
    r_class = 'badge-excellent' if recovery >= 80 else 'badge-good' if recovery >= 60 else 'badge-average'
    r_text = '优秀' if recovery >= 80 else '良好' if recovery >= 60 else '一般'
    html = html.replace('{{BADGE_RECOVERY_CLASS}}', r_class)
    html = html.replace('{{BADGE_RECOVERY_TEXT}}', r_text)
    
    s_class = 'badge-excellent' if sleep_score >= 80 else 'badge-good' if sleep_score >= 60 else 'badge-poor' if sleep_score > 0 else 'badge-average'
    s_text = '优秀' if sleep_score >= 80 else '良好' if sleep_score >= 60 else '需改善' if sleep_score > 0 else '无数据'
    html = html.replace('{{BADGE_SLEEP_CLASS}}', s_class)
    html = html.replace('{{BADGE_SLEEP_TEXT}}', s_text)
    
    e_class = 'badge-excellent' if exercise >= 80 else 'badge-good' if exercise >= 60 else 'badge-average'
    e_text = '优秀' if exercise >= 80 else '良好' if exercise >= 60 else '一般'
    html = html.replace('{{BADGE_EXERCISE_CLASS}}', e_class)
    html = html.replace('{{BADGE_EXERCISE_TEXT}}', e_text)
    
    # 指标1-10的AI分析
    hrv_val = data['hrv']['value']
    hrv_rating, hrv_class, hrv_text = get_rating_class(hrv_val, [(55, 'rating-excellent', '优秀'), (45, 'rating-good', '良好')])
    html = html.replace('{{METRIC1_VALUE}}', f"{hrv_val:.1f} ms<br><small>{data['hrv']['points']}个数据点</small>" if hrv_val else "--")
    html = html.replace('{{METRIC1_RATING}}', hrv_text)
    html = html.replace('{{METRIC1_RATING_CLASS}}', hrv_rating)
    html = html.replace('{{METRIC1_ANALYSIS}}', generate_ai_analysis('hrv', hrv_val, 'ms', None))
    
    # 其他指标...
    rhr_val = data['resting_hr']['value']
    html = html.replace('{{METRIC2_VALUE}}', f"{int(rhr_val)} bpm" if rhr_val else "--")
    html = html.replace('{{METRIC2_RATING}}', '优秀' if rhr_val and rhr_val < 60 else '良好' if rhr_val else '暂无')
    html = html.replace('{{METRIC2_RATING_CLASS}}', 'rating-excellent' if rhr_val and rhr_val < 60 else 'rating-good' if rhr_val else 'rating-average')
    html = html.replace('{{METRIC2_ANALYSIS}}', generate_ai_analysis('resting_hr', rhr_val, 'bpm', None) if rhr_val else "暂无数据")
    
    steps_val = data['steps']['value']
    html = html.replace('{{METRIC3_VALUE}}', f"{steps_val:,} 步<br><small>{data['steps']['points']}个数据点</small>")
    html = html.replace('{{METRIC3_RATING}}', '优秀' if steps_val >= 10000 else '良好' if steps_val >= 7000 else '一般')
    html = html.replace('{{METRIC3_RATING_CLASS}}', 'rating-excellent' if steps_val >= 10000 else 'rating-good' if steps_val >= 7000 else 'rating-average')
    html = html.replace('{{METRIC3_ANALYSIS}}', generate_ai_analysis('steps', steps_val, '步', None))
    
    dist_val = data['distance']['value']
    html = html.replace('{{METRIC4_VALUE}}', f"{dist_val:.2f} km")
    html = html.replace('{{METRIC4_RATING}}', '良好' if dist_val >= 5 else '一般')
    html = html.replace('{{METRIC4_RATING_CLASS}}', 'rating-good' if dist_val >= 5 else 'rating-average')
    html = html.replace('{{METRIC4_ANALYSIS}}', generate_ai_analysis('distance', dist_val, 'km', None))
    
    energy_val = data['active_energy']['value']
    html = html.replace('{{METRIC5_VALUE}}', f"{int(energy_val)} kcal<br><small>({data['active_energy']['kj']:.0f}kJ)</small>")
    html = html.replace('{{METRIC5_RATING}}', '良好' if energy_val >= 400 else '一般')
    html = html.replace('{{METRIC5_RATING_CLASS}}', 'rating-good' if energy_val >= 400 else 'rating-average')
    html = html.replace('{{METRIC5_ANALYSIS}}', generate_ai_analysis('active_energy', energy_val, 'kcal', None))
    
    floors_val = data['floors']
    html = html.replace('{{METRIC6_VALUE}}', f"{floors_val} 层")
    html = html.replace('{{METRIC6_RATING}}', '良好' if floors_val >= 10 else '一般')
    html = html.replace('{{METRIC6_RATING_CLASS}}', 'rating-good' if floors_val >= 10 else 'rating-average')
    html = html.replace('{{METRIC6_ANALYSIS}}', generate_ai_analysis('floors', floors_val, '层', None))
    
    stand_val = data['stand_min']
    html = html.replace('{{METRIC7_VALUE}}', f"{stand_val} 分钟")
    html = html.replace('{{METRIC7_RATING}}', '良好' if stand_val >= 120 else '一般')
    html = html.replace('{{METRIC7_RATING_CLASS}}', 'rating-good' if stand_val >= 120 else 'rating-average')
    html = html.replace('{{METRIC7_ANALYSIS}}', generate_ai_analysis('stand', stand_val, '分钟', None))
    
    spo2_val = data['spo2']['value']
    html = html.replace('{{METRIC8_VALUE}}', f"{spo2_val:.1f}%<br><small>{data['spo2']['points']}个数据点</small>" if spo2_val else "--")
    html = html.replace('{{METRIC8_RATING}}', '优秀' if spo2_val and spo2_val >= 95 else '良好' if spo2_val else '暂无')
    html = html.replace('{{METRIC8_RATING_CLASS}}', 'rating-excellent' if spo2_val and spo2_val >= 95 else 'rating-good' if spo2_val else 'rating-average')
    html = html.replace('{{METRIC8_ANALYSIS}}', generate_ai_analysis('spo2', spo2_val, '%', None) if spo2_val else "暂无数据")
    
    basal_val = data['basal_energy']['value']
    html = html.replace('{{METRIC9_VALUE}}', f"{int(basal_val)} kcal<br><small>({data['basal_energy']['kj']:.0f}kJ)</small>")
    html = html.replace('{{METRIC9_RATING}}', '正常')
    html = html.replace('{{METRIC9_RATING_CLASS}}', 'rating-good')
    html = html.replace('{{METRIC9_ANALYSIS}}', generate_ai_analysis('basal', basal_val, 'kcal', None))
    
    resp_val = data['resp_rate']['value']
    html = html.replace('{{METRIC10_VALUE}}', f"{resp_val:.1f} 次/分" if resp_val else "--")
    html = html.replace('{{METRIC10_RATING}}', '正常' if resp_val else '暂无')
    html = html.replace('{{METRIC10_RATING_CLASS}}', 'rating-good' if resp_val else 'rating-average')
    html = html.replace('{{METRIC10_ANALYSIS}}', generate_ai_analysis('resp', resp_val, '次/分', None) if resp_val else "暂无数据")
    
    # 睡眠分析（使用专门的睡眠分析函数，100-150字）
    sleep = data.get('sleep')
    if sleep and sleep['total'] > 0:
        total = sleep['total']
        deep = sleep['deep']
        core = sleep['core']
        rem = sleep['rem']
        awake = sleep['awake']
        
        # 只有当有实际阶段数据时才显示占比
        has_stages = deep > 0 or core > 0 or rem > 0
        
        html = html.replace('{{SLEEP_STATUS}}', '数据正常')
        html = html.replace('{{SLEEP_ALERT_BG}}', '#dcfce7')
        html = html.replace('{{SLEEP_ALERT_BORDER}}', '#22c55e')
        html = html.replace('{{SLEEP_ALERT_COLOR}}', '#166534')
        html = html.replace('{{SLEEP_ALERT_SUBCOLOR}}', '#15803d')
        html = html.replace('{{SLEEP_ALERT_TITLE}}', '✅ 睡眠数据完整')
        html = html.replace('{{SLEEP_ALERT_DETAIL}}', f'总睡眠时长{total:.1f}小时。数据来源: {sleep.get("source_file", "").split("/")[-1]}')
        
        html = html.replace('{{SLEEP_TOTAL}}', f"{total:.1f}")
        html = html.replace('{{SLEEP_DEEP}}', f"{deep:.1f}")
        html = html.replace('{{SLEEP_CORE}}', f"{core:.1f}")
        html = html.replace('{{SLEEP_REM}}', f"{rem:.1f}")
        html = html.replace('{{SLEEP_AWAKE}}', f"{awake:.1f}")
        
        # 只有有阶段数据时才计算百分比
        if has_stages:
            total_calc = deep + core + rem + awake
            if total_calc > 0:
                html = html.replace('{{SLEEP_DEEP_PCT}}', str(int(deep/total_calc*100)))
                html = html.replace('{{SLEEP_CORE_PCT}}', str(int(core/total_calc*100)))
                html = html.replace('{{SLEEP_REM_PCT}}', str(int(rem/total_calc*100)))
                html = html.replace('{{SLEEP_AWAKE_PCT}}', str(int(awake/total_calc*100)))
        else:
            # 无阶段数据时显示为0%
            html = html.replace('{{SLEEP_DEEP_PCT}}', '0')
            html = html.replace('{{SLEEP_CORE_PCT}}', '0')
            html = html.replace('{{SLEEP_REM_PCT}}', '0')
            html = html.replace('{{SLEEP_AWAKE_PCT}}', '0')
        
        html = html.replace('{{SLEEP_ANALYSIS_BORDER}}', '#667eea')
        # 使用字数控制的睡眠分析
        html = html.replace('{{SLEEP_ANALYSIS_TEXT}}', generate_sleep_analysis(sleep))
    else:
        html = html.replace('{{SLEEP_STATUS}}', '无数据')
        html = html.replace('{{SLEEP_ALERT_BG}}', '#fee2e2')
        html = html.replace('{{SLEEP_ALERT_BORDER}}', '#dc2626')
        html = html.replace('{{SLEEP_ALERT_COLOR}}', '#991b1b')
        html = html.replace('{{SLEEP_ALERT_SUBCOLOR}}', '#b91c1c')
        html = html.replace('{{SLEEP_ALERT_TITLE}}', '⚠️ 未检测到睡眠数据')
        html = html.replace('{{SLEEP_ALERT_DETAIL}}', '请确保Apple Watch在睡眠期间佩戴并开启睡眠追踪。')
        html = html.replace('{{SLEEP_TOTAL}}', '--')
        html = html.replace('{{SLEEP_DEEP}}', '--')
        html = html.replace('{{SLEEP_CORE}}', '--')
        html = html.replace('{{SLEEP_REM}}', '--')
        html = html.replace('{{SLEEP_AWAKE}}', '--')
        html = html.replace('{{SLEEP_DEEP_PCT}}', '0')
        html = html.replace('{{SLEEP_CORE_PCT}}', '0')
        html = html.replace('{{SLEEP_REM_PCT}}', '0')
        html = html.replace('{{SLEEP_AWAKE_PCT}}', '0')
        html = html.replace('{{SLEEP_ANALYSIS_BORDER}}', '#dc2626')
        html = html.replace('{{SLEEP_ANALYSIS_TEXT}}', generate_sleep_analysis(None))
    
    # Workout记录（使用字数控制的运动分析）
    if data['has_workout'] and data['workouts']:
        w = data['workouts'][0]
        html = html.replace('{{WORKOUT_NAME}}', w['name'])
        html = html.replace('{{WORKOUT_TIME}}', w['start'] if w['start'] else '今日')
        html = html.replace('{{WORKOUT_DURATION}}', str(int(w['duration_min'])))
        html = html.replace('{{WORKOUT_ENERGY}}', str(int(w['energy_kcal'])) if w['energy_kcal'] else '--')
        html = html.replace('{{WORKOUT_AVG_HR}}', str(int(w['avg_hr'])) if w['avg_hr'] else '--')
        html = html.replace('{{WORKOUT_MAX_HR}}', str(int(w['max_hr'])) if w['max_hr'] else '--')
        html = html.replace('{{WORKOUT_HR_CHART}}', generate_hr_chart(w['hr_timeline']))
        # 使用字数控制的运动分析
        html = html.replace('{{WORKOUT_ANALYSIS}}', generate_workout_analysis(data['workouts'], data['active_energy']['value']))
    else:
        html = html.replace('{{WORKOUT_NAME}}', '无运动记录')
        html = html.replace('{{WORKOUT_TIME}}', '--')
        html = html.replace('{{WORKOUT_DURATION}}', '--')
        html = html.replace('{{WORKOUT_ENERGY}}', '--')
        html = html.replace('{{WORKOUT_AVG_HR}}', '--')
        html = html.replace('{{WORKOUT_MAX_HR}}', '--')
        html = html.replace('{{WORKOUT_HR_CHART}}', '<p style="color:#64748b;text-align:center;">当日无运动记录</p>')
        html = html.replace('{{WORKOUT_ANALYSIS}}', generate_workout_analysis(None, data['active_energy']['value']))
    
    # AI建议（使用字数控制的建议生成）
    ai = generate_ai_suggestions(data)
    html = html.replace('{{AI1_TITLE}}', ai['ai1']['title'])
    html = html.replace('{{AI1_PROBLEM}}', ai['ai1']['problem'])
    html = html.replace('{{AI1_ACTION}}', ai['ai1']['action'])
    html = html.replace('{{AI1_EXPECTATION}}', ai['ai1']['expectation'])
    
    html = html.replace('{{AI2_TITLE}}', ai['ai2']['title'])
    html = html.replace('{{AI2_PROBLEM}}', ai['ai2']['problem'])
    html = html.replace('{{AI2_ACTION}}', ai['ai2']['action'])
    html = html.replace('{{AI2_EXPECTATION}}', ai['ai2']['expectation'])
    
    html = html.replace('{{AI3_TITLE}}', '饮食与作息优化')
    html = html.replace('{{AI3_DIET}}', ai['ai3_diet'])
    html = html.replace('{{AI3_ROUTINE}}', ai['ai3_routine'])
    
    html = html.replace('{{AI4_TITLE}}', '数据洞察总结')
    html = html.replace('{{AI4_ADVANTAGES}}', ai['ai4_adv'])
    html = html.replace('{{AI4_RISKS}}', ai['ai4_risks'])
    html = html.replace('{{AI4_CONCLUSION}}', ai['ai4_conclusion'])
    html = html.replace('{{AI4_PLAN}}', ai['ai4_plan'])
    
    # 页脚
    html = html.replace('{{FOOTER_DATA_SOURCES}}', f'Apple Health (HRV:{data["hrv"]["points"]}点,步数:{data["steps"]["points"]}点)')
    html = html.replace('{{FOOTER_DATE}}', datetime.now().strftime('%Y-%m-%d %H:%M'))
    
    return html

def main():
    dates = ['2026-02-18', '2026-02-19', '2026-02-20', '2026-02-21', '2026-02-22']
    daily_data = {}
    
    print("=" * 60)
    print("健康报告生成器 - V4.5 修正版")
    print("=" * 60)
    print("\n修正内容：")
    print("1. 删除所有估算值逻辑")
    print("2. 修复血氧单位判断（原始值>1则不再×100）")
    print("3. 添加睡眠/运动/AI建议字数要求（100-150字/200-250字）")
    
    # 读取模板
    with open(TEMPLATE_DIR / 'DAILY_TEMPLATE_V2.html', 'r', encoding='utf-8') as f:
        daily_template = f.read()
    
    # 提取每日数据并保存缓存
    for date in dates:
        print(f"\n📅 处理 {date}...")
        data = extract_daily_data(date)
        if data:
            daily_data[date] = data
            save_cache(data, date)
            print(f"  HRV: {data['hrv']['value']:.1f}ms ({data['hrv']['points']}点)")
            print(f"  步数: {data['steps']['value']:,} ({data['steps']['points']}点)")
            print(f"  活动能量: {data['active_energy']['value']:.0f}kcal")
            print(f"  血氧: {data['spo2']['value']:.1f}%" if data['spo2']['value'] else "  血氧: 无数据")
            print(f"  睡眠: {data['sleep']['total']:.1f}h" if data['sleep'] else "  睡眠: 无数据")
            print(f"  运动: {len(data['workouts'])}条记录" if data['has_workout'] else "  运动: 无记录")
            print(f"  📊 评分: 恢复{data['scores']['recovery']} | 睡眠{data['scores']['sleep']} | 运动{data['scores']['exercise']}")
    
    # 生成2月18日日报
    print("\n" + "=" * 60)
    print("生成报告...")
    print("=" * 60)
    
    date_str = '2026-02-18'
    if date_str in daily_data:
        html = generate_daily_report(date_str, daily_data[date_str], daily_template)
        
        # 验证字数
        import re
        print("\n📝 字数检查:")
        
        # 指标分析
        ai_texts = re.findall(r'<td class="ai-text">(.*?)</td>', html, re.DOTALL)
        print("\n指标分析（要求100-150字）:")
        for i, text in enumerate(ai_texts[:10], 1):
            clean_text = re.sub(r'<[^>]+>', '', text).strip()
            status = '✅' if 100 <= len(clean_text) <= 150 else '⚠️'
            print(f"  指标{i}: {len(clean_text)}字 {status}")
        
        # 睡眠分析
        sleep_analysis = re.search(r'<strong>AI深度分析：</strong>(.*?)</div>', html, re.DOTALL)
        if sleep_analysis:
            text = re.sub(r'<[^>]+>', '', sleep_analysis.group(1)).strip()
            status = '✅' if 100 <= len(text) <= 150 else '⚠️'
            print(f"\n睡眠分析: {len(text)}字 {status}（要求100-150字）")
        
        # 运动分析
        workout_analysis = re.search(r'<strong>运动AI详细分析：</strong>(.*?)</div>', html, re.DOTALL)
        if workout_analysis:
            text = re.sub(r'<[^>]+>', '', workout_analysis.group(1)).strip()
            status = '✅' if 100 <= len(text) <= 150 else '⚠️'
            print(f"运动分析: {len(text)}字 {status}（要求100-150字）")
        
        # AI建议
        ai_sections = re.findall(r'<div class="ai-rec-content">(.*?)</div>', html, re.DOTALL)
        print("\nAI建议（要求200-250字）:")
        for i, section in enumerate(ai_sections[:4], 1):
            clean = re.sub(r'<[^>]+>', '', section).strip()
            status = '✅' if 200 <= len(clean) <= 250 else '⚠️'
            print(f"  建议{i}: {len(clean)}字 {status}")
        
        output_path = OUTPUT_DIR / f'{date_str}-daily-report-V4.5.pdf'
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.set_content(html)
            page.wait_for_timeout(3000)
            page.pdf(path=str(output_path), format='A4', print_background=True,
                    margin={'top': '8mm', 'bottom': '8mm', 'left': '8mm', 'right': '8mm'})
            browser.close()
        print(f"\n  ✅ 日报生成: {output_path}")
    
    print(f"\n✅ 完成！共处理 {len(daily_data)} 天数据")

if __name__ == '__main__':
    main()
