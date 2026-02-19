#!/bin/bash
#
# 每日健康报告自动化脚本
# 每天 12:30 运行，生成前一天的健康报告并发送邮件
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WORKSPACE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# 计算昨天的日期
YESTERDAY=$(date -v-1d +%F)
YESTERDAY_FORMATTED=$(date -v-1d +%Y-%m-%d)

echo "=========================================="
echo "  每日健康报告自动化"
echo "  报告日期: ${YESTERDAY}"
echo "  生成时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "=========================================="
echo ""

# 文件路径
HEALTH_FILE="${HOME}/我的云端硬盘/Health Auto Export/Health Data/HealthAutoExport-${YESTERDAY}.json"
WORKOUT_FILE="${HOME}/我的云端硬盘/Health Auto Export/Workout Data/HealthAutoExport-${YESTERDAY}.json"
OUTPUT_HTML="${WORKSPACE_DIR}/../workspace/shared/health-reports/${YESTERDAY}-daily-report.html"
OUTPUT_PDF="${WORKSPACE_DIR}/../workspace/shared/health-reports/pdf/${YESTERDAY}-daily-report.pdf"
RECIPIENT="revolutionljk@gmail.com"

# 检查 Health 数据文件是否存在
if [[ ! -f "$HEALTH_FILE" ]]; then
    echo "❌ 未找到 Health 数据文件: $HEALTH_FILE"
    echo "   跳过今日报告生成"
    exit 1
fi

if [[ ! -f "$WORKOUT_FILE" ]]; then
    echo "⚠️ 未找到 Workout 数据文件: $WORKOUT_FILE"
    echo "   将继续生成报告（不含详细运动数据）"
fi

echo "✅ 数据文件检查通过"
echo "   Health: $HEALTH_FILE"
echo "   Workout: $WORKOUT_FILE"
echo ""

# 生成 HTML 报告
echo "📊 生成健康报告..."
cd "$WORKSPACE_DIR"
python3 "${SCRIPT_DIR}/generate_report_final.py" \
    --health "$HEALTH_FILE" \
    --workout "$WORKOUT_FILE" \
    --output "$OUTPUT_HTML" \
    --date "$YESTERDAY"

echo ""

# 生成 PDF
echo "📄 生成 PDF..."
python3 "${SCRIPT_DIR}/generate_pdf_playwright.py" "$OUTPUT_HTML" "$OUTPUT_PDF"

echo ""

# 发送邮件
echo "📧 发送邮件到 ${RECIPIENT}..."
osascript "${SCRIPT_DIR}/send_email_applescript.scpt" "$OUTPUT_PDF" "$RECIPIENT"

echo ""

# Git 提交
echo "💾 提交到 Git..."
cd "$WORKSPACE_DIR"
if [[ -n $(git status --porcelain 2>/dev/null) ]]; then
    git add -A
    git commit -m "chore(health): daily report for ${YESTERDAY}" || true
    git push || echo "⚠️ Push 失败"
    echo "✅ 已提交到 Git"
else
    echo "⚠️ 无变更需要提交"
fi

echo ""
echo "=========================================="
echo "  ✅ 每日健康报告完成！"
echo "  报告已发送至: ${RECIPIENT}"
echo "  PDF: ${OUTPUT_PDF}"
echo "=========================================="
