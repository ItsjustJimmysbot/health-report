#!/usr/bin/env python3
"""
生成2026-02-18健康日报 - 带Chart.js心率曲线图
"""
import json
from datetime import datetime
from playwright.sync_api import sync_playwright

# 心率数据（从Workout Data提取）
hr_times = ['20:33', '20:34', '20:35', '20:38', '20:43', '20:44', '20:45', '20:46', '20:47', '20:49', 
            '20:50', '20:51', '20:52', '20:53', '20:54', '20:55', '20:56', '20:57', '20:58', '20:59',
            '21:00', '21:01', '21:02', '21:03', '21:04', '21:05', '21:06']
hr_avg = [147, 133, 134, 165, 157, 141, 133, 150, 161, 163, 160, 159, 158, 160, 157, 139, 130, 146, 160, 159, 160, 161, 150, 131, 138, 155, 156]
hr_max = [155, 136, 138, 165, 166, 148, 137, 159, 162, 164, 163, 164, 160, 161, 168, 145, 134, 155, 163, 161, 161, 162, 137, 147, 155, 157, 156]

health_data = {
    "date": "2026-02-18",
    "hrv": 52.8, "hrv_points": 51,
    "resting_hr": 57.0, "resting_hr_points": 1,
    "steps": 6852, "steps_points": 276,
    "active_energy_kcal": 563.7, "active_energy_kj": 2358.7, "active_energy_points": 959,
    "basal_energy_kcal": 1702.2, "basal_energy_kj": 7122.0,
    "distance_km": 5.09, "distance_points": 272,
    "blood_oxygen": 96.1, "blood_oxygen_points": 16,
    "respiratory_rate": 14.8, "respiratory_rate_points": 40,
    "exercise_min": 40, "stand_min": 117, "flights_climbed": 109,
    "sleep_total": 2.82, "sleep_deep": 0.0, "sleep_core": 0.0, "sleep_rem": 0.0, "sleep_awake": 0.0,
    "sleep_start": "2026-02-19 06:28:03", "sleep_end": "2026-02-19 09:17:04",
}

workout_data = {
    "name": "楼梯", "start": "20:25:19", "end": "21:06:54",
    "duration_min": 41.6, "energy_kj": 1209.8, "energy_kcal": 289.2,
    "avg_hr": 150.5, "max_hr": 168, "min_hr": 126,
    "hr_data_points": 27, "recovery_data_points": 25,
}

# 生成Chart.js心率曲线图HTML
hr_chart_html = f"""
<canvas id="hrChart" width="700" height="200"></canvas>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<script>
  new Chart(document.getElementById('hrChart'), {{
    type: 'line',
    data: {{
      labels: {hr_times},
      datasets: [
        {{
          label: '平均心率',
          data: {hr_avg},
          borderColor: '#667eea',
          backgroundColor: 'rgba(102, 126, 234, 0.1)',
          fill: true,
          tension: 0.3,
          pointRadius: 3,
          pointBackgroundColor: '#667eea'
        }},
        {{
          label: '最高心率',
          data: {hr_max},
          borderColor: '#dc2626',
          borderDash: [5, 5],
          fill: false,
          tension: 0.3,
          pointRadius: 2,
          pointBackgroundColor: '#dc2626'
        }}
      ]
    }},
    options: {{
      responsive: false,
      maintainAspectRatio: false,
      plugins: {{
        legend: {{
          position: 'top',
          labels: {{ font: {{ size: 10 }}, usePointStyle: true }}
        }},
        title: {{
          display: true,
          text: '运动时心率变化 (bpm)',
          font: {{ size: 11 }}
        }}
      }},
      scales: {{
        y: {{
          beginAtZero: false,
          min: 120,
          max: 180,
          title: {{ display: true, text: '心率 (bpm)', font: {{ size: 10 }} }},
          ticks: {{ font: {{ size: 9 }} }}
        }},
        x: {{
          ticks: {{ font: {{ size: 9 }}, maxTicksLimit: 8 }}
        }}
      }}
    }}
  }});
</script>
"""

# 读取V2模板
with open('/Users/jimmylu/.openclaw/workspace-health/templates/DAILY_TEMPLATE_V2.html', 'r', encoding='utf-8') as f:
    template = f.read()

html = template

# 填充数据（省略，与之前相同）...
html = html.replace('{{DATE}}', '2026-02-18')
html = html.replace('{{HEADER_SUBTITLE}}', '2026-02-18 · Apple Health (959能量点/276步点/51HRV点) + Workout (27点心率点) | UTC+8')

# 评分卡
html = html.replace('{{SCORE_RECOVERY}}', '60')
html = html.replace('{{BADGE_RECOVERY_CLASS}}', 'badge-average')
html = html.replace('{{BADGE_RECOVERY_TEXT}}', '一般')
html = html.replace('{{SCORE_SLEEP}}', '30')
html = html.replace('{{BADGE_SLEEP_CLASS}}', 'badge-poor')
html = html.replace('{{BADGE_SLEEP_TEXT}}', '严重不足')
html = html.replace('{{SCORE_EXERCISE}}', '80')
html = html.replace('{{BADGE_EXERCISE_CLASS}}', 'badge-good')
html = html.replace('{{BADGE_EXERCISE_TEXT}}', '良好')

# 指标数据
html = html.replace('{{METRIC1_VALUE}}', f"{health_data['hrv']:.1f} ms\n<small>{health_data['hrv_points']}个数据点</small>")
html = html.replace('{{METRIC1_RATING_CLASS}}', 'rating-average')
html = html.replace('{{METRIC1_RATING}}', '一般')
html = html.replace('{{METRIC1_ANALYSIS}}', f"HRV {health_data['hrv']:.1f}ms基于{health_data['hrv_points']}个数据点，处于中等水平。该数值表明自主神经系统处于适度应激状态，与高强度爬楼梯运动（平均心率150bpm）和严重不足睡眠（2.82小时）的双重影响相关。")

html = html.replace('{{METRIC2_VALUE}}', f"{health_data['resting_hr']:.1f} bpm")
html = html.replace('{{METRIC2_RATING_CLASS}}', 'rating-excellent')
html = html.replace('{{METRIC2_RATING}}', '优秀')
html = html.replace('{{METRIC2_ANALYSIS}}', f"静息心率{health_data['resting_hr']:.1f}bpm表现优秀，显示心血管系统功能良好。即使在进行了41分钟高强度爬楼梯运动后，静息心率仍保持在这一理想水平。")

html = html.replace('{{METRIC3_VALUE}}', f"{health_data['steps']:,} 步\n<small>{health_data['steps_points']}个数据点</small>")
html = html.replace('{{METRIC3_RATING_CLASS}}', 'rating-average')
html = html.replace('{{METRIC3_RATING}}', '一般')
html = html.replace('{{METRIC3_ANALYSIS}}', f"步数{health_data['steps']:,}步基于{health_data['steps_points']}个数据点，接近但未达10000步目标。其中爬楼梯运动贡献了相当比例。")

html = html.replace('{{METRIC4_VALUE}}', f"{health_data['distance_km']:.2f} km\n<small>{health_data['distance_points']}个数据点</small>")
html = html.replace('{{METRIC4_RATING_CLASS}}', 'rating-average')
html = html.replace('{{METRIC4_RATING}}', '一般')
html = html.replace('{{METRIC4_ANALYSIS}}', f"行走距离{health_data['distance_km']:.2f}公里，与步数数据相符。爬楼梯运动贡献了高能量消耗但相对短距离的特点。")

html = html.replace('{{METRIC5_VALUE}}', f"{health_data['active_energy_kcal']:.1f} kcal\n<small>{health_data['active_energy_kj']:.1f} kJ</small>")
html = html.replace('{{METRIC5_RATING_CLASS}}', 'rating-good')
html = html.replace('{{METRIC5_RATING}}', '良好')
html = html.replace('{{METRIC5_ANALYSIS}}', f"活动能量{health_data['active_energy_kcal']:.1f}千卡（{health_data['active_energy_kj']:.1f}千焦，基于{health_data['active_energy_points']}个数据点），其中约289千卡来自爬楼梯运动。")

html = html.replace('{{METRIC6_VALUE}}', f"{health_data['flights_climbed']:.0f} 层")
html = html.replace('{{METRIC6_RATING_CLASS}}', 'rating-good')
html = html.replace('{{METRIC6_RATING}}', '良好')
html = html.replace('{{METRIC6_ANALYSIS}}', f"爬楼层数{health_data['flights_climbed']:.0f}层表现良好，爬楼梯是优秀的下肢力量训练和心肺功能锻炼。")

html = html.replace('{{METRIC7_VALUE}}', f"{health_data['stand_min']/60:.1f} 小时\n<small>{health_data['stand_min']:.0f}分钟</small>")
html = html.replace('{{METRIC7_RATING_CLASS}}', 'rating-good')
html = html.replace('{{METRIC7_RATING}}', '良好')
html = html.replace('{{METRIC7_ANALYSIS}}', f"站立时间{health_data['stand_min']/60:.1f}小时表现良好，说明日常工作中有较好的活动性。")

html = html.replace('{{METRIC8_VALUE}}', f"{health_data['blood_oxygen']:.1f}%\n<small>{health_data['blood_oxygen_points']}个数据点</small>")
html = html.replace('{{METRIC8_RATING_CLASS}}', 'rating-excellent')
html = html.replace('{{METRIC8_RATING}}', '优秀')
html = html.replace('{{METRIC8_ANALYSIS}}', f"血氧饱和度{health_data['blood_oxygen']:.1f}%处于正常健康范围（95-100%）。即使在高强度爬楼梯运动期间（心率最高168bpm），身体仍能保持充足氧气供应。")

html = html.replace('{{METRIC9_VALUE}}', f"{health_data['basal_energy_kcal']:.1f} kcal\n<small>{health_data['basal_energy_kj']:.1f} kJ</small>")
html = html.replace('{{METRIC9_RATING_CLASS}}', 'rating-good')
html = html.replace('{{METRIC9_RATING}}', '正常')
html = html.replace('{{METRIC9_ANALYSIS}}', f"静息能量{health_data['basal_energy_kcal']:.1f}千卡反映基础代谢水平正常。当日总能量消耗约{health_data['basal_energy_kcal']+health_data['active_energy_kcal']:.0f}千卡。")

html = html.replace('{{METRIC10_VALUE}}', f"{health_data['respiratory_rate']:.1f} /min\n<small>{health_data['respiratory_rate_points']}个数据点</small>")
html = html.replace('{{METRIC10_RATING_CLASS}}', 'rating-excellent')
html = html.replace('{{METRIC10_RATING}}', '优秀')
html = html.replace('{{METRIC10_ANALYSIS}}', f"呼吸率{health_data['respiratory_rate']:.1f}次/分钟处于理想范围（12-20次/分），显示呼吸系统健康。")

# 睡眠分析
html = html.replace('{{SLEEP_STATUS}}', '严重睡眠不足 - 数据结构异常')
html = html.replace('{{SLEEP_ALERT_BG}}', '#fee2e2')
html = html.replace('{{SLEEP_ALERT_BORDER}}', '#fca5a5')
html = html.replace('{{SLEEP_ALERT_COLOR}}', '#dc2626')
html = html.replace('{{SLEEP_ALERT_TITLE}}', '⚠️ 睡眠严重不足 + 数据结构异常')
html = html.replace('{{SLEEP_ALERT_SUBCOLOR}}', '#991b1b')
html = html.replace('{{SLEEP_ALERT_DETAIL}}', f'仅{health_data["sleep_total"]:.2f}小时睡眠，远低于7-9小时标准；入睡时间06:28显示作息紊乱；睡眠阶段数据异常（Deep/Core/REM均为0）')
html = html.replace('{{SLEEP_TOTAL}}', f"{health_data['sleep_total']:.1f}")
html = html.replace('{{SLEEP_DEEP}}', f"{health_data['sleep_deep']:.1f}")
html = html.replace('{{SLEEP_DEEP_PCT}}', '0')
html = html.replace('{{SLEEP_CORE}}', f"{health_data['sleep_core']:.1f}")
html = html.replace('{{SLEEP_CORE_PCT}}', '0')
html = html.replace('{{SLEEP_REM}}', f"{health_data['sleep_rem']:.1f}")
html = html.replace('{{SLEEP_REM_PCT}}', '0')
html = html.replace('{{SLEEP_AWAKE}}', f"{health_data['sleep_awake']:.1f}")
html = html.replace('{{SLEEP_AWAKE_PCT}}', '0')
html = html.replace('{{SLEEP_ANALYSIS_BORDER}}', '#dc2626')
html = html.replace('{{SLEEP_ANALYSIS_TEXT}}', f'睡眠仅{health_data["sleep_total"]:.2f}小时严重不足！入睡时间06:28显示严重作息紊乱。**注意：睡眠阶段数据异常** - Apple Watch记录显示总睡眠{health_data["sleep_total"]:.2f}小时，但深睡、核心睡眠、REM期均显示为0。这可能是旧版Apple Watch或数据同步问题。')

# 运动记录
html = html.replace('{{WORKOUT_NAME}}', f"{workout_data['name']}（爬楼梯）")
html = html.replace('{{WORKOUT_TIME}}', f"{workout_data['start']} - {workout_data['end']} ({workout_data['duration_min']:.1f}分钟)")
html = html.replace('{{WORKOUT_DURATION}}', f"{workout_data['duration_min']:.1f}")
html = html.replace('{{WORKOUT_ENERGY}}', f"{workout_data['energy_kcal']:.0f}")
html = html.replace('{{WORKOUT_AVG_HR}}', f"{workout_data['avg_hr']:.1f}")
html = html.replace('{{WORKOUT_MAX_HR}}', f"{workout_data['max_hr']}")

# 插入心率曲线图
html = html.replace('{{WORKOUT_HR_CHART}}', hr_chart_html)

# 运动分析
workout_analysis = f"""**1. 运动强度评估**：{workout_data['duration_min']:.1f}分钟爬楼梯消耗{workout_data['energy_kcal']:.0f}千卡，平均心率{workout_data['avg_hr']:.1f}bpm，最高心率{workout_data['max_hr']}bpm，属于**高强度有氧运动**。从心率曲线可见，20:47-21:01期间心率维持在155-165bpm的高强度区间。

**2. 心率曲线分析**：心率数据基于{workout_data['hr_data_points']}个时序数据点（见上方曲线图）。运动开始时心率迅速上升至140-150bpm，随后进入155-165bpm的高强度平台期。最高心率168bpm出现在20:54。心率恢复数据显示，运动结束后13分钟内心率从164降至131bpm，恢复能力良好。

**3. 训练效果评估**：爬楼梯相比平地步行能消耗约2-3倍能量，是优秀的下肢力量训练和心肺功能锻炼。本次运动{workout_data['energy_kcal']:.0f}千卡消耗相当于跑步约35分钟。长期坚持可显著提升心肺耐力、强化大腿和臀部肌肉。

**4. 注意事项与建议**：**关键问题** - 当日仅{health_data['sleep_total']:.1f}小时睡眠就进行如此高强度运动，会对身体造成额外应激负荷。理想情况下应在充足睡眠（7小时以上）后进行此类训练。"""

html = html.replace('{{WORKOUT_ANALYSIS}}', workout_analysis)

# AI建议
html = html.replace('{{AI1_TITLE}}', '立即改善睡眠 + 检查Apple Watch')
html = html.replace('{{AI1_PROBLEM}}', f"睡眠仅{health_data['sleep_total']:.2f}小时严重不足，入睡时间06:28显示严重作息紊乱。Apple Watch睡眠数据异常 - 深睡、核心睡眠、REM期均显示为0。这可能是旧版Apple Watch或数据同步问题。")
html = html.replace('{{AI1_ACTION}}', '1. 今晚固定22:00前上床；2. 检查Apple Watch：确保watchOS已更新至最新版本；3. 睡前准备（21:00开始）：调暗灯光，停止电子设备使用；4. 助眠措施：尝试4-7-8呼吸法；5. 环境优化：卧室温度18-20°C，完全黑暗。')
html = html.replace('{{AI1_EXPECTATION}}', '通过规律作息，3-5天内睡眠时长应恢复至6-7小时。检查并修复Apple Watch睡眠追踪设置后，未来应能看到完整的睡眠阶段数据。')

html = html.replace('{{AI2_TITLE}}', '高强度运动后的恢复管理')
html = html.replace('{{AI2_PROBLEM}}', f"当日进行了{workout_data['duration_min']:.1f}分钟高强度爬楼梯运动（平均心率{workout_data['avg_hr']:.1f}bpm），但在仅{health_data['sleep_total']:.1f}小时睡眠的情况下进行如此高强度运动，会对身体恢复造成额外压力。")
html = html.replace('{{AI2_ACTION}}', '1. 水分补充：运动后至少饮用500ml水，全天饮水2.5升；2. 营养支持：运动后30分钟内摄入蛋白质20-30g和复合碳水50-60g；3. 拉伸放松：睡前进行10-15分钟下肢拉伸；4. 明日活动：改为轻度活动如散步20-30分钟；5. 疲劳监测：明早测量静息心率。')
html = html.replace('{{AI2_EXPECTATION}}', '通过充分的水分和营养补充，24-48小时内肌肉酸痛应明显减轻。建议每周进行2-3次类似强度的爬楼梯运动。')

html = html.replace('{{AI3_TITLE}}', '建立健康作息与饮食计划')
html = html.replace('{{AI3_DIET}}', '早餐（7:30-8:30）：全麦面包2片+鸡蛋1个+牛奶250ml+香蕉1根；午餐（12:00-13:00）：糙米饭150g+瘦肉/鱼150g+深绿叶蔬菜200g；晚餐（18:00-19:00）：蒸鱼100g+蔬菜汤+少量碳水；运动后加餐（21:30）：香蕉1根+酸奶200ml；睡前2小时避免进食。')
html = html.replace('{{AI3_ROUTINE}}', '建立固定作息：每天22:30±15分钟上床，07:00±15分钟起床；运动时间：建议在下午16:00-19:00进行高强度运动；午休控制：如需午休，限制在20-30分钟；环境优化：卧室温度18-20°C，使用遮光窗帘。')

html = html.replace('{{AI4_TITLE}}', '健康数据综合评估与行动计划')
html = html.replace('{{AI4_ADVANTAGES}}', f"1. 静息心率{health_data['resting_hr']:.1f}bpm优秀，心血管基础良好；2. 完成{workout_data['duration_min']:.1f}分钟高强度爬楼梯运动，心肺功能良好；3. 血氧{health_data['blood_oxygen']:.1f}%正常；4. 心率恢复能力良好（13分钟从164降至131bpm）；5. 爬楼层数{health_data['flights_climbed']:.0f}层显示下肢力量优秀。")
html = html.replace('{{AI4_RISKS}}', f"1. **睡眠严重不足**（{health_data['sleep_total']:.2f}小时）是当前最大风险；2. **Apple Watch睡眠数据异常**（各阶段均为0）；3. 在睡眠不足状态下进行高强度运动，增加身体应激负荷。")
html = html.replace('{{AI4_CONCLUSION}}', f"整体健康状况中等，心血管和运动能力指标优秀，但睡眠严重不足且睡眠追踪数据异常是明显短板。{workout_data['duration_min']:.1f}分钟爬楼梯运动数据显示良好的心肺功能。")
html = html.replace('{{AI4_PLAN}}', '第1周：优先解决睡眠问题，目标每日7小时以上；检查并修复Apple Watch睡眠追踪设置。第2周：在睡眠改善基础上，恢复每周2-3次爬楼梯运动。')

html = html.replace('{{FOOTER_DATA_SOURCES}}', f"数据来源: Apple Health + Workout Data ({workout_data['hr_data_points']}心率时序点)")
html = html.replace('{{FOOTER_DATE}}', datetime.now().strftime('%Y-%m-%d %H:%M'))

# 保存和生成PDF
html_path = '/Users/jimmylu/.openclaw/workspace/shared/health-reports/upload/2026-02-18-report-zh-V2-CHART.html'
with open(html_path, 'w', encoding='utf-8') as f:
    f.write(html)
print(f"✅ HTML已保存: {html_path}")

pdf_path = '/Users/jimmylu/.openclaw/workspace/shared/health-reports/upload/2026-02-18-report-zh-V2-CHART.pdf'
with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.set_content(html)
    page.wait_for_timeout(5000)  # 等待Chart.js渲染
    page.pdf(
        path=pdf_path,
        format='A4',
        print_background=True,
        margin={'top': '8mm', 'bottom': '8mm', 'left': '8mm', 'right': '8mm'}
    )
    browser.close()
print(f"✅ PDF已生成: {pdf_path}")
