#!/usr/bin/env python3
#
# 修复中文乱码的 PDF 生成脚本
# 使用系统自带中文字体
#

import sys
import os
from pathlib import Path
from datetime import datetime

def convert_md_to_pdf(input_file, output_file=None):
    """将 Markdown 文件转换为 PDF（支持中文）"""
    
    try:
        from weasyprint import HTML, CSS
        import markdown
    except ImportError:
        print("❌ 需要安装依赖:")
        print("   pip3 install weasyprint markdown")
        sys.exit(1)
    
    if not output_file:
        output_file = input_file.replace('.md', '.pdf')
    
    print(f"🔄 转换 {input_file} → PDF (修复中文)...")
    
    # 读取 markdown
    with open(input_file, 'r', encoding='utf-8') as f:
        md_content = f.read()
    
    # 转换为 HTML
    html_body = markdown.markdown(md_content, extensions=['tables'])
    
    # 构建完整 HTML 文档，使用系统字体
    html_content = f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>健康报告</title>
    <style>
        @page {{
            size: A4;
            margin: 2cm;
        }}
        body {{
            font-family: "SF Pro Text", "SF Pro Display", "Helvetica Neue", "Arial", "STHeiti", "Microsoft YaHei", sans-serif;
            font-size: 11pt;
            line-height: 1.6;
            color: #333;
        }}
        h1 {{
            font-family: "SF Pro Display", "Helvetica Neue", "Arial", "STHeiti", sans-serif;
            font-size: 20pt;
            color: #2c3e50;
            border-bottom: 2px solid #3498db;
            padding-bottom: 10px;
            margin-top: 0;
        }}
        h2 {{
            font-family: "SF Pro Display", "Helvetica Neue", "Arial", "STHeiti", sans-serif;
            font-size: 14pt;
            color: #34495e;
            margin-top: 25px;
            border-bottom: 1px solid #ecf0f1;
            padding-bottom: 5px;
        }}
        h3 {{
            font-family: "SF Pro Display", "Helvetica Neue", "Arial", "STHeiti", sans-serif;
            font-size: 12pt;
            color: #7f8c8d;
            margin-top: 20px;
        }}
        table {{
            border-collapse: collapse;
            width: 100%;
            margin: 15px 0;
            font-size: 10pt;
        }}
        th, td {{
            border: 1px solid #bdc3c7;
            padding: 8px 12px;
            text-align: left;
        }}
        th {{
            background-color: #f8f9fa;
            font-weight: bold;
            color: #2c3e50;
        }}
        tr:nth-child(even) {{
            background-color: #f8f9fa;
        }}
        code {{
            background-color: #f4f4f4;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: "SF Mono", "Monaco", "Consolas", monospace;
            font-size: 10pt;
        }}
        pre {{
            background-color: #f8f9fa;
            padding: 15px;
            border-radius: 5px;
            overflow-x: auto;
            font-family: "SF Mono", "Monaco", "Consolas", monospace;
            font-size: 10pt;
        }}
        blockquote {{
            border-left: 4px solid #3498db;
            margin: 15px 0;
            padding: 10px 15px;
            background-color: #f8f9fa;
            color: #555;
        }}
        hr {{
            border: none;
            border-top: 1px solid #ecf0f1;
            margin: 25px 0;
        }}
        p {{
            margin: 10px 0;
        }}
        ul, ol {{
            margin: 10px 0;
            padding-left: 25px;
        }}
        li {{
            margin: 5px 0;
        }}
        strong {{
            color: #2c3e50;
            font-weight: 600;
        }}
        em {{
            color: #7f8c8d;
        }}
        /* Emoji 样式 */
        .emoji {{
            font-family: "Apple Color Emoji", "Segoe UI Emoji", sans-serif;
        }}
    </style>
</head>
<body>
{html_body}
</body>
</html>'''
    
    # 保存临时 HTML（用于调试）
    html_file = output_file.replace('.pdf', '.html')
    with open(html_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    # 使用 weasyprint 生成 PDF
    try:
        HTML(string=html_content).write_pdf(output_file)
        print(f"✅ PDF 已生成: {output_file}")
        print(f"   临时 HTML: {html_file}")
        return output_file
    except Exception as e:
        print(f"❌ 生成失败: {e}")
        print(f"   但 HTML 已保存: {html_file}")
        print(f"   可以用浏览器打开 HTML 手动打印为 PDF")
        sys.exit(1)

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='健康报告 PDF 导出（修复中文）')
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
