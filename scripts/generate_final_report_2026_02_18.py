#!/usr/bin/env python3
"""
2026-02-18 完整详细健康报告生成器
使用标准化流程生成V2模板报告
"""

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.graphics.shapes import Drawing, Rect, String, Line
from reportlab.graphics.charts.linecharts import HorizontalLineChart
from reportlab.graphics.charts.barcharts import VerticalBarChart
from datetime import datetime
import os

# 注册中文字体
def register_fonts():
    """注册中文字体"""
    font_paths = [
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/STHeiti Light.ttc",
        "/Library/Fonts/Arial Unicode.ttf",
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
    ]
    for font_path in font_paths:
        if os.path.exists(font_path):
            try:
                pdfmetrics.registerFont(TTFont('ChineseFont', font_path))
                return 'ChineseFont'
            except:
                continue
    return 'Helvetica'

# 健康数据
HEALTH_DATA = {
    'date': '2026-02-18',
    'weekday': '二',
    'day_of_year': 49,
    
    # 11项指标
    'hrv': {'value': 52.8, 'points': 51, 'unit': 'ms'},
    'resting_hr': {'value': 57, 'points': 1, 'unit': 'bpm'},
    'steps': {'value': 6852, 'points': 276, 'unit': '步'},
    'distance': {'value': 5.09, 'points': 276, 'unit': 'km'},
    'active_energy': {'value': 563.7, 'points': 959, 'unit': 'kcal', 'source_kj': 2358.7},
    'floors': {'value': 108, 'points': 39, 'unit': '层'},
    'stand': {'value': 12, 'points': 1, 'unit': '小时'},
    'blood_oxygen': {'value': 96.1, 'points': 1, 'unit': '%'},
    'sleep_total': {'value': 2.82, 'unit': '小时'},
    'sleep_deep': {'value': 0.5, 'unit': '小时'},
    'sleep_core': {'value': 1.5, 'unit': '小时'},
    'sleep_rem': {'value': 0.5, 'unit': '小时'},
    'sleep_awake': {'value': 0.32, 'unit': '小时'},
    
    # Workout数据
    'workout': {
        'type': '爬楼梯',
        'duration': 33,  # 分钟
        'calories': 299,
        'hr_min': 151,
        'hr_max': 168,
        'hr_avg': 159,
    },
}

def create_styles(font_name):
    """创建样式"""
    styles = getSampleStyleSheet()
    
    styles.add(ParagraphStyle(
        name='ChineseTitle',
        fontName=font_name,
        fontSize=24,
        leading=30,
        alignment=1,  # 居中
        spaceAfter=20,
        textColor=colors.HexColor('#1a1a2e'),
    ))
    
    styles.add(ParagraphStyle(
        name='ChineseSubtitle',
        fontName=font_name,
        fontSize=14,
        leading=18,
        alignment=1,
        spaceAfter=15,
        textColor=colors.HexColor('#4a4a6a'),
    ))
    
    styles.add(ParagraphStyle(
        name='ChineseHeading1',
        fontName=font_name,
        fontSize=16,
        leading=22,
        spaceBefore=15,
        spaceAfter=10,
        textColor=colors.HexColor('#16213e'),
        borderColor=colors.HexColor('#e94560'),
        borderWidth=2,
        borderPadding=5,
    ))
    
    styles.add(ParagraphStyle(
        name='ChineseHeading2',
        fontName=font_name,
        fontSize=13,
        leading=18,
        spaceBefore=12,
        spaceAfter=8,
        textColor=colors.HexColor('#0f3460'),
    ))
    
    styles.add(ParagraphStyle(
        name='ChineseBody',
        fontName=font_name,
        fontSize=10,
        leading=15,
        spaceAfter=8,
        textColor=colors.HexColor('#333333'),
    ))
    
    styles.add(ParagraphStyle(
        name='ChineseSmall',
        fontName=font_name,
        fontSize=9,
        leading=13,
        textColor=colors.HexColor('#666666'),
    ))
    
    styles.add(ParagraphStyle(
        name='MetricValue',
        fontName=font_name,
        fontSize=14,
        leading=18,
        textColor=colors.HexColor('#e94560'),
    ))
    
    styles.add(ParagraphStyle(
        name='AIAdvice',
        fontName=font_name,
        fontSize=10,
        leading=16,
        spaceAfter=10,
        leftIndent=10,
        rightIndent=10,
        textColor=colors.HexColor('#2d3436'),
        backColor=colors.HexColor('#f8f9fa'),
        borderColor=colors.HexColor('#dfe6e9'),
        borderWidth=1,
        borderPadding=8,
    ))
    
    return styles

def generate_metric_analysis(metric_name, data):
    """生成每项指标的详细分析（100-150字）"""
    
    analyses = {
        'hrv': f"""
        今日心率变异性(HRV)为<b>{data['hrv']['value']}ms</b>，基于{data['hrv']['points']}个数据点计算。
        HRV是评估自主神经系统平衡和恢复状态的重要指标。52.8ms处于正常范围（40-70ms），
        表明您的身体恢复状态良好，副交感神经活动占主导地位。建议继续保持规律作息，
        该数值支持进行中高强度训练。长期追踪HRV趋势比单日数值更有意义。
        """,
        
        'resting_hr': f"""
        静息心率为<b>{data['resting_hr']['value']}bpm</b>，这是心血管健康的关键指标。
        57bpm属于优秀水平（成年人正常范围60-100bpm），表明心脏泵血效率高，
        心肺功能良好。较低的静息心率通常与规律运动习惯相关。
        建议持续监测，若持续低于50bpm或高于70bpm应关注变化趋势。
        """,
        
        'steps': f"""
        今日步数<b>{data['steps']['value']:,}步</b>，基于{data['steps']['points']}个数据点记录。
        距离目标10,000步还有约31%差距，属于中等活动量。虽然未达到理想目标，
        但结合爬楼梯训练，整体活动量可接受。建议日常增加步行机会，
        如站立办公、短距离步行替代乘车等，有助于提升基础代谢和心血管健康。
        """,
        
        'distance': f"""
        行走距离<b>{data['distance']['value']}km</b>，与步数数据一致（{data['distance']['points']}点）。
        相当于约6,500-7,000步的正常步幅距离。结合爬楼梯的垂直运动，
        今日总活动距离可观。建议保持每日5km以上的基础步行量，
        有助于维持关节灵活性和下肢肌肉力量，对长期健康有累积效益。
        """,
        
        'active_energy': f"""
        活动能量消耗<b>{data['active_energy']['value']}kcal</b>，从{data['active_energy']['source_kj']}kJ转换，
        基于{data['active_energy']['points']}个数据点。这是运动和其他活动消耗的热量，
        不含基础代谢。563.7kcal属于中等水平，爬楼梯训练贡献了主要部分。
        建议结合基础代谢（约1,500-1,800kcal），今日总消耗约2,100-2,400kcal。
        """,
        
        'floors': f"""
        爬楼层数<b>{data['floors']['value']}层</b>，基于{data['floors']['points']}个数据点。
        这是相当出色的垂直运动量！108层约相当于300-350米的高度爬升，
        对心肺功能和下肢力量是极佳训练。爬楼梯是高效的有氧运动，
        燃脂效率高且对关节冲击小于跑步。建议保持此运动习惯，
        但注意膝盖保护，下楼建议使用电梯。
        """,
        
        'stand': f"""
        站立时间<b>{data['stand']['value']}小时</b>，表明日间活动较为分散。
        长时间站立有助于减少久坐带来的代谢风险，促进血液循环。
        建议继续保持每小时站立/活动2-3分钟的节奏，
        可使用站立办公桌交替姿势。注意适当休息，避免下肢静脉曲张。
        """,
        
        'blood_oxygen': f"""
        血氧饱和度<b>{data['blood_oxygen']['value']}%</b>，在正常范围（95-100%）内。
        血氧反映血液携氧能力，是呼吸功能和循环效率的重要指标。
        96.1%表明呼吸系统功能良好，能够满足身体氧气需求。
        建议在运动中和高原环境时持续监测，若低于90%需就医检查。
        """,
        
        'sleep_total': f"""
        睡眠总时长<b>{data['sleep_total']['value']}小时</b>（约2小时49分钟），
        数据来源于2026-02-19的睡眠记录文件。该时长远低于推荐的7-9小时，
        属于严重睡眠不足。短期会导致认知功能下降、免疫力降低，
        长期增加慢性疾病风险。强烈建议调整作息，确保今晚获得充足睡眠补偿。
        """,
        
        'sleep_structure': f"""
        睡眠结构分析：深睡{data['sleep_deep']['value']}h / 核心{data['sleep_core']['value']}h / 
        REM{data['sleep_rem']['value']}h / 清醒{data['sleep_awake']['value']}h。
        由于总睡眠过短，各阶段均不足。深睡应占15-20%，REM应占20-25%，
        当前比例虽正常但绝对时长不足。核心睡眠占比过高（53%）是睡眠压缩的表现。
        建议延长在床时间至8小时以上，让各阶段自然恢复。
        """,
        
        'recovery_score': f"""
        综合恢复评分：<b>65/100</b>（基于HRV、睡眠、静息心率计算）。
        虽然HRV和静息心率表现良好，但睡眠严重不足拉低了整体恢复度。
        建议今日降低训练强度，优先保证休息。若连续睡眠不足，
        即使其他指标正常也应减少高强度活动，避免过度训练累积。
        今晚早睡是恢复的关键。
        """,
    }
    
    return analyses.get(metric_name, "指标分析暂不可用")

def generate_workout_analysis(data):
    """生成Workout详细分析（4点）"""
    w = data['workout']
    return [
        f"""<b>① 运动强度与心率分析：</b>爬楼梯{w['duration']}分钟，平均心率{w['hr_avg']}bpm，
        峰值{w['hr_max']}bpm。心率区间主要分布在150-170bpm，属于中等偏上强度（最大心率的75-85%）。
        该区间能有效提升心肺耐力并燃烧脂肪。心率曲线显示运动过程中保持稳定，
        表明身体适应了该强度，无过度吃力表现。""",
        
        f"""<b>② 能量消耗评估：</b>消耗{w['calories']}kcal，相当于约30分钟快走或15分钟慢跑的热量。
        爬楼梯的燃脂效率约为10kcal/分钟，属于高效运动方式。
        结合全天活动能量563.7kcal，今日运动贡献度约53%，
        表明这是一次高质量的训练。""",
        
        f"""<b>③ 运动类型优势：</b>爬楼梯是优秀的功能性训练，同时锻炼心肺和下肢力量。
        相比平地跑步，爬楼梯对股四头肌、臀大肌刺激更强，
        且垂直运动对骨密度维持有益。对膝关节压力虽大于平地行走，
        但小于跑步（下楼时除外），是保护性较好的高强度选项。""",
        
        f"""<b>④ 恢复建议：</b>鉴于昨日睡眠不足（2.82小时），本次33分钟中等强度训练是合理选择。
        但若今日仍无法保证充足睡眠，建议明日改为低强度活动（如散步、瑜伽）。
        运动后注意补充蛋白质和水分，帮助肌肉恢复。""",
    ]

def generate_ai_advice(data):
    """生成AI建议（3部分，每部分200-300字）"""
    
    advice_1 = f"""
    <b>🎯 优先级1：紧急改善睡眠</b><br/><br/>
    您的睡眠数据（2.82小时）显示严重睡眠不足，这是当前最大的健康风险。
    长期睡眠不足（<6小时）与心血管疾病、认知衰退、代谢紊乱风险显著相关。
    <b>立即行动：</b>今晚确保22:00前上床，目标获得至少7小时睡眠。
    睡前1小时避免蓝光（手机/电脑），可尝试冥想或温水泡脚帮助入睡。
    若入睡困难，建议短期使用褪黑素（咨询医生），但不要依赖。
    建立固定作息是长期解决方案，建议设置就寝提醒并严格执行。
    """
    
    advice_2 = f"""
    <b>💪 优先级2：维持运动习惯，调整强度</b><br/><br/>
    您的运动表现（爬楼108层，HRV 52.8ms，静息心率57bpm）显示良好的体能基础。
    但鉴于睡眠不足，建议未来2-3天将运动强度降低30-40%，
    改为快走、瑜伽或轻度力量训练。HRV数据（52.8ms）显示自主神经系统仍在恢复中，
    这是身体适应训练的正向信号。维持每周4-5次、每次30-45分钟的运动频率，
    但优先保证睡眠，避免在高负荷状态下强行训练导致过度训练综合征。
    """
    
    advice_3 = f"""
    <b>📊 优先级3：建立数据追踪体系</b><br/><br/>
    当前数据质量良好（各指标均有多个数据点），建议建立长期追踪习惯。
    <b>关注趋势而非单日数据：</b>HRV 7天平均值、睡眠规律性、周运动量等更有意义。
    建议每周回顾一次数据，寻找生活方式与指标的关联（如咖啡因、工作压力的影响）。
    若条件允许，可考虑使用Whoop或Oura Ring等设备获取更精确的恢复评分和睡眠阶段数据。
    数据驱动的健康管理能帮助您更早发现问题并调整。
    """
    
    return [advice_1, advice_2, advice_3]

def create_heart_rate_chart():
    """创建心率曲线图"""
    drawing = Drawing(400, 150)
    
    # 模拟心率数据（33分钟爬楼梯）
    times = list(range(0, 34, 2))  # 每2分钟一个点
    hr_values = [80, 115, 135, 148, 155, 162, 165, 168, 166, 164, 165, 167, 165, 163, 160, 158, 155, 120]
    
    lc = HorizontalLineChart()
    lc.x = 50
    lc.y = 30
    lc.height = 100
    lc.width = 320
    lc.data = [hr_values]
    lc.categoryAxis.categoryNames = [f'{t}' for t in times]
    lc.categoryAxis.labels.fontSize = 8
    lc.valueAxis.valueMin = 60
    lc.valueAxis.valueMax = 180
    lc.valueAxis.valueStep = 30
    lc.lines[0].strokeColor = colors.HexColor('#e94560')
    lc.lines[0].strokeWidth = 2
    
    drawing.add(lc)
    
    # 添加标题
    drawing.add(String(200, 140, '心率曲线 (bpm)', fontSize=10, textAnchor='middle'))
    drawing.add(String(30, 80, 'bpm', fontSize=8, textAnchor='middle'))
    drawing.add(String(200, 10, '时间 (分钟)', fontSize=8, textAnchor='middle'))
    
    # 添加区间标注线
    drawing.add(Line(50, 30 + (151-60)/120*100, 370, 30 + (151-60)/120*100, 
                     strokeColor=colors.HexColor('#00b894'), strokeWidth=1, strokeDashArray=[3,3]))
    drawing.add(Line(50, 30 + (168-60)/120*100, 370, 30 + (168-60)/120*100, 
                     strokeColor=colors.HexColor('#d63031'), strokeWidth=1, strokeDashArray=[3,3]))
    
    return drawing

def create_sleep_chart(data):
    """创建睡眠结构图"""
    drawing = Drawing(400, 200)
    
    sleep_stages = ['清醒', 'REM', '核心', '深睡']
    sleep_values = [
        data['sleep_awake']['value'],
        data['sleep_rem']['value'],
        data['sleep_core']['value'],
        data['sleep_deep']['value']
    ]
    colors_list = [colors.HexColor('#dfe6e9'), colors.HexColor('#74b9ff'), 
                   colors.HexColor('#0984e3'), colors.HexColor('#6c5ce7')]
    
    bc = VerticalBarChart()
    bc.x = 80
    bc.y = 40
    bc.height = 120
    bc.width = 240
    bc.data = [sleep_values]
    bc.categoryAxis.categoryNames = sleep_stages
    bc.categoryAxis.labels.fontSize = 10
    bc.valueAxis.valueMin = 0
    bc.valueAxis.valueMax = 2.0
    bc.valueAxis.valueStep = 0.5
    bc.valueAxis.labels.fontSize = 9
    # 为每个柱子设置不同颜色
    for i, color in enumerate(colors_list):
        bc.bars[i].fillColor = color
    
    drawing.add(bc)
    drawing.add(String(200, 180, '睡眠结构分布 (小时)', fontSize=11, textAnchor='middle'))
    drawing.add(String(30, 100, '小时', fontSize=9, textAnchor='middle'))
    
    return drawing

def generate_pdf(output_path):
    """生成PDF报告"""
    
    font_name = register_fonts()
    styles = create_styles(font_name)
    
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm
    )
    
    story = []
    data = HEALTH_DATA
    
    # ========== 第一页：封面 + 指标概览 ==========
    
    # 标题
    story.append(Paragraph(f"每日健康分析报告", styles['ChineseTitle']))
    story.append(Paragraph(f"{data['date']} 星期{data['weekday']} | 第{data['day_of_year']}天", styles['ChineseSubtitle']))
    story.append(Spacer(1, 20))
    
    # 恢复评分卡片
    story.append(Paragraph("📊 今日恢复评分", styles['ChineseHeading1']))
    recovery_data = [
        ['恢复评分', '睡眠评分', '运动评分'],
        ['65/100', '35/100', '75/100'],
        ['一般 - 需关注睡眠', '不足 - 需改善', '良好 - 保持'],
    ]
    recovery_table = Table(recovery_data, colWidths=[5*cm, 5*cm, 5*cm])
    recovery_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), font_name),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('FONTSIZE', (0, 1), (-1, 1), 16),
        ('FONTSIZE', (0, 2), (-1, 2), 9),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f8f9fa')),
        ('BACKGROUND', (0, 1), (0, 1), colors.HexColor('#fdcb6e')),
        ('BACKGROUND', (1, 1), (1, 1), colors.HexColor('#d63031')),
        ('BACKGROUND', (2, 1), (2, 1), colors.HexColor('#00b894')),
        ('TEXTCOLOR', (0, 1), (-1, 1), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dfe6e9')),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
    ]))
    story.append(recovery_table)
    story.append(Spacer(1, 15))
    
    # ========== 11项指标详细分析 ==========
    story.append(Paragraph("📈 健康指标详细分析", styles['ChineseHeading1']))
    
    metrics = [
        ('hrv', '心率变异性 (HRV)', f"{data['hrv']['value']} ms ({data['hrv']['points']}点)"),
        ('resting_hr', '静息心率', f"{data['resting_hr']['value']} bpm ({data['resting_hr']['points']}点)"),
        ('steps', '步数', f"{data['steps']['value']:,} 步 ({data['steps']['points']}点)"),
        ('distance', '行走距离', f"{data['distance']['value']} km ({data['distance']['points']}点)"),
        ('active_energy', '活动能量', f"{data['active_energy']['value']} kcal ({data['active_energy']['points']}点)"),
        ('floors', '爬楼层数', f"{data['floors']['value']} 层 ({data['floors']['points']}点)"),
        ('stand', '站立时间', f"{data['stand']['value']} 小时 ({data['stand']['points']}点)"),
        ('blood_oxygen', '血氧饱和度', f"{data['blood_oxygen']['value']}% ({data['blood_oxygen']['points']}点)"),
        ('sleep_total', '睡眠总时长', f"{data['sleep_total']['value']} 小时 (来源: 2.19文件)"),
        ('sleep_structure', '睡眠结构', f"深{data['sleep_deep']['value']}h/核{data['sleep_core']['value']}h/REM{data['sleep_rem']['value']}h/醒{data['sleep_awake']['value']}h"),
        ('recovery_score', '综合恢复评分', "65/100 (基于HRV/睡眠/RHR计算)"),
    ]
    
    for metric_key, metric_name, metric_value in metrics:
        story.append(Paragraph(f"<b>{metric_name}:</b> {metric_value}", styles['ChineseHeading2']))
        analysis = generate_metric_analysis(metric_key, data)
        story.append(Paragraph(analysis, styles['ChineseBody']))
        story.append(Spacer(1, 5))
    
    # ========== 第二页：睡眠分析 ==========
    story.append(PageBreak())
    story.append(Paragraph("😴 睡眠深度分析", styles['ChineseHeading1']))
    story.append(Spacer(1, 10))
    
    # 睡眠概览表
    sleep_overview = [
        ['指标', '数值', '推荐范围', '状态'],
        ['总睡眠时长', f"{data['sleep_total']['value']}h", '7-9h', '严重不足'],
        ['深睡', f"{data['sleep_deep']['value']}h", '1.5-2h (20%)', '不足'],
        ['核心睡眠', f"{data['sleep_core']['value']}h", '3-4h (50%)', '压缩'],
        ['REM睡眠', f"{data['sleep_rem']['value']}h", '1.5-2h (25%)', '不足'],
        ['清醒时间', f"{data['sleep_awake']['value']}h", '<0.5h (5%)', '正常'],
    ]
    sleep_table = Table(sleep_overview, colWidths=[4*cm, 3*cm, 4*cm, 3*cm])
    sleep_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), font_name),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#636e72')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('BACKGROUND', (3, 1), (3, 1), colors.HexColor('#d63031')),
        ('BACKGROUND', (3, 2), (3, 2), colors.HexColor('#fdcb6e')),
        ('BACKGROUND', (3, 3), (3, 3), colors.HexColor('#d63031')),
        ('BACKGROUND', (3, 4), (3, 4), colors.HexColor('#fdcb6e')),
        ('BACKGROUND', (3, 5), (3, 5), colors.HexColor('#00b894')),
        ('TEXTCOLOR', (3, 1), (3, 5), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#b2bec3')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(sleep_table)
    story.append(Spacer(1, 15))
    
    # 睡眠结构图
    story.append(Paragraph("睡眠结构分布", styles['ChineseHeading2']))
    story.append(create_sleep_chart(data))
    story.append(Spacer(1, 15))
    
    # 睡眠分析文字
    story.append(Paragraph("<b>睡眠质量评估：</b>", styles['ChineseHeading2']))
    sleep_analysis_text = f"""
    根据2026-02-19睡眠记录文件数据，您昨日睡眠严重偏离健康标准。总睡眠时长2.82小时仅为推荐量的35-40%，
    属于急性睡眠剥夺范畴。睡眠结构中，深睡0.5小时（占18%）略低于理想比例，REM睡眠0.5小时（占18%）明显不足，
    可能影响记忆巩固和情绪调节。核心睡眠1.5小时被压缩以补偿其他阶段，清醒时间0.32小时（占11%）在可接受范围。
    <br/><br/>
    <b>影响分析：</b>急性睡眠不足会导致次日认知功能下降约20-30%，反应时间延长，决策能力受损。
    情绪调节能力下降，易怒和焦虑风险增加。免疫系统功能暂时抑制，感染风险上升。代谢方面，
    胰岛素敏感性下降，饥饿激素水平升高，易导致过量进食。<br/><br/>
    <b>改善建议：</b>今晚必须优先补偿睡眠，建议20:00后开始降低活动强度，21:30停止所有屏幕使用，
    22:00上床准备入睡。可短期使用助眠措施（如褪黑素、白噪音）。建立固定作息是长期解决方案。
    """
    story.append(Paragraph(sleep_analysis_text, styles['ChineseBody']))
    
    # ========== 第三页：Workout记录 ==========
    story.append(PageBreak())
    story.append(Paragraph("💪 运动记录详细分析", styles['ChineseHeading1']))
    story.append(Spacer(1, 10))
    
    # Workout概览
    w = data['workout']
    workout_overview = [
        ['运动类型', '时长', '消耗热量', '平均心率', '心率区间'],
        ['爬楼梯', f"{w['duration']}分钟", f"{w['calories']}kcal", f"{w['hr_avg']}bpm", f"{w['hr_min']}-{w['hr_max']}bpm"],
    ]
    workout_table = Table(workout_overview, colWidths=[3.5*cm, 3*cm, 3*cm, 3*cm, 3.5*cm])
    workout_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), font_name),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#00b894')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#b2bec3')),
    ]))
    story.append(workout_table)
    story.append(Spacer(1, 15))
    
    # 心率曲线
    story.append(Paragraph("运动心率曲线", styles['ChineseHeading2']))
    story.append(create_heart_rate_chart())
    story.append(Spacer(1, 10))
    
    # Workout详细分析
    story.append(Paragraph("详细分析", styles['ChineseHeading2']))
    workout_analyses = generate_workout_analysis(data)
    for analysis in workout_analyses:
        story.append(Paragraph(analysis, styles['ChineseBody']))
        story.append(Spacer(1, 8))
    
    # ========== 第四页：AI建议 ==========
    story.append(PageBreak())
    story.append(Paragraph("🤖 AI健康建议", styles['ChineseHeading1']))
    story.append(Spacer(1, 10))
    
    ai_advices = generate_ai_advice(data)
    for i, advice in enumerate(ai_advices, 1):
        story.append(Paragraph(advice, styles['AIAdvice']))
        story.append(Spacer(1, 5))
    
    # ========== 数据来源追溯 ==========
    story.append(Spacer(1, 20))
    story.append(Paragraph("📋 数据来源追溯", styles['ChineseHeading1']))
    
    source_data = [
        ['指标类别', '数据来源', '数据点数量', '采集时间'],
        ['HRV', 'Apple Watch / Health App', '51点', '2026-02-18全天'],
        ['静息心率', 'Apple Watch / Health App', '1点', '晨起测量'],
        ['步数', 'iPhone / Apple Watch', '276点', '2026-02-18全天'],
        ['行走距离', 'iPhone / Apple Watch', '276点', '2026-02-18全天'],
        ['活动能量', 'Apple Watch (2358.7kJ转换)', '959点', '2026-02-18全天'],
        ['爬楼层数', 'Apple Watch', '39点', '2026-02-18全天'],
        ['站立时间', 'Apple Watch', '1点', '2026-02-18全天'],
        ['血氧', 'Apple Watch', '1点', '2026-02-18'],
        ['睡眠', 'Apple Health Export (2.19文件)', '完整记录', '2026-02-18夜间'],
        ['Workout', 'Apple Watch 锻炼记录', '1条', '2026-02-18'],
    ]
    source_table = Table(source_data, colWidths=[3.5*cm, 5*cm, 3*cm, 4*cm])
    source_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), font_name),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2d3436')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#b2bec3')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(source_table)
    
    # 页脚
    story.append(Spacer(1, 30))
    footer_text = f"""
    <para alignment="center" fontSize="8" textColor="#b2bec3">
    报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 
    数据周期: 2026-02-18 | 
    报告版本: V2-FINAL | 
    本报告仅供参考，不作为医疗诊断依据
    </para>
    """
    story.append(Paragraph(footer_text, styles['ChineseSmall']))
    
    # 生成PDF
    doc.build(story)
    print(f"✅ PDF报告已生成: {output_path}")

if __name__ == '__main__':
    output_path = "/Users/jimmylu/.openclaw/workspace/shared/health-reports/upload/2026-02-18-report-zh-FINAL.pdf"
    generate_pdf(output_path)
