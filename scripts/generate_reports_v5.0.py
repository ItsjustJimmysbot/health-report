#!/usr/bin/env python3
"""
健康报告生成器 - V5.0 个性化版
使用personalized_ai_analyzer生成详细、个性化的分析
"""
import json
import os
import sys
sys.path.insert(0, '/Users/jimmylu/.openclaw/workspace-health/scripts')

from datetime import datetime, timedelta
from pathlib import Path
from playwright.sync_api import sync_playwright
from personalized_ai_analyzer import generate_personalized_analysis, PersonalizedAIAnalyzer

HOME = Path.home()
HEALTH_DIR = HOME / '我的云端硬盘' / 'Health Auto Export' / 'Health Data'
WORKOUT_DIR = HOME / '我的云端硬盘' / 'Health Auto Export' / 'Workout Data'
TEMPLATE_DIR = HOME / '.openclaw' / 'workspace-health' / 'templates'
OUTPUT_DIR = HOME / '.openclaw' / 'workspace' / 'shared' / 'health-reports' / 'upload'
CACHE_DIR = HOME / '.openclaw' / 'workspace-health' / 'cache' / 'daily'

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(CACHE_DIR, exist_ok=True)

# ========== 标准化的评分计算函数 ==========
def calc_recovery_score(hrv, resting_hr, sleep_hours):
    score = 70
    if hrv and hrv > 50: score += 10
    if resting_hr and resting_hr < 65: score += 10
    if sleep_hours and sleep_hours > 7: score += 10
    return min(100, score)

def calc_sleep_score(sleep_hours, deep_hours, rem_hours):
    if not sleep_hours or sleep_hours == 0: return 0
    if sleep_hours < 6: score = 30
    elif sleep_hours < 7: score = 50
    elif sleep_hours < 8: score = 70
    else: score = 80
    if deep_hours and deep_hours >= 1.5: score += 10
    if rem_hours and rem_hours >= 1.5: score += 10
    return min(100, score)

def calc_exercise_score(steps, has_workout, energy_kcal):
    score = 50
    if steps >= 10000: score += 25
    elif steps >= 7000: score += 15
    elif steps >= 5000: score += 10
    if has_workout: score += 15
    if energy_kcal >= 500: score += 10
    return min(100, score)

# ========== 数据提取函数（与V4.5相同） ==========
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
    if not filepath.exists(): return None
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return {m['name']: m for m in data.get('data', {}).get('metrics', [])}

def parse_workout_data(date_str):
    filepath = WORKOUT_DIR / f'HealthAutoExport-{date_str}.json'
    if not filepath.exists(): return []
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    workouts = data.get('data', []) if isinstance(data.get('data'), list) else data.get('data', {}).get('workouts', [])
    
    result = []
    for w in workouts:
        energy_list = w.get('activeEnergy', [])
        if isinstance(energy_list, list) and energy_list: total_kj = sum(e.get('qty', 0) for e in energy_list)
        elif isinstance(energy_list, dict): total_kj = energy_list.get('qty', 0)
        else: total_kj = 0
        
        hr_data = w.get('heartRateData', [])
        hr_timeline = [{'time': hr.get('date', '').split(' ')[1][:5] if ' ' in hr.get('date', '') else '',
                       'avg': round(hr.get('Avg', 0)), 'max': hr.get('Max', 0), 'min': hr.get('Min', 0)} 
                      for hr in hr_data if 'Avg' in hr]
        
        if hr_timeline:
            avg_hr_calc = sum(h['avg'] for h in hr_timeline) / len(hr_timeline)
            max_hr_calc = max(h['max'] for h in hr_timeline)
        else: avg_hr_calc = max_hr_calc = None
        
        hr_field = w.get('heartRate', {})
        avg_hr = hr_field.get('avg', {}).get('qty') if isinstance(hr_field, dict) and hr_field.get('avg') else avg_hr_calc
        max_hr = hr_field.get('max', {}).get('qty') if isinstance(hr_field, dict) and hr_field.get('max') else max_hr_calc
        
        result.append({'name': w.get('name', '未知运动'), 'start': w.get('start', '')[:16] if w.get('start') else '',
                      'duration_min': round(w.get('duration', 0) / 60, 1), 'energy_kj': total_kj,
                      'energy_kcal': round(total_kj / 4.184, 0) if total_kj else 0,
                      'avg_hr': round(avg_hr) if avg_hr else None, 'max_hr': round(max_hr) if max_hr else None,
                      'hr_timeline': hr_timeline, 'hr_points': len(hr_timeline)})
    return result

def parse_sleep_data(date_str):
    date = datetime.strptime(date_str, '%Y-%m-%d')
    next_date = (date + timedelta(days=1)).strftime('%Y-%m-%d')
    filepath = HEALTH_DIR / f'HealthAutoExport-{next_date}.json'
    if not filepath.exists(): return None
    
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    metrics = {m['name']: m for m in data.get('data', {}).get('metrics', [])}
    sleep_metric = metrics.get('sleep_analysis', {})
    if not sleep_metric or not sleep_metric.get('data'): return None
    
    window_start = date.replace(hour=20, minute=0)
    window_end = (date + timedelta(days=1)).replace(hour=12, minute=0)
    
    sleep_records = []
    for sleep in sleep_metric.get('data', []):
        sleep_start_str = sleep.get('sleepStart', '')
        if not sleep_start_str: continue
        try:
            sleep_start = datetime.strptime(sleep_start_str[:19], '%Y-%m-%d %H:%M:%S')
            if window_start <= sleep_start <= window_end:
                asleep = sleep.get('asleep', 0) or sleep.get('totalSleep', 0)
                deep = sleep.get('deep', 0); core = sleep.get('core', 0); rem = sleep.get('rem', 0); awake = sleep.get('awake', 0)
                if asleep == 0 and (deep + core + rem + awake) > 0: asleep = deep + core + rem + awake
                sleep_records.append({'total': asleep, 'deep': deep, 'core': core, 'rem': rem, 'awake': awake,
                                     'sleep_start': sleep_start_str, 'sleep_end': sleep.get('sleepEnd', ''),
                                     'source_file': str(filepath)})
        except: continue
    
    if not sleep_records: return None
    return {'total': round(sum(r['total'] for r in sleep_records), 2),
            'deep': round(sum(r['deep'] for r in sleep_records), 2),
            'core': round(sum(r['core'] for r in sleep_records), 2),
            'rem': round(sum(r['rem'] for r in sleep_records), 2),
            'awake': round(sum(r['awake'] for r in sleep_records), 2),
            'records': sleep_records, 'source_file': sleep_records[0]['source_file']}

def extract_daily_data(date_str):
    metrics = parse_health_data(date_str)
    if not metrics: return None
    
    hrv, hrv_points = extract_metric_avg(metrics, 'heart_rate_variability')
    resting_hr, _ = extract_metric_avg(metrics, 'resting_heart_rate')
    steps, steps_points = extract_metric_sum(metrics, 'step_count')
    distance, _ = extract_metric_sum(metrics, 'walking_running_distance')
    active_energy_kj, _ = extract_metric_sum(metrics, 'active_energy')
    basal_energy_kj, _ = extract_metric_sum(metrics, 'basal_energy_burned')
    floors, _ = extract_metric_sum(metrics, 'flights_climbed')
    stand_min, _ = extract_metric_sum(metrics, 'apple_stand_time')
    
    spo2_raw, spo2_points = extract_metric_avg(metrics, 'blood_oxygen_saturation')
    if spo2_raw and spo2_raw > 1: spo2 = spo2_raw
    elif spo2_raw: spo2 = spo2_raw * 100
    else: spo2 = None
    
    resp_rate, _ = extract_metric_avg(metrics, 'respiratory_rate')
    active_energy_kcal = active_energy_kj / 4.184 if active_energy_kj else 0
    basal_energy_kcal = basal_energy_kj / 4.184 if basal_energy_kj else 0
    
    workouts = parse_workout_data(date_str)
    sleep = parse_sleep_data(date_str)
    
    return {'date': date_str, 'hrv': {'value': round(hrv, 1) if hrv else None, 'points': hrv_points},
            'resting_hr': {'value': round(resting_hr) if resting_hr else None},
            'steps': {'value': int(steps), 'points': steps_points}, 'distance': {'value': round(distance, 2)},
            'active_energy': {'value': round(active_energy_kcal), 'kj': active_energy_kj},
            'basal_energy': {'value': round(basal_energy_kcal), 'kj': basal_energy_kj},
            'floors': int(floors), 'stand_min': int(stand_min),
            'spo2': {'value': round(spo2, 1) if spo2 else None, 'points': spo2_points},
            'resp_rate': {'value': round(resp_rate, 1) if resp_rate else None},
            'workouts': workouts, 'has_workout': len(workouts) > 0, 'sleep': sleep,
            'scores': {'recovery': calc_recovery_score(hrv, resting_hr, sleep['total'] if sleep else 0),
                      'sleep': calc_sleep_score(sleep['total'] if sleep else 0, sleep['deep'] if sleep else 0, sleep['rem'] if sleep else 0) if sleep else 0,
                      'exercise': calc_exercise_score(int(steps) if steps else 0, len(workouts) > 0, active_energy_kcal)}}

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

# ========== 周报/月报个性化分析 ==========
def generate_weekly_personalized_analysis(weekly_data, avg_hrv, avg_steps, avg_sleep, workout_days):
    """生成周报个性化分析（每部分200-250字）"""
    
    # 计算波动范围
    hrv_values = [d['hrv']['value'] for d in weekly_data if d['hrv']['value']]
    hrv_min, hrv_max = min(hrv_values), max(hrv_values) if hrv_values else (0, 0)
    
    step_values = [d['steps']['value'] for d in weekly_data]
    step_min, step_max = min(step_values), max(step_values) if step_values else (0, 0)
    
    # 趋势分析
    hrv_trend = f"""本周HRV平均{avg_hrv:.1f}ms，波动范围{hrv_min:.1f}-{hrv_max:.1f}ms，标准差{((hrv_max-hrv_min)/2):.1f}ms。

从趋势看，本周HRV{'整体向好' if avg_hrv > 50 else '处于一般水平' if avg_hrv > 45 else '偏低'}。

结合睡眠数据（平均{avg_sleep:.1f}小时），{'充足睡眠有助于维持良好HRV' if avg_sleep >= 7 else '睡眠不足可能是HRV波动的因素' if avg_sleep < 6 else '睡眠对HRV影响需持续关注'}。

活动量方面（日均{int(avg_steps):,}步），{'适度活动有助于HRV稳定' if 6000 <= avg_steps <= 10000 else '活动量偏低或过高都可能影响恢复'}。

下周建议：{'保持当前作息，可尝试冥想优化' if avg_hrv > 50 else '优先保证7-8小时睡眠，降低训练强度' if avg_hrv <= 45 else '关注睡眠质量，适度增加活动量'}。"""
    
    activity_trend = f"""本周日均步数{int(avg_steps):,}步，波动范围{step_min:,}-{step_max:,}步，工作日与周末差异{abs(step_max-step_min):,}步。

从活动模式看，{'活动量相对稳定' if step_max - step_min < 5000 else '工作日与周末活动量差异较大，建议平衡'}。

{ '已达到推荐目标，有助于维持健康体重和心血管功能' if avg_steps >= 10000 else '距离10000步目标有差距，建议增加日常步行' if avg_steps < 8000 else '活动量基本达标，建议保持稳定并尝试挑战更高目标'}。

结合运动记录（{workout_days}天），{'结构化运动频率良好' if workout_days >= 3 else '建议增加结构化运动，目标每周3-4次'}。

下周目标：{'维持当前水平，尝试增加运动强度' if avg_steps >= 10000 else '日均步数提升至{int(avg_steps*1.2):,}步，增加1-2次结构化运动' if avg_steps < 8000 else '保持当前水平，关注活动强度'}."""
    
    return hrv_trend, activity_trend

def main():
    dates = ['2026-02-18', '2026-02-19', '2026-02-20', '2026-02-21', '2026-02-22']
    daily_data = {}
    
    print("=" * 60)
    print("健康报告生成器 - V5.0 个性化版")
    print("=" * 60)
    print("\n🆕 使用个性化AI分析模块")
    print("- 基于具体数据点生成洞察")
    print("- 指标间关联分析")
    print("- 可操作的个性化建议")
    
    # 读取模板
    with open(TEMPLATE_DIR / 'DAILY_TEMPLATE_V2.html', 'r', encoding='utf-8') as f:
        daily_template = f.read()
    
    # 提取数据
    for date in dates:
        print(f"\n📅 处理 {date}...")
        data = extract_daily_data(date)
        if data:
            daily_data[date] = data
            save_cache(data, date)
            print(f"  HRV: {data['hrv']['value']:.1f}ms | 步数: {data['steps']['value']:,} | 睡眠: {data['sleep']['total']:.1f}h" if data['sleep'] else f"  HRV: {data['hrv']['value']:.1f}ms | 步数: {data['steps']['value']:,} | 睡眠: 无数据")
    
    # 生成2月18日报表
    date_str = '2026-02-18'
    if date_str in daily_data:
        print("\n" + "=" * 60)
        print("生成个性化分析...")
        print("=" * 60)
        
        # 准备历史数据（前4天作为历史）
        history = [daily_data[d] for d in dates[:4] if d in daily_data and d != date_str]
        
        # 生成个性化分析
        analysis = generate_personalized_analysis(daily_data[date_str], history)
        
        print(f"\n📝 HRV分析 ({len(analysis['hrv_analysis'])}字):")
        print(analysis['hrv_analysis'][:150] + "...")
        
        print(f"\n😴 睡眠分析 ({len(analysis['sleep_analysis'])}字):")
        print(analysis['sleep_analysis'][:150] + "...")
        
        print(f"\n🏃 运动分析 ({len(analysis['workout_analysis'])}字):")
        print(analysis['workout_analysis'][:150] + "...")
        
        print(f"\n💡 最高优先级建议 ({len(analysis['priority_recommendation']['problem'])}字):")
        print(f"标题: {analysis['priority_recommendation']['title']}")
        print(analysis['priority_recommendation']['problem'][:150] + "...")
        
        print("\n✅ 日报生成完成（使用个性化AI分析）")

if __name__ == '__main__':
    main()
