#!/usr/bin/env python3
"""
周报和月报生成器 - V5.7.1 Medical Dashboard版 (支持多语言 CN/EN)
使用新模板 WEEKLY_TEMPLATE_MEDICAL.html / MONTHLY_TEMPLATE_MEDICAL.html
用法:
  python3 scripts/generate_weekly_monthly_medical.py weekly <start_date> <end_date> < ai_analysis.json
  python3 scripts/generate_weekly_monthly_medical.py monthly <year> <month> < ai_analysis.json
"""
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from playwright.sync_api import sync_playwright

HOME = Path.home()
TEMPLATE_DIR = Path(__file__).parent.parent / 'templates'

# ==================== 配置加载 ====================
def load_config():
    """从 config.json 加载配置"""
    config_paths = [
        Path(__file__).parent.parent / "config.json",
        HOME / '.openclaw' / 'workspace-health' / 'config.json',
    ]
    
    for config_path in config_paths:
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
    
    # 默认配置
    return {
        "version": "5.7.1",
        "members": [{
            "name": "默认用户",
            "health_dir": "~/我的云端硬盘/Health Auto Export/Health Data",
            "workout_dir": "~/我的云端硬盘/Health Auto Export/Workout Data",
            "email": ""
        }],
        "language": "CN"
    }

# 加载配置
CONFIG = load_config()
LANGUAGE = CONFIG.get("language", "CN")
VALIDATION_MODE = CONFIG.get("validation_mode", "strict")

OUTPUT_DIR = Path(CONFIG.get("output_dir", str(Path(__file__).parent.parent / 'output'))).expanduser()
CACHE_DIR = Path(CONFIG.get("cache_dir", str(Path(__file__).parent.parent / 'cache' / 'daily'))).expanduser()
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# ==================== 验证函数 ====================
def verify_ai_analysis_weekly(ai_analysis):
    """验证周报AI分析字数"""
    errors = []
    total_text = ""
    
    # 收集所有文本
    trend_analysis = ai_analysis.get('trend_analysis') or ai_analysis.get('weekly_analysis', '')
    total_text += trend_analysis
    
    recommendations = ai_analysis.get('recommendations', [])
    for rec in recommendations:
        total_text += rec.get('title', '')
        total_text += rec.get('content', '')
    
    # 检查周报总字数（要求≥800字）
    if len(total_text) < 800:
        errors.append(f"❌ 周报总字数不足: {len(total_text)}字 (要求≥800字)")
    
    return errors

def verify_ai_analysis_monthly(ai_analysis):
    """验证月报AI分析字数"""
    errors = []
    total_text = ""
    
    # 收集所有文本
    hrv_analysis = ai_analysis.get('hrv_analysis') or ai_analysis.get('monthly_analysis', '')
    sleep_analysis = ai_analysis.get('sleep_analysis', '')
    activity_analysis = ai_analysis.get('activity_analysis') or ai_analysis.get('key_findings', '')
    trend_assessment = ai_analysis.get('trend_assessment') or ai_analysis.get('trend_forecast', '')
    
    total_text += hrv_analysis + sleep_analysis + activity_analysis + trend_assessment
    
    recommendations = ai_analysis.get('recommendations', [])
    for rec in recommendations:
        total_text += rec.get('title', '')
        total_text += rec.get('content', '')
    
    # 检查月报总字数（要求≥1000字）
    if len(total_text) < 1000:
        errors.append(f"❌ 月报总字数不足: {len(total_text)}字 (要求≥1000字)")
    
    # 同时检查 trend_assessment 单独字数（原逻辑保留）
    trend_text_clean = trend_assessment.replace('<strong>', '').replace('</strong>', '').replace('<br>', '').replace('\n', '')
    if len(trend_text_clean) < 150:
        errors.append(f"❌ 月报趋势评估字数不足: {len(trend_text_clean)}字 (要求≥150字)")
    
    return errors

# ==================== 趋势计算函数 ====================
def load_previous_period_data(current_dates, member_name="默认用户"):
    """加载上一周期（7天前）的数据用于趋势对比"""
    if not current_dates:
        return []
    
    # 计算7天前的对应日期
    previous_dates = []
    for date_str in current_dates:
        date = datetime.strptime(date_str, '%Y-%m-%d')
        prev_date = date - timedelta(days=7)
        previous_dates.append(prev_date.strftime('%Y-%m-%d'))
    
    previous_data = []
    for date in previous_dates:
        data = load_cache(date, member_name)
        if data:
            previous_data.append(data)
    
    return previous_data

def calculate_trend(current_values, previous_values):
    """计算趋势变化（环比）"""
    if not current_values or not previous_values:
        return 0, 'stable'
    
    current_avg = sum(current_values) / len(current_values)
    previous_avg = sum(previous_values) / len(previous_values)
    
    if previous_avg == 0:
        return 0, 'stable'
    
    change_pct = ((current_avg - previous_avg) / previous_avg) * 100
    
    if change_pct > 5:
        return change_pct, 'increase'
    elif change_pct < -5:
        return change_pct, 'decrease'
    else:
        return change_pct, 'stable'

def get_trend_html(change_pct, trend_type):
    """生成趋势变化HTML"""
    if trend_type == 'increase':
        return f"↑ {change_pct:+.1f}%", 'change-up'
    elif trend_type == 'decrease':
        return f"↓ {change_pct:+.1f}%", 'change-down'
    else:
        return "→ 持平", 'change-stable'

# 多语言文本
def get_text(key):
    """获取多语言文本"""
    texts = {
        "CN": {
            "no_trend_data": "暂无趋势数据",
            "no_monthly_data": "暂无月度趋势数据",
            "date": "日期",
            "hrv": "HRV",
            "steps": "步数",
            "sleep": "睡眠",
            "active_energy": "活动能量",
            "workout": "运动",
            "recovery": "恢复度",
            "week": "周",
            "high_priority": "🔴 高优先级",
            "medium_priority": "🟡 中优先级",
            "low_priority": "🔵 低优先级",
            "good": "良好",
            "days": "天",
        },
        "EN": {
            "no_trend_data": "No trend data available",
            "no_monthly_data": "No monthly trend data available",
            "date": "Date",
            "hrv": "HRV",
            "steps": "Steps",
            "sleep": "Sleep",
            "active_energy": "Active Energy",
            "workout": "Workout",
            "recovery": "Recovery",
            "week": "Week",
            "high_priority": "🔴 High Priority",
            "medium_priority": "🟡 Medium Priority",
            "low_priority": "🔵 Low Priority",
            "good": "Good",
            "days": "days",
        }
    }
    return texts.get(LANGUAGE, texts["CN"]).get(key, key)

def load_cache(date_str, member_name="默认用户"):
    """加载单日缓存数据"""
    # 优先尝试带成员名的缓存
    cache_path = CACHE_DIR / f'{date_str}_{member_name}.json'
    if not cache_path.exists():
        # 回退到无成员名的旧格式
        cache_path = CACHE_DIR / f'{date_str}.json'
    
    if cache_path.exists():
        with open(cache_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

def _build_chartjs_template(canvas_id, display_dates, hrv_values, steps_values, sleep_values, lang_labels, height_px):
    return f'''<div style="height: {height_px}px;">
  <canvas id="{canvas_id}"></canvas>
</div>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<script>
  const ctx = document.getElementById('{canvas_id}').getContext('2d');
  new Chart(ctx, {{
    type: 'line',
    data: {{
      labels: {display_dates},
      datasets: [
        {{
          label: '{lang_labels["hrv"]}',
          data: {hrv_values},
          borderColor: '#22C55E',
          backgroundColor: 'rgba(34, 197, 94, 0.1)',
          yAxisID: 'y',
          tension: 0.3,
          fill: true,
          pointRadius: 5,
          pointHoverRadius: 7
        }},
        {{
          label: '{lang_labels["steps"]}',
          data: [{','.join([str(s/1000) for s in steps_values])}],
          borderColor: '#3B82F6',
          backgroundColor: 'rgba(59, 130, 246, 0.1)',
          yAxisID: 'y1',
          tension: 0.3,
          fill: true,
          pointRadius: 5,
          pointHoverRadius: 7
        }},
        {{
          label: '{lang_labels["sleep"]}',
          data: {sleep_values},
          borderColor: '#A855F7',
          backgroundColor: 'rgba(168, 85, 247, 0.1)',
          yAxisID: 'y2',
          tension: 0.3,
          fill: true,
          pointRadius: 5,
          pointHoverRadius: 7
        }}
      ]
    }},
    options: {{
      responsive: true,
      maintainAspectRatio: false,
      interaction: {{
        mode: 'index',
        intersect: false,
      }},
      plugins: {{
        legend: {{
          position: 'top',
          labels: {{ font: {{ size: 12 }} }}
        }},
        title: {{
          display: true,
          text: '{lang_labels["title"]}',
          font: {{ size: 14 }}
        }}
      }},
      scales: {{
        y: {{
          type: 'linear',
          display: true,
          position: 'left',
          title: {{ display: true, text: 'HRV (ms)' }},
          min: 40,
          max: 60
        }},
        y1: {{
          type: 'linear',
          display: true,
          position: 'right',
          title: {{ display: true, text: '{lang_labels["steps"]}' }},
          min: 0,
          max: 8,
          grid: {{ drawOnChartArea: false }}
        }},
        y2: {{
          type: 'linear',
          display: true,
          position: 'right',
          title: {{ display: true, text: '{lang_labels["sleep"]}' }},
          min: 0,
          max: 10,
          grid: {{ drawOnChartArea: false }}
        }}
      }}
    }}
  }});
</script>'''

def generate_trend_chart(dates, hrv_values, steps_values, sleep_values, chart_type='weekly'):
    """生成Chart.js趋势图表"""
    if not dates or not hrv_values:
        return f'<div style="text-align:center;color:#999;padding:40px;">{get_text("no_trend_data")}</div>'
    
    # 格式化日期显示
    display_dates = [d[5:] if len(d) > 5 else d for d in dates]
    
    # 多语言图表标签
    labels = {
        "CN": {"hrv": "HRV (ms)", "steps": "步数 (÷1000)", "sleep": "睡眠 (h)", "title": "HRV · 步数 · 睡眠 趋势"},
        "EN": {"hrv": "HRV (ms)", "steps": "Steps (÷1000)", "sleep": "Sleep (h)", "title": "HRV · Steps · Sleep Trends"}
    }
    lang_labels = labels.get(LANGUAGE, labels["CN"])
    
    return _build_chartjs_template('trendChart', display_dates, hrv_values, steps_values, sleep_values, lang_labels, 250)

def generate_monthly_chart(dates, hrv_values, steps_values, sleep_values):
    """生成月度Chart.js趋势图表"""
    if not dates or not hrv_values:
        return f'<div style="text-align:center;color:#999;padding:40px;">{get_text("no_monthly_data")}</div>'
    
    # 格式化日期显示 (只显示日)
    if LANGUAGE == "CN":
        display_dates = [d[8:10] + '日' if len(d) >= 10 else d for d in dates]
    else:
        display_dates = [d[8:10] if len(d) >= 10 else d for d in dates]
    
    # 多语言图表标签
    labels = {
        "CN": {"hrv": "HRV (ms)", "steps": "步数 (÷1000)", "sleep": "睡眠 (h)", "title": "月度 HRV · 步数 · 睡眠 趋势"},
        "EN": {"hrv": "HRV (ms)", "steps": "Steps (÷1000)", "sleep": "Sleep (h)", "title": "Monthly HRV · Steps · Sleep Trends"}
    }
    lang_labels = labels.get(LANGUAGE, labels["CN"])
    
    return _build_chartjs_template('monthlyChart', display_dates, hrv_values, steps_values, sleep_values, lang_labels, 280)

def generate_weekly_report(start_date, end_date, ai_analysis, template, member_name="默认用户"):
    """生成周报 - 使用Medical Dashboard模板"""
    
    # 计算日期范围
    start = datetime.strptime(start_date, '%Y-%m-%d')
    end = datetime.strptime(end_date, '%Y-%m-%d')
    week_dates = []
    current = start
    while current <= end:
        week_dates.append(current.strftime('%Y-%m-%d'))
        current += timedelta(days=1)
    
    # 加载每日数据
    weekly_data = []
    for date in week_dates:
        data = load_cache(date, member_name)
        if data:
            weekly_data.append(data)
    
    if not weekly_data:
        print(f"⚠️ 警告: 未找到 {start_date} 至 {end_date} 的缓存数据")
        return None
    
    # 计算统计数据
    hrv_values = [d['hrv']['value'] for d in weekly_data if d.get('hrv', {}).get('value')]
    steps_values = [d['steps'] for d in weekly_data if d.get('steps')]
    sleep_values = [d['sleep']['total'] for d in weekly_data if d.get('sleep', {}).get('total')]
    workout_days = sum(1 for d in weekly_data if d.get('has_workout'))
    
    avg_hrv = sum(hrv_values) / len(hrv_values) if hrv_values else 0
    avg_steps = sum(steps_values) / len(steps_values) if steps_values else 0
    avg_sleep = sum(sleep_values) / len(sleep_values) if sleep_values else 0
    
    # 生成每日明细行
    daily_rows = []
    for date in week_dates:
        data = load_cache(date, member_name)
        if data:
            workout_mark = '✓' if data['has_workout'] else '-'
            row = f"""<tr>
                <td>{date[5:]}</td>
                <td class="cell-primary">{data['hrv']['value']:.1f}</td>
                <td class="cell-primary">{data['steps']:,}</td>
                <td class="cell-primary">{data['sleep']['total']:.1f}h</td>
                <td>{data['active_energy']}kcal</td>
                <td>{workout_mark}</td>
                <td><span class="rating rating-good">{get_text('good')}</span></td>
            </tr>"""
            daily_rows.append(row)
    
    # 填充模板
    html = template
    html = html.replace('{{START_DATE}}', start_date)
    html = html.replace('{{END_DATE}}', end_date)
    week_num = start.isocalendar()[1]
    if LANGUAGE == "EN":
        html = html.replace('{{WEEK_RANGE}}', f"Week {week_num}")
    else:
        html = html.replace('{{WEEK_RANGE}}', f"第{week_num}周")
    html = html.replace('{{DAYS_COUNT}}', str(len(weekly_data)))
    
    # 概览数据
    html = html.replace('{{AVG_HRV}}', f"{avg_hrv:.1f}")
    html = html.replace('{{AVG_STEPS}}', f"{int(avg_steps):,}")
    html = html.replace('{{AVG_SLEEP}}', f"{avg_sleep:.1f}")
    html = html.replace('{{WORKOUT_DAYS}}', str(workout_days))
    html = html.replace('{{WORKOUT_RATIO}}', f"{workout_days}/{len(weekly_data)} {get_text('days')}")
    
    # 验证AI分析字数
    print(f"📏 验证AI分析字数...")
    validation_errors = verify_ai_analysis_weekly(ai_analysis)
    if validation_errors:
        print(f"⚠️  发现 {len(validation_errors)} 处字数不足:")
        for error in validation_errors:
            print(f"   {error}")
        if VALIDATION_MODE == "strict":
            print(f"❌ 严格模式: 字数验证失败，停止生成")
            return None
        else:
            print(f"⚠️ 警告模式: 继续生成，但请注意内容可能不够详细")
    else:
        print(f"   ✅ 字数验证通过")
    
    # 加载上一周期数据用于趋势对比
    print(f"📊 计算趋势变化...")
    previous_data = load_previous_period_data(week_dates, member_name)
    
    # 计算趋势变化
    if previous_data:
        prev_hrv = [d['hrv']['value'] for d in previous_data if d.get('hrv', {}).get('value')]
        prev_steps = [d['steps'] for d in previous_data if d.get('steps')]
        prev_sleep = [d['sleep']['total'] for d in previous_data if d.get('sleep', {}).get('total')]
        
        hrv_change_pct, hrv_trend = calculate_trend(hrv_values, prev_hrv)
        steps_change_pct, steps_trend = calculate_trend(steps_values, prev_steps)
        sleep_change_pct, sleep_trend = calculate_trend(sleep_values, prev_sleep)
        
        hrv_change_html, hrv_class = get_trend_html(hrv_change_pct, hrv_trend)
        steps_change_html, steps_class = get_trend_html(steps_change_pct, steps_trend)
        sleep_change_html, sleep_class = get_trend_html(sleep_change_pct, sleep_trend)
        
        print(f"   HRV: {hrv_change_html}, 步数: {steps_change_html}, 睡眠: {sleep_change_html}")
    else:
        print(f"   ⚠️  未找到上一周期数据，趋势显示为持平")
        hrv_change_html, hrv_class = get_trend_html(0, 'stable')
        steps_change_html, steps_class = get_trend_html(0, 'stable')
        sleep_change_html, sleep_class = get_trend_html(0, 'stable')
    
    # 趋势变化
    html = html.replace('{{HRV_CHANGE}}', hrv_change_html)
    html = html.replace('{{STEPS_CHANGE}}', steps_change_html)
    html = html.replace('{{SLEEP_CHANGE}}', sleep_change_html)
    html = html.replace('{{HRV_TREND_CLASS}}', hrv_class)
    html = html.replace('{{STEPS_TREND_CLASS}}', steps_class)
    html = html.replace('{{SLEEP_TREND_CLASS}}', sleep_class)
    
    # 表格和AI分析
    html = html.replace('{{DAILY_ROWS}}', '\n'.join(daily_rows))
    
    # 生成真实趋势图表
    trend_chart = generate_trend_chart(week_dates, hrv_values, steps_values, sleep_values, 'weekly')
    html = html.replace('{{TREND_CHART}}', trend_chart)
    
    # AI趋势分析 - 严格检查，必须在当前session生成
    trend_analysis = ai_analysis.get('trend_analysis') or ai_analysis.get('weekly_analysis')
    if not trend_analysis:
        raise ValueError("❌ 错误: 缺少周报AI趋势分析 - 必须在当前AI对话中生成")
    html = html.replace('{{TREND_ANALYSIS}}', trend_analysis.replace('\n', '<br>'))
    
    # 下周建议 - 严格检查，必须在当前session生成
    recommendations = ai_analysis.get('recommendations', [])
    if not recommendations:
        raise ValueError("❌ 错误: 缺少周报下周建议 - 必须在当前AI对话中生成（recommendations数组或priority/ai字段）")
    
    html = html.replace('{{RECOMMENDATIONS}}', generate_recommendations_html(recommendations))
    html = html.replace('{{DATA_SOURCE}}', 'Apple Health')
    
    return html

def generate_monthly_report(year, month, ai_analysis, template, member_name="默认用户"):
    """生成月报 - 使用Medical Dashboard模板"""
    
    # 计算月份天数
    if month == 12:
        next_month = datetime(year + 1, 1, 1)
    else:
        next_month = datetime(year, month + 1, 1)
    last_day = (next_month - timedelta(days=1)).day
    
    # 加载整月数据
    month_dates = [f"{year}-{month:02d}-{day:02d}" for day in range(1, last_day + 1)]
    monthly_data = []
    for date in month_dates:
        data = load_cache(date, member_name)
        if data:
            monthly_data.append(data)
    
    if not monthly_data:
        print(f"⚠️ 警告: 未找到 {year}-{month:02d} 的缓存数据")
        return None
    
    # 按周汇总
    weeks = {}
    for data in monthly_data:
        date = datetime.strptime(data['date'], '%Y-%m-%d')
        week_num = date.isocalendar()[1]
        if week_num not in weeks:
            weeks[week_num] = []
        weeks[week_num].append(data)
    
    # 计算每周统计
    weekly_rows = []
    for week_num, week_data in sorted(weeks.items()):
        hrv_values = [d['hrv']['value'] for d in week_data if d.get('hrv', {}).get('value')]
        steps_values = [d['steps'] for d in week_data if d.get('steps')]
        sleep_values = [d['sleep']['total'] for d in week_data if d.get('sleep', {}).get('total')]
        workout_days = sum(1 for d in week_data if d.get('has_workout'))
        
        avg_hrv = sum(hrv_values) / len(hrv_values) if hrv_values else 0
        avg_steps = sum(steps_values) / len(steps_values) if steps_values else 0
        avg_sleep = sum(sleep_values) / len(sleep_values) if sleep_values else 0
        
        row = f"""<tr>
            <td>{get_text('week')} {week_num}</td>
            <td class="cell-primary">{avg_hrv:.1f}</td>
            <td class="cell-primary">{int(avg_steps):,}</td>
            <td class="cell-primary">{avg_sleep:.1f}h</td>
            <td>{workout_days} {get_text('days')}</td>
            <td><span class="rating rating-good">{get_text('good')}</span></td>
        </tr>"""
        weekly_rows.append(row)
    
    # 计算全月统计
    hrv_values = [d['hrv']['value'] for d in monthly_data if d.get('hrv', {}).get('value')]
    steps_values = [d['steps'] for d in monthly_data if d.get('steps')]
    sleep_values = [d['sleep']['total'] for d in monthly_data if d.get('sleep', {}).get('total')]
    active_energy_values = [d.get('active_energy', 0) for d in monthly_data if d.get('active_energy')]
    stand_time_values = [d.get('apple_stand_time', 0) for d in monthly_data if d.get('apple_stand_time')]
    workout_days = sum(1 for d in monthly_data if d.get('has_workout'))
    
    # 提取实际有数据的日期（用于图表X轴）
    actual_dates = [d['date'] for d in monthly_data]
    
    avg_hrv = sum(hrv_values) / len(hrv_values) if hrv_values else 0
    avg_steps = sum(steps_values) / len(steps_values) if steps_values else 0
    avg_sleep = sum(sleep_values) / len(sleep_values) if sleep_values else 0
    avg_calories = sum(active_energy_values) / len(active_energy_values) if active_energy_values else 0
    avg_stand = sum(stand_time_values) / len(stand_time_values) / 60 if stand_time_values else 0  # 转换为小时
    
    # 填充模板
    html = template
    html = html.replace('{{YEAR}}', str(year))
    html = html.replace('{{MONTH}}', str(month))
    html = html.replace('{{DAYS_COUNT}}', str(len(monthly_data)))
    html = html.replace('{{WEEKS_COUNT}}', str(len(weeks)))
    
    # 概览数据
    html = html.replace('{{AVG_HRV}}', f"{avg_hrv:.1f}")
    html = html.replace('{{AVG_STEPS}}', f"{int(avg_steps):,}")
    html = html.replace('{{AVG_SLEEP}}', f"{avg_sleep:.1f}")
    html = html.replace('{{WORKOUT_DAYS}}', str(workout_days))
    html = html.replace('{{WORKOUT_RATIO}}', f"{workout_days}/{len(monthly_data)} {get_text('days')}")
    html = html.replace('{{AVG_CALORIES}}', f"{int(avg_calories):,}")
    html = html.replace('{{AVG_STAND}}', f"{avg_stand:.1f}")
    
    # 验证AI分析字数
    print(f"📏 验证AI分析字数...")
    validation_errors = verify_ai_analysis_monthly(ai_analysis)
    if validation_errors:
        print(f"⚠️  发现 {len(validation_errors)} 处字数不足:")
        for error in validation_errors:
            print(f"   {error}")
        if VALIDATION_MODE == "strict":
            print(f"❌ 严格模式: 字数验证失败，停止生成")
            return None
        else:
            print(f"⚠️ 警告模式: 继续生成，但请注意内容可能不够详细")
    else:
        print(f"   ✅ 字数验证通过")
    
    # 加载上一周期数据用于趋势对比（上月同期）
    print(f"📊 计算趋势变化...")
    # 计算上月日期范围
    if month == 1:
        prev_month = 12
        prev_year = year - 1
    else:
        prev_month = month - 1
        prev_year = year
    
    # 简化为加载上月同日的数据（大致范围）
    prev_month_dates = [f"{prev_year}-{prev_month:02d}-{d['date'][8:10]}" for d in monthly_data if d.get('date')]
    previous_data = []
    for date in prev_month_dates:
        data = load_cache(date, member_name)
        if data:
            previous_data.append(data)
    
    # 计算趋势变化
    if previous_data:
        prev_hrv = [d['hrv']['value'] for d in previous_data if d.get('hrv', {}).get('value')]
        prev_steps = [d['steps'] for d in previous_data if d.get('steps')]
        prev_sleep = [d['sleep']['total'] for d in previous_data if d.get('sleep', {}).get('total')]
        prev_calories = [d.get('active_energy', 0) for d in previous_data if d.get('active_energy')]
        prev_stand = [d.get('apple_stand_time', 0) for d in previous_data if d.get('apple_stand_time')]
        
        hrv_change_pct, hrv_trend = calculate_trend(hrv_values, prev_hrv)
        steps_change_pct, steps_trend = calculate_trend(steps_values, prev_steps)
        sleep_change_pct, sleep_trend = calculate_trend(sleep_values, prev_sleep)
        calories_change_pct, calories_trend = calculate_trend(active_energy_values, prev_calories)
        stand_change_pct, stand_trend = calculate_trend(stand_time_values, prev_stand)
        
        hrv_change_html, hrv_class = get_trend_html(hrv_change_pct, hrv_trend)
        steps_change_html, steps_class = get_trend_html(steps_change_pct, steps_trend)
        sleep_change_html, sleep_class = get_trend_html(sleep_change_pct, sleep_trend)
        calories_change_html, calories_class = get_trend_html(calories_change_pct, calories_trend)
        stand_change_html, stand_class = get_trend_html(stand_change_pct, stand_trend)
        
        print(f"   HRV: {hrv_change_html}, 步数: {steps_change_html}, 睡眠: {sleep_change_html}")
    else:
        print(f"   ⚠️  未找到上月数据，趋势显示为持平")
        hrv_change_html, hrv_class = get_trend_html(0, 'stable')
        steps_change_html, steps_class = get_trend_html(0, 'stable')
        sleep_change_html, sleep_class = get_trend_html(0, 'stable')
        calories_change_html, calories_class = get_trend_html(0, 'stable')
        stand_change_html, stand_class = get_trend_html(0, 'stable')
    
    # 趋势变化
    html = html.replace('{{HRV_CHANGE}}', hrv_change_html)
    html = html.replace('{{STEPS_CHANGE}}', steps_change_html)
    html = html.replace('{{SLEEP_CHANGE}}', sleep_change_html)
    html = html.replace('{{CALORIES_CHANGE}}', calories_change_html)
    html = html.replace('{{STAND_CHANGE}}', stand_change_html)
    html = html.replace('{{HRV_TREND_CLASS}}', hrv_class)
    html = html.replace('{{STEPS_TREND_CLASS}}', steps_class)
    html = html.replace('{{SLEEP_TREND_CLASS}}', sleep_class)
    html = html.replace('{{CALORIES_TREND_CLASS}}', calories_class)
    html = html.replace('{{STAND_TREND_CLASS}}', stand_class)
    
    # 表格和AI分析
    html = html.replace('{{WEEKLY_ROWS}}', '\n'.join(weekly_rows))
    
    # 生成真实月度趋势图表 - 使用实际有数据的日期
    monthly_chart = generate_monthly_chart(actual_dates, hrv_values, steps_values, sleep_values)
    html = html.replace('{{MONTHLY_CHART}}', monthly_chart)
    
    # AI深度分析 - 严格检查，必须在当前session生成
    hrv_analysis = ai_analysis.get('hrv_analysis') or ai_analysis.get('monthly_analysis')
    if not hrv_analysis:
        raise ValueError("❌ 错误: 缺少月报HRV分析 - 必须在当前AI对话中生成")
    
    sleep_analysis = ai_analysis.get('sleep_analysis')
    if not sleep_analysis:
        raise ValueError("❌ 错误: 缺少月报睡眠质量分析 - 必须在当前AI对话中生成")
    
    activity_analysis = ai_analysis.get('activity_analysis') or ai_analysis.get('key_findings')
    if not activity_analysis:
        raise ValueError("❌ 错误: 缺少月报活动量分析 - 必须在当前AI对话中生成")
    
    trend_assessment = ai_analysis.get('trend_assessment') or ai_analysis.get('trend_forecast')
    if not trend_assessment:
        raise ValueError("❌ 错误: 缺少月报整体趋势评估 - 必须在当前AI对话中生成")
    
    # V5.0: 检查字数，如果不足要求抛出错误（不在脚本中自动生成模板）
    trend_text_clean = trend_assessment.replace('<strong>', '').replace('</strong>', '').replace('<br>', '').replace('\n', '')
    if len(trend_text_clean) < 150:
        raise ValueError(f"❌ 错误: 月报趋势评估字数不足（当前{len(trend_text_clean)}字，要求≥150字）- 请在当前AI对话中重新生成完整分析，必须包含具体数据点引用和指标间关联分析")
    
    html = html.replace('{{HRV_ANALYSIS}}', hrv_analysis.replace('\n', '<br>'))
    html = html.replace('{{SLEEP_ANALYSIS}}', sleep_analysis.replace('\n', '<br>'))
    html = html.replace('{{ACTIVITY_ANALYSIS}}', activity_analysis.replace('\n', '<br>'))
    html = html.replace('{{TREND_ASSESSMENT}}', trend_assessment.replace('\n', '<br>'))
    
    # 下月建议 - 严格检查，必须在当前session生成，直接使用recommendations数组
    recommendations = ai_analysis.get('recommendations', [])
    if not recommendations:
        raise ValueError("❌ 错误: 缺少月报下月建议 - 必须在当前AI对话中生成（recommendations数组）")
    
    html = html.replace('{{RECOMMENDATIONS}}', generate_recommendations_html(recommendations))
    html = html.replace('{{DATA_SOURCE}}', 'Apple Health')
    
    return html

def generate_recommendations_html(recommendations):
    """生成建议HTML - 将\n替换为<br>"""
    html_parts = []
    priority_classes = {'high': 'rec-high', 'medium': 'rec-medium', 'low': 'rec-low'}
    priority_labels = {
        'high': get_text('high_priority'),
        'medium': get_text('medium_priority'),
        'low': get_text('low_priority')
    }
    
    for rec in recommendations:
        p_class = priority_classes.get(rec.get('priority', 'medium'), 'rec-medium')
        p_label = priority_labels.get(rec.get('priority', 'medium'), get_text('medium_priority'))
        # 将\n替换为<br>以正确显示换行
        content = rec.get('content', '').replace('\n', '<br>')
        
        html = f"""<div class="rec-card {p_class}">
            <div class="rec-priority">{p_label}</div>
            <div class="rec-title">{rec.get('title', '')}</div>
            <div class="rec-content">{content}</div>
        </div>"""
        html_parts.append(html)
    
    return '\n'.join(html_parts)

# 成员数量（最多3人）
MEMBERS = CONFIG.get("members", [{}])
MEMBER_COUNT = min(len(MEMBERS), 3)

def get_member_config(index: int):
    """获取指定成员的配置"""
    if index < len(MEMBERS):
        member = MEMBERS[index]
        return {
            "name": member.get("name", f"成员{index+1}"),
            "health_dir": Path(member.get("health_dir", "~/我的云端硬盘/Health Auto Export/Health Data")).expanduser(),
            "workout_dir": Path(member.get("workout_dir", "~/我的云端硬盘/Health Auto Export/Workout Data")).expanduser(),
            "email": member.get("email", "")
        }
    return {
        "name": f"成员{index+1}",
        "health_dir": Path('~/我的云端硬盘/Health Auto Export/Health Data').expanduser(),
        "workout_dir": Path('~/我的云端硬盘/Health Auto Export/Workout Data').expanduser(),
        "email": ""
    }

def main():
    if len(sys.argv) < 2:
        print('用法:')
        print('  周报: python3 scripts/generate_weekly_monthly_medical.py weekly <start_date> <end_date> < ai_analysis.json')
        print('  月报: python3 scripts/generate_weekly_monthly_medical.py monthly <year> <month> < ai_analysis.json')
        sys.exit(1)
    
    report_type = sys.argv[1]
    
    # 读取AI分析
    raw_ai_analyses = json.load(sys.stdin)
    
    member_count = max(1, min(MEMBER_COUNT, 3))
    
    if isinstance(raw_ai_analyses, dict) and "members" in raw_ai_analyses:
        raw_ai_analyses = raw_ai_analyses["members"]
    
    # 根据语言选择模板
    template_suffix = "_EN" if LANGUAGE == "EN" else ""
    
    if report_type == 'weekly':
        if len(sys.argv) < 4:
            print('Error: Weekly report requires start and end dates')
            sys.exit(1)
        
        start_date = sys.argv[2]
        end_date = sys.argv[3]
        
        # 加载模板
        template_path = TEMPLATE_DIR / f'WEEKLY_TEMPLATE_MEDICAL{template_suffix}.html'
        with open(template_path, 'r', encoding='utf-8') as f:
            template = f.read()
            
        for idx in range(member_count):
            member_cfg = get_member_config(idx)
            member_name = member_cfg['name']
            
            # 健壮的成员匹配逻辑
            ai_analysis = {}
            if isinstance(raw_ai_analyses, dict):
                if member_name in raw_ai_analyses:
                    ai_analysis = raw_ai_analyses[member_name]
                elif "默认用户" in raw_ai_analyses:
                    ai_analysis = raw_ai_analyses["默认用户"]
                else:
                    ai_analysis = list(raw_ai_analyses.values())[0] if raw_ai_analyses else {}
            elif isinstance(raw_ai_analyses, list):
                if idx < len(raw_ai_analyses):
                    ai_analysis = raw_ai_analyses[idx]
            else:
                ai_analysis = raw_ai_analyses if isinstance(raw_ai_analyses, dict) else {}
            
            print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            print(f"🧑 正在为成员 {idx+1}/{member_count} 生成周报: {member_name}")
            
            # 生成报告
            html = generate_weekly_report(start_date, end_date, ai_analysis, template, member_name)
            if not html:
                continue
            
            safe_name = member_name.replace('/', '_').replace('\\', '_')
            
            # 保存HTML
            html_path = OUTPUT_DIR / f'{start_date}_to_{end_date}-weekly-medical-{safe_name}.html'
            html_path.write_text(html, encoding='utf-8')
            
            # 生成PDF
            pdf_path = OUTPUT_DIR / f'{start_date}_to_{end_date}-weekly-medical-{safe_name}.pdf'
            with sync_playwright() as p:
                browser = p.chromium.launch()
                page = browser.new_page()
                page.goto(f'file://{html_path}')
                page.wait_for_timeout(2500)
                page.pdf(path=str(pdf_path), format='A4', print_background=True,
                         margin={'top': '10mm', 'bottom': '10mm', 'left': '10mm', 'right': '10mm'})
                browser.close()
            
            if LANGUAGE == "EN":
                print(f'✅ Weekly report generated: {pdf_path}')
                print(f'   Period: {start_date} to {end_date}')
            else:
                print(f'✅ 周报已生成: {pdf_path}')
                print(f'   周期: {start_date} 至 {end_date}')
        
    elif report_type == 'monthly':
        if len(sys.argv) < 4:
            print('Error: Monthly report requires year and month')
            sys.exit(1)
        
        year = int(sys.argv[2])
        month = int(sys.argv[3])
        
        # 加载模板
        template_path = TEMPLATE_DIR / f'MONTHLY_TEMPLATE_MEDICAL{template_suffix}.html'
        with open(template_path, 'r', encoding='utf-8') as f:
            template = f.read()
            
        for idx in range(member_count):
            member_cfg = get_member_config(idx)
            member_name = member_cfg['name']
            
            # 健壮的成员匹配逻辑
            ai_analysis = {}
            if isinstance(raw_ai_analyses, dict):
                if member_name in raw_ai_analyses:
                    ai_analysis = raw_ai_analyses[member_name]
                elif "默认用户" in raw_ai_analyses:
                    ai_analysis = raw_ai_analyses["默认用户"]
                else:
                    ai_analysis = list(raw_ai_analyses.values())[0] if raw_ai_analyses else {}
            elif isinstance(raw_ai_analyses, list):
                if idx < len(raw_ai_analyses):
                    ai_analysis = raw_ai_analyses[idx]
            else:
                ai_analysis = raw_ai_analyses if isinstance(raw_ai_analyses, dict) else {}
            
            print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            print(f"🧑 正在为成员 {idx+1}/{member_count} 生成月报: {member_name}")
            
            # 生成报告
            html = generate_monthly_report(year, month, ai_analysis, template, member_name)
            if not html:
                continue
            
            safe_name = member_name.replace('/', '_').replace('\\', '_')
            
            # 保存HTML
            html_path = OUTPUT_DIR / f'{year}-{month:02d}-monthly-medical-{safe_name}.html'
            html_path.write_text(html, encoding='utf-8')
            
            # 生成PDF
            pdf_path = OUTPUT_DIR / f'{year}-{month:02d}-monthly-medical-{safe_name}.pdf'
            with sync_playwright() as p:
                browser = p.chromium.launch()
                page = browser.new_page()
                page.goto(f'file://{html_path}')
                page.wait_for_timeout(2500)
                page.pdf(path=str(pdf_path), format='A4', print_background=True,
                         margin={'top': '10mm', 'bottom': '10mm', 'left': '10mm', 'right': '10mm'})
                browser.close()
            
            if LANGUAGE == "EN":
                print(f'✅ Monthly report generated: {pdf_path}')
                print(f'   Month: {year}-{month:02d}')
            else:
                print(f'✅ 月报已生成: {pdf_path}')
                print(f'   月份: {year}年{month}月')
    
    else:
        print(f'错误: 未知报告类型 {report_type}')
        sys.exit(1)

if __name__ == '__main__':
    main()
