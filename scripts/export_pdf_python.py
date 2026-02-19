#!/usr/bin/env python3
#
# 使用纯 Python 生成 PDF 报告
# 需要: pip3 install fpdf2
#

import sys
import os
from pathlib import Path
from datetime import datetime

def convert_md_to_pdf(input_file, output_file=None):
    """将 Markdown 文件转换为 PDF"""
    
    try:
        from fpdf import FPDF
        import markdown
    except ImportError:
        print("❌ 需要安装依赖:")
        print("   pip3 install fpdf2 markdown")
        sys.exit(1)
    
    if not output_file:
        output_file = input_file.replace('.md', '.pdf')
    
    print(f"🔄 转换 {input_file} → PDF...")
    
    # 读取 markdown
    with open(input_file, 'r', encoding='utf-8') as f:
        md_content = f.read()
    
    # 转换为 HTML 然后处理
    html = markdown.markdown(md_content)
    
    # 创建 PDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    # 使用系统字体（支持中文）
    font_paths = [
        '/System/Library/Fonts/PingFang.ttc',
        '/System/Library/Fonts/STHeiti Light.ttc',
        '/Library/Fonts/Arial Unicode.ttf',
    ]
    
    font_loaded = False
    for font_path in font_paths:
        if os.path.exists(font_path):
            try:
                pdf.add_font('CustomFont', '', font_path, uni=True)
                pdf.set_font('CustomFont', size=12)
                font_loaded = True
                break
            except:
                continue
    
    if not font_loaded:
        pdf.set_font('Arial', size=12)
    
    # 处理内容
    lines = md_content.split('\n')
    for line in lines:
        line = line.strip()
        if not line:
            pdf.ln(5)
            continue
        
        # 处理标题
        if line.startswith('# '):
            pdf.set_font_size(18)
            pdf.cell(0, 10, line[2:], ln=True)
            pdf.ln(5)
        elif line.startswith('## '):
            pdf.set_font_size(14)
            pdf.cell(0, 8, line[3:], ln=True)
            pdf.ln(3)
        elif line.startswith('### '):
            pdf.set_font_size(12)
            pdf.set_font('' if not font_loaded else 'CustomFont', 'B', 12)
            pdf.cell(0, 6, line[4:], ln=True)
            pdf.set_font('' if not font_loaded else 'CustomFont', '', 12)
        elif line.startswith('---'):
            pdf.ln(5)
        else:
            pdf.set_font_size(10)
            # 处理表格行
            if '|' in line:
                cells = [c.strip() for c in line.split('|') if c.strip()]
                if cells and not all(c in '-|: ' for c in line):
                    pdf.cell(0, 5, ' | '.join(cells)[:100], ln=True)
            else:
                # 普通文本
                pdf.multi_cell(0, 5, line[:500])
    
    pdf.output(output_file)
    print(f"✅ PDF 已生成: {output_file}")
    return output_file

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='健康报告 PDF 导出')
    parser.add_argument('input', nargs='?', help='输入 Markdown 文件')
    parser.add_argument('-o', '--output', help='输出 PDF 文件路径')
    
    args = parser.parse_args()
    
    # 默认使用最新报告
    if not args.input:
        reports_dir = Path.home() / '.openclaw' / 'workspace-health' / 'memory' / 'health-daily'
        md_files = sorted(reports_dir.glob('*.md'), key=lambda x: x.stat().st_mtime, reverse=True)
        if md_files:
            args.input = str(md_files[0])
        else:
            print("❌ 没有找到报告文件")
            sys.exit(1)
    
    convert_md_to_pdf(args.input, args.output)
