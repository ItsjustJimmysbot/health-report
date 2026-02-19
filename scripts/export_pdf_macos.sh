#!/bin/bash
#
# macOS 原生方式生成 PDF
# 使用 textutil 和系统打印功能
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WORKSPACE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
REPORTS_DIR="$WORKSPACE_DIR/memory/health-daily"
SAFE_DIR="/Users/jimmylu/.openclaw/workspace/shared/health-reports"
OUTPUT_DIR="$SAFE_DIR/pdf"

mkdir -p "$OUTPUT_DIR"

INPUT_FILE="${1:-$(ls -t "$REPORTS_DIR"/*.md 2>/dev/null | head -n 1)}"

if [[ ! -f "$INPUT_FILE" ]]; then
  echo "❌ 没有找到报告文件"
  exit 1
fi

BASENAME=$(basename "$INPUT_FILE" .md)
OUTPUT_FILE="$OUTPUT_DIR/${BASENAME}.pdf"

echo "🔄 转换 $INPUT_FILE → PDF..."

# 方法1: 使用 textutil 转换为 rtf，再打开打印为 PDF
# 先创建一个临时 RTF 文件
TMP_RTF="/tmp/${BASENAME}.rtf"

# 使用 markdown 转换为 HTML，然后用 wkhtmltopdf 或系统浏览器
cat > /tmp/convert_to_pdf.py << 'EOF'
import sys
import os
from pathlib import Path

input_file = sys.argv[1]
output_file = sys.argv[2]

# 读取 markdown
with open(input_file, 'r', encoding='utf-8') as f:
    content = f.read()

# 创建简单 HTML
html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>健康报告</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            color: #333;
        }}
        h1 {{ color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
        h2 {{ color: #34495e; margin-top: 30px; }}
        h3 {{ color: #7f8c8d; }}
        table {{ border-collapse: collapse; width: 100%; margin: 15px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f8f9fa; font-weight: bold; }}
        code {{ background-color: #f4f4f4; padding: 2px 5px; border-radius: 3px; }}
        blockquote {{ border-left: 4px solid #3498db; margin: 0; padding-left: 15px; color: #666; }}
        hr {{ border: none; border-top: 1px solid #eee; margin: 30px 0; }}
    </style>
</head>
<body>
"""

# 简单的 markdown 到 HTML 转换
import re

lines = content.split('\n')
html_body = []
in_code = False

for line in lines:
    # 代码块
    if line.startswith('```'):
        if in_code:
            html_body.append('</pre></code>')
            in_code = False
        else:
            html_body.append('<code><pre>')
            in_code = True
        continue
    
    if in_code:
        html_body.append(line)
        continue
    
    # 标题
    if line.startswith('# '):
        html_body.append(f'<h1>{line[2:]}</h1>')
    elif line.startswith('## '):
        html_body.append(f'<h2>{line[3:]}</h2>')
    elif line.startswith('### '):
        html_body.append(f'<h3>{line[4:]}</h3>')
    # 分隔线
    elif line.strip() == '---':
        html_body.append('<hr>')
    # 表格 (简化处理)
    elif '|' in line and not line.strip().startswith('|-'):
        cells = [c.strip() for c in line.split('|') if c.strip()]
        if cells:
            row = ''.join([f'<td>{c}</td>' for c in cells])
            html_body.append(f'<tr>{row}</tr>')
    # 普通段落
    elif line.strip():
        html_body.append(f'<p>{line}</p>')
    else:
        html_body.append('<br>')

html_content += '\n'.join(html_body)
html_content += "\n</body>\n</html>"

# 保存 HTML
html_file = output_file.replace('.pdf', '.html')
with open(html_file, 'w', encoding='utf-8') as f:
    f.write(html_content)

print(f"✅ HTML 已生成: {html_file}")

# 尝试使用 wkhtmltopdf 或系统打印功能生成 PDF
import subprocess

try:
    # 尝试使用 wkhtmltopdf
    subprocess.run(['wkhtmltopdf', '--encoding', 'utf-8', html_file, output_file], check=True)
    print(f"✅ PDF 已生成: {output_file}")
except:
    # 如果没有 wkhtmltopdf，提示用户使用浏览器打开 HTML 打印为 PDF
    print(f"⚠️ 未找到 wkhtmltopdf，请打开以下文件用浏览器打印为 PDF:")
    print(f"   {html_file}")
EOF

python3 /tmp/convert_to_pdf.py "$INPUT_FILE" "$OUTPUT_FILE" || {
  echo "❌ 转换失败"
  exit 1
}
