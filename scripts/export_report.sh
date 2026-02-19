#!/bin/bash
#
# 健康报告 PDF 导出脚本
# 支持多种格式: PDF, HTML, DOCX
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WORKSPACE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
REPORTS_DIR="$WORKSPACE_DIR/memory/health-daily"
SAFE_DIR="/Users/jimmylu/.openclaw/workspace/shared/health-reports"
OUTPUT_DIR="$SAFE_DIR/pdf"

mkdir -p "$OUTPUT_DIR"

# 检查工具
 check_pandoc() {
  if ! command -v pandoc &> /dev/null; then
    echo "❌ pandoc 未安装"
    echo ""
    echo "安装方法:"
    echo "  brew install pandoc"
    echo "  brew install --cask wkhtmltopdf"
    return 1
  fi
  return 0
}

# Markdown → PDF (需要 pandoc + wkhtmltopdf)
convert_to_pdf() {
  local input_file="$1"
  local output_file="${2:-$OUTPUT_DIR/$(basename "$input_file" .md).pdf}"
  
  if ! check_pandoc; then
    return 1
  fi
  
  echo "🔄 转换 $input_file → PDF..."
  
  # 使用 pandoc + wkhtmltopdf 生成 PDF
  pandoc "$input_file" \
    --pdf-engine=wkhtmltopdf \
    --metadata title="健康报告" \
    --metadata author="Health Agent" \
    --metadata date="$(date +%Y-%m-%d)" \
    -o "$output_file"
  
  echo "✅ PDF 已生成: $output_file"
}

# Markdown → HTML
convert_to_html() {
  local input_file="$1"
  local output_file="${2:-$OUTPUT_DIR/$(basename "$input_file" .md).html}"
  
  if ! check_pandoc; then
    return 1
  fi
  
  echo "🔄 转换 $input_file → HTML..."
  
  pandoc "$input_file" \
    --standalone \
    --metadata title="健康报告" \
    -c "https://cdn.jsdelivr.net/npm/water.css@2/out/water.css" \
    -o "$output_file"
  
  echo "✅ HTML 已生成: $output_file"
}

# Markdown → DOCX
convert_to_docx() {
  local input_file="$1"
  local output_file="${2:-$OUTPUT_DIR/$(basename "$input_file" .md).docx}"
  
  if ! check_pandoc; then
    return 1
  fi
  
  echo "🔄 转换 $input_file → DOCX..."
  
  pandoc "$input_file" \
    -o "$output_file"
  
  echo "✅ DOCX 已生成: $output_file"
}

# 使用 Python 生成简单 PDF (备用方案)
convert_to_pdf_python() {
  local input_file="$1"
  local output_file="${2:-$OUTPUT_DIR/$(basename "$input_file" .md).pdf}"
  
  echo "🔄 使用 Python 转换 $input_file → PDF..."
  
  python3 << EOF
import sys

try:
    from fpdf import FPDF
    import markdown
except ImportError:
    print("❌ 需要安装依赖: pip3 install fpdf2 markdown")
    sys.exit(1)

# 读取 markdown
with open("$input_file", 'r', encoding='utf-8') as f:
    md_content = f.read()

# 转换为纯文本（简化版）
html = markdown.markdown(md_content)
# 简单的 HTML tag 移除
import re
text = re.sub('<[^<]+?>', '', html)

# 创建 PDF
pdf = FPDF()
pdf.add_page()
pdf.set_auto_page_break(auto=True, margin=15)

# 尝试使用支持中文的字体
try:
    pdf.add_font('DejaVu', '', '/System/Library/Fonts/PingFang.ttc', uni=True)
    pdf.set_font('DejaVu', size=12)
except:
    pdf.set_font('Arial', size=12)

# 添加内容
for line in text.split('\n'):
    if line.strip():
        pdf.cell(0, 10, line[:100], ln=True)  # 限制每行长度

pdf.output("$output_file")
print(f"✅ PDF 已生成: $output_file")
EOF
}

# 主函数
main() {
  local format="${1:-pdf}"
  local input_file="${2:-}"
  
  # 如果没有指定输入文件，使用最新的报告
  if [[ -z "$input_file" ]]; then
    input_file="$(ls -t "$REPORTS_DIR"/*.md 2>/dev/null | head -n 1 || true)"
    if [[ -z "$input_file" ]]; then
      echo "❌ 没有找到报告文件"
      exit 1
    fi
  fi
  
  if [[ ! -f "$input_file" ]]; then
    echo "❌ 文件不存在: $input_file"
    exit 1
  fi
  
  case "$format" in
    pdf)
      if check_pandoc; then
        convert_to_pdf "$input_file"
      else
        echo ""
        echo "尝试使用 Python 备用方案..."
        convert_to_pdf_python "$input_file"
      fi
      ;;
    html)
      convert_to_html "$input_file"
      ;;
    docx)
      convert_to_docx "$input_file"
      ;;
    *)
      echo "用法: $0 [pdf|html|docx] [文件路径]"
      echo ""
      echo "示例:"
      echo "  $0 pdf                    # 转换最新报告为 PDF"
      echo "  $0 html                   # 转换最新报告为 HTML"
      echo "  $0 pdf /path/to/file.md   # 转换指定文件"
      exit 1
      ;;
  esac
}

main "$@"
