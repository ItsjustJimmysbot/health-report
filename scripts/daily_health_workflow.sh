#!/bin/bash
#
# 每日健康报告完整流程
# 1. 获取 Apple Health 数据
# 2. 生成 Markdown 报告
# 3. 生成 PDF
# 4. 发送邮件
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WORKSPACE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
DATE=$(date +%Y-%m-%d)
YESTERDAY=$(date -v-1d +%Y-%m-%d)

echo "=========================================="
echo "  每日健康报告 - ${DATE}"
echo "=========================================="
echo ""

# 1. 检查 Apple Health 数据
echo "📱 步骤 1: 检查 Apple Health 数据"
AH_FILE="${HOME}/我的云端硬盘/Health Auto Export/Health Data/HealthAutoExport-${YESTERDAY}.json"

if [[ ! -f "$AH_FILE" ]]; then
    echo "⚠️  未找到 ${YESTERDAY} 的健康数据"
    echo "   请确保 iPhone 已同步到 Google Drive"
    exit 1
fi

echo "✅ 找到数据文件"
echo ""

# 2. 运行健康分析脚本
echo "📊 步骤 2: 生成健康报告"
cd "$WORKSPACE_DIR"
bash scripts/daily-health-report.sh
echo ""

# 3. 生成 PDF
echo "📄 步骤 3: 生成 PDF 报告"
REPORT_MD="${WORKSPACE_DIR}/memory/health-daily/${YESTERDAY}-detailed-report.md"
REPORT_PDF="${WORKSPACE_DIR}/../workspace/shared/health-reports/pdf/${YESTERDAY}-health-report.pdf"

# 使用 pandoc + weasyprint 生成 PDF
if [[ -f "$REPORT_MD" ]]; then
    # 生成 HTML
    pandoc "$REPORT_MD" -t html --wrap=none -o /tmp/health-report-${YESTERDAY}.html
    
    # 添加 CSS
    cat > /tmp/health-report-final-${YESTERDAY}.html <> HTMLHEAD
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<style>
body { font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif; font-size: 11pt; line-height: 1.6; color: #333; max-width: 800px; margin: 0 auto; padding: 20px; }
h1 { font-size: 20pt; color: #2c3e50; border-bottom: 2px solid #3498db; }
h2 { font-size: 14pt; color: #34495e; margin-top: 25px; border-bottom: 1px solid #ecf0f1; }
table { border-collapse: collapse; width: 100%; margin: 15px 0; font-size: 10pt; }
th, td { border: 1px solid #bdc3c7; padding: 8px; text-align: left; }
th { background-color: #f8f9fa; }
</style>
</head>
<body>
HTMLHEAD

    cat /tmp/health-report-${YESTERDAY}.html >> /tmp/health-report-final-${YESTERDAY}.html
    echo "</body></html>" >> /tmp/health-report-final-${YESTERDAY}.html
    
    # 使用 weasyprint 生成 PDF
    weasyprint /tmp/health-report-final-${YESTERDAY}.html "$REPORT_PDF" 2>/dev/null
    
    echo "✅ PDF 已生成: ${REPORT_PDF}"
else
    echo "❌ 未找到 Markdown 报告"
    exit 1
fi
echo ""

# 4. 发送邮件
echo "📧 步骤 4: 发送邮件"
osascript "$SCRIPT_DIR/send_email_applescript.scpt" "$REPORT_PDF" "itestmolt@outlook.com"
echo ""

# 5. Git 提交
echo "💾 步骤 5: 保存到 Git"
cd "$WORKSPACE_DIR"
if [[ -n $(git status --porcelain 2>/dev/null) ]]; then
    git add -A
    git commit -m "chore(health): daily report for ${YESTERDAY}" || true
    git push || echo "⚠️ Push 失败"
    echo "✅ 已保存到 Git"
else
    echo "⚠️ 无变更需要提交"
fi
echo ""

echo "=========================================="
echo "  ✅ 完成！"
echo "=========================================="
echo ""
echo "📧 邮件已发送到: itestmolt@outlook.com"
echo "📄 PDF 报告: ${REPORT_PDF}"
echo ""
