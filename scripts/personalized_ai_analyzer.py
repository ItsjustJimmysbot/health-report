#!/usr/bin/env python3
"""
个性化AI分析生成模块 - V5.0
基于具体数据点生成详细、个性化的健康分析
"""
from typing import Dict, List, Optional
from datetime import datetime

class PersonalizedAIAnalyzer:
    """个性化AI分析器 - 基于具体数据生成详细洞察"""
    
    def __init__(self, user_data: Dict, historical_data: List[Dict] = None):
        self.data = user_data
        self.history = historical_data or []
        self.date = user_data.get('date', '')
    
    # ========== 指标分析（150-200字，更详细个性化） ==========
    
    def analyze_hrv(self) -> str:
        """HRV个性化分析"""
        hrv = self.data['hrv']['value']
        points = self.data['hrv']['points']
        
        # 与历史对比
        if self.history:
            prev_hrv = [h['hrv']['value'] for h in self.history if h['hrv']['value']]
            avg_hrv = sum(prev_hrv) / len(prev_hrv) if prev_hrv else hrv
            diff = hrv - avg_hrv
            trend = f"较近期平均{'上升' if diff > 0 else '下降'}{abs(diff):.1f}ms" if abs(diff) > 3 else "与近期平均基本持平"
        else:
            trend = "暂无历史数据对比"
        
        analysis = f"""心率变异性今日为{hrv:.1f}ms（基于{points}个数据点测量）。{trend}。
        
从生理机制看，HRV反映交感神经与副交感神经的动态平衡。您的数值处于{'优秀' if hrv > 55 else '良好' if hrv > 45 else '一般' if hrv > 35 else '需关注'}水平，表明自主神经系统{'调节能力良好，身体具备较强的恢复潜力和压力适应力' if hrv > 45 else '调节能力一般，可能面临恢复不足或压力积累的情况'}。

结合今日睡眠{self.data['sleep']['total'] if self.data.get('sleep') else '无数据'}小时、步数{self.data['steps']['value']:,}步的活动量，{'充足的睡眠和适度活动有助于维持良好的HRV水平' if hrv > 45 and self.data.get('sleep') and self.data['sleep']['total'] > 6 else '睡眠不足或过度活动可能是HRV偏低的因素之一' if hrv <= 45 else '建议关注睡眠质量对HRV的影响'}。

建议：{'继续保持当前作息规律，可尝试冥想或深呼吸练习进一步优化' if hrv > 45 else '优先保证7-8小时睡眠，减少晚间蓝光暴露，必要时降低训练强度'}。"""
        
        return self._ensure_length(analysis, 150, 200)
    
    def analyze_sleep(self) -> str:
        """睡眠个性化分析"""
        sleep = self.data.get('sleep')
        if not sleep or sleep['total'] == 0:
            return """今日未检测到有效睡眠数据。从健康角度看，睡眠是身体修复、记忆巩固和免疫调节的关键时期。

未记录睡眠可能的原因包括：Apple Watch未佩戴或电量不足、睡眠模式未开启、或入睡时间不在追踪窗口（20:00-次日12:00）。

结合今日活动数据（步数{self.data['steps']['value']:,}步，活动消耗{self.data['active_energy']['value']:.0f}千卡），缺乏睡眠记录使得无法准确评估恢复状态。长期睡眠不足与认知功能下降、代谢紊乱、心血管疾病风险增加相关。

强烈建议：检查Apple Watch睡眠追踪设置，确保就寝时正确佩戴设备；同时建立固定作息时间，目标每晚23:00前入睡，保证7-8小时优质睡眠。充足睡眠是维持HRV稳定和日间精力的基础。""".format(**self.data)
        
        total = sleep['total']
        deep = sleep['deep']
        core = sleep['core']
        rem = sleep['rem']
        has_stages = deep > 0 or core > 0 or rem > 0
        
        # 睡眠效率分析
        if has_stages:
            efficiency = (deep + core + rem) / total * 100 if total > 0 else 0
            stage_analysis = f"睡眠效率约{efficiency:.0f}%。深睡{deep:.1f}小时({'充足' if deep >= 1.5 else '偏少'})，核心睡眠{core:.1f}小时，REM{rem:.1f}小时({'充足' if rem >= 1.5 else '偏少'})。"
        else:
            stage_analysis = f"总睡眠{total:.1f}小时，但睡眠阶段数据未记录。建议检查Apple Watch睡眠追踪设置以确保完整记录睡眠结构。"
        
        # 与HRV关联分析
        hrv = self.data['hrv']['value']
        hrv_sleep_correlation = "充足睡眠有助于维持良好HRV水平。" if total >= 7 and hrv > 50 else "睡眠不足可能是HRV偏低的因素之一，建议优先改善睡眠。" if total < 6 and hrv <= 50 else ""
        
        analysis = f"""今日睡眠总时长{total:.1f}小时。{stage_analysis}

从睡眠医学角度，成年人推荐每晚7-9小时睡眠，其中深睡应占15-20%（约1-2小时），REM占20-25%（约1.5-2小时）。您的睡眠时长{'达到推荐标准，有助于身体恢复和记忆巩固' if total >= 7 else '低于推荐标准，可能影响日间精力和长期健康' if total < 6 else '基本达标，但仍有提升空间'}。

{hrv_sleep_correlation}结合今日活动量（步数{self.data['steps']['value']:,}步），{'良好的睡眠有助于运动后恢复' if self.data['has_workout'] else '适度活动配合充足睡眠是维持健康的基础'}。

建议：{'继续保持规律作息' if total >= 7 else '今晚提前30-60分钟入睡，营造黑暗安静的睡眠环境，避免睡前使用电子设备' if total < 6 else '尝试固定就寝时间，目标每晚23:00前入睡'}。"""
        
        return self._ensure_length(analysis, 150, 200)
    
    def analyze_workout(self) -> str:
        """运动个性化分析"""
        if not self.data['has_workout'] or not self.data['workouts']:
            steps = self.data['steps']['value']
            energy = self.data['active_energy']['value']
            
            return f"""今日未记录到结构化运动数据。从活动量看，步数{steps:,}步、活动消耗{energy:.0f}千卡，属于{'轻度' if steps < 5000 else '中等' if steps < 8000 else '较高'}日常活动水平。

未进行结构化运动意味着错过了专门提升心肺功能、肌肉力量和骨密度的机会。规律运动（每周150分钟中等强度或75分钟高强度）可降低心血管疾病风险30-40%，改善胰岛素敏感性，并显著提升心理健康。

从恢复角度看，今日HRV{self.data['hrv']['value']:.1f}ms显示身体状态{'良好，适合进行中等强度运动' if self.data['hrv']['value'] > 50 else '一般，建议选择低强度活动如散步或瑜伽' if self.data['hrv']['value'] > 40 else '有待恢复，应以休息为主'}。

强烈建议：明日安排30-45分钟中等强度运动，如快走、慢跑、骑行或游泳。选择您喜欢的运动形式更容易坚持，从每周2-3次开始逐步建立习惯。"""
        
        w = self.data['workouts'][0]
        name = w['name']
        duration = w['duration_min']
        avg_hr = w['avg_hr']
        max_hr = w['max_hr']
        energy = w['energy_kcal']
        
        # 心率区间分析
        if avg_hr:
            if avg_hr > 160:
                intensity = "高强度"
                zone = "心率区间4-5（无氧/最大摄氧量区）"
                effect = "主要提升无氧能力和乳酸阈值"
            elif avg_hr > 140:
                intensity = "中高强度"
                zone = "心率区间3（乳酸阈值区）"
                effect = "提升心肺耐力和脂肪燃烧效率"
            elif avg_hr > 120:
                intensity = "中等强度"
                zone = "心率区间2（有氧基础区）"
                effect = "增强有氧基础代谢和脂肪利用"
            else:
                intensity = "低强度"
                zone = "心率区间1（恢复区）"
                effect = "促进恢复和基础有氧能力"
        else:
            intensity = "未记录心率"
            zone = "无法评估"
            effect = "建议下次运动时佩戴心率监测设备"
        
        # 与昨日恢复关联
        sleep = self.data.get('sleep')
        recovery_status = ""
        if sleep and sleep['total'] < 6:
            recovery_status = "值得注意的是，昨夜睡眠较短，今日进行高强度运动可能增加过度训练风险，建议关注身体信号。"
        
        analysis = f"""今日完成{name}运动，持续{duration:.0f}分钟{ f'，平均心率{avg_hr}bpm，最高心率{max_hr}bpm' if avg_hr else ''}。{f'消耗能量约{energy:.0f}千卡。' if energy else ''}

运动强度评估：{intensity}（{zone}）。{effect}。{recovery_status}

从训练效果看，{'本次运动强度适中，有助于提升心肺功能而不至于过度消耗' if avg_hr and 120 <= avg_hr <= 150 else '本次运动强度较高，建议关注恢复，明日可降低强度或安排休息' if avg_hr and avg_hr > 160 else '本次运动强度较低，适合恢复性训练' if avg_hr and avg_hr < 120 else ''}

结合今日步数{self.data['steps']['value']:,}步，{'今日总活动量充足，明日建议安排恢复性活动' if self.data['steps']['value'] > 8000 else '可考虑增加日常步行以提升整体活动量'}。

建议：运动后进行10-15分钟拉伸，补充水分和适量蛋白质，监测明日晨起HRV以评估恢复情况。"""
        
        return self._ensure_length(analysis, 150, 200)
    
    # ========== AI建议生成（250-300字，更详细可操作） ==========
    
    def generate_priority_recommendation(self) -> Dict[str, str]:
        """生成最高优先级建议（250-300字）"""
        hrv = self.data['hrv']['value']
        sleep = self.data.get('sleep')
        sleep_hours = sleep['total'] if sleep else 0
        steps = self.data['steps']['value']
        
        # 根据数据确定最紧急的问题
        if sleep_hours == 0:
            return {
                'title': '【紧急】修复睡眠追踪设置',
                'problem': f"今日未检测到睡眠数据，这意味着无法评估昨夜恢复质量。结合HRV {hrv:.1f}ms和步数{steps:,}步的活动量，缺乏睡眠数据使得无法制定精准的恢复建议。长期睡眠追踪缺失会导致健康评估盲区，可能错过早期恢复不足信号。",
                'action': "1. 立即检查Apple Watch设置：进入「健康」应用→睡眠→开启「通过Apple Watch跟踪睡眠」\n2. 确保Apple Watch电量充足（就寝前至少30%），建议启用睡眠模式自动开启剧院模式省电\n3. 确认睡眠定时器设置：就寝时间设为22:30，起床时间设为06:30，保证8小时睡眠窗口\n4. 检查手腕检测功能是否开启，这是睡眠追踪的前提条件\n5. 今晚开始佩戴手表入睡，建立7天连续睡眠数据基线",
                'expectation': "修复睡眠追踪后，7天内将获得完整的睡眠结构数据（深睡/核心/REM），可以准确评估睡眠质量与HRV的关联，为训练恢复提供数据支撑。预期2周内形成稳定的睡眠-恢复数据模式。"
            }
        elif sleep_hours < 6:
            return {
                'title': '【最高优先级】改善睡眠时长和质量',
                'problem': f"昨夜仅睡{sleep_hours:.1f}小时，远低于7-9小时推荐标准。短期睡眠不足会立即影响今日认知功能（注意力下降30-40%）和情绪稳定性；长期睡眠不足与肥胖、糖尿病、心血管疾病风险增加50-70%相关。今日HRV {hrv:.1f}ms{'可能已受睡眠不足影响' if hrv < 50 else '尚处于正常范围，但持续睡眠不足将逐渐侵蚀恢复能力'}。",
                'action': "1. 今晚就寝时间提前至22:30（比平时早60-90分钟），设定闹钟提醒开始睡前准备\n2. 建立睡前1小时「无屏幕时间」：21:30后关闭手机/电脑/电视，蓝光会抑制褪黑素分泌达50%\n3. 卧室环境优化：温度调至18-20°C（核心体温下降促进入睡），使用遮光窗帘（黑暗促进褪黑素分泌），白噪音或耳塞减少噪音干扰\n4. 睡前放松仪式：10分钟温和拉伸→5分钟深呼吸（4-7-8呼吸法）→阅读纸质书15分钟\n5. 避免午后咖啡因：14:00后停止摄入咖啡、茶、可乐等含咖啡因饮品",
                'expectation': "通过上述措施，预期3-5天内入睡时间缩短至20分钟以内，睡眠效率提升至85%以上，1周内睡眠时长稳定在7小时以上。相应的，HRV应提升5-10ms，日间精力和工作效率显著改善。"
            }
        elif steps < 5000:
            return {
                'title': '【最高优先级】大幅提升日常活动量',
                'problem': f"今日仅走{steps:,}步，属于久坐生活方式（<5000步）。研究显示，每日步数<5000步的人群心血管疾病风险比8000步人群高40%，代谢综合征风险增加2倍。今日活动消耗仅{self.data['active_energy']['value']:.0f}千卡，远低于维持健康体重所需的每日400+千卡活动消耗。结合HRV {hrv:.1f}ms，{'虽然自主神经功能尚可，但久坐会逐步侵蚀心血管健康' if hrv > 50 else '缺乏活动可能是HRV偏低的原因之一'}。",
                'action': "1. 即刻行动：设置每小时站立提醒，工作日8小时至少起身活动8次，每次5分钟（累计40分钟）\n2. 通勤改造：如条件允许，提前一站下车步行（+2000步）；或停车在远处（+1000步）；楼层≤5层一律走楼梯（爬楼10层≈+100千卡消耗）\n3. 饭后步行：每餐后立即散步15-20分钟（+3000-4000步），促进血糖控制和消化\n4. 建立「步数目标阶梯」：本周目标6000步/天，下周7000步，第3周8000步，逐步达到10000步推荐标准\n5. 周末补偿：周六/日安排60分钟户外活动（徒步、骑行、游泳），单日目标15000步",
                'expectation': "2-3周后日均步数可稳定在8000步以上，心肺功能（静息心率预期下降3-5bpm）和代谢指标（空腹血糖、血脂）将开始改善。体重管理方面，从5000步提升至10000步每日可多消耗200-300千卡，理论上每月可减重0.5-1kg（配合饮食控制）。"
            }
        else:
            return {
                'title': '【优化级】建立规律运动习惯',
                'problem': f"今日步数{steps:,}步已达标，但缺乏结构化运动（有氧/力量训练）。日常步行虽好，但无法完全替代专门运动对心肺功能、肌肉力量和骨密度的提升作用。今日活动消耗{self.data['active_energy']['value']:.0f}千卡主要来自日常活动，{'缺乏高强度间歇对心肺的刺激' if self.data['active_energy']['value'] < 500 else '运动量尚可但缺乏系统性'}。HRV {hrv:.1f}ms显示身体状态良好，是开始规律训练的合适时机。",
                'action': "1. 制定每周运动计划：选择固定3天（如周二、四、六），每次30-45分钟，避免「想起来才动」的随意性\n2. 循序渐进：第1-2周快走或慢跑（心率120-140bpm），第3-4周加入间歇（1分钟快+2分钟慢交替），第5周起可尝试 HIIT 或力量训练\n3. 运动类型多样化：有氧（跑步、游泳、骑行）与力量（哑铃、自重训练）交替，每周2次有氧+1次力量\n4. 使用心率监测：运动时保持心率在最大心率的60-80%（约120-150bpm），这是燃脂和心肺提升的最佳区间\n5. 记录训练日志：每次记录运动类型、时长、平均心率、主观疲劳度（1-10分），追踪进步",
                'expectation': "4-6周后，最大摄氧量（VO2max）预期提升5-10%，静息心率下降5-8bpm，日常精力显著改善。12周后体成分改善：体脂率下降2-3%，肌肉量增加1-2kg，基础代谢率提升。长期规律运动可将心血管疾病风险降低30-40%，预期寿命延长3-5年。"
            }
    
    def _ensure_length(self, text: str, min_len: int, max_len: int) -> str:
        """确保文本长度在指定范围内"""
        text = text.strip()
        if len(text) < min_len:
            # 添加通用补充
            text += "建议持续监测该指标的变化趋势，结合其他健康数据综合评估身体状况。如有持续异常，建议咨询专业医疗人员。"
        if len(text) > max_len:
            text = text[:max_len-3] + "..."
        return text

# 使用示例函数
def generate_personalized_analysis(data: Dict, history: List[Dict] = None) -> Dict[str, str]:
    """生成个性化分析的主入口"""
    analyzer = PersonalizedAIAnalyzer(data, history)
    
    return {
        'hrv_analysis': analyzer.analyze_hrv(),
        'sleep_analysis': analyzer.analyze_sleep(),
        'workout_analysis': analyzer.analyze_workout(),
        'priority_recommendation': analyzer.generate_priority_recommendation()
    }
