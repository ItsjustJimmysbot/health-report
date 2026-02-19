#!/bin/bash
# 生成无页脚 URL 的 PDF

HTML_FILE="$1"
PDF_FILE="$2"

if [ -z "$HTML_FILE" ] || [ -z "$PDF_FILE" ]; then
    echo "Usage: $0 <html_file> <pdf_file>"
    exit 1
fi

# 创建临时修改的 HTML（添加打印样式隐藏页脚）
TEMP_HTML="${HTML_FILE%.html}_print.html"

# 在 HTML 中添加打印样式
cat "$HTML_FILE" | sed 's|</head>|<style>
@media print {
    @page { margin: 1cm; }
    body { -webkit-print-color-adjust: exact; }
}
</style></head>|' > "$TEMP_HTML"

# 使用 Chrome 生成 PDF
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
    --headless \
    --disable-gpu \
    --print-to-pdf="$PDF_FILE" \
    --run-all-compositor-stages-before-draw \
    --virtual-time-budget=15000 \
    "file://$TEMP_HTML" 2>/dev/null

# 删除临时文件
rm -f "$TEMP_HTML"

if [ -f "$PDF_FILE" ]; then
    echo "✅ PDF 已生成: $PDF_FILE"
    ls -lh "$PDF_FILE"
else
    echo "❌ PDF 生成失败"
    exit 1
fi
