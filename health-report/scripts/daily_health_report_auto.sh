#!/bin/bash
#
# Health Report - 每日健康报告
# 自动从 Apple Health 和 Google Fit 生成健康报告
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WORKSPACE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# 计算昨天的日期
YESTERDAY=$(date -v-1d +%F 2>/dev/null || date -d "yesterday" +%F)

echo "=========================================="
echo "  Daily Health Report"
echo "  Report Date: ${YESTERDAY}"
echo "  Generated: $(date '+%Y-%m-%d %H:%M:%S')"
echo "=========================================="
echo ""

# 配置文件路径
CREDENTIALS_DIR="${HOME}/.openclaw/credentials"
mkdir -p "$CREDENTIALS_DIR"

# 读取配置
HEALTH_PATH_FILE="$CREDENTIALS_DIR/health-report-path.conf"
EMAIL_FILE="$CREDENTIALS_DIR/health-report-email.conf"

if [[ -f "$HEALTH_PATH_FILE" ]]; then
    HEALTH_PATH=$(cat "$HEALTH_PATH_FILE")
else
    HEALTH_PATH="${HOME}/Google Drive/Health Auto Export"
    if [[ ! -d "$HEALTH_PATH" ]]; then
        HEALTH_PATH="${HOME}/Library/CloudStorage/GoogleDrive-*/Health Auto Export"
    fi
fi

if [[ -f "$EMAIL_FILE" ]]; then
    RECIPIENT=$(cat "$EMAIL_FILE")
else
    RECIPIENT=""
fi

HEALTH_FILE="${HEALTH_PATH}/Health Data/HealthAutoExport-${YESTERDAY}.json"
WORKOUT_FILE="${HEALTH_PATH}/Workout Data/HealthAutoExport-${YESTERDAY}.json"
OUTPUT_HTML="${WORKSPACE_DIR}/reports/${YESTERDAY}-report.html"
OUTPUT_PDF="${WORKSPACE_DIR}/reports/${YESTERDAY}-report.pdf"
mkdir -p "${WORKSPACE_DIR}/reports"

# 检查必要文件
if [[ ! -f "$HEALTH_FILE" ]]; then
    echo "❌ Health data file not found: $HEALTH_FILE"
    echo "   Please ensure Health Auto Export is syncing to Google Drive"
    exit 1
fi

if [[ ! -f "$WORKOUT_FILE" ]]; then
    echo "⚠️  Workout data file not found, continuing without workout details"
    WORKOUT_FILE="/dev/null"
fi

# 检测系统语言
LANG=$(defaults read -g AppleLocale 2>/dev/null || echo "en_US")
if [[ "$LANG" == zh* ]]; then
    REPORT_LANG="zh"
    echo "📝 Generating Chinese report..."
else
    REPORT_LANG="en"
    echo "📝 Generating English report..."
fi

# 生成报告
cd "$WORKSPACE_DIR"
python3 "${SCRIPT_DIR}/generate_multilingual_report.py" \
    --health "$HEALTH_FILE" \
    --workout "$WORKOUT_FILE" \
    --output "$OUTPUT_HTML" \
    --date "$YESTERDAY" \
    --lang "$REPORT_LANG"

echo ""
echo "📄 Generating PDF..."
python3 "${SCRIPT_DIR}/generate_pdf_playwright.py" "$OUTPUT_HTML" "$OUTPUT_PDF"

echo ""

# 发送邮件（如果配置了邮箱）
if [[ -n "$RECIPIENT" ]]; then
    echo "📧 Sending email to ${RECIPIENT}..."
    osascript "${SCRIPT_DIR}/send_email_applescript.scpt" "$OUTPUT_PDF" "$RECIPIENT"
    echo ""
fi

# Git 提交
echo "💾 Saving to Git..."
cd "$WORKSPACE_DIR"
if [[ -n $(git status --porcelain 2>/dev/null) ]]; then
    git add -A
    git commit -m "chore: daily report for ${YESTERDAY}" || true
    git push 2>/dev/null || echo "⚠️  Push failed"
    echo "✅ Saved to Git"
else
    echo "⚠️  No changes to commit"
fi

echo ""
echo "=========================================="
echo "  ✅ Daily Health Report Complete!"
echo "  HTML: $OUTPUT_HTML"
echo "  PDF:  $OUTPUT_PDF"
if [[ -n "$RECIPIENT" ]]; then
    echo "  Email sent to: ${RECIPIENT}"
fi
echo "=========================================="