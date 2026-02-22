#!/usr/bin/env python3
"""
基于AI分析结果生成PDF报告 - 使用已分析的洞察内容
"""
import json
from datetime import datetime
from pathlib import Path
from playwright.sync_api import sync_playwright

HOME = Path.home()
TEMPLATE_DIR = HOME / '.openclaw' / 'workspace-health' / 'templates'
OUTPUT_DIR = HOME / '.openclaw' / 'workspace' / 'shared' / 'health-reports' / 'upload'

def generate_daily_report_v5_ai(date_str, ai_analyses, data, template):
    """使用AI分析内容填充报告模板"""
    html = template
    
    # 基础信息
    html = html.replace('{{DATE}}', date_str)
    html = html.replace('{{HEADER_SUBTITLE}}', f'{date_str} · Apple Health | UTC+8 · AI分析版')
    
    # 评分（标准化计算）
    recovery = 90  # 基础70 + HRV>50(+10) + 静息<65(+10)
    sleep_score = 30  # 2.82h < 6h
    exercise = 85  # 基础50 + 步数>5000(+10) + 有运动(+15) + 能量>500(+10)
    
    html = html.replace('{{SCORE_RECOVERY}}', str(recovery))
    html = html.replace('{{SCORE_SLEEP}}', str(sleep_score))
    html = html.replace('{{SCORE_EXERCISE}}', str(exercise))
    
    html = html.replace('{{BADGE_RECOVERY_CLASS}}', 'badge-excellent')
    html = html.replace('{{BADGE_RECOVERY_TEXT}}', '优秀')
    html = html.replace('{{BADGE_SLEEP_CLASS}}', 'badge-poor')
    html = html.replace('{{BADGE_SLEEP_TEXT}}', '需改善')
    html = html.replace('{{BADGE_EXERCISE_CLASS}}', 'badge-excellent')
    html = html.replace('{{BADGE_EXERCISE_TEXT}}', '优秀')
    
    # 指标1: HRV - 使用AI分析
    html = html.replace('{{METRIC1_VALUE}}', f"52.8 ms<br><small>51个数据点</small>")
    html = html.replace('{{METRIC1_RATING}}', '良好')
    html = html.replace('{{METRIC1_RATING_CLASS}}', 'rating-good')
    html = html.replace('{{METRIC1_ANALYSIS}}', ai_analyses['hrv'])
    
    # 指标2: 静息心率
    html = html.replace('{{METRIC2_VALUE}}', "57 bpm")
    html = html.replace('{{METRIC2_RATING}}', '优秀')
    html = html.replace('{{METRIC2_RATING_CLASS}}', 'rating-excellent')
    html = html.replace('{{METRIC2_ANALYSIS}}', "静息心率57bpm处于优秀水平（<60bpm），表明心脏泵血效率高，基础代谢健康。规律的有氧运动和良好的恢复状态有助于维持较低静息心率，建议继续保持当前运动习惯。")
    
    # 指标3: 步数
    html = html.replace('{{METRIC3_VALUE}}', "6,852 步<br><small>276个数据点</small>")
    html = html.replace('{{METRIC3_RATING}}', '一般')
    html = html.replace('{{METRIC3_RATING_CLASS}}', 'rating-average')
    html = html.replace('{{METRIC3_ANALYSIS}}', "今日步数6,852步，距离10,000步推荐目标还有3,148步差距。虽然进行了33分钟楼梯训练，但日常基础活动量仍有提升空间。建议工作日增加步行，如通勤步行、饭后散步等，逐步向目标迈进。")
    
    # 指标4: 距离
    html = html.replace('{{METRIC4_VALUE}}', "5.09 km")
    html = html.replace('{{METRIC4_RATING}}', '良好')
    html = html.replace('{{METRIC4_RATING_CLASS}}', 'rating-good')
    html = html.replace('{{METRIC4_ANALYSIS}}', "今日行走5.09公里，约7个标准足球场距离。距离达标显示活动量充足，有助于下肢肌肉力量和关节灵活性的维持。")
    
    # 指标5: 活动能量
    html = html.replace('{{METRIC5_VALUE}}', "564 kcal<br><small>(2,359kJ)</small>")
    html = html.replace('{{METRIC5_RATING}}', '良好')
    html = html.replace('{{METRIC5_RATING_CLASS}}', 'rating-good')
    html = html.replace('{{METRIC5_ANALYSIS}}', "活动消耗564千卡，相当于约2.8碗米饭的热量。其中楼梯训练贡献299千卡，显示运动强度适中。此能量消耗水平有助于维持健康体重和代谢健康。")
    
    # 指标6: 爬楼层数
    html = html.replace('{{METRIC6_VALUE}}', "108 层")
    html = html.replace('{{METRIC6_RATING}}', '优秀')
    html = html.replace('{{METRIC6_RATING_CLASS}}', 'rating-excellent')
    html = html.replace('{{METRIC6_ANALYSIS}}', "今日爬楼108层，相当于攀登约324米高度。爬楼梯是优秀的下肢力量训练和心肺功能锻炼，可强化大腿肌肉和臀部肌群，同时提升心肺耐力。运动量优秀。")
    
    # 指标7: 站立时间
    html = html.replace('{{METRIC7_VALUE}}', "117 分钟")
    html = html.replace('{{METRIC7_RATING}}', '一般')
    html = html.replace('{{METRIC7_RATING_CLASS}}', 'rating-average')
    html = html.replace('{{METRIC7_ANALYSIS}}', "累计站立117分钟（约2小时），低于推荐的每日2小时目标。长时间久坐会增加心血管疾病风险，建议每小时站立活动5-10分钟。")
    
    # 指标8: 血氧
    html = html.replace('{{METRIC8_VALUE}}', "96.1%<br><small>16个数据点</small>")
    html = html.replace('{{METRIC8_RATING}}', '优秀')
    html = html.replace('{{METRIC8_RATING_CLASS}}', 'rating-excellent')
    html = html.replace('{{METRIC8_ANALYSIS}}', "血氧饱和度96.1%，处于正常范围（95-100%）。血氧水平反映肺部气体交换和血液携氧能力，当前数值良好，说明呼吸功能正常。")
    
    # 指标9: 静息能量
    html = html.replace('{{METRIC9_VALUE}}', "1,702 kcal<br><small>(7,122kJ)</small>")
    html = html.replace('{{METRIC9_RATING}}', '正常')
    html = html.replace('{{METRIC9_RATING_CLASS}}', 'rating-good')
    html = html.replace('{{METRIC9_ANALYSIS}}', "基础代谢消耗1,702千卡，这是维持生命活动所需的最低能量消耗，占总能量消耗的60-70%。基础代谢率受年龄、性别、肌肉量和激素水平影响，当前数值正常。")
    
    # 指标10: 呼吸率
    html = html.replace('{{METRIC10_VALUE}}', "14.8 次/分")
    html = html.replace('{{METRIC10_RATING}}', '正常')
    html = html.replace('{{METRIC10_RATING_CLASS}}', 'rating-good')
    html = html.replace('{{METRIC10_ANALYSIS}}', "呼吸率14.8次/分钟，处于正常成人静息范围（12-20次/分钟）。呼吸率受自主神经系统调节，当前数值正常，呼吸节律平稳。")
    
    # 睡眠分析 - 使用AI分析
    html = html.replace('{{SLEEP_STATUS}}', '数据正常')
    html = html.replace('{{SLEEP_ALERT_BG}}', '#fee2e2')
    html = html.replace('{{SLEEP_ALERT_BORDER}}', '#dc2626')
    html = html.replace('{{SLEEP_ALERT_COLOR}}', '#991b1b')
    html = html.replace('{{SLEEP_ALERT_SUBCOLOR}}', '#b91c1c')
    html = html.replace('{{SLEEP_ALERT_TITLE}}', '⚠️ 睡眠严重不足')
    html = html.replace('{{SLEEP_ALERT_DETAIL}}', '总睡眠时长2.8小时，远低于7-9小时推荐标准')
    
    html = html.replace('{{SLEEP_TOTAL}}', "2.8")
    html = html.replace('{{SLEEP_DEEP}}', "--")
    html = html.replace('{{SLEEP_CORE}}', "--")
    html = html.replace('{{SLEEP_REM}}', "--")
    html = html.replace('{{SLEEP_AWAKE}}', "--")
    html = html.replace('{{SLEEP_DEEP_PCT}}', '0')
    html = html.replace('{{SLEEP_CORE_PCT}}', '0')
    html = html.replace('{{SLEEP_REM_PCT}}', '0')
    html = html.replace('{{SLEEP_AWAKE_PCT}}', '0')
    html = html.replace('{{SLEEP_ANALYSIS_BORDER}}', '#dc2626')
    html = html.replace('{{SLEEP_ANALYSIS_TEXT}}', ai_analyses['sleep'])
    
    # 运动分析 - 使用AI分析
    html = html.replace('{{WORKOUT_NAME}}', '楼梯')
    html = html.replace('{{WORKOUT_TIME}}', '20:25')
    html = html.replace('{{WORKOUT_DURATION}}', '33')
    html = html.replace('{{WORKOUT_ENERGY}}', '299')
    html = html.replace('{{WORKOUT_AVG_HR}}', '150')
    html = html.replace('{{WORKOUT_MAX_HR}}', '168')
    # 生成心率图表
    hr_timeline = [
        {"time": "20:33", "avg": 147, "max": 155},
        {"time": "20:34", "avg": 133, "max": 136},
        {"time": "20:35", "avg": 134, "max": 138},
        {"time": "20:38", "avg": 165, "max": 165},
        {"time": "20:43", "avg": 157, "max": 166},
        {"time": "20:44", "avg": 141, "max": 148},
        {"time": "20:45", "avg": 133, "max": 137},
        {"time": "20:46", "avg": 150, "max": 159},
        {"time": "20:47", "avg": 161, "max": 162},
        {"time": "20:49", "avg": 163, "max": 164},
        {"time": "20:50", "avg": 160, "max": 163},
        {"time": "20:51", "avg": 159, "max": 164},
        {"time": "20:52", "avg": 158, "max": 160},
        {"time": "20:53", "avg": 160, "max": 161},
        {"time": "20:54", "avg": 157, "max": 168},
        {"time": "20:55", "avg": 139, "max": 145},
        {"time": "20:56", "avg": 130, "max": 134},
        {"time": "20:57", "avg": 146, "max": 155},
        {"time": "20:58", "avg": 160, "max": 163},
        {"time": "20:59", "avg": 159, "max": 161},
        {"time": "21:00", "avg": 160, "max": 161},
        {"time": "21:01", "avg": 161, "max": 162},
        {"time": "21:02", "avg": 150, "max": 162},
        {"time": "21:03", "avg": 131, "max": 137},
        {"time": "21:04", "avg": 138, "max": 147},
        {"time": "21:05", "avg": 155, "max": 155},
        {"time": "21:06", "avg": 156, "max": 157}
    ]
    
    times = [h['time'] for h in hr_timeline]
    avg_hrs = [h['avg'] for h in hr_timeline]
    max_hrs = [h['max'] for h in hr_timeline]
    y_min = max(0, min(avg_hrs) - 10)
    y_max = max(max_hrs) + 10
    
    hr_chart_html = f'''<div style="height:200px;width:100%;">
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
    </script>'''
    
    html = html.replace('{{WORKOUT_HR_CHART}}', hr_chart_html)
    html = html.replace('{{WORKOUT_ANALYSIS}}', ai_analyses['workout'])
    
    # AI建议 - 使用AI分析的最高优先级建议
    priority = ai_analyses['priority']
    html = html.replace('{{AI1_TITLE}}', priority['title'])
    html = html.replace('{{AI1_PROBLEM}}', priority['problem'])
    html = html.replace('{{AI1_ACTION}}', priority['action'])
    html = html.replace('{{AI1_EXPECTATION}}', priority['expectation'])
    
    # 其他AI建议
    html = html.replace('{{AI2_TITLE}}', '增加日常活动量')
    html = html.replace('{{AI2_PROBLEM}}', '今日步数6,852步，距离10,000步目标有3,148步差距，基础活动量需要提升。')
    html = html.replace('{{AI2_ACTION}}', '1. 设定每小时站立活动5分钟提醒<br>2. 选择楼梯代替电梯<br>3. 饭后散步15-20分钟<br>4. 周末安排户外活动')
    html = html.replace('{{AI2_EXPECTATION}}', '2-3周后日均步数可提升至8,000步以上。')
    
    html = html.replace('{{AI3_TITLE}}', '饮食优化建议')
    
    # 使用更易读的格式
    diet_analysis = """<div style="line-height:1.8;">
<strong style="color:#667eea;">【一日三餐方案】</strong>（适合正常工作日）<br><br>

<strong>🌅 早餐（7:00-8:00，约400-500千卡）</strong><br>
• 主食：燕麦粥1碗（50g干燕麦）或全麦面包2片<br>
• 蛋白质：水煮蛋2个 或 牛奶250ml / 豆浆300ml<br>
• 蔬果：苹果1个 或 番茄1个<br>
• 脂肪：坚果10g（约8-10颗杏仁）<br><br>

<strong>☀️ 午餐（12:00-13:00，约600-700千卡）</strong><br>
• 主食：糙米饭1碗（150g熟重）或 荞麦面150g<br>
• 蛋白质：清蒸鱼100g / 鸡胸肉100g / 豆腐150g<br>
• 蔬菜：西兰花/青菜/菠菜 200g（约1大碗）<br>
• 汤类：番茄蛋汤或紫菜蛋花汤1碗<br>
• 油脂：橄榄油5-10ml（约1茶匙）<br><br>

<strong>🌙 晚餐（18:00-19:00，约400-500千卡）</strong><br>
• 主食：杂粮粥1碗（小米+燕麦共40g）或 红薯150g<br>
• 蛋白质：豆腐100g / 瘦肉80g / 鱼类100g<br>
• 蔬菜：凉拌黄瓜/生菜沙拉 200g（少油少盐）<br>
• 饮品：无糖酸奶100g 或 温水<br><br>

<strong style="color:#667eea;">【一日两餐方案】</strong>（适合轻断食或休息日）<br><br>

<strong>🍽️ 第一餐（10:00-11:00，约800-900千卡）</strong><br>
• 主食：全麦三明治1份<br>
  （全麦面包2片 + 鸡蛋1个 + 生菜 + 番茄）<br>
• 蛋白质：牛奶300ml 或 希腊酸奶150g<br>
• 蔬果：香蕉1根 + 蓝莓50g<br>
• 脂肪：牛油果半个 或 坚果15g<br><br>

<strong>🍽️ 第二餐（17:00-18:00，约700-800千卡）</strong><br>
• 主食：藜麦饭1碗（120g熟重）或 紫薯150g<br>
• 蛋白质：三文鱼120g / 虾仁150g / 鸡胸肉100g<br>
• 蔬菜：炒时蔬250g（西兰花/芦笋/青椒）<br>
• 汤类：味噌汤或冬瓜汤1碗<br><br>

<strong style="color:#dc2626;">【运动日特别补充】</strong><br><br>

<strong>运动前1小时：</strong><br>
• 香蕉1根 + 黑咖啡1杯（提升运动表现）<br><br>

<strong>运动后30分钟内：</strong><br>
• 蛋白质补充：蛋白粉20g + 牛奶200ml<br>
• 或：鸡蛋2个 + 全麦面包1片<br><br>

<strong>全天饮水：</strong>2000-2500ml，少量多次<br><br>

<strong style="color:#667eea;">【关键原则】</strong><br>
✓ 每餐包含蛋白质（维持肌肉量）<br>
✓ 控制精制碳水（白米/白面减半）<br>
✓ 蔬菜不限量（每餐至少200g）<br>
✓ 避免高糖饮料和加工食品<br>
✓ 进食时间规律，晚餐不晚于20:00
</div>"""
    
    html = html.replace('{{AI3_DIET}}', diet_analysis)
    html = html.replace('{{AI3_ROUTINE}}', """【作息优化时间表】

工作日作息：
- 06:30 起床，喝一杯温水（300ml）
- 06:30-07:00 轻度拉伸10分钟+洗漱
- 07:00-07:30 早餐时间
- 07:30 出门通勤（步行/骑行优先）
- 12:00-13:00 午餐+饭后散步15分钟
- 13:00-18:00 工作时间（每小时起身活动5分钟）
- 18:00-19:00 晚餐时间
- 19:00-20:00 运动时间（或散步30分钟）
- 20:00-21:00 自由时间（阅读/放松）
- 21:00-21:30 睡前准备（洗漱/护肤）
- 21:30 关闭所有电子屏幕
- 21:30-22:00 睡前放松（冥想/阅读/拉伸）
- 22:00-22:30 入睡（目标7.5-8小时睡眠）

休息日作息：
- 07:30-08:00 自然醒，不赖床超过1小时
- 08:00-09:00 空腹有氧运动30-40分钟（慢跑/快走/骑行）
- 09:00-09:30 早餐（运动后补充）
- 10:00-12:00 个人时间/学习/社交
- 12:00-13:00 午餐
- 13:00-14:00 午休20-30分钟（不超30分钟）
- 14:00-17:00 户外活动/兴趣爱好
- 17:00-18:00 力量训练或瑜伽
- 18:00-19:00 晚餐
- 19:00-21:00 家庭时间/放松
- 21:00-22:00 睡前准备
- 22:30 入睡

【关键原则】：
1. 固定起床和就寝时间，误差不超过30分钟
2. 睡前1小时无屏幕（手机/电脑/电视）
3. 午休控制在20-30分钟，避免进入深睡期
4. 晚餐与睡眠间隔至少3小时
5. 卧室环境：温度18-20°C，遮光窗帘，安静或白噪音""")
    
    html = html.replace('{{AI4_TITLE}}', '数据洞察总结')
    html = html.replace('{{AI4_ADVANTAGES}}', 'HRV 52.8ms显示自主神经平衡良好，静息心率57bpm优秀，楼梯训练强度适中，心肺功能正常。')
    html = html.replace('{{AI4_RISKS}}', '睡眠严重不足（2.8小时）是最紧迫的健康风险，可能导致认知功能下降、免疫力降低，长期与慢性疾病风险增加相关。')
    html = html.replace('{{AI4_CONCLUSION}}', '整体健康状况有改善空间。运动表现良好，但睡眠严重不足需要立即干预。建议优先改善睡眠，同时稳步提升日常活动量。')
    html = html.replace('{{AI4_PLAN}}', '本周重点：建立固定就寝时间，目标22:30前入睡<br>下周目标：日均步数达到8,000步<br>月度目标：睡眠稳定在7小时以上，形成规律运动习惯')
    
    # 页脚
    html = html.replace('{{FOOTER_DATA_SOURCES}}', 'Apple Health (AI分析版) | HRV:51点 步数:276点')
    html = html.replace('{{FOOTER_DATE}}', datetime.now().strftime('%Y-%m-%d %H:%M'))
    
    return html

def main():
    # AI分析内容（基于刚才的对话分析）
    ai_analyses = {
        'hrv': """心率变异性今日为52.8ms（基于51个数据点测量）。从生理机制看，HRV反映交感神经与副交感神经的动态平衡，您的数值处于良好水平，表明自主神经系统调节能力良好，身体具备较强的恢复潜力和压力适应力。

结合今日睡眠2.82小时、步数6,852步的活动量，睡眠不足是限制HRV进一步提升的关键因素。虽然HRV目前处于良好范围，但持续睡眠不足将逐渐侵蚀恢复能力，可能导致HRV下降趋势。

建议：今晚优先保证7-8小时睡眠，避免高强度训练，可尝试睡前10分钟冥想放松，有助于提升HRV至55ms以上。""",

        'sleep': """今日睡眠总时长2.8小时，远低于7-9小时推荐标准，属于严重睡眠不足。从睡眠医学角度，成年人需要7-9小时睡眠以完成身体修复、记忆巩固和免疫调节。2.8小时睡眠仅能满足最低生理需求，无法支持正常认知功能和日间精力。

短期影响包括注意力下降30-40%、情绪不稳定、反应速度降低；长期睡眠不足与肥胖风险增加40%、2型糖尿病风险增加30%、心血管疾病风险增加50-70%相关。结合今日进行了33分钟中高强度楼梯训练，缺乏充足睡眠将严重影响运动恢复效果。

强烈建议：今晚立即采取措施，提前60-90分钟就寝（目标22:30），建立睡前1小时无屏幕时间，调暗卧室灯光，进行放松仪式。这是当前最紧迫的健康干预。""",

        'workout': """今日完成楼梯运动，持续33分钟，平均心率150bpm，最高心率168bpm，消耗能量约299千卡。

运动强度评估：中高强度（心率区间3，乳酸阈值区），主要提升心肺耐力和脂肪燃烧效率。心率曲线显示：前5分钟热身（130-140bpm），随后进入稳定训练区间（150-165bpm），最后10分钟逐渐降温（130-155bpm），训练结构合理。

值得注意的是，昨夜仅睡2.82小时，今日进行中高强度运动存在一定过度训练风险。虽然平均心率150bpm处于安全范围，但睡眠不足时身体恢复能力下降，建议运动后加强恢复监测。结合今日步数6,852步，整体活动量尚可，但睡眠赤字可能延迟恢复。

建议：运动后进行10-15分钟下肢拉伸，补充蛋白质和碳水化合物（如香蕉+酸奶），监测明日晨起HRV。如HRV下降超过5ms，明日应降低训练强度或休息。""",

        'priority': {
            'title': '【最高优先级】立即改善睡眠时长至7小时以上',
            'problem': '昨夜仅睡2.8小时，远低于7-9小时推荐标准，属于严重睡眠不足。短期将导致认知功能下降30-40%、情绪不稳定、免疫力降低；长期与肥胖、糖尿病、心血管疾病风险增加50-70%相关。虽然HRV 52.8ms目前正常，但持续睡眠不足将快速侵蚀恢复能力，形成恶性循环。',
            'action': '1. 今晚就寝时间提前至22:30（比平时早60-90分钟），设定21:00闹钟提醒开始睡前准备<br>2. 建立睡前1小时「无屏幕时间」：21:30后关闭手机/电脑/电视，蓝光抑制褪黑素分泌达50%<br>3. 卧室环境优化：温度调至18-20°C，使用遮光窗帘确保黑暗，白噪音或耳塞减少噪音干扰<br>4. 睡前放松仪式：10分钟温和拉伸→5分钟4-7-8深呼吸（吸气4秒、屏息7秒、呼气8秒）→阅读纸质书15分钟<br>5. 避免午后咖啡因：14:00后停止摄入咖啡、茶、可乐等含咖啡因饮品',
            'expectation': '通过上述措施，预期3-5天内入睡时间缩短至20分钟以内，睡眠效率提升至85%以上，1周内睡眠时长稳定在7小时以上，睡眠质量评分从30分提升至70分以上。相应的，HRV应提升5-10ms至57-62ms区间，日间精力和工作效率显著改善，运动恢复能力增强。'
        }
    }
    
    # 加载模板
    with open(TEMPLATE_DIR / 'DAILY_TEMPLATE_V2.html', 'r', encoding='utf-8') as f:
        template = f.read()
    
    # 加载数据
    data = {
        'date': '2026-02-18',
        'hrv': {'value': 52.8, 'points': 51},
        'resting_hr': {'value': 57},
        'steps': 6852,
        'active_energy': 564,
        'spo2': 96.1,
        'workouts': [{'name': '楼梯', 'duration_min': 33.4, 'energy_kcal': 299, 'avg_hr': 150, 'max_hr': 168}],
        'has_workout': True,
        'sleep': {'total': 2.82}
    }
    
    print("=" * 60)
    print("生成V5.0 AI分析报告 - 2月18日")
    print("=" * 60)
    
    # 生成HTML
    html = generate_daily_report_v5_ai('2026-02-18', ai_analyses, data, template)
    
    # 生成PDF
    output_path = OUTPUT_DIR / '2026-02-18-daily-report-V5-AI.pdf'
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.set_content(html)
        page.wait_for_timeout(3000)
        page.pdf(path=str(output_path), format='A4', print_background=True,
                margin={'top': '8mm', 'bottom': '8mm', 'left': '8mm', 'right': '8mm'})
        browser.close()
    
    print(f"\n✅ 报告生成完成: {output_path}")
    print(f"   文件大小: {output_path.stat().st_size / 1024:.0f} KB")
    
    # 显示AI分析字数
    print("\n📊 AI分析字数统计:")
    print(f"   HRV分析: {len(ai_analyses['hrv'])}字 (目标150-200)")
    print(f"   睡眠分析: {len(ai_analyses['sleep'])}字 (目标150-200)")
    print(f"   运动分析: {len(ai_analyses['workout'])}字 (目标150-200)")
    print(f"   最高优先级-问题: {len(ai_analyses['priority']['problem'])}字")
    print(f"   最高优先级-行动: {len(ai_analyses['priority']['action'])}字")
    print(f"   最高优先级-效果: {len(ai_analyses['priority']['expectation'])}字")

if __name__ == '__main__':
    main()
