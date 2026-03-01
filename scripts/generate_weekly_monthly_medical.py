#!/usr/bin/env python3
"""
周报和月报生成器 - V5.4 Medical Dashboard版 (支持多语言 CN/EN)
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
TEMPLATE_DIR = HOME / '.openclaw' / 'workspace-health' / 'templates'
OUTPUT_DIR = HOME / '.openclaw' / 'workspace' / 'shared' / 'health-reports' / 'upload'
CACHE_DIR = HOME / '.openclaw' / 'workspace-health' / 'cache' / 'daily'

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
        "version": "5.4.1",
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
    
    # Chart.js 图表代码
    chart_html = f'''<div style="height: 250px;">
  <canvas id="trendChart"></canvas>
</div>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<script>
  const ctx = document.getElementById('trendChart').getContext('2d');
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
    
    return chart_html


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
    
    # Chart.js 月度图表代码
    chart_html = f'''<div style="height: 280px;">
  <canvas id="monthlyChart"></canvas>
</div>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<script>
  const ctx = document.getElementById('monthlyChart').getContext('2d');
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
    
    return chart_html
    if not dates or not hrv_values:
        return '<div style="text-align:center;color:#999;padding:40px;">暂无月度趋势数据</div>'
    
    n = len(dates)
    width = 700
    height = 250
    padding = {'top': 30, 'right': 40, 'bottom': 50, 'left': 50}
    chart_w = width - padding['left'] - padding['right']
    chart_h = height - padding['top'] - padding['bottom']
    
    # 计算范围
    hrv_min, hrv_max = min(hrv_values) * 0.9, max(hrv_values) * 1.1
    steps_min, steps_max = 0, max(steps_values) * 1.2
    
    # 生成点
    def get_points(values, min_v, max_v):
        points = []
        for i, v in enumerate(values):
            x = padding['left'] + (i / max(n - 1, 1)) * chart_w
            y = padding['top'] + chart_h - ((v - min_v) / (max_v - min_v + 0.001)) * chart_h
            points.append(f"{x:.1f},{y:.1f}")
        return points
    
    hrv_points = get_points(hrv_values, hrv_min, hrv_max)
    steps_points = get_points(steps_values, steps_min, steps_max)
    sleep_points = get_points(sleep_values, 0, max(sleep_values) * 1.2 if sleep_values else 10)
    
    # X轴标签 - 与数据点对齐，每5天或每天显示（根据数据量）
    x_labels = ""
    label_interval = max(1, n // 6)  # 确保标签数量合理，不会重叠
    for i in range(0, n, label_interval):
        x = padding['left'] + (i / max(n - 1, 1)) * chart_w
        label = dates[i][8:10] if len(dates[i]) >= 10 else str(i+1)
        x_labels += f'<text x="{x}" y="{height - 15}" text-anchor="middle" font-size="10" fill="#64748B">{label}日</text>'
    
    # 确保最后一个数据点有标签
    if (n - 1) % label_interval != 0:
        x = padding['left'] + chart_w
        label = dates[-1][8:10] if len(dates[-1]) >= 10 else str(n)
        x_labels += f'<text x="{x}" y="{height - 15}" text-anchor="middle" font-size="10" fill="#64748B">{label}日</text>'
    
    # 生成SVG
    svg = f'''<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" style="background:#fff;">
        <!-- 网格线 -->
        {''.join([f'<line x1="{padding["left"]}" y1="{padding["top"] + (height - padding["top"] - padding["bottom"]) / 4 * i}" x2="{width - padding["right"]}" y2="{padding["top"] + (height - padding["top"] - padding["bottom"]) / 4 * i}" stroke="#E2E8F0" stroke-width="1"/>' for i in range(5)])}
        
        <!-- HRV曲线（绿色） -->
        <polyline fill="none" stroke="#22C55E" stroke-width="2.5" points="{' '.join(hrv_points)}"/>
        {''.join([f'<circle cx="{p.split(",")[0]}" cy="{p.split(",")[1]}" r="3" fill="#22C55E"/>' for p in hrv_points])}
        
        <!-- 步数曲线（蓝色，虚线） -->
        <polyline fill="none" stroke="#3B82F6" stroke-width="2" stroke-dasharray="5,3" points="{' '.join(steps_points)}"/>
        
        <!-- 睡眠曲线（紫色，点线） -->
        <polyline fill="none" stroke="#A855F7" stroke-width="2" stroke-dasharray="3,3" points="{' '.join(sleep_points)}"/>
        
        <!-- X轴标签 -->
        {x_labels}
        
        <!-- 图例 -->
        <g transform="translate({width/2 - 120}, 10)">
            <line x1="0" y1="6" x2="20" y2="6" stroke="#22C55E" stroke-width="2.5"/>
            <text x="25" y="10" font-size="10" fill="#64748B">HRV (ms)</text>
            
            <line x1="80" y1="6" x2="100" y2="6" stroke="#3B82F6" stroke-width="2" stroke-dasharray="5,3"/>
            <text x="105" y="10" font-size="10" fill="#64748B">步数</text>
            
            <line x1="160" y1="6" x2="180" y2="6" stroke="#A855F7" stroke-width="2" stroke-dasharray="3,3"/>
            <text x="185" y="10" font-size="10" fill="#64748B">睡眠(h)</text>
        </g>
    </svg>'''
    
    return svg

def generate_weekly_report(start_date, end_date, ai_analysis, template):
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
        data = load_cache(date)
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
        data = load_cache(date)
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
    
    # 趋势变化
    html = html.replace('{{HRV_CHANGE}}', '→ 持平')
    html = html.replace('{{STEPS_CHANGE}}', '→ 持平')
    html = html.replace('{{SLEEP_CHANGE}}', '→ 持平')
    html = html.replace('{{HRV_TREND_CLASS}}', 'change-stable')
    html = html.replace('{{STEPS_TREND_CLASS}}', 'change-stable')
    html = html.replace('{{SLEEP_TREND_CLASS}}', 'change-stable')
    
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

def generate_monthly_report(year, month, ai_analysis, template):
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
        data = load_cache(date)
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
    workout_days = sum(1 for d in monthly_data if d.get('has_workout'))
    
    # 提取实际有数据的日期（用于图表X轴）
    actual_dates = [d['date'] for d in monthly_data]
    
    avg_hrv = sum(hrv_values) / len(hrv_values) if hrv_values else 0
    avg_steps = sum(steps_values) / len(steps_values) if steps_values else 0
    avg_sleep = sum(sleep_values) / len(sleep_values) if sleep_values else 0
    
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
    html = html.replace('{{AVG_CALORIES}}', '2,100')
    html = html.replace('{{AVG_STAND}}', '8.5')
    
    # 趋势变化
    html = html.replace('{{HRV_CHANGE}}', '→ 持平')
    html = html.replace('{{STEPS_CHANGE}}', '→ 持平')
    html = html.replace('{{SLEEP_CHANGE}}', '→ 持平')
    html = html.replace('{{CALORIES_CHANGE}}', '→ 持平')
    html = html.replace('{{STAND_CHANGE}}', '→ 持平')
    html = html.replace('{{HRV_TREND_CLASS}}', 'change-stable')
    html = html.replace('{{STEPS_TREND_CLASS}}', 'change-stable')
    html = html.replace('{{SLEEP_TREND_CLASS}}', 'change-stable')
    html = html.replace('{{CALORIES_TREND_CLASS}}', 'change-stable')
    html = html.replace('{{STAND_TREND_CLASS}}', 'change-stable')
    
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

def main():
    if len(sys.argv) < 2:
        print('用法:')
        print('  周报: python3 scripts/generate_weekly_monthly_medical.py weekly <start_date> <end_date> < ai_analysis.json')
        print('  月报: python3 scripts/generate_weekly_monthly_medical.py monthly <year> <month> < ai_analysis.json')
        sys.exit(1)
    
    report_type = sys.argv[1]
    
    # 读取AI分析
    ai_analysis = json.load(sys.stdin)
    
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
        
        # 生成报告
        html = generate_weekly_report(start_date, end_date, ai_analysis, template)
        if not html:
            sys.exit(1)
        
        # 保存HTML
        html_path = OUTPUT_DIR / f'{start_date}_to_{end_date}-weekly-medical.html'
        html_path.write_text(html, encoding='utf-8')
        
        # 生成PDF
        pdf_path = OUTPUT_DIR / f'{start_date}_to_{end_date}-weekly-medical.pdf'
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
        
        # 生成报告
        html = generate_monthly_report(year, month, ai_analysis, template)
        if not html:
            sys.exit(1)
        
        # 保存HTML
        html_path = OUTPUT_DIR / f'{year}-{month:02d}-monthly-medical.html'
        html_path.write_text(html, encoding='utf-8')
        
        # 生成PDF
        pdf_path = OUTPUT_DIR / f'{year}-{month:02d}-monthly-medical.pdf'
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
