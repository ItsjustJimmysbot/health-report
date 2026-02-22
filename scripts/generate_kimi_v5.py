#!/usr/bin/env python3
"""
健康报告生成器 - V5.0 Kimi AI版
使用Kimi API生成个性化、详细的健康分析
"""
import json
import os
import urllib.request
import urllib.error
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

# Kimi API配置
KIMI_API_URL = "https://api.moonshot.cn/v1/chat/completions"
KIMI_MODEL = "kimi-k2.5"  # 尝试使用正确的模型名称

def load_kimi_api_key():
    """加载Kimi API密钥"""
    # 首先检查环境变量
    api_key = os.getenv("KIMI_API_KEY", "")
    if api_key:
        return api_key
    
    # 然后检查本地文件
    env_file = Path('/Users/jimmylu/.openclaw/workspace-health/.env.kimi')
    if env_file.exists():
        with open(env_file, 'r') as f:
            for line in f:
                if line.startswith('KIMI_API_KEY='):
                    return line.strip().split('=', 1)[1]
    
    return None

def call_kimi_api(prompt, system_prompt=None):
    """调用Kimi API生成分析"""
    api_key = load_kimi_api_key()
    
    if not api_key:
        print("  ⚠️ 未找到Kimi API密钥")
        return None
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    
    data = {
        "model": KIMI_MODEL,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 1000
    }
    
    try:
        req = urllib.request.Request(
            KIMI_API_URL,
            data=json.dumps(data).encode('utf-8'),
            headers=headers,
            method='POST'
        )
        with urllib.request.urlopen(req, timeout=60) as response:
            result = json.loads(response.read().decode('utf-8'))
            return result['choices'][0]['message']['content']
    except urllib.error.HTTPError as e:
        print(f"  ⚠️ API HTTP错误: {e.code} - {e.reason}")
        try:
            error_body = e.read().decode('utf-8')
            print(f"     详情: {error_body[:200]}")
        except:
            pass
        return None
    except Exception as e:
        print(f"  ⚠️ API调用异常: {e}")
        return None

# ========== AI提示词模板 ==========

def generate_hrv_prompt(hrv_value, hrv_points, sleep_hours, steps, history_avg=None):
    """生成HRV分析提示词"""
    trend_text = f"较近期平均{'上升' if hrv_value > history_avg else '下降'}{abs(hrv_value - history_avg):.1f}ms" if history_avg else "暂无历史数据对比"
    sleep_comment = f"昨夜睡眠{sleep_hours:.1f}小时" if sleep_hours > 0 else "昨夜无睡眠数据"
    
    return f"""请基于以下具体数据生成HRV（心率变异性）健康分析，要求150-200字：

【用户今日数据】
- HRV数值：{hrv_value:.1f}ms（基于{hrv_points}个数据点测量）
- 趋势：{trend_text}
- {sleep_comment}
- 今日步数：{steps:,}步

【分析要求】
1. 开头必须引用具体HRV数值
2. 解释HRV的生理意义（自主神经系统平衡）
3. 结合睡眠和步数分析HRV状态
4. 给出1-2条具体、可操作的改善建议（含具体时间或方法）
5. 禁止使用"良好""注意"等模糊词汇，使用具体数值和判断
6. 字数控制在150-200字之间
7. 语气专业但易懂，像医生对患者说话

请直接输出分析文本，不要加标题或序号。"""

def generate_sleep_prompt(sleep_hours, has_stages, deep, core, rem, steps, hrv_value):
    """生成睡眠分析提示词"""
    if sleep_hours == 0:
        return f"""请基于以下情况生成睡眠健康分析，要求150-200字：

【用户情况】
- 今日未检测到睡眠数据
- 今日步数：{steps:,}步
- 今日HRV：{hrv_value:.1f}ms
- 活动消耗：{steps * 0.04:.0f}千卡（估算）

【分析要求】
1. 解释未记录睡眠的可能原因（Apple Watch设置、佩戴等）
2. 说明缺乏睡眠数据对恢复评估的影响
3. 结合今日活动量说明充足睡眠的重要性
4. 给出3-5条具体检查/改善步骤（具体到设置路径）
5. 禁止使用"注意休息"等模糊表达
6. 字数150-200字

请直接输出分析文本。"""
    
    stage_text = f"睡眠结构：深睡{deep:.1f}h/核心{core:.1f}h/REM{rem:.1f}h" if has_stages else "睡眠阶段数据未记录"
    
    return f"""请基于以下具体数据生成睡眠健康分析，要求150-200字：

【用户今日睡眠数据】
- 总睡眠时长：{sleep_hours:.1f}小时
- {stage_text}
- 今日步数：{steps:,}步
- 今日HRV：{hrv_value:.1f}ms

【分析要求】
1. 引用具体睡眠时长，与7-9小时推荐标准对比
2. 如有阶段数据，分析睡眠结构；如无，说明检查设置
3. 结合HRV和步数分析睡眠对恢复的影响
4. 给出具体改善建议（具体到就寝时间、环境调整）
5. 禁止使用"良好""适当"等模糊词，使用具体时间和数值
6. 字数150-200字

请直接输出分析文本。"""

def generate_workout_prompt(workout_name, duration, avg_hr, max_hr, energy, steps, sleep_hours, hrv_value):
    """生成运动分析提示词"""
    if not workout_name:
        return f"""请基于以下数据生成运动建议分析，要求150-200字：

【用户情况】
- 今日无结构化运动记录
- 今日步数：{steps:,}步
- 活动消耗：{energy:.0f}千卡
- HRV：{hrv_value:.1f}ms
- 昨夜睡眠：{sleep_hours:.1f}小时

【分析要求】
1. 基于HRV评估今日身体状态（{'>50适合运动' if hrv_value > 50 else '<40建议休息' if hrv_value < 40 else '可适度活动'}）
2. 解释缺乏结构化运动的健康影响（心血管、代谢等具体风险）
3. 给出具体运动建议：类型（快走/慢跑/游泳等）、时长（30-45分钟）、心率目标（120-140bpm）
4. 强调循序渐进建立习惯（从每周2-3次开始）
5. 使用具体数值，禁止模糊表达
6. 字数150-200字

请直接输出分析文本。"""
    
    # 心率区间判断
    if avg_hr and avg_hr > 160:
        zone, effect = "心率区间4-5（无氧/最大摄氧量区）", "主要提升无氧能力和乳酸阈值"
    elif avg_hr and avg_hr > 140:
        zone, effect = "心率区间3（乳酸阈值区）", "提升心肺耐力和脂肪燃烧效率"
    elif avg_hr and avg_hr > 120:
        zone, effect = "心率区间2（有氧基础区）", "增强有氧基础代谢和脂肪利用"
    else:
        zone, effect = "心率区间1（恢复区）", "促进恢复和基础有氧能力"
    
    recovery_risk = ""
    if sleep_hours < 6:
        recovery_risk = f"注意：昨夜仅睡{sleep_hours:.1f}小时，今日进行高强度运动可能增加过度训练风险，建议关注身体信号。"
    
    return f"""请基于以下具体数据生成运动健康分析，要求150-200字：

【用户今日运动数据】
- 运动类型：{workout_name}
- 时长：{duration:.0f}分钟
- 平均心率：{avg_hr}bpm，最高心率：{max_hr}bpm
- 消耗能量：{energy:.0f}千卡
- 昨夜睡眠：{sleep_hours:.1f}小时
- 今日步数：{steps:,}步

【分析要求】
1. 分析心率区间（{zone}）和训练效果（{effect}）
2. {recovery_risk if recovery_risk else '结合睡眠评估恢复状态'}
3. 结合HRV {hrv_value:.1f}ms评估训练是否适宜
4. 给出具体恢复建议（拉伸/营养/监测）
5. 使用具体数值，禁止模糊表达
6. 字数150-200字

请直接输出分析文本。"""

def generate_priority_recommendation_prompt(hrv_value, sleep_hours, steps, has_workout):
    """生成最高优先级建议提示词"""
    
    # 确定最紧急的问题
    if sleep_hours == 0:
        focus = "睡眠数据缺失"
        problem_detail = f"今日未检测到睡眠数据，无法评估昨夜恢复状态。"
        severity = "高"
    elif sleep_hours < 6:
        focus = "严重不足"
        problem_detail = f"昨夜仅睡{sleep_hours:.1f}小时，远低于7-9小时推荐标准。"
        severity = "极高"
    elif sleep_hours < 7:
        focus = "睡眠不足"
        problem_detail = f"昨夜睡眠{sleep_hours:.1f}小时，低于7-9小时推荐标准。"
        severity = "高"
    elif steps < 5000:
        focus = "活动量不足"
        problem_detail = f"今日仅{steps:,}步，属于久坐生活方式。"
        severity = "中"
    elif steps < 8000:
        focus = "活动量偏低"
        problem_detail = f"今日{steps:,}步，距离10000步目标有差距。"
        severity = "中"
    elif not has_workout:
        focus = "缺乏结构化运动"
        problem_detail = "日常步行达标但缺乏专门运动训练。"
        severity = "低"
    else:
        focus = "恢复优化"
        problem_detail = "整体状态良好，可进一步优化。"
        severity = "低"
    
    return f"""请为用户生成最高优先级健康建议，要求250-300字，分三部分：

【用户健康数据】
- HRV（心率变异性）：{hrv_value:.1f}ms
- 昨夜睡眠：{sleep_hours:.1f}小时
- 今日步数：{steps:,}步
- 有结构化运动：{'是' if has_workout else '否'}
- 最紧急问题：{focus}（严重程度：{severity}）

【输出格式要求】

标题：【最高优先级】+ 具体问题（如"改善睡眠时长至7小时"）

问题识别（80-100字）：
{problem_detail}说明短期影响（今日/本周）和长期健康风险（引用具体数据如"风险增加30%"）。结合HRV {hrv_value:.1f}ms分析当前身体状态。

行动计划（100-120字）：
列出5个具体步骤，每个必须包含：
- 具体时间（如22:30、21:30）
- 具体动作（如关闭手机、调暗灯光）
- 量化标准（如温度18-20°C、10分钟拉伸）

预期效果（70-80字）：
量化预期改善：
- 时间：3-5天/1周/2周
- 指标：HRV提升Xms、入睡时间缩短至X分钟、步数达到X步
- 主观感受：精力改善、效率提升

【禁止事项】
- 禁止使用"良好""注意""适当"等模糊表达
- 禁止缺乏具体时间/数值的建议
- 禁止无法量化的预期效果

请直接输出三部分内容，用【问题识别】【行动计划】【预期效果】标记。"""

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
                       'avg': round(hr.get('Avg', 0)), 'max': hr.get('Max', 0)} for hr in hr_data if 'Avg' in hr]
        
        if hr_timeline:
            avg_hr_calc = sum(h['avg'] for h in hr_timeline) / len(hr_timeline)
            max_hr_calc = max(h['max'] for h in hr_timeline)
        else: avg_hr_calc = max_hr_calc = None
        
        hr_field = w.get('heartRate', {})
        avg_hr = hr_field.get('avg', {}).get('qty') if isinstance(hr_field, dict) and hr_field.get('avg') else avg_hr_calc
        max_hr = hr_field.get('max', {}).get('qty') if isinstance(hr_field, dict) and hr_field.get('max') else max_hr_calc
        
        result.append({'name': w.get('name', '未知运动'), 'start': w.get('start', '')[:16] if w.get('start') else '',
                      'duration_min': round(w.get('duration', 0) / 60, 1), 'energy_kcal': round(total_kj / 4.184) if total_kj else 0,
                      'avg_hr': round(avg_hr) if avg_hr else None, 'max_hr': round(max_hr) if max_hr else None,
                      'hr_timeline': hr_timeline})
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
                deep = sleep.get('deep', 0); core = sleep.get('core', 0); rem = sleep.get('rem', 0)
                if asleep == 0 and (deep + core + rem) > 0: asleep = deep + core + rem
                sleep_records.append({'total': asleep, 'deep': deep, 'core': core, 'rem': rem, 'awake': sleep.get('awake', 0)})
        except: continue
    
    if not sleep_records: return None
    return {'total': round(sum(r['total'] for r in sleep_records), 2),
            'deep': round(sum(r['deep'] for r in sleep_records), 2),
            'core': round(sum(r['core'] for r in sleep_records), 2),
            'rem': round(sum(r['rem'] for r in sleep_records), 2),
            'awake': round(sum(r['awake'] for r in sleep_records), 2)}

def extract_daily_data(date_str):
    metrics = parse_health_data(date_str)
    if not metrics: return None
    
    hrv, hrv_points = extract_metric_avg(metrics, 'heart_rate_variability')
    resting_hr, _ = extract_metric_avg(metrics, 'resting_heart_rate')
    steps, _ = extract_metric_sum(metrics, 'step_count')
    active_energy_kj, _ = extract_metric_sum(metrics, 'active_energy')
    
    spo2_raw, _ = extract_metric_avg(metrics, 'blood_oxygen_saturation')
    spo2 = spo2_raw if spo2_raw and spo2_raw > 1 else (spo2_raw * 100 if spo2_raw else None)
    
    workouts = parse_workout_data(date_str)
    sleep = parse_sleep_data(date_str)
    
    return {
        'date': date_str,
        'hrv': {'value': round(hrv, 1) if hrv else None, 'points': hrv_points},
        'resting_hr': {'value': round(resting_hr) if resting_hr else None},
        'steps': int(steps),
        'active_energy': round(active_energy_kj / 4.184) if active_energy_kj else 0,
        'spo2': round(spo2, 1) if spo2 else None,
        'workouts': workouts,
        'has_workout': len(workouts) > 0,
        'sleep': sleep
    }

def save_cache(data, date_str):
    cache_path = CACHE_DIR / f'{date_str}.json'
    with open(cache_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def generate_daily_report_kimi(date_str):
    """使用Kimi API生成日报"""
    print(f"\n{'='*60}")
    print(f"生成 {date_str} 日报 - 使用Kimi AI")
    print('='*60)
    
    # 提取数据
    data = extract_daily_data(date_str)
    if not data:
        print(f"❌ 无法提取 {date_str} 数据")
        return None
    
    save_cache(data, date_str)
    print(f"\n📊 基础数据:")
    print(f"  HRV: {data['hrv']['value']:.1f}ms ({data['hrv']['points']}点)")
    print(f"  步数: {data['steps']:,}")
    print(f"  睡眠: {data['sleep']['total']:.1f}h" if data['sleep'] else "  睡眠: 无数据")
    print(f"  运动: {data['workouts'][0]['name'] if data['has_workout'] else '无'}")
    
    # 加载历史数据
    history = []
    for d in ['2026-02-19', '2026-02-20', '2026-02-21', '2026-02-22']:
        cache_path = CACHE_DIR / f'{d}.json'
        if cache_path.exists():
            with open(cache_path, 'r') as f:
                history.append(json.load(f))
    
    history_hrv = [h['hrv']['value'] for h in history if h.get('hrv', {}).get('value')]
    history_avg = sum(history_hrv) / len(history_hrv) if history_hrv else None
    
    analyses = {}
    
    # 1. HRV分析
    print("\n🤖 调用Kimi生成HRV分析...")
    hrv_prompt = generate_hrv_prompt(
        data['hrv']['value'], data['hrv']['points'],
        data['sleep']['total'] if data['sleep'] else 0,
        data['steps'], history_avg
    )
    hrv_analysis = call_kimi_api(hrv_prompt, "你是一位专业的健康数据分析师，擅长基于具体数据生成个性化健康洞察。")
    if hrv_analysis:
        analyses['hrv'] = hrv_analysis
        print(f"  ✅ 完成 ({len(hrv_analysis)}字)")
        print(f"  预览: {hrv_analysis[:80]}...")
    else:
        print("  ❌ 生成失败")
        return None
    
    # 2. 睡眠分析
    print("\n🤖 调用Kimi生成睡眠分析...")
    sleep_prompt = generate_sleep_prompt(
        data['sleep']['total'] if data['sleep'] else 0,
        data['sleep']['deep'] > 0 if data['sleep'] else False,
        data['sleep']['deep'] if data['sleep'] else 0,
        data['sleep']['core'] if data['sleep'] else 0,
        data['sleep']['rem'] if data['sleep'] else 0,
        data['steps'], data['hrv']['value']
    )
    sleep_analysis = call_kimi_api(sleep_prompt, "你是一位专业的睡眠医学专家，擅长基于睡眠数据生成个性化分析和建议。")
    if sleep_analysis:
        analyses['sleep'] = sleep_analysis
        print(f"  ✅ 完成 ({len(sleep_analysis)}字)")
    else:
        print("  ❌ 生成失败")
        return None
    
    # 3. 运动分析
    print("\n🤖 调用Kimi生成运动分析...")
    w = data['workouts'][0] if data['has_workout'] else None
    workout_prompt = generate_workout_prompt(
        w['name'] if w else None, w['duration_min'] if w else 0,
        w['avg_hr'] if w else None, w['max_hr'] if w else None,
        w['energy_kcal'] if w else 0, data['steps'],
        data['sleep']['total'] if data['sleep'] else 0, data['hrv']['value']
    )
    workout_analysis = call_kimi_api(workout_prompt, "你是一位专业的运动医学专家，擅长基于运动数据生成个性化训练分析和恢复建议。")
    if workout_analysis:
        analyses['workout'] = workout_analysis
        print(f"  ✅ 完成 ({len(workout_analysis)}字)")
    else:
        print("  ❌ 生成失败")
        return None
    
    # 4. 最高优先级建议
    print("\n🤖 调用Kimi生成最高优先级建议...")
    priority_prompt = generate_priority_recommendation_prompt(
        data['hrv']['value'], data['sleep']['total'] if data['sleep'] else 0,
        data['steps'], data['has_workout']
    )
    priority = call_kimi_api(priority_prompt, "你是一位专业的健康管理师，擅长基于健康数据生成优先级明确的可执行建议。")
    if priority:
        analyses['priority'] = priority
        print(f"  ✅ 完成 ({len(priority)}字)")
    else:
        print("  ❌ 生成失败")
        return None
    
    # 保存AI分析结果
    analysis_path = CACHE_DIR / f'{date_str}_kimi_analysis.json'
    with open(analysis_path, 'w', encoding='utf-8') as f:
        json.dump(analyses, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ Kimi AI分析已保存: {analysis_path}")
    return analyses

def main():
    print("="*60)
    print("健康报告生成器 - V5.0 Kimi AI版")
    print("="*60)
    
    # 检查API密钥
    api_key = load_kimi_api_key()
    if not api_key:
        print("\n❌ 错误：未找到Kimi API密钥")
        print("请设置环境变量：export KIMI_API_KEY='your-key'")
        print("或在 .env.kimi 文件中设置")
        return
    
    print(f"\n✅ Kimi API密钥已加载 ({len(api_key)}字符)")
    
    # 生成2月18日报表
    analyses = generate_daily_report_kimi('2026-02-18')
    
    if analyses:
        print("\n" + "="*60)
        print("生成的AI分析内容：")
        print("="*60)
        print("\n【HRV分析】")
        print(analyses['hrv'])
        print("\n【睡眠分析】")
        print(analyses['sleep'])
        print("\n【运动分析】")
        print(analyses['workout'])
        print("\n【最高优先级建议】")
        print(analyses['priority'])

if __name__ == '__main__':
    main()
