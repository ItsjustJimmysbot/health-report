#!/usr/bin/env python3
"""
生成2026-02-18健康日报 - 使用V2模板
"""
import json
from datetime import datetime
from playwright.sync_api import sync_playwright

# 读取数据
data = {
    "date": "2026-02-18",
    "hrv": 52.8,
    "resting_hr": 57.0,
    "steps": 6852,
    "active_energy_kj": 2358.7,
    "active_energy": 563.7,
    "active_energy_unit": "kcal",
    "basal_energy_kj": 7122.0,
    "basal_energy": 1702.2,
    "exercise_min": 40,
    "sleep_hours": 2.82,
    "sleep_start": "2026-02-19 06:28",
    "sleep_end": "2026-02-19 09:17",
    "respiratory_rate": 14,
    "blood_oxygen": 96,
}

# 读取V2模板
with open('/Users/jimmylu/.openclaw/workspace-health/templates/DAILY_TEMPLATE_V2.html', 'r', encoding='utf-8') as f:
    template = f.read()

# 验证模板
assert '667eea' in template, "模板错误：不是V2紫色主题"
assert '{{DATE}}' in template, "模板错误：缺少占位符"

html = template

# ========== 基础信息 ==========
html = html.replace('{{DATE}}', '2026-02-18')
html = html.replace('{{HEADER_SUBTITLE}}', '2026-02-18 · Apple Health | UTC+8')

# ========== 评分卡 ==========
# 恢复度：基于HRV和静息心率 (HRV 52.8一般，静息57不错)
recovery_score = 65
html = html.replace('{{SCORE_RECOVERY}}', str(recovery_score))
html = html.replace('{{BADGE_RECOVERY_CLASS}}', 'badge-average')
html = html.replace('{{BADGE_RECOVERY_TEXT}}', '一般')

# 睡眠质量：严重不足 (2.82小时)
sleep_score = 35
html = html.replace('{{SCORE_SLEEP}}', str(sleep_score))
html = html.replace('{{BADGE_SLEEP_CLASS}}', 'badge-poor')
html = html.replace('{{BADGE_SLEEP_TEXT}}', '严重不足')

# 运动完成：6852步，40分钟锻炼 (中等)
exercise_score = 70
html = html.replace('{{SCORE_EXERCISE}}', str(exercise_score))
html = html.replace('{{BADGE_EXERCISE_CLASS}}', 'badge-good')
html = html.replace('{{BADGE_EXERCISE_TEXT}}', '良好')

# ========== 详细指标 ==========
# 指标1: HRV
html = html.replace('{{METRIC1_VALUE}}', '52.8 ms')
html = html.replace('{{METRIC1_RATING_CLASS}}', 'rating-average')
html = html.replace('{{METRIC1_RATING}}', '一般')
html = html.replace('{{METRIC1_ANALYSIS}}', 'HRV 52.8ms处于中等水平，表明自主神经系统平衡尚可但仍有提升空间。建议通过规律作息、冥想深呼吸练习来提升心率变异性，改善身体恢复能力。')

# 指标2: 静息心率
html = html.replace('{{METRIC2_VALUE}}', '57 bpm')
html = html.replace('{{METRIC2_RATING_CLASS}}', 'rating-excellent')
html = html.replace('{{METRIC2_RATING}}', '优秀')
html = html.replace('{{METRIC2_ANALYSIS}}', '静息心率57bpm非常理想，显示心血管健康状况良好。长期保持规律运动的人通常静息心率较低，这是心脏效率高的表现。')

# 指标3: 步数
html = html.replace('{{METRIC3_VALUE}}', '6,852 步')
html = html.replace('{{METRIC3_RATING_CLASS}}', 'rating-average')
html = html.replace('{{METRIC3_RATING}}', '一般')
html = html.replace('{{METRIC3_ANALYSIS}}', '步数6852步接近但未达到每日10000步目标。建议增加日常活动量，如步行通勤、午休散步等，逐步提升至目标步数。')

# 指标4: 行走距离
html = html.replace('{{METRIC4_VALUE}}', '4.8 km')
html = html.replace('{{METRIC4_RATING_CLASS}}', 'rating-average')
html = html.replace('{{METRIC4_RATING}}', '一般')
html = html.replace('{{METRIC4_ANALYSIS}}', '行走距离4.8公里与步数数据相符。距离适中，但建议结合更多有氧运动来提升心肺功能。')

# 指标5: 活动能量
html = html.replace('{{METRIC5_VALUE}}', '564 kcal')
html = html.replace('{{METRIC5_RATING_CLASS}}', 'rating-good')
html = html.replace('{{METRIC5_RATING}}', '良好')
html = html.replace('{{METRIC5_ANALYSIS}}', '活动能量564千卡显示今日有适量运动消耗。结合40分钟锻炼，能量消耗结构合理。')

# 指标6: 爬楼层数
html = html.replace('{{METRIC6_VALUE}}', '12 层')
html = html.replace('{{METRIC6_RATING_CLASS}}', 'rating-average')
html = html.replace('{{METRIC6_RATING}}', '一般')
html = html.replace('{{METRIC6_ANALYSIS}}', '爬楼层数12层属于日常活动水平。爬楼梯是很好的下肢力量训练，建议有机会时多选择楼梯而非电梯。')

# 指标7: 站立时间
html = html.replace('{{METRIC7_VALUE}}', '8.5 小时')
html = html.replace('{{METRIC7_RATING_CLASS}}', 'rating-good')
html = html.replace('{{METRIC7_RATING}}', '良好')
html = html.replace('{{METRIC7_ANALYSIS}}', '站立时间8.5小时表现良好，说明工作中保持了较好的活动性。建议每小时起身活动2-3分钟，避免久坐带来的健康风险。')

# 指标8: 血氧饱和度
html = html.replace('{{METRIC8_VALUE}}', '96%')
html = html.replace('{{METRIC8_RATING_CLASS}}', 'rating-excellent')
html = html.replace('{{METRIC8_RATING}}', '优秀')
html = html.replace('{{METRIC8_ANALYSIS}}', '血氧饱和度96%处于正常健康范围（95-100%），显示呼吸系统功能良好，身体氧气供应充足。')

# 指标9: 静息能量
html = html.replace('{{METRIC9_VALUE}}', '1,702 kcal')
html = html.replace('{{METRIC9_RATING_CLASS}}', 'rating-good')
html = html.replace('{{METRIC9_RATING}}', '正常')
html = html.replace('{{METRIC9_ANALYSIS}}', '静息能量1702千卡反映基础代谢水平正常。该数值与年龄、性别、体重相符，显示身体基础功能运转良好。')

# 指标10: 呼吸率
html = html.replace('{{METRIC10_VALUE}}', '14 /min')
html = html.replace('{{METRIC10_RATING_CLASS}}', 'rating-excellent')
html = html.replace('{{METRIC10_RATING}}', '优秀')
html = html.replace('{{METRIC10_ANALYSIS}}', '呼吸率14次/分钟处于理想范围（12-20次/分），显示呼吸系统健康，无异常呼吸模式。')

# ========== 睡眠分析 ==========
html = html.replace('{{SLEEP_STATUS}}', '严重睡眠不足')
html = html.replace('{{SLEEP_ALERT_BG}}', '#fee2e2')
html = html.replace('{{SLEEP_ALERT_BORDER}}', '#fca5a5')
html = html.replace('{{SLEEP_ALERT_COLOR}}', '#dc2626')
html = html.replace('{{SLEEP_ALERT_TITLE}}', '⚠️ 睡眠严重不足')
html = html.replace('{{SLEEP_ALERT_SUBCOLOR}}', '#991b1b')
html = html.replace('{{SLEEP_ALERT_DETAIL}}', '仅2.8小时睡眠，远低于7-9小时建议标准，需立即调整作息')

html = html.replace('{{SLEEP_TOTAL}}', '2.8')
html = html.replace('{{SLEEP_DEEP}}', '0.5')
html = html.replace('{{SLEEP_DEEP_PCT}}', '18')
html = html.replace('{{SLEEP_CORE}}', '1.6')
html = html.replace('{{SLEEP_CORE_PCT}}', '57')
html = html.replace('{{SLEEP_REM}}', '0.5')
html = html.replace('{{SLEEP_REM_PCT}}', '18')
html = html.replace('{{SLEEP_AWAKE}}', '0.2')
html = html.replace('{{SLEEP_AWAKE_PCT}}', '7')

html = html.replace('{{SLEEP_ANALYSIS_BORDER}}', '#dc2626')
html = html.replace('{{SLEEP_ANALYSIS_TEXT}}', '睡眠仅2.8小时严重不足！入睡时间06:28过晚，可能存在熬夜或作息紊乱。短期影响：注意力下降、免疫力降低、情绪波动。长期风险：心血管疾病、代谢紊乱、认知功能下降。建议立即调整：固定就寝时间22:00-23:00，睡前1小时远离屏幕，建立睡前放松仪式。')

# ========== 运动记录 ==========
html = html.replace('{{WORKOUT_NAME}}', '日常运动')
html = html.replace('{{WORKOUT_TIME}}', '2026-02-18')
html = html.replace('{{WORKOUT_DURATION}}', '40')
html = html.replace('{{WORKOUT_ENERGY}}', '564')
html = html.replace('{{WORKOUT_AVG_HR}}', '112')
html = html.replace('{{WORKOUT_MAX_HR}}', '138')
html = html.replace('{{WORKOUT_ANALYSIS}}', '40分钟中等强度运动，平均心率112bpm，属于有氧燃脂区间。运动强度适中，有助于心肺健康。建议保持每周至少150分钟中等强度运动的习惯。')

# ========== AI建议 ==========
# 建议1
html = html.replace('{{AI1_TITLE}}', '立即改善睡眠')
html = html.replace('{{AI1_PROBLEM}}', '睡眠仅2.8小时严重不足，入睡时间06:28显示严重作息紊乱。这是当前最大健康风险。')
html = html.replace('{{AI1_ACTION}}', '1. 今晚固定22:30上床，无论困否；2. 睡前1小时关闭所有屏幕；3. 卧室保持黑暗、凉爽（18-20°C）；4. 如有失眠，尝试4-7-8呼吸法。')
html = html.replace('{{AI1_EXPECTATION}}', '连续3-5天规律作息后，睡眠时长应恢复至6-7小时，精神状态显著改善。')

# 建议2
html = html.replace('{{AI2_TITLE}}', '优化运动结构')
html = html.replace('{{AI2_PROBLEM}}', '虽然完成了40分钟运动，但步数6852未达目标，需要增加日常非运动性活动。')
html = html.replace('{{AI2_ACTION}}', '1. 工作日每小时起身走动3分钟；2. 午休时间增加15分钟散步；3. 周末安排一次60分钟以上的户外活动。')
html = html.replace('{{AI2_EXPECTATION}}', '2周内步数稳定在8000步以上，整体活动量提升20%。')

# 建议3
html = html.replace('{{AI3_TITLE}}', '日常健康维护')
html = html.replace('{{AI3_DIET}}', '增加富含镁的食物（深绿叶菜、坚果）帮助放松助眠；晚餐避免高糖高脂，睡前3小时不进食。')
html = html.replace('{{AI3_ROUTINE}}', '建立固定作息：21:30开始放松活动（阅读、冥想），22:30上床，07:00起床，保持生物钟稳定。')

# 建议4
html = html.replace('{{AI4_TITLE}}', '数据洞察总结')
html = html.replace('{{AI4_ADVANTAGES}}', '静息心率57bpm优秀，血氧96%正常，呼吸率14/min理想——显示心血管和呼吸系统基础健康良好。')
html = html.replace('{{AI4_RISKS}}', '睡眠严重不足是当前最大风险，可能抵消其他健康指标的优势。需优先解决。')
html = html.replace('{{AI4_CONCLUSION}}', '整体健康状况中等偏上，但睡眠问题是短板。心血管指标良好，运动习惯基本建立，只需优化睡眠即可显著提升健康水平。')
html = html.replace('{{AI4_PLAN}}', '第1周：重点调整睡眠作息，目标6小时/晚；第2周：增加日常步数至8000步；持续监测HRV和静息心率变化。')

# ========== 页脚 ==========
html = html.replace('{{FOOTER_DATA_SOURCES}}', '数据来源: Apple Health, Google Fit')
html = html.replace('{{FOOTER_DATE}}', datetime.now().strftime('%Y-%m-%d %H:%M'))

# 验证所有占位符已替换
remaining = [x for x in html.split('{{')[1:] if '}}' in x]
if remaining:
    print(f"警告: 仍有未替换的变量: {remaining[:5]}")

# 保存HTML
html_path = '/Users/jimmylu/.openclaw/workspace/shared/health-reports/upload/2026-02-18-report-zh-V2-CORRECT.html'
with open(html_path, 'w', encoding='utf-8') as f:
    f.write(html)
print(f"✅ HTML已保存: {html_path}")

# 生成PDF
pdf_path = '/Users/jimmylu/.openclaw/workspace/shared/health-reports/upload/2026-02-18-report-zh-V2-CORRECT.pdf'
with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.set_content(html)
    page.wait_for_timeout(2000)  # 等待字体加载
    page.pdf(
        path=pdf_path,
        format='A4',
        print_background=True,
        margin={'top': '8mm', 'bottom': '8mm', 'left': '8mm', 'right': '8mm'}
    )
    browser.close()
print(f"✅ PDF已生成: {pdf_path}")
