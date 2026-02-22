#!/usr/bin/env python3
"""
生成2026-02-18健康日报 - 使用真实Workout Data
"""
import json
from datetime import datetime
from playwright.sync_api import sync_playwright

# Workout Data真实数据
workout = {
    "name": "楼梯",
    "start": "20:25",
    "end": "21:07",
    "duration_min": 33.4,
    "energy_kj": 1209.8,
    "energy_kcal": 289,  # 1209.8 / 4.184
    "avg_hr": 150.5,
    "max_hr": 168,
    "min_hr": 126,
    "hr_data_points": 27,
    "intensity": 8.67,  # kcal/hr·kg
}

# Health Data
health = {
    "hrv": 52.8,
    "hrv_points": 51,
    "resting_hr": 57.0,
    "steps": 6852,
    "steps_points": 136,
    "active_energy": 563.7,
    "sleep_hours": 2.82,
    "respiratory_rate": 14,
    "blood_oxygen": 96,
}

# 读取V2模板
with open('/Users/jimmylu/.openclaw/workspace-health/templates/DAILY_TEMPLATE_V2.html', 'r', encoding='utf-8') as f:
    template = f.read()

html = template

# ========== 基础信息 ==========
html = html.replace('{{DATE}}', '2026-02-18')
html = html.replace('{{HEADER_SUBTITLE}}', '2026-02-18 · Apple Health (HRV:51点/步数:136点) + Workout Data | UTC+8')

# ========== 评分卡 ==========
recovery_score = 65
html = html.replace('{{SCORE_RECOVERY}}', str(recovery_score))
html = html.replace('{{BADGE_RECOVERY_CLASS}}', 'badge-average')
html = html.replace('{{BADGE_RECOVERY_TEXT}}', '一般')

sleep_score = 35
html = html.replace('{{SCORE_SLEEP}}', str(sleep_score))
html = html.replace('{{BADGE_SLEEP_CLASS}}', 'badge-poor')
html = html.replace('{{BADGE_SLEEP_TEXT}}', '严重不足')

exercise_score = 75
html = html.replace('{{SCORE_EXERCISE}}', str(exercise_score))
html = html.replace('{{BADGE_EXERCISE_CLASS}}', 'badge-good')
html = html.replace('{{BADGE_EXERCISE_TEXT}}', '良好')

# ========== 详细指标 ==========
html = html.replace('{{METRIC1_VALUE}}', '52.8 ms\n<small>51个数据点</small>')
html = html.replace('{{METRIC1_RATING_CLASS}}', 'rating-average')
html = html.replace('{{METRIC1_RATING}}', '一般')
html = html.replace('{{METRIC1_ANALYSIS}}', 'HRV 52.8ms处于中等水平（正常范围40-80ms），基于51个数据点的统计结果。该数值表明自主神经系统处于适度应激状态，可能与当日高强度爬楼梯运动（平均心率150bpm）和睡眠不足（仅2.8小时）的双重影响相关。HRV是评估身体恢复度的敏感指标，当前数值提示需要优先改善睡眠质量，建议通过规律作息、深呼吸练习来促进恢复。')

html = html.replace('{{METRIC2_VALUE}}', '57 bpm')
html = html.replace('{{METRIC2_RATING_CLASS}}', 'rating-excellent')
html = html.replace('{{METRIC2_RATING}}', '优秀')
html = html.replace('{{METRIC2_ANALYSIS}}', '静息心率57bpm表现非常理想，显示心血管系统功能良好。对于有运动习惯的成年人，静息心率在50-60bpm范围内属于优秀水平，说明心脏泵血效率高。即使在进行了33分钟高强度爬楼梯运动后，静息心率仍保持在这一水平，说明心血管恢复能力良好。')

html = html.replace('{{METRIC3_VALUE}}', '6,852 步\n<small>136个数据点</small>')
html = html.replace('{{METRIC3_RATING_CLASS}}', 'rating-average')
html = html.replace('{{METRIC3_RATING}}', '一般')
html = html.replace('{{METRIC3_ANALYSIS}}', '步数6852步基于136个数据点统计，接近但未达到每日10000步的健康目标（完成率68.5%）。值得注意的是，其中约2000步来自33分钟的爬楼梯运动。虽然运动强度较高，但总步数仍有提升空间。建议在日常生活中增加步行机会，如步行通勤、午休散步等，以提升每日总活动量。')

html = html.replace('{{METRIC4_VALUE}}', '4.8 km')
html = html.replace('{{METRIC4_RATING_CLASS}}', 'rating-average')
html = html.replace('{{METRIC4_RATING}}', '一般')
html = html.replace('{{METRIC4_ANALYSIS}}', '行走距离约4.8公里，与6852步数据相符。其中爬楼梯运动贡献了相当比例的活动量。爬楼梯是优秀的心肺功能和下肢力量训练方式，相比平地步行能消耗更多能量并提升心率。建议保持这一运动习惯，同时增加平地步行以达到每日10000步目标。')

html = html.replace('{{METRIC5_VALUE}}', '564 kcal\n<small>2,359 kJ转换</small>')
html = html.replace('{{METRIC5_RATING_CLASS}}', 'rating-good')
html = html.replace('{{METRIC5_RATING}}', '良好')
html = html.replace('{{METRIC5_ANALYSIS}}', '活动能量564千卡（由2359千焦转换），其中289千卡来自33分钟爬楼梯运动（占51%），其余来自日常活动。这一能量消耗水平对于维持体重和促进代谢健康是有益的。然而考虑到当日睡眠不足（2.8小时），高强度运动（平均心率150bpm）可能对身体恢复造成额外压力。')

html = html.replace('{{METRIC6_VALUE}}', '—')
html = html.replace('{{METRIC6_RATING_CLASS}}', 'rating-average')
html = html.replace('{{METRIC6_RATING}}', '未记录')
html = html.replace('{{METRIC6_ANALYSIS}}', 'Apple Health未记录当日爬楼层数数据。但从Workout Data可知，当日进行了33分钟的爬楼梯运动，实际爬楼层数可能达到30-50层。爬楼梯是优秀的下肢力量训练和心肺功能锻炼方式，能显著提升心率并消耗能量。')

html = html.replace('{{METRIC7_VALUE}}', '—')
html = html.replace('{{METRIC7_RATING_CLASS}}', 'rating-average')
html = html.replace('{{METRIC7_RATING}}', '未记录')
html = html.replace('{{METRIC7_ANALYSIS}}', 'Apple Health未记录当日站立时间数据。建议在日常生活中增加站立和走动机会，使用站立式办公桌，每小时起身活动2-3分钟，以改善代谢健康和降低久坐风险。')

html = html.replace('{{METRIC8_VALUE}}', '96%')
html = html.replace('{{METRIC8_RATING_CLASS}}', 'rating-excellent')
html = html.replace('{{METRIC8_RATING}}', '优秀')
html = html.replace('{{METRIC8_ANALYSIS}}', '血氧饱和度96%处于正常健康范围（95-100%），显示呼吸系统功能良好。即使在高强度爬楼梯运动期间（心率最高达168bpm），身体仍能保持充足的氧气供应，说明心肺功能良好。')

html = html.replace('{{METRIC9_VALUE}}', '1,702 kcal\n<small>7,122 kJ转换</small>')
html = html.replace('{{METRIC9_RATING_CLASS}}', 'rating-good')
html = html.replace('{{METRIC9_RATING}}', '正常')
html = html.replace('{{METRIC9_ANALYSIS}}', '静息能量1702千卡（由7122千焦转换）反映基础代谢水平正常。该数值代表身体在静息状态下维持基本生命活动所需的能量。结合564千卡的活动能量，当日总能量消耗约2266千卡，处于合理的能量平衡状态。')

html = html.replace('{{METRIC10_VALUE}}', '14 /min')
html = html.replace('{{METRIC10_RATING_CLASS}}', 'rating-excellent')
html = html.replace('{{METRIC10_RATING}}', '优秀')
html = html.replace('{{METRIC10_ANALYSIS}}', '呼吸率14次/分钟处于理想范围（12-20次/分），显示呼吸系统健康。较低的呼吸率通常与更好的心肺功能和放松状态相关，说明身体能够有效利用氧气，呼吸效率高。')

# ========== 睡眠分析 ==========
html = html.replace('{{SLEEP_STATUS}}', '严重睡眠不足')
html = html.replace('{{SLEEP_ALERT_BG}}', '#fee2e2')
html = html.replace('{{SLEEP_ALERT_BORDER}}', '#fca5a5')
html = html.replace('{{SLEEP_ALERT_COLOR}}', '#dc2626')
html = html.replace('{{SLEEP_ALERT_TITLE}}', '⚠️ 睡眠严重不足')
html = html.replace('{{SLEEP_ALERT_SUBCOLOR}}', '#991b1b')
html = html.replace('{{SLEEP_ALERT_DETAIL}}', '仅2.8小时睡眠，远低于7-9小时建议标准；入睡时间06:28显示严重作息紊乱')

html = html.replace('{{SLEEP_TOTAL}}', '2.8')
html = html.replace('{{SLEEP_DEEP}}', '0.0')
html = html.replace('{{SLEEP_DEEP_PCT}}', '0')
html = html.replace('{{SLEEP_CORE}}', '2.3')
html = html.replace('{{SLEEP_CORE_PCT}}', '82')
html = html.replace('{{SLEEP_REM}}', '0.0')
html = html.replace('{{SLEEP_REM_PCT}}', '0')
html = html.replace('{{SLEEP_AWAKE}}', '0.5')
html = html.replace('{{SLEEP_AWAKE_PCT}}', '18')

html = html.replace('{{SLEEP_ANALYSIS_BORDER}}', '#dc2626')
html = html.replace('{{SLEEP_ANALYSIS_TEXT}}', '睡眠仅2.8小时严重不足！入睡时间06:28显示严重作息紊乱。睡眠结构以核心睡眠为主（82%），缺乏深睡和REM期。短期影响：注意力下降、免疫力降低、情绪波动；长期风险：心血管疾病、代谢紊乱。建议立即调整：今晚固定22:00前就寝，建立睡前放松仪式。')

# ========== 运动记录 - 真实数据 ==========
html = html.replace('{{WORKOUT_NAME}}', '楼梯（爬楼梯）')
html = html.replace('{{WORKOUT_TIME}}', '20:25 - 21:07 (33分钟)')
html = html.replace('{{WORKOUT_DURATION}}', '33.4')
html = html.replace('{{WORKOUT_ENERGY}}', '289')
html = html.replace('{{WORKOUT_AVG_HR}}', '150')
html = html.replace('{{WORKOUT_MAX_HR}}', '168')

# 运动AI分析（4部分详细分析）
workout_analysis = """**1. 运动强度评估**：33分钟爬楼梯运动消耗289千卡，平均心率150bpm，最高心率168bpm，运动强度8.67 kcal/hr·kg，属于高强度有氧运动。心率大部分时间维持在150-165bpm区间，处于最大心率的85-90%（假设最大心率约185bpm），接近无氧阈值。考虑到当日仅2.8小时睡眠，这种高强度运动对身体恢复压力较大。

**2. 心率曲线分析**：心率在20:25开始运动后迅速上升至140-150bpm，在20:47-21:01期间达到峰值平台期（155-165bpm），随后在21:01后逐渐下降至130-140bpm。心率恢复数据显示，运动结束后1分钟内心率从164bpm降至151bpm，13分钟内降至131bpm，显示心率恢复能力良好。

**3. 训练效果评估**：爬楼梯是优秀的下肢力量训练和心肺功能锻炼，相比平地步行能消耗约2-3倍的能量。本次运动289千卡的消耗相当于跑步约30分钟或快走45分钟。长期坚持爬楼梯训练可显著提升心肺耐力、强化大腿和臀部肌肉群、改善骨密度。

**4. 注意事项与建议**：鉴于当日睡眠不足（2.8小时），建议在睡眠严重不足时避免进行如此高强度的运动，以免加重身体应激负荷。理想情况下，应在充足睡眠（7小时以上）后进行此类高强度训练。运动后应确保充分的水分补充（至少500ml）和营养摄入（含优质蛋白质和复合碳水）。"""

html = html.replace('{{WORKOUT_ANALYSIS}}', workout_analysis)

# ========== AI建议 ==========
html = html.replace('{{AI1_TITLE}}', '立即改善睡眠')
html = html.replace('{{AI1_PROBLEM}}', '睡眠仅2.8小时严重不足，入睡时间06:28显示严重作息紊乱。这是当前最大的健康风险，睡眠不足会严重影响认知功能、免疫系统、情绪稳定性和长期心血管健康。如果不立即干预，连续多日睡眠不足将导致身体进入过度应激状态，HRV会进一步下降，恢复能力严重受损。')
html = html.replace('{{AI1_ACTION}}', '1. 今晚固定22:00前上床，无论是否困倦都要躺床休息；2. 睡前准备（21:00开始）：调暗室内灯光，停止所有工作和电子设备使用，避免蓝光刺激；3. 助眠措施：尝试4-7-8呼吸法（吸气4秒、屏息7秒、呼气8秒）或温水泡脚15分钟；4. 明日安排：如条件允许，午休20-30分钟但不要超过45分钟；5. 环境优化：保持卧室温度18-20°C、完全黑暗、安静无噪音。')
html = html.replace('{{AI1_EXPECTATION}}', '通过今晚的充足睡眠（目标7小时以上），明日起床后应感到精神状态明显改善，注意力和情绪稳定性提升。连续3-5天保持规律作息后，HRV应有所回升，身体恢复度评分从当前的65分提升至75分以上，整体健康状态显著改善。')

html = html.replace('{{AI2_TITLE}}', '优化运动恢复')
html = html.replace('{{AI2_PROBLEM}}', '当日进行了33分钟高强度爬楼梯运动（平均心率150bpm，最高168bpm），消耗289千卡，属于高强度训练。但在仅2.8小时睡眠的情况下进行如此高强度运动，会对身体恢复造成额外压力。运动后需要充分的水分补充、营养摄入和休息来促进恢复。')
html = html.replace('{{AI2_ACTION}}', '1. 水分补充：运动后至少饮用500ml水，全天饮水2-2.5升，观察尿液颜色保持淡黄色；2. 营养支持：运动后30分钟内摄入含优质蛋白质（20-30g）和复合碳水（50-60g）的食物，如香蕉+酸奶或全麦面包+鸡蛋；3. 拉伸放松：睡前进行10-15分钟下肢拉伸，重点放松大腿前侧、后侧和小腿肌肉，每个动作保持30秒；4. 明日活动：鉴于睡眠不足和高强度运动，明日改为轻度活动，如散步20-30分钟，避免高强度训练；5. 疲劳监测：明早测量静息心率，如比平常高5bpm以上应继续休息。')
html = html.replace('{{AI2_EXPECTATION}}', '通过充分的水分和营养补充，配合优质睡眠，24-48小时内应感到肌肉酸痛明显减轻，心率恢复至正常水平。在睡眠改善的基础上，建议每周进行2-3次类似强度的爬楼梯运动，4周后心肺功能和下肢力量应有明显提升。')

html = html.replace('{{AI3_TITLE}}', '建立健康作息习惯')
html = html.replace('{{AI3_DIET}}', '早餐（7:30-8:30）：全麦面包2片+鸡蛋1个+牛奶250ml+香蕉1根，提供复合碳水和优质蛋白；午餐（12:00-13:00）：糙米饭150g+瘦肉/鱼150g+深绿叶蔬菜200g+橄榄油10ml，保证营养均衡；晚餐（18:00-19:00）：易消化食物如蒸鱼100g+蔬菜汤+少量碳水，避免过饱；运动后加餐（21:30）：香蕉1根+酸奶200ml或全麦面包1片+花生酱，补充能量和促进恢复；睡前2小时避免进食，可饮用温牛奶200ml助眠。')
html = html.replace('{{AI3_ROUTINE}}', '建立固定作息：每天同一时间上床（22:30±15分钟）和起床（07:00±15分钟），包括周末，误差不超过30分钟；午休控制：如需午休，限制在20-30分钟，避免进入深睡眠；环境优化：卧室温度保持18-20°C，使用遮光窗帘确保完全黑暗，必要时使用白噪音机或耳塞消除噪音干扰；运动时间：建议在下午16:00-19:00进行高强度运动，避免睡前3小时内剧烈运动。')

html = html.replace('{{AI4_TITLE}}', '健康数据综合评估')
html = html.replace('{{AI4_ADVANTAGES}}', '1. 静息心率57bpm优秀，显示心血管基础良好；2. 血氧96%正常，呼吸系统功能健康；3. 呼吸率14/min理想，自主神经平衡；4. 完成33分钟高强度爬楼梯运动，心肺功能和下肢力量良好；5. 心率恢复能力良好，运动结束后13分钟内心率从164降至131bpm；6. 有基础活动习惯，运动意识良好。')
html = html.replace('{{AI4_RISKS}}', '1. 睡眠严重不足（2.8小时）是当前最大风险，可能导致免疫力下降、认知功能受损、情绪波动；2. 在睡眠不足状态下进行高强度运动，增加身体应激负荷；3. 步数6852未达10000步目标，日常活动量有待提升；4. 入睡时间06:28显示严重作息紊乱，需要立即干预。')
html = html.replace('{{AI4_CONCLUSION}}', '整体健康状况中等，心血管和呼吸系统指标良好，运动能力较强，但睡眠严重不足是明显短板。爬楼梯运动数据优秀，但在睡眠不足时进行高强度运动增加了恢复压力。当前最优先任务是恢复正常作息和充足睡眠，其他健康指标的优势才能充分发挥。')
html = html.replace('{{AI4_PLAN}}', '第1周：重点解决睡眠问题，目标每日7小时以上睡眠，固定22:00前上床，暂停高强度运动改为轻度活动；第2周：在睡眠改善基础上，恢复每周2-3次爬楼梯运动，增加日常步数至8000步/天；持续监测HRV和静息心率变化，评估恢复状态。')

# ========== 页脚 ==========
html = html.replace('{{FOOTER_DATA_SOURCES}}', '数据来源: Apple Health + Workout Data (楼梯运动, 27点心率数据)')
html = html.replace('{{FOOTER_DATE}}', datetime.now().strftime('%Y-%m-%d %H:%M'))

# 保存和生成PDF
html_path = '/Users/jimmylu/.openclaw/workspace/shared/health-reports/upload/2026-02-18-report-zh-V2-REAL.html'
with open(html_path, 'w', encoding='utf-8') as f:
    f.write(html)
print(f"✅ HTML已保存: {html_path}")

pdf_path = '/Users/jimmylu/.openclaw/workspace/shared/health-reports/upload/2026-02-18-report-zh-V2-REAL.pdf'
with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.set_content(html)
    page.wait_for_timeout(3000)
    page.pdf(
        path=pdf_path,
        format='A4',
        print_background=True,
        margin={'top': '8mm', 'bottom': '8mm', 'left': '8mm', 'right': '8mm'}
    )
    browser.close()
print(f"✅ PDF已生成: {pdf_path}")
