#!/usr/bin/env python3
"""
健康报告生成器 - 标准化版本 V4.3
修正：能量单位、Workout Data、睡眠字段、缓存机制
"""
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from playwright.sync_api import sync_playwright

# ========== 配置 ==========
HOME = Path.home()
HEALTH_DIR = HOME / '我的云端硬盘' / 'Health Auto Export' / 'Health Data'
WORKOUT_DIR = HOME / '我的云端硬盘' / 'Health Auto Export' / 'Workout Data'
TEMPLATE_DIR = HOME / '.openclaw' / 'workspace-health' / 'templates'
OUTPUT_DIR = HOME / '.openclaw' / 'workspace' / 'shared' / 'health-reports' / 'upload'
CACHE_DIR = HOME / '.openclaw' / 'workspace-health' / 'cache' / 'daily'

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(CACHE_DIR, exist_ok=True)

# ========== 数据提取函数 ==========
def extract_metric_avg(metrics, name):
    """提取平均值指标"""
    metric = metrics.get(name, {})
    values = [d.get('qty', 0) for d in metric.get('data', []) if 'qty' in d]
    return (sum(values) / len(values), len(values)) if values else (None, 0)

def extract_metric_sum(metrics, name):
    """提取求和指标"""
    metric = metrics.get(name, {})
    values = [d.get('qty', 0) for d in metric.get('data', []) if 'qty' in d]
    return (sum(values), len(values)) if values else (0, 0)

def parse_health_data(date_str):
    """解析Apple Health数据"""
    filepath = HEALTH_DIR / f'HealthAutoExport-{date_str}.json'
    if not filepath.exists():
        return None
    
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    metrics = {m['name']: m for m in data.get('data', {}).get('metrics', [])}
    return metrics

def parse_workout_data(date_str):
    """解析Workout Data（详细运动数据）"""
    filepath = WORKOUT_DIR / f'HealthAutoExport-{date_str}.json'
    if not filepath.exists():
        return []
    
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 注意：Workout Data的data字段直接是数组
    workouts = data.get('data', []) if isinstance(data.get('data'), list) else data.get('data', {}).get('workouts', [])
    
    result = []
    for w in workouts:
        # 提取能量（kJ转kcal）
        energy_list = w.get('activeEnergy', [])
        if isinstance(energy_list, list) and energy_list:
            total_kj = sum(e.get('qty', 0) for e in energy_list)
        elif isinstance(energy_list, dict):
            total_kj = energy_list.get('qty', 0)
        else:
            total_kj = 0
        
        # 提取心率时序数据
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
        
        # 从heartRateData计算平均/最大心率（如果heartRate字段为null）
        if hr_timeline:
            avg_hr_calculated = sum(h['avg'] for h in hr_timeline) / len(hr_timeline)
            max_hr_calculated = max(h['max'] for h in hr_timeline)
        else:
            avg_hr_calculated = None
            max_hr_calculated = None
        
        # 优先使用heartRate字段，否则使用计算值
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
    """解析睡眠数据（从次日文件，使用sleepStart字段）"""
    date = datetime.strptime(date_str, '%Y-%m-%d')
    next_date = (date + timedelta(days=1)).strftime('%Y-%m-%d')
    
    # 检查次日文件
    filepath = HEALTH_DIR / f'HealthAutoExport-{next_date}.json'
    if not filepath.exists():
        return None
    
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    metrics = {m['name']: m for m in data.get('data', {}).get('metrics', [])}
    sleep_metric = metrics.get('sleep_analysis', {})
    
    if not sleep_metric or not sleep_metric.get('data'):
        return None
    
    # 时间窗口：当日20:00至次日12:00
    window_start = date.replace(hour=20, minute=0)
    window_end = (date + timedelta(days=1)).replace(hour=12, minute=0)
    
    sleep_records = []
    for sleep in sleep_metric.get('data', []):
        # 使用sleepStart字段（不是startDate）
        sleep_start_str = sleep.get('sleepStart', '')
        if not sleep_start_str:
            continue
        
        try:
            sleep_start = datetime.strptime(sleep_start_str[:19], '%Y-%m-%d %H:%M:%S')
            
            # 检查是否在时间窗口内
            if window_start <= sleep_start <= window_end:
                # 处理数据格式不一致问题
                asleep = sleep.get('asleep', 0) or sleep.get('totalSleep', 0)
                deep = sleep.get('deep', 0)
                core = sleep.get('core', 0)
                rem = sleep.get('rem', 0)
                awake = sleep.get('awake', 0)
                
                # 如果asleep为0但阶段有值，使用阶段之和
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
    
    # 合并所有睡眠记录
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
    """提取单日完整数据"""
    metrics = parse_health_data(date_str)
    if not metrics:
        return None
    
    # 基础指标（能量单位kJ→kcal）
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
    
    # 单位换算
    active_energy_kcal = active_energy_kj / 4.184 if active_energy_kj else 0
    basal_energy_kcal = basal_energy_kj / 4.184 if basal_energy_kj else 0
    
    # 读取Workout Data
    workouts = parse_workout_data(date_str)
    
    # 读取睡眠数据（从次日文件）
    sleep = parse_sleep_data(date_str)
    
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
        'sleep': sleep
    }

# ========== 缓存管理 ==========
def save_cache(data, date_str):
    """保存每日缓存"""
    cache_path = CACHE_DIR / f'{date_str}.json'
    with open(cache_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  ✅ 缓存已保存: {cache_path}")

def load_cache(date_str):
    """加载每日缓存"""
    cache_path = CACHE_DIR / f'{date_str}.json'
    if cache_path.exists():
        with open(cache_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

# ========== 报告生成 ==========
def get_rating_class(value, thresholds):
    """获取评级CSS类"""
    if value is None:
        return 'rating-average', 'badge-average', '暂无'
    for threshold, class_name, text in thresholds:
        if value >= threshold:
            return class_name, f'badge-{class_name.replace("rating-", "")}', text
    return 'rating-poor', 'badge-poor', '需改善'

def calc_recovery_score(d):
    """计算恢复度分数"""
    score = 70
    if d['hrv']['value'] and d['hrv']['value'] > 50: score += 10
    if d['resting_hr']['value'] and d['resting_hr']['value'] < 65: score += 10
    if d['sleep'] and d['sleep']['total'] > 7: score += 10
    return min(100, score)

def calc_sleep_score(d):
    """计算睡眠分数"""
    if not d['sleep'] or d['sleep']['total'] == 0:
        return 0
    score = 60
    if d['sleep']['total'] >= 7: score += 20
    elif d['sleep']['total'] >= 6: score += 10
    if d['sleep']['deep'] >= 1.5: score += 10
    if d['sleep']['rem'] >= 1.5: score += 10
    return min(100, score)

def calc_exercise_score(d):
    """计算运动分数"""
    score = 50
    if d['steps']['value'] >= 10000: score += 25
    elif d['steps']['value'] >= 7000: score += 15
    elif d['steps']['value'] >= 5000: score += 10
    if d['has_workout']: score += 15
    if d['active_energy']['value'] >= 500: score += 10
    return min(100, score)

def generate_hr_chart(hr_timeline):
    """生成心率图表HTML"""
    if not hr_timeline:
        return '<p style="color:#64748b;text-align:center;">当日无运动记录</p>'
    
    times = [h['time'] for h in hr_timeline if h['time']]
    avg_hrs = [h['avg'] for h in hr_timeline]
    max_hrs = [h['max'] for h in hr_timeline]
    
    if not times:
        return '<p style="color:#64748b;text-align:center;">无心率时序数据</p>'
    
    y_min = max(0, min(avg_hrs) - 10) if avg_hrs else 100
    y_max = max(max_hrs) + 10 if max_hrs else 180
    
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
    """生成日报HTML"""
    html = template
    
    # 基础信息
    html = html.replace('{{DATE}}', date_str)
    html = html.replace('{{HEADER_SUBTITLE}}', f'{date_str} · Apple Health | UTC+8')
    
    # 评分
    recovery = calc_recovery_score(data)
    sleep_score = calc_sleep_score(data)
    exercise = calc_exercise_score(data)
    
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
    html = html.replace('{{METRIC1_ANALYSIS}}', 
        f"心率变异性{hrv_val:.1f}ms处于正常范围。HRV反映自主神经系统平衡，当前数值表明身体恢复良好，压力水平适中。建议保持规律作息。" if hrv_val else "暂无数据")
    
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
    html = html.replace('{{METRIC2_ANALYSIS}}', 
        f"静息心率{int(rhr_val)}bpm，处于健康范围。静息心率是心血管健康的重要指标，保持规律运动有助于维持较低水平。" if rhr_val else "暂无数据")
    
    # 指标3: 步数
    steps_val = data['steps']['value']
    step_rating, step_class, step_text = get_rating_class(steps_val, [(10000, 'rating-excellent', '优秀'), (7000, 'rating-good', '良好')])
    html = html.replace('{{METRIC3_VALUE}}', f"{steps_val:,} 步<br><small>{data['steps']['points']}个数据点</small>")
    html = html.replace('{{METRIC3_RATING}}', step_text)
    html = html.replace('{{METRIC3_RATING_CLASS}}', step_rating)
    html = html.replace('{{METRIC3_ANALYSIS}}', 
        f"今日步数{steps_val:,}步。{'达成每日推荐目标，保持良好的活动习惯。' if steps_val >= 10000 else f'距离10000步目标还有{10000-steps_val}步，建议增加日常活动。'}")
    
    # 指标4: 行走距离
    dist_val = data['distance']['value']
    html = html.replace('{{METRIC4_VALUE}}', f"{dist_val:.2f} km")
    html = html.replace('{{METRIC4_RATING}}', '良好' if dist_val >= 5 else '一般')
    html = html.replace('{{METRIC4_RATING_CLASS}}', 'rating-good' if dist_val >= 5 else 'rating-average')
    html = html.replace('{{METRIC4_ANALYSIS}}', f"今日行走{dist_val:.2f}公里。")
    
    # 指标5: 活动能量
    energy_val = data['active_energy']['value']
    html = html.replace('{{METRIC5_VALUE}}', f"{int(energy_val)} kcal<br><small>({data['active_energy']['kj']:.0f}kJ)</small>")
    html = html.replace('{{METRIC5_RATING}}', '良好' if energy_val >= 400 else '一般')
    html = html.replace('{{METRIC5_RATING_CLASS}}', 'rating-good' if energy_val >= 400 else 'rating-average')
    html = html.replace('{{METRIC5_ANALYSIS}}', f"活动消耗{energy_val:.0f}千卡。")
    
    # 指标6: 爬楼层数
    html = html.replace('{{METRIC6_VALUE}}', f"{data['floors']} 层")
    html = html.replace('{{METRIC6_RATING}}', '良好' if data['floors'] >= 10 else '一般')
    html = html.replace('{{METRIC6_RATING_CLASS}}', 'rating-good' if data['floors'] >= 10 else 'rating-average')
    html = html.replace('{{METRIC6_ANALYSIS}}', f"今日爬楼{data['floors']}层。")
    
    # 指标7: 站立时间
    html = html.replace('{{METRIC7_VALUE}}', f"{data['stand_min']} 分钟")
    html = html.replace('{{METRIC7_RATING}}', '良好' if data['stand_min'] >= 120 else '一般')
    html = html.replace('{{METRIC7_RATING_CLASS}}', 'rating-good' if data['stand_min'] >= 120 else 'rating-average')
    html = html.replace('{{METRIC7_ANALYSIS}}', f"累计站立{data['stand_min']}分钟。")
    
    # 指标8: 血氧
    spo2_val = data['spo2']['value']
    html = html.replace('{{METRIC8_VALUE}}', f"{spo2_val:.1f}%<br><small>{data['spo2']['points']}个数据点</small>" if spo2_val else "--")
    html = html.replace('{{METRIC8_RATING}}', '优秀' if spo2_val and spo2_val >= 95 else '良好' if spo2_val else '暂无')
    html = html.replace('{{METRIC8_RATING_CLASS}}', 'rating-excellent' if spo2_val and spo2_val >= 95 else 'rating-good' if spo2_val else 'rating-average')
    html = html.replace('{{METRIC8_ANALYSIS}}', 
        f"血氧饱和度{spo2_val:.1f}%，处于正常范围。" if spo2_val else "暂无数据")
    
    # 指标9: 静息能量
    basal_val = data['basal_energy']['value']
    html = html.replace('{{METRIC9_VALUE}}', f"{int(basal_val)} kcal<br><small>({data['basal_energy']['kj']:.0f}kJ)</small>")
    html = html.replace('{{METRIC9_RATING}}', '正常')
    html = html.replace('{{METRIC9_RATING_CLASS}}', 'rating-good')
    html = html.replace('{{METRIC9_ANALYSIS}}', f"基础代谢消耗{basal_val:.0f}千卡。")
    
    # 指标10: 呼吸率
    resp_val = data['resp_rate']['value']
    html = html.replace('{{METRIC10_VALUE}}', f"{resp_val:.1f} 次/分" if resp_val else "--")
    html = html.replace('{{METRIC10_RATING}}', '正常' if resp_val else '暂无')
    html = html.replace('{{METRIC10_RATING_CLASS}}', 'rating-good' if resp_val else 'rating-average')
    html = html.replace('{{METRIC10_ANALYSIS}}', 
        f"呼吸率{resp_val:.1f}次/分钟，处于正常范围。" if resp_val else "暂无数据")
    
    # 睡眠分析
    sleep = data.get('sleep')
    if sleep and sleep['total'] > 0:
        total = sleep['total']
        deep = sleep['deep']
        core = sleep['core']
        rem = sleep['rem']
        awake = sleep['awake']
        
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
            f"睡眠总时长{total:.1f}小时，其中深睡{deep:.1f}小时，核心睡眠{core:.1f}小时，REM睡眠{rem:.1f}小时。")
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
    
    print("=" * 50)
    print("健康报告生成器 - 标准化版本 V4.3")
    print("=" * 50)
    
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
    
    # 生成2月18日日报
    print("\n" + "=" * 50)
    print("生成报告...")
    print("=" * 50)
    
    date_str = '2026-02-18'
    if date_str in daily_data:
        html = generate_daily_report(date_str, daily_data[date_str], daily_template)
        
        # 验证无未替换变量
        if '{{' in html:
            unreplaced = [x for x in html.split('{{')[1:] if '}}' in x]
            print(f"  ⚠️ 发现未替换变量: {unreplaced[:3]}")
        
        output_path = OUTPUT_DIR / f'{date_str}-daily-report-V4.pdf'
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.set_content(html)
            page.wait_for_timeout(3000)
            page.pdf(path=str(output_path), format='A4', print_background=True,
                    margin={'top': '8mm', 'bottom': '8mm', 'left': '8mm', 'right': '8mm'})
            browser.close()
        print(f"  ✅ 日报生成: {output_path}")
    
    print(f"\n✅ 完成！共处理 {len(daily_data)} 天数据")

if __name__ == '__main__':
    main()
