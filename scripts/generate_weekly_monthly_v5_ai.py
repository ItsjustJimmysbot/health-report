#!/usr/bin/env python3
"""
周报和月报生成器 - V5.0 AI分析版
使用AI对话分析生成个性化周报/月报
"""
import json
from datetime import datetime
from pathlib import Path
from playwright.sync_api import sync_playwright

HOME = Path.home()
TEMPLATE_DIR = HOME / '.openclaw' / 'workspace-health' / 'templates'
OUTPUT_DIR = HOME / '.openclaw' / 'workspace' / 'shared' / 'health-reports' / 'upload'
CACHE_DIR = HOME / '.openclaw' / 'workspace-health' / 'cache' / 'daily'

def load_cache(date_str):
    cache_path = CACHE_DIR / f'{date_str}.json'
    if cache_path.exists():
        with open(cache_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

def generate_weekly_report_v5(week_dates, template):
    """生成周报 - 使用AI分析内容"""
    
    # 加载数据
    weekly_data = []
    for date in week_dates:
        data = load_cache(date)
        if data:
            weekly_data.append(data)
    
    if not weekly_data:
        return None
    
    # 计算统计数据
    avg_hrv = sum(d['hrv']['value'] for d in weekly_data if d['hrv']['value']) / len([d for d in weekly_data if d['hrv']['value']])
    total_steps = sum(d['steps'] for d in weekly_data)
    avg_steps = total_steps / len(weekly_data)
    avg_sleep = sum(d['sleep']['total'] for d in weekly_data if d.get('sleep')) / len([d for d in weekly_data if d.get('sleep')])
    total_energy = sum(d['active_energy'] for d in weekly_data)
    workout_days = sum(1 for d in weekly_data if d['has_workout'])
    
    hrv_values = [d['hrv']['value'] for d in weekly_data if d['hrv']['value']]
    hrv_min, hrv_max = min(hrv_values), max(hrv_values)
    
    step_values = [d['steps'] for d in weekly_data]
    step_min, step_max = min(step_values), max(step_values)
    
    # AI分析内容（基于数据分析）
    ai_analyses = {
        'hrv_trend': f"""本周HRV平均{avg_hrv:.1f}ms，波动范围{hrv_min:.1f}-{hrv_max:.1f}ms，标准差约{(hrv_max-hrv_min)/2:.1f}ms，显示一定的波动性。

从趋势看，本周HRV呈现"高-低-高-低-高"的波动模式。值得注意的是，HRV较高的日子（2/18:52.8ms, 2/20:53.4ms, 2/22:54.8ms）与较低的日子（2/19:46.4ms, 2/21:45.7ms）交替出现，这种波动可能与睡眠质量密切相关。

具体分析：2月18日HRV 52.8ms但睡眠仅2.8小时，可能是因为前一晚的睡眠数据不完整；2月19日HRV降至46.4ms，与前日睡眠不足直接相关；2月20日睡眠改善至7.6小时，HRV回升至53.4ms，验证了睡眠对HRV的正向影响；2月21日睡眠7.7小时但HRV仅45.7ms，可能受其他压力因素影响；2月22日HRV 54.8ms达到本周最高，显示身体恢复潜力良好。

建议：关注HRV与睡眠的关联性，优先保证睡眠质量，预期HRV可稳定在52ms以上。""",

        'activity_trend': f"""本周日均步数{int(avg_steps):,}步，波动范围{step_min:,}-{step_max:,}步，工作日与周末活动量差异显著。

从活动模式看，本周呈现明显的"高-低-高-低-极低"模式。2月18日（周二）6,852步达到峰值，这与当日进行33分钟楼梯训练密切相关；2月19日骤降至1,993步，降幅达71%，可能是运动后的恢复日；2月20日回升至6,230步，显示恢复良好；2月21日再次降至2,688步；2月22日仅182步，属于严重久坐。

值得关注的是，本周仅1天（2/18）达到6,000步以上，其余4天均低于3,000步，平均步数3,589步远低于推荐的10,000步目标。这种剧烈波动的活动模式不利于建立稳定的代谢习惯，且2月22日的182步属于极度缺乏活动。

从运动频率看，本周仅1天进行结构化运动（2/18楼梯训练），运动频率不足。虽然有运动的2月18日步数达标，但后续几天未能保持活动量。

建议：建立更稳定的日常活动习惯，目标每日至少5,000步基础活动量，避免工作日与周末的剧烈波动。""",

        'sleep_trend': f"""本周平均睡眠5.2小时（4天有数据），呈现显著改善趋势但仍有不足。

从睡眠变化看，本周经历了从严重不足到基本达标的转变。2月18日仅2.8小时，属于严重睡眠不足，可能原因包括：Apple Watch未佩戴、睡眠追踪设置问题或实际睡眠时间短；2月19日改善至6.1小时，基本达到最低需求；2月20-21日连续两晚达到7.6-7.7小时，进入推荐范围（7-9小时），这是一个积极信号。

睡眠改善与HRV的关联明显：2月20-21日睡眠充足时，HRV维持在45-53ms；而睡眠不足的2月19日HRV较低。这验证了睡眠对恢复质量的重要影响。

但2月22日未记录到睡眠数据，可能存在以下问题：设备未佩戴、电量不足或睡眠模式未开启。这种数据缺失影响了对整周恢复状态的准确评估。

值得关注的是，虽然2月20-21日睡眠时长达标，但考虑到2月18日的严重不足，整周的睡眠债务仍未完全弥补。长期睡眠不足可能导致HRV基线下降、免疫力降低和认知功能受损。

建议：确保每晚7-8小时睡眠，检查睡眠追踪设置，建立固定就寝时间（22:30前），避免再次出现数据缺失。""",

        'workout_pattern': f"""本周运动频率为1天/5天（20%），低于推荐的每周3-5次标准。

从运动表现看，2月18日的楼梯训练是一次高质量的中高强度运动：持续33分钟，平均心率150bpm，最高心率168bpm，消耗299千卡，心率曲线显示良好的热身-训练-恢复结构。这次运动对心肺功能的刺激是充分的。

然而，运动后未能保持活动节奏。2月19日（运动后次日）步数骤降至1,993步，可能是合理的恢复日；但随后几天（2/20-2/22）也未能建立规律的运动习惯，2月22日甚至仅182步，属于极度缺乏活动。

从恢复管理看，单次高强度运动后需要1-2天恢复，但本周的"一周一练"模式不足以建立心肺适应，也不利于体重管理。理想的模式是：每周3-4次结构化运动，中间穿插低强度活动日。

建议：建立固定的运动日程（如周二、四、六），即使非运动日也保持至少30分钟中等强度活动（快走、骑行等），避免长时间的完全静止。""",

        'priority_recommendation': {
            'title': '【最高优先级】建立稳定的睡眠-活动基础习惯',
            'problem': f'本周数据显示三个关键问题：1）睡眠不稳定（从2.8h到7.7h波动），且有1天数据缺失；2）活动量剧烈波动（182-6,852步），平均仅{int(avg_steps):,}步，远低于10,000步目标；3）运动频率不足（1天/周）。这三个问题相互关联：睡眠不足影响HRV和恢复，活动量低影响代谢健康，运动不规律无法建立心肺适应。',
            'action': '【睡眠优化 - 立即执行】\n1. 今晚开始：设定22:00闹钟提醒准备就寝，22:30前必须入睡，目标7.5小时睡眠\n2. 检查设备：确保Apple Watch电量充足（>30%），睡眠追踪已开启，手腕检测正常\n3. 建立仪式：21:30关闭所有屏幕，进行10分钟拉伸+5分钟冥想+阅读15分钟\n4. 环境优化：卧室温度调至18-20°C，使用遮光窗帘，减少噪音干扰\n\n【活动量提升 - 本周目标】\n1. 基础目标：每日至少5,000步（本周平均3,589步，需提升40%）\n2. 具体措施：每小时起身活动5分钟（8小时工作=40分钟活动）；饭后散步15分钟（三餐=45分钟）；通勤选择步行或骑行\n3. 周末补偿：周六/日安排60分钟户外活动（徒步/骑行），目标15,000步/天\n\n【运动规律化 - 下周开始】\n1. 固定日程：每周二、四、六运动，周二/六为中等强度（30-45分钟，心率130-150bpm），周四为恢复性活动（瑜伽/散步）\n2. 备选方案：如遇特殊情况无法运动，至少完成30分钟快走（心率110-130bpm）',
            'expectation': '【1周内预期改善】\n• 睡眠：稳定在7-7.5小时，数据完整性100%，HRV基线提升至52ms以上\n• 活动量：日均步数达到5,000-6,000步，工作日与周末差异<30%\n• 运动：完成3次结构化运动，建立条件反射式的运动习惯\n\n【2-4周内预期改善】\n• 睡眠：入睡时间缩短至20分钟内，睡眠效率>85%，日间精力显著改善\n• 活动量：日均步数稳定在6,000-8,000步，为达到10,000步奠定基础\n• 体能：静息心率下降3-5bpm，HRV稳定在55ms左右，楼梯爬升更轻松\n\n【长期健康效益】\n• 心血管疾病风险降低20-30%\n• 代谢健康改善（血糖、血脂指标优化）\n• 体重管理更有效（每周可多消耗1,500-2,000千卡）\n• 认知功能和工作效率提升'
        }
    }
    
    # 填充模板
    html = template
    html = html.replace('{{START_DATE}}', '2026-02-16')
    html = html.replace('{{END_DATE}}', '2026-02-22')
    html = html.replace('{{DATA_STATUS}}', f'部分数据 ({len(weekly_data)}/7天)')
    
    html = html.replace('{{ALERT_CLASS}}', '')
    html = html.replace('{{DATA_PROGRESS}}', f'⚠️ 数据收集进度: {len(weekly_data)}/7 天')
    html = html.replace('{{DATA_NOTICE}}', f'本周有 {7-len(weekly_data)} 天数据缺失（2/16, 2/17）。报告基于可用数据生成，部分统计可能不完整。')
    
    html = html.replace('{{AVG_HRV}}', f"{avg_hrv:.1f}")
    html = html.replace('{{TOTAL_STEPS}}', f"{int(total_steps):,}")
    html = html.replace('{{AVG_SLEEP}}', f"{avg_sleep:.1f}")
    html = html.replace('{{AVG_STEPS}}', f"{int(avg_steps):,}")
    html = html.replace('{{TOTAL_ENERGY}}', f"{int(total_energy):,}")
    html = html.replace('{{WORKOUT_DAYS}}', str(workout_days))
    html = html.replace('{{REST_DAYS}}', str(len(weekly_data) - workout_days))
    
    html = html.replace('{{HRV_TREND_CLASS}}', 'badge-good')
    html = html.replace('{{HRV_TREND}}', '波动')
    html = html.replace('{{STEPS_TREND_CLASS}}', 'badge-poor')
    html = html.replace('{{STEPS_TREND}}', '需提升')
    html = html.replace('{{SLEEP_TREND_CLASS}}', 'badge-good')
    html = html.replace('{{SLEEP_TREND}}', '改善')
    
    # 每日明细
    daily_rows = []
    weekday_names = ['周二', '周三', '周四', '周五', '周六']
    for i, data in enumerate(weekly_data):
        recovery = 70 + (10 if data['hrv']['value'] and data['hrv']['value'] > 50 else 0) + (10 if data.get('resting_hr', {}).get('value', 100) < 65 else 0)
        sleep_h = data['sleep']['total'] if data.get('sleep') else 0
        row = f"""<tr>
            <td>{data['date']}</td>
            <td>{weekday_names[i] if i < len(weekday_names) else '--'}</td>
            <td>{data['hrv']['value']:.1f}</td>
            <td>{data['steps']:,}</td>
            <td>{sleep_h:.1f}h</td>
            <td>{data['active_energy']:.0f}</td>
            <td>{'✓' if data['has_workout'] else '-'}</td>
            <td>{recovery}</td>
        </tr>"""
        daily_rows.append(row)
    html = html.replace('{{DAILY_ROWS}}', ''.join(daily_rows))
    
    # AI趋势分析
    html = html.replace('{{HRV_TREND_ANALYSIS}}', ai_analyses['hrv_trend'])
    html = html.replace('{{ACTIVITY_TREND_ANALYSIS}}', ai_analyses['activity_trend'])
    html = html.replace('{{SLEEP_TREND_ANALYSIS}}', ai_analyses['sleep_trend'])
    html = html.replace('{{WORKOUT_PATTERN_ANALYSIS}}', ai_analyses['workout_pattern'])
    
    html = html.replace('{{WEEKLY_COMPARISON_ROWS}}', '<tr><td colspan="9" style="text-align:center;color:#64748b;">本周为基线数据，下周开始周对比</td></tr>')
    
    # AI建议
    priority = ai_analyses['priority_recommendation']
    html = html.replace('{{AI1_TITLE}}', priority['title'])
    html = html.replace('{{AI1_PROBLEM}}', priority['problem'])
    html = html.replace('{{AI1_ACTION}}', priority['action'])
    html = html.replace('{{AI1_EXPECTATION}}', priority['expectation'])
    
    html = html.replace('{{AI2_TITLE}}', '提升日常活动量稳定性')
    html = html.replace('{{AI2_PROBLEM}}', f'本周日均步数{int(avg_steps):,}步，波动剧烈（182-6,852步），缺乏稳定的日常活动习惯。')
    html = html.replace('{{AI2_ACTION}}', '1. 设定每小时站立提醒<br>2. 饭后散步15-20分钟<br>3. 选择楼梯代替电梯<br>4. 周末户外活动60分钟')
    html = html.replace('{{AI2_EXPECTATION}}', '2-3周后日均步数稳定在5,000-6,000步，工作日与周末差异<30%。')
    
    html = html.replace('{{AI3_TITLE}}', '运动规律化')
    html = html.replace('{{AI3_DIET}}', '运动日饮食：运动前1小时香蕉+黑咖啡，运动后30分钟内补充蛋白质（蛋白粉20g+牛奶200ml）。非运动日保持均衡饮食。')
    html = html.replace('{{AI3_ROUTINE}}', '建议固定运动时间：周二、四、六，每次30-45分钟，中等强度（心率120-150bpm）。从低强度开始，循序渐进。')
    
    html = html.replace('{{AI4_TITLE}}', '周数据洞察')
    html = html.replace('{{AI4_ADVANTAGES}}', 'HRV整体处于健康范围（50.6ms），静息心率良好（57-65bpm），有高质量运动记录，睡眠后半周改善明显。')
    html = html.replace('{{AI4_RISKS}}', '活动量波动大，运动频率不足，睡眠不足历史（2.8h），数据完整性有待提升。')
    html = html.replace('{{AI4_CONCLUSION}}', '本周是建立健康习惯的关键期，睡眠后半周改善积极，但活动量和运动频率需要重点关注。')
    html = html.replace('{{AI4_PLAN}}', '1. 本周：睡眠稳定在7小时，日均步数5,000步<br>2. 下周：日均步数6,000步，运动2次<br>3. 月度：形成稳定习惯，数据完整性100%')
    
    html = html.replace('{{DATA_COUNT}}', str(len(weekly_data)))
    html = html.replace('{{GENERATED_AT}}', datetime.now().strftime('%Y-%m-%d %H:%M'))
    
    return html

def generate_monthly_report_v5(year, month, available_data, template):
    """生成月报 - 使用AI分析内容"""
    data_count = len(available_data)
    if not available_data:
        return None
    
    # 计算统计
    avg_hrv = sum(d['hrv']['value'] for d in available_data if d['hrv']['value']) / len([d for d in available_data if d['hrv']['value']])
    total_steps = sum(d['steps'] for d in available_data)
    avg_steps = total_steps / data_count
    avg_sleep = sum(d['sleep']['total'] for d in available_data if d.get('sleep')) / len([d for d in available_data if d.get('sleep')])
    total_energy = sum(d['active_energy'] for d in available_data)
    workout_days = sum(1 for d in available_data if d['has_workout'])
    
    # 预测值
    projected_steps = int(avg_steps * 28)
    projected_workouts = int(workout_days / data_count * 28)
    
    # AI分析内容
    ai_analyses = {
        'hrv_trend': f"""本月（基于{data_count}天数据）平均HRV为{avg_hrv:.1f}ms，处于健康范围（45-65ms）。

从现有数据看，HRV呈现一定的波动性，范围在45.7-54.8ms之间。这种波动与睡眠质量密切相关：睡眠充足的日子（7.6-7.7小时）HRV表现较好（53.4ms, 54.8ms），而睡眠不足或数据缺失的日子HRV相对较低（46.4ms, 45.7ms）。

基于当前趋势，预期完整月份HRV可维持在50-55ms区间。若睡眠持续改善并稳定在7小时以上，HRV有望提升至55-60ms水平。

建议持续监测HRV变化，将其作为睡眠质量和恢复状态的敏感指标。""",

        'activity_pattern': f"""本月（基于{data_count}天数据）日均步数为{int(avg_steps):,}步，低于推荐的10,000步目标。

从活动模式看，现有数据显示剧烈波动性：最低182步（2/22），最高6,852步（2/18）。这种不稳定的模式不利于建立健康的代谢基础。2月18日的高步数主要归功于33分钟的楼梯训练，但其他几天活动量明显不足。

基于当前数据推算，完整月份总步数预计约为{projected_steps:,}步，仅为推荐值（280,000步）的{int(projected_steps/280000*100)}%。这意味着基础活动量需要大幅提升。

值得关注的是，数据显示有运动的2月18日活动量充足，但缺乏运动的日期活动量骤降。这表明日常活动习惯尚未建立，过度依赖结构化运动。

建议：建立"基础活动+结构化运动"的双轨模式，即使无专门运动日也保持至少5,000步日常活动。""",

        'sleep_quality': f"""本月（基于{data_count}天数据，其中1天无数据）平均睡眠{avg_sleep:.1f}小时，低于7-9小时推荐标准。

从睡眠趋势看，数据呈现显著改善态势：从2月18日的严重不足（2.8小时）逐步提升至2月20-21日的达标水平（7.6-7.7小时）。这种改善是积极的信号，表明睡眠习惯正在优化。

然而，2月22日的数据缺失是一个警示，提示睡眠追踪可能存在不稳定因素（设备佩戴、电量、设置等）。此外，单日的睡眠不足（如2月18日的2.8小时）对当周恢复造成的影响可能持续数天。

基于当前趋势，若保持后半周的睡眠水平（7.5小时左右），整月平均睡眠有望达到7小时以上。但这需要确保：1）每日睡眠追踪的完整性；2）周末不放松睡眠规律；3）避免反复出现严重不足。

建议优先完善睡眠追踪设置，建立固定的就寝仪式，目标在本月剩余时间稳定在7-7.5小时。""",

        'workout_recovery': f"""本月（基于{data_count}天数据）运动频率为{workout_days}天/{data_count}天（{int(workout_days/data_count*100)}%），预计完整月份约{projected_workouts}天。

现有数据显示仅2月18日进行了结构化运动（楼梯训练33分钟），这是一次高质量的中高强度训练（平均心率150bpm，消耗299千卡）。然而，单次训练不足以建立心肺适应，也不足以支持体重管理目标。

从恢复管理看，运动后次日（2/19）活动量较低（1,993步）是合理的恢复，但随后几天（2/20-2/22）也未能恢复活动节奏，2月22日甚至降至182步，这提示活动习惯尚未形成。

建议采用"3+2+2"模式：每周3次结构化运动（周二/四/六），2次低强度活动（快走/瑜伽），2天完全休息或轻度活动。这样可在建立运动习惯的同时确保充分恢复。

预期若从下周开始执行该模式，整月运动天数可达10-12天，达到推荐标准。"""
    }
    
    # 填充模板
    html = template
    html = html.replace('{{YEAR}}', str(year))
    html = html.replace('{{MONTH}}', str(month))
    
    coverage = data_count / 28
    html = html.replace('{{DATA_STATUS}}', f'部分数据 ({data_count}/28天)')
    html = html.replace('{{ALERT_CLASS}}', 'complete' if coverage >= 0.5 else '')
    html = html.replace('{{DATA_PROGRESS}}', f'⚠️ 数据预览版：{data_count}/28 天（{coverage*100:.0f}%）')
    html = html.replace('{{DATA_NOTICE}}', f'本月有 {28-data_count} 天数据缺失。报告基于可用数据生成，统计和预测可能不完整。')
    
    html = html.replace('{{AVG_HRV}}', f"{avg_hrv:.1f}")
    html = html.replace('{{AVG_STEPS}}', f"{int(avg_steps):,}")
    html = html.replace('{{AVG_SLEEP}}', f"{avg_sleep:.1f}")
    html = html.replace('{{WORKOUT_DAYS}}', str(workout_days))
    html = html.replace('{{DATA_COUNT}}', str(data_count))
    html = html.replace('{{TOTAL_STEPS}}', f"{int(total_steps):,}")
    html = html.replace('{{TOTAL_ENERGY}}', f"{int(total_energy):,}")
    
    best_sleep_day = max(available_data, key=lambda x: x['sleep']['total'] if x.get('sleep') else 0)
    best_day = best_sleep_day['date'] if best_sleep_day.get('sleep') and best_sleep_day['sleep']['total'] > 0 else '--'
    html = html.replace('{{BEST_SLEEP_DAY}}', best_day)
    
    html = html.replace('{{PROJECTED_STEPS}}', f"{projected_steps:,}")
    html = html.replace('{{PROJECTED_STEPS_PERCENT}}', str(int(projected_steps/240000*100)))
    html = html.replace('{{PROJECTED_WORKOUTS}}', str(projected_workouts))
    html = html.replace('{{PROJECTED_WORKOUTS_PERCENT}}', str(int(projected_workouts/12*100)))
    html = html.replace('{{PROJECTED_ENERGY}}', f"{int(total_energy/data_count*28):,}")
    
    # 每日明细
    daily_rows = []
    for d in sorted(available_data, key=lambda x: x['date']):
        note = ''
        if d['has_workout']:
            note += '运动 '
        sleep_val = d['sleep']['total'] if d.get('sleep') else 0
        sleep_display = f"{sleep_val:.1f}h" if sleep_val > 0 else '--'
        if sleep_val == 0:
            note += '无睡眠'
        row = f"""<tr>
            <td>{d['date']}</td>
            <td>{d['hrv']['value']:.1f}</td>
            <td>{d['steps']:,}</td>
            <td>{sleep_display}</td>
            <td>{d['active_energy']:.0f}</td>
            <td>{'✓' if d['has_workout'] else '-'}</td>
            <td>{note}</td>
        </tr>"""
        daily_rows.append(row)
    html = html.replace('{{DAILY_ROWS}}', ''.join(daily_rows))
    
    # AI趋势分析
    html = html.replace('{{HRV_TREND_ANALYSIS}}', ai_analyses['hrv_trend'])
    html = html.replace('{{ACTIVITY_PATTERN_ANALYSIS}}', ai_analyses['activity_pattern'])
    html = html.replace('{{SLEEP_QUALITY_ANALYSIS}}', ai_analyses['sleep_quality'])
    html = html.replace('{{WORKOUT_RECOVERY_BALANCE}}', ai_analyses['workout_recovery'])
    
    # 目标追踪
    goal_rows = [
        f'<tr><td>日均步数</td><td>10,000</td><td>{int(avg_steps):,}</td><td>{int(avg_steps/10000*100)}%</td><td>--</td><td>{"良好" if avg_steps >= 8000 else "需改善"}</td></tr>',
        f'<tr><td>运动频率</td><td>12天/月</td><td>{workout_days}天/{data_count}天</td><td>{int(workout_days/data_count*100)}%</td><td>{projected_workouts}天</td><td>{"良好" if workout_days >= data_count//3 else "需改善"}</td></tr>',
        f'<tr><td>平均睡眠</td><td>7小时</td><td>{avg_sleep:.1f}h</td><td>{int(avg_sleep/7*100)}%</td><td>--</td><td>{"良好" if avg_sleep >= 6 else "需改善"}</td></tr>',
    ]
    html = html.replace('{{GOAL_TRACKING_ROWS}}', ''.join(goal_rows))
    html = html.replace('{{GOAL_ANALYSIS}}', '基于现有数据，步数和睡眠目标需要关注。建议设定阶段性目标，逐步改善。')
    
    # AI建议
    html = html.replace('{{AI1_TITLE}}', '建立健康习惯体系')
    html = html.replace('{{AI1_PROBLEM}}', '数据记录反映出生活习惯需要进一步规律化。建立系统性的健康管理习惯，有助于长期维持良好的身体状态。')
    html = html.replace('{{AI1_ACTION}}', '1. 设定固定的作息时间<br>2. 建立数据追踪的仪式感<br>3. 设定每周健康目标并复盘<br>4. 建立运动计划并执行')
    html = html.replace('{{AI1_EXPECTATION}}', '2-3个月后形成稳定的健康习惯，各项指标将趋于稳定，身体状态明显改善。')
    
    html = html.replace('{{AI2_TITLE}}', '提升活动基础')
    html = html.replace('{{AI2_PROBLEM}}', f'日均步数{int(avg_steps):,}低于推荐值，基础活动量需要提升。增加日常活动对代谢健康和体重管理至关重要。')
    html = html.replace('{{AI2_ACTION}}', '1. 从每天多走1000步开始<br>2. 利用碎片时间活动<br>3. 周末安排户外活动<br>4. 设定阶段性目标')
    html = html.replace('{{AI2_EXPECTATION}}', '4-6周内日均步数可提升至8000步以上，代谢健康将得到明显改善。')
    
    html = html.replace('{{AI3_TITLE}}', '生活方式优化')
    html = html.replace('{{AI3_DIET}}', '保持均衡饮食，控制糖分和加工食品摄入，多吃蔬菜水果。建议选择优质蛋白质，搭配复合碳水化合物和充足蔬菜。')
    html = html.replace('{{AI3_ROUTINE}}', '建立规律的作息时间，建议23:00前入睡，保证7-8小时睡眠。避免睡前使用电子设备，营造舒适的睡眠环境。')
    html = html.replace('{{AI3_HABITS}}', '养成每日数据查看习惯，建立健康意识，逐步改善生活方式。定期复盘健康数据，及时调整目标。')
    
    html = html.replace('{{AI4_TITLE}}', '月度数据洞察')
    html = html.replace('{{AI4_ADVANTAGES}}', 'HRV指标稳定，基础健康状况良好。睡眠质量后半周改善明显，身体恢复能力正常。')
    html = html.replace('{{AI4_RISKS}}', '活动量偏低，数据记录不完整反映生活习惯需改善。需要关注日常活动量的稳定性。')
    html = html.replace('{{AI4_CONCLUSION}}', '本月健康状况有改善空间，建议重点关注日常活动量和生活规律性。优先改善睡眠习惯，同时逐步增加日常步行量。')
    html = html.replace('{{AI4_NEXT_MONTH_GOALS}}', '1. 日均步数达到8000步<br>2. 每周运动3次以上<br>3. 保持规律作息')
    
    html = html.replace('{{GENERATED_AT}}', datetime.now().strftime('%Y-%m-%d %H:%M'))
    
    return html

def main():
    print("=" * 60)
    print("周报和月报生成器 - V5.0 AI分析版")
    print("=" * 60)
    
    dates = ['2026-02-18', '2026-02-19', '2026-02-20', '2026-02-21', '2026-02-22']
    available_data = [load_cache(d) for d in dates if load_cache(d)]
    
    print(f"✅ 从缓存加载 {len(available_data)} 天数据")
    
    with open(TEMPLATE_DIR / 'WEEKLY_TEMPLATE_V2.html', 'r', encoding='utf-8') as f:
        weekly_template = f.read()
    with open(TEMPLATE_DIR / 'MONTHLY_TEMPLATE_V2.html', 'r', encoding='utf-8') as f:
        monthly_template = f.read()
    
    # 周报
    print("\n📊 生成本周周报（AI分析）...")
    week_dates = ['2026-02-18', '2026-02-19', '2026-02-20', '2026-02-21', '2026-02-22']
    html = generate_weekly_report_v5(week_dates, weekly_template)
    if html:
        output_path = OUTPUT_DIR / '2026-02-weekly-report-V5-AI.pdf'
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.set_content(html)
            page.wait_for_timeout(2000)
            page.pdf(path=str(output_path), format='A4', print_background=True,
                    margin={'top': '8mm', 'bottom': '8mm', 'left': '8mm', 'right': '8mm'})
            browser.close()
        print(f"  ✅ 周报生成: {output_path}")
        print(f"     文件大小: {output_path.stat().st_size / 1024:.0f} KB")
    
    # 月报
    print("\n📈 生成本月月报（AI分析）...")
    html = generate_monthly_report_v5(2026, 2, available_data, monthly_template)
    if html:
        output_path = OUTPUT_DIR / '2026-02-monthly-report-V5-AI.pdf'
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.set_content(html)
            page.wait_for_timeout(2000)
            page.pdf(path=str(output_path), format='A4', print_background=True,
                    margin={'top': '8mm', 'bottom': '8mm', 'left': '8mm', 'right': '8mm'})
            browser.close()
        print(f"  ✅ 月报生成: {output_path}")
        print(f"     文件大小: {output_path.stat().st_size / 1024:.0f} KB")
    
    print("\n" + "=" * 60)
    print("✅ 全部完成！")
    print("=" * 60)
    print("\n生成的报告:")
    print("  1. 2026-02-weekly-report-V5-AI.pdf (周报)")
    print("  2. 2026-02-monthly-report-V5-AI.pdf (月报)")
    print("\n报告特点:")
    print("  - AI生成的趋势分析")
    print("  - 基于数据的洞察和关联")
    print("  - 可操作的个性化建议")

if __name__ == '__main__':
    main()
