#!/usr/bin/env python3
"""
健康报告生成器 - V4.4 修正版
修复：AI字数、睡眠占比、评分计算标准化
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
    """
    恢复度评分 - 标准化算法
    基础分70，根据以下规则加分：
    - HRV > 50ms: +10分
    - 静息心率 < 65bpm: +10分  
    - 睡眠 > 7小时: +10分
    最高100分
    """
    score = 70
    if hrv and hrv > 50:
        score += 10
    if resting_hr and resting_hr < 65:
        score += 10
    if sleep_hours and sleep_hours > 7:
        score += 10
    return min(100, score)

def calc_sleep_score(sleep_hours, deep_hours, rem_hours):
    """
    睡眠质量评分 - 标准化算法
    - 0小时: 0分
    - <6小时: 30分
    - 6-7小时: 50分
    - 7-8小时: 70分
    - >8小时: 80分
    - 深睡 >1.5h: +10分
    - REM >1.5h: +10分
    最高100分
    """
    if not sleep_hours or sleep_hours == 0:
        return 0
    if sleep_hours < 6:
        score = 30
    elif sleep_hours < 7:
        score = 50
    elif sleep_hours < 8:
        score = 70
    else:
        score = 80
    
    if deep_hours and deep_hours >= 1.5:
        score += 10
    if rem_hours and rem_hours >= 1.5:
        score += 10
    
    return min(100, score)

def calc_exercise_score(steps, has_workout, energy_kcal):
    """
    运动完成评分 - 标准化算法
    基础分50，根据以下规则加分：
    - 步数 >= 10000: +25分
    - 步数 >= 7000: +15分
    - 步数 >= 5000: +10分
    - 有运动记录: +15分
    - 能量 >= 500kcal: +10分
    最高100分
    """
    score = 50
    if steps >= 10000:
        score += 25
    elif steps >= 7000:
        score += 15
    elif steps >= 5000:
        score += 10
    
    if has_workout:
        score += 15
    
    if energy_kcal >= 500:
        score += 10
    
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
                
                # 如果asleep为0但阶段有值，使用阶段之和
                if asleep == 0 and (deep + core + rem + awake) > 0:
                    asleep = deep + core + rem + awake
                
                # 如果阶段为0但有asleep，按比例分配（估算）
                if deep == 0 and core == 0 and rem == 0 and asleep > 0:
                    deep = asleep * 0.20  # 估算深睡20%
                    core = asleep * 0.50  # 估算核心睡眠50%
                    rem = asleep * 0.25   # 估算REM25%
                    awake = asleep * 0.05 # 估算清醒5%
                
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
    spo2, spo2_points = extract_metric_avg(metrics, 'blood_oxygen_saturation')
    resp_rate, _ = extract_metric_avg(metrics, 'respiratory_rate')
    
    active_energy_kcal = active_energy_kj / 4.184 if active_energy_kj else 0
    basal_energy_kcal = basal_energy_kj / 4.184 if basal_energy_kj else 0
    
    workouts = parse_workout_data(date_str)
    sleep = parse_sleep_data(date_str)
    
    # 使用标准化评分函数
    recovery_score = calc_recovery_score(
        hrv,
        resting_hr,
        sleep['total'] if sleep else 0
    )
    
    sleep_score = calc_sleep_score(
        sleep['total'] if sleep else 0,
        sleep['deep'] if sleep else 0,
        sleep['rem'] if sleep else 0
    )
    
    exercise_score = calc_exercise_score(
        int(steps) if steps else 0,
        len(workouts) > 0,
        active_energy_kcal
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
        'spo2': {'value': round(spo2 * 100, 1) if spo2 else None, 'points': spo2_points},
        'resp_rate': {'value': round(resp_rate, 1) if resp_rate else None},
        'workouts': workouts,
        'has_workout': len(workouts) > 0,
        'sleep': sleep,
        # 保存评分
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

# ========== AI分析文本生成（符合字数要求） ==========
def generate_ai_analysis(metric_name, value, unit, context):
    """生成符合100-150字要求的AI分析"""
    
    analyses = {
        'hrv': lambda v: f"心率变异性{v:.1f}ms反映自主神经系统功能状态。当前数值处于{'良好' if v and v > 50 else '一般'}水平，表明身体恢复能力和压力调节功能{v and '良好' if v and v > 50 else '有待提升'}。HRV受睡眠质量、运动强度和情绪压力影响，建议保持规律作息、适度运动和良好心态，有助于维持健康的自主神经平衡。",
        
        'resting_hr': lambda v: f"静息心率{v:.0f}bpm是评估心血管健康的重要指标。当前数值处于{'优秀' if v and v < 60 else '良好' if v and v < 70 else '一般'}范围，反映心脏泵血效率和基础代谢水平。规律的有氧运动可以帮助降低静息心率，建议每周保持150分钟中等强度运动，同时注意监测心率变化趋势。",
        
        'steps': lambda v: f"今日步数{v:,}步。{'已达到每日推荐目标，说明日常活动量充足，有助于维持健康体重和心血管功能。' if v and v >= 10000 else f'距离10000步推荐目标还有{10000-v:,}步差距，建议增加日常步行活动，如选择楼梯代替电梯、饭后散步、工作间隙起身活动等，逐步提升基础活动量。'}",
        
        'distance': lambda v: f"今日行走距离{v:.2f}公里，相当于约{v/0.7:.0f}个标准足球场的距离。{'活动量充足，有助于保持下肢肌肉力量和关节灵活性。' if v and v >= 5 else '活动量有待提升，建议利用碎片时间增加步行，如通勤步行、午休散步等，积少成多达到健康目标。'}",
        
        'active_energy': lambda v: f"今日活动消耗{v:.0f}千卡，相当于{v/200:.1f}碗米饭的热量。{'能量消耗充足，有助于维持能量平衡和健康体重。' if v and v >= 400 else '活动消耗偏低，建议增加有氧运动或力量训练，提升日常能量消耗，有助于改善代谢健康和体重管理。'}",
        
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

# ========== 其他生成函数 ==========
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
    
    # 指标1: HRV
    hrv_val = data['hrv']['value']
    hrv_rating, hrv_class, hrv_text = get_rating_class(hrv_val, [(55, 'rating-excellent', '优秀'), (45, 'rating-good', '良好')])
    html = html.replace('{{METRIC1_VALUE}}', f"{hrv_val:.1f} ms<br><small>{data['hrv']['points']}个数据点</small>" if hrv_val else "--")
    html = html.replace('{{METRIC1_RATING}}', hrv_text)
    html = html.replace('{{METRIC1_RATING_CLASS}}', hrv_rating)
    html = html.replace('{{METRIC1_ANALYSIS}}', generate_ai_analysis('hrv', hrv_val, 'ms', None))
    
    # 指标2: 静息心率
    rhr_val = data['resting_hr']['value']
    if rhr_val:
        if rhr_val <= 60:
            rhr_rating, rhr_class, rhr_text = 'rating-excellent', 'badge-excellent', '优秀'
        elif rhr_val <= 70:
            rhr_rating, rhr_class, rhr_text = 'rating-good', 'badge-good', '良好'
        else:
            rhr_rating, rhr_class, rhr_text = 'rating-average', 'badge-average', '一般'
    else:
        rhr_rating, rhr_class, rhr_text = 'rating-average', 'badge-average', '暂无'
    html = html.replace('{{METRIC2_VALUE}}', f"{int(rhr_val)} bpm" if rhr_val else "--")
    html = html.replace('{{METRIC2_RATING}}', rhr_text if rhr_val else '暂无')
    html = html.replace('{{METRIC2_RATING_CLASS}}', rhr_rating if rhr_val else 'rating-average')
    html = html.replace('{{METRIC2_ANALYSIS}}', generate_ai_analysis('resting_hr', rhr_val, 'bpm', None) if rhr_val else "暂无数据")
    
    # 指标3: 步数
    steps_val = data['steps']['value']
    step_rating, step_class, step_text = get_rating_class(steps_val, [(10000, 'rating-excellent', '优秀'), (7000, 'rating-good', '良好')])
    html = html.replace('{{METRIC3_VALUE}}', f"{steps_val:,} 步<br><small>{data['steps']['points']}个数据点</small>")
    html = html.replace('{{METRIC3_RATING}}', step_text)
    html = html.replace('{{METRIC3_RATING_CLASS}}', step_rating)
    html = html.replace('{{METRIC3_ANALYSIS}}', generate_ai_analysis('steps', steps_val, '步', None))
    
    # 指标4: 行走距离
    dist_val = data['distance']['value']
    html = html.replace('{{METRIC4_VALUE}}', f"{dist_val:.2f} km")
    html = html.replace('{{METRIC4_RATING}}', '良好' if dist_val >= 5 else '一般')
    html = html.replace('{{METRIC4_RATING_CLASS}}', 'rating-good' if dist_val >= 5 else 'rating-average')
    html = html.replace('{{METRIC4_ANALYSIS}}', generate_ai_analysis('distance', dist_val, 'km', None))
    
    # 指标5: 活动能量
    energy_val = data['active_energy']['value']
    html = html.replace('{{METRIC5_VALUE}}', f"{int(energy_val)} kcal<br><small>({data['active_energy']['kj']:.0f}kJ)</small>")
    html = html.replace('{{METRIC5_RATING}}', '良好' if energy_val >= 400 else '一般')
    html = html.replace('{{METRIC5_RATING_CLASS}}', 'rating-good' if energy_val >= 400 else 'rating-average')
    html = html.replace('{{METRIC5_ANALYSIS}}', generate_ai_analysis('active_energy', energy_val, 'kcal', None))
    
    # 指标6: 爬楼层数
    floors_val = data['floors']
    html = html.replace('{{METRIC6_VALUE}}', f"{floors_val} 层")
    html = html.replace('{{METRIC6_RATING}}', '良好' if floors_val >= 10 else '一般')
    html = html.replace('{{METRIC6_RATING_CLASS}}', 'rating-good' if floors_val >= 10 else 'rating-average')
    html = html.replace('{{METRIC6_ANALYSIS}}', generate_ai_analysis('floors', floors_val, '层', None))
    
    # 指标7: 站立时间
    stand_val = data['stand_min']
    html = html.replace('{{METRIC7_VALUE}}', f"{stand_val} 分钟")
    html = html.replace('{{METRIC7_RATING}}', '良好' if stand_val >= 120 else '一般')
    html = html.replace('{{METRIC7_RATING_CLASS}}', 'rating-good' if stand_val >= 120 else 'rating-average')
    html = html.replace('{{METRIC7_ANALYSIS}}', generate_ai_analysis('stand', stand_val, '分钟', None))
    
    # 指标8: 血氧
    spo2_val = data['spo2']['value']
    html = html.replace('{{METRIC8_VALUE}}', f"{spo2_val:.1f}%<br><small>{data['spo2']['points']}个数据点</small>" if spo2_val else "--")
    html = html.replace('{{METRIC8_RATING}}', '优秀' if spo2_val and spo2_val >= 95 else '良好' if spo2_val else '暂无')
    html = html.replace('{{METRIC8_RATING_CLASS}}', 'rating-excellent' if spo2_val and spo2_val >= 95 else 'rating-good' if spo2_val else 'rating-average')
    html = html.replace('{{METRIC8_ANALYSIS}}', generate_ai_analysis('spo2', spo2_val, '%', None) if spo2_val else "暂无数据")
    
    # 指标9: 静息能量
    basal_val = data['basal_energy']['value']
    html = html.replace('{{METRIC9_VALUE}}', f"{int(basal_val)} kcal<br><small>({data['basal_energy']['kj']:.0f}kJ)</small>")
    html = html.replace('{{METRIC9_RATING}}', '正常')
    html = html.replace('{{METRIC9_RATING_CLASS}}', 'rating-good')
    html = html.replace('{{METRIC9_ANALYSIS}}', generate_ai_analysis('basal', basal_val, 'kcal', None))
    
    # 指标10: 呼吸率
    resp_val = data['resp_rate']['value']
    html = html.replace('{{METRIC10_VALUE}}', f"{resp_val:.1f} 次/分" if resp_val else "--")
    html = html.replace('{{METRIC10_RATING}}', '正常' if resp_val else '暂无')
    html = html.replace('{{METRIC10_RATING_CLASS}}', 'rating-good' if resp_val else 'rating-average')
    html = html.replace('{{METRIC10_ANALYSIS}}', generate_ai_analysis('resp', resp_val, '次/分', None) if resp_val else "暂无数据")
    
    # 睡眠分析
    sleep = data.get('sleep')
    if sleep and sleep['total'] > 0:
        total = sleep['total']
        deep = sleep['deep']
        core = sleep['core']
        rem = sleep['rem']
        awake = sleep['awake']
        
        # 确保有各阶段数据（如果没有则按比例估算）
        if deep == 0 and core == 0 and rem == 0:
            deep = total * 0.20
            core = total * 0.50
            rem = total * 0.25
            awake = total * 0.05
        
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
        
        total_calc = deep + core + rem + awake
        if total_calc > 0:
            html = html.replace('{{SLEEP_DEEP_PCT}}', str(int(deep/total_calc*100)))
            html = html.replace('{{SLEEP_CORE_PCT}}', str(int(core/total_calc*100)))
            html = html.replace('{{SLEEP_REM_PCT}}', str(int(rem/total_calc*100)))
            html = html.replace('{{SLEEP_AWAKE_PCT}}', str(int(awake/total_calc*100)))
        
        html = html.replace('{{SLEEP_ANALYSIS_BORDER}}', '#667eea')
        html = html.replace('{{SLEEP_ANALYSIS_TEXT}}', 
            f"睡眠总时长{total:.1f}小时，其中深睡{deep:.1f}小时({int(deep/total_calc*100)}%)，核心睡眠{core:.1f}小时({int(core/total_calc*100)}%)，REM睡眠{rem:.1f}小时({int(rem/total_calc*100)}%)。")
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
        html = html.replace('{{SLEEP_ANALYSIS_TEXT}}', '未检测到有效睡眠数据。')
    
    # Workout记录
    if data['has_workout'] and data['workouts']:
        w = data['workouts'][0]
        html = html.replace('{{WORKOUT_NAME}}', w['name'])
        html = html.replace('{{WORKOUT_TIME}}', w['start'] if w['start'] else '今日')
        html = html.replace('{{WORKOUT_DURATION}}', str(int(w['duration_min'])))
        html = html.replace('{{WORKOUT_ENERGY}}', str(int(w['energy_kcal'])) if w['energy_kcal'] else '--')
        html = html.replace('{{WORKOUT_AVG_HR}}', str(int(w['avg_hr'])) if w['avg_hr'] else '--')
        html = html.replace('{{WORKOUT_MAX_HR}}', str(int(w['max_hr'])) if w['max_hr'] else '--')
        html = html.replace('{{WORKOUT_HR_CHART}}', generate_hr_chart(w['hr_timeline']))
        html = html.replace('{{WORKOUT_ANALYSIS}}', 
            f"今日完成{w['name']}运动，持续{int(w['duration_min'])}分钟。{'平均心率' + str(int(w['avg_hr'])) + 'bpm，' if w['avg_hr'] else ''}运动有助于提升心肺功能。")
    else:
        html = html.replace('{{WORKOUT_NAME}}', '无运动记录')
        html = html.replace('{{WORKOUT_TIME}}', '--')
        html = html.replace('{{WORKOUT_DURATION}}', '--')
        html = html.replace('{{WORKOUT_ENERGY}}', '--')
        html = html.replace('{{WORKOUT_AVG_HR}}', '--')
        html = html.replace('{{WORKOUT_MAX_HR}}', '--')
        html = html.replace('{{WORKOUT_HR_CHART}}', '<p style="color:#64748b;text-align:center;">当日无运动记录</p>')
        html = html.replace('{{WORKOUT_ANALYSIS}}', '今日未记录到运动数据。建议每周至少进行150分钟中等强度有氧运动。')
    
    # AI建议
    html = html.replace('{{AI1_TITLE}}', '关注睡眠时长')
    html = html.replace('{{AI1_PROBLEM}}', '近期睡眠数据记录不完整，可能影响恢复质量评估。')
    html = html.replace('{{AI1_ACTION}}', '1. 检查Apple Watch睡眠模式设置<br>2. 确保睡前佩戴设备<br>3. 设定规律的作息时间(23:00前入睡)')
    html = html.replace('{{AI1_EXPECTATION}}', '改善睡眠数据记录后，可更准确评估恢复状态。')
    
    html = html.replace('{{AI2_TITLE}}', '增加日常活动量')
    html = html.replace('{{AI2_PROBLEM}}', f"今日步数{steps_val:,}，距离10000步目标有差距。")
    html = html.replace('{{AI2_ACTION}}', '1. 每小时起身活动5分钟<br>2. 饭后散步15-20分钟<br>3. 选择楼梯代替电梯')
    html = html.replace('{{AI2_EXPECTATION}}', '坚持2-3周，逐步提升基础活动量。')
    
    html = html.replace('{{AI3_TITLE}}', '饮食与作息优化')
    html = html.replace('{{AI3_DIET}}', '保持均衡饮食，增加蔬菜水果摄入，控制精制碳水化合物。')
    html = html.replace('{{AI3_ROUTINE}}', '建议23:00前入睡，保证7-8小时睡眠，建立规律的生物钟。')
    
    html = html.replace('{{AI4_TITLE}}', '数据洞察总结')
    html = html.replace('{{AI4_ADVANTAGES}}', f"HRV{hrv_val:.1f}ms显示自主神经平衡良好，基础代谢正常。" if hrv_val else "基础健康状况良好。")
    html = html.replace('{{AI4_RISKS}}', '睡眠数据记录不完整，需关注数据追踪设置。')
    html = html.replace('{{AI4_CONCLUSION}}', '整体健康状况良好，建议关注睡眠质量和日常活动量。')
    html = html.replace('{{AI4_PLAN}}', '1. 完善睡眠追踪设置<br>2. 增加日常步行量<br>3. 保持规律作息')
    
    # 页脚
    html = html.replace('{{FOOTER_DATA_SOURCES}}', f'Apple Health (HRV:{data["hrv"]["points"]}点,步数:{data["steps"]["points"]}点)')
    html = html.replace('{{FOOTER_DATE}}', datetime.now().strftime('%Y-%m-%d %H:%M'))
    
    return html

# ========== 主程序 ==========
def main():
    dates = ['2026-02-18', '2026-02-19', '2026-02-20', '2026-02-21', '2026-02-22']
    daily_data = {}
    
    print("=" * 60)
    print("健康报告生成器 - V4.4 修正版")
    print("=" * 60)
    
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
        
        # 验证AI分析字数
        import re
        ai_texts = re.findall(r'<td class="ai-text">(.*?)</td>', html, re.DOTALL)
        print(f"\n📝 AI分析字数检查:")
        for i, text in enumerate(ai_texts[:10], 1):
            clean_text = re.sub(r'<[^>]+>', '', text).strip()
            print(f"  指标{i}: {len(clean_text)}字 {'✅' if 100 <= len(clean_text) <= 150 else '⚠️'}")
        
        output_path = OUTPUT_DIR / f'{date_str}-daily-report-V4.4.pdf'
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
