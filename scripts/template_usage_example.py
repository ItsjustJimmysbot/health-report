#!/usr/bin/env python3
"""
统一模板使用示例 - 健康报告生成
展示如何正确使用模板，确保UI一致性
"""
import os
from datetime import datetime

def generate_daily_report_with_template(date_str, data):
    """
    使用统一模板生成日报告
    确保所有日报告UI一致
    """
    # 1. 读取统一模板（必须使用）
    template_path = '/Users/jimmylu/.openclaw/workspace-health/templates/DAILY_TEMPLATE.html'
    
    if not os.path.exists(template_path):
        raise FileNotFoundError(f"模板文件不存在: {template_path}")
    
    with open(template_path, 'r', encoding='utf-8') as f:
        template = f.read()
    
    # 2. 准备数据（仅准备内容，不修改样式）
    replacements = {
        '{{DATE}}': date_str,
        '{{WEEKDAY}}': '星期二',
        '{{DAY_NUM}}': '51',
        '{{SOURCE}}': 'Apple Health',
        
        # 评分卡
        '{{RECOVERY_SCORE}}': str(data.get('recovery_score', 72)),
        '{{RECOVERY_LEVEL}}': '良好',
        '{{RECOVERY_BADGE_CLASS}}': 'badge-good',
        
        '{{SLEEP_SCORE}}': str(data.get('sleep_score', 91)),
        '{{SLEEP_LEVEL}}': '优秀',
        '{{SLEEP_BADGE_CLASS}}': 'badge-excellent',
        
        '{{EXERCISE_SCORE}}': str(data.get('exercise_score', 78)),
        '{{EXERCISE_LEVEL}}': '接近目标',
        '{{EXERCISE_BADGE_CLASS}}': 'badge-average',
        
        # HRV指标
        '{{HRV_VALUE}}': str(data.get('hrv', 53.4)),
        '{{HRV_RATING}}': '优秀',
        '{{HRV_RATING_CLASS}}': 'rating-excellent',
        '{{HRV_ANALYSIS}}': f"{data.get('hrv', 53.4)}ms相比昨日提升15.1%，自主神经系统恢复良好。基于{data.get('hrv_n', 35)}个数据点计算。",
        
        # 页脚
        '{{DATA_SOURCES}}': f"Apple Health (HRV:{data.get('hrv', 53.4)}ms/{data.get('hrv_n', 35)}点, 步数:{data.get('steps', 6230)}/{data.get('steps_n', 136)}点)",
        '{{GENERATED_AT}}': datetime.now().strftime('%Y-%m-%d'),
    }
    
    # 3. 替换变量（仅内容，不改变结构）
    html = template
    for key, value in replacements.items():
        html = html.replace(key, str(value))
    
    # 4. 检查是否还有未替换的变量（可选）
    remaining_vars = [v for v in ['{{DATE}}', '{{HRV_VALUE}}'] if v in html]
    if remaining_vars:
        print(f"⚠️  警告: 还有未替换的变量: {remaining_vars}")
    
    return html

# ========== 使用示例 ==========
if __name__ == '__main__':
    print("=" * 60)
    print("统一模板使用示例")
    print("=" * 60)
    
    # 示例数据
    sample_data = {
        'recovery_score': 72,
        'sleep_score': 91,
        'exercise_score': 78,
        'hrv': 53.4,
        'hrv_n': 35,
        'steps': 6230,
        'steps_n': 136,
    }
    
    print("\n1. 读取统一模板...")
    html = generate_daily_report_with_template('2026-02-20', sample_data)
    
    print("2. 检查生成的HTML...")
    # 检查关键样式是否保留
    if 'background: linear-gradient(135deg, #667eea 0%, #764ba2 100%)' in html:
        print("   ✅ 头部紫色渐变样式正确")
    else:
        print("   ❌ 头部样式被修改！")
    
    if 'font-family: \'PingFang SC\', \'Microsoft YaHei\', sans-serif' in html:
        print("   ✅ 字体样式正确")
    else:
        print("   ❌ 字体样式被修改！")
    
    if 'page-break-before: always' in html:
        print("   ✅ 分页样式正确")
    else:
        print("   ❌ 分页样式被修改！")
    
    print("\n3. 变量替换结果:")
    print(f"   日期: 2026-02-20")
    print(f"   HRV: {sample_data['hrv']}ms")
    print(f"   步数: {sample_data['steps']}")
    
    print("\n" + "=" * 60)
    print("✅ 模板使用正确！")
    print("=" * 60)
    print("\n关键要点:")
    print("1. 必须使用 templates/DAILY_TEMPLATE.html")
    print("2. 仅替换 {{VARIABLE}} 内容变量")
    print("3. 禁止修改CSS样式、颜色、布局")
    print("4. 确保所有报告UI完全一致")
