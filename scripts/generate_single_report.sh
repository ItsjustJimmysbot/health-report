#!/bin/bash
#
# 生成指定日期的健康报告
#

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WORKSPACE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# 获取日期参数
if [ -z "$1" ]; then
    echo "用法: $0 YYYY-MM-DD"
    echo "示例: $0 2026-02-18"
    exit 1
fi

DATE="$1"

# 读取配置
CREDENTIALS_DIR="${HOME}/.openclaw/credentials"
if [[ -f "$CREDENTIALS_DIR/health-report-path.conf" ]]; then
    HEALTH_PATH=$(cat "$CREDENTIALS_DIR/health-report-path.conf")
else
    HEALTH_PATH="${HOME}/我的云端硬盘/Health Auto Export"
fi

HEALTH_FILE="${HEALTH_PATH}/Health Data/HealthAutoExport-${DATE}.json"
WORKOUT_FILE="${HEALTH_PATH}/Workout Data/HealthAutoExport-${DATE}.json"
OUTPUT_DIR="${WORKSPACE_DIR}/reports"
mkdir -p "$OUTPUT_DIR"

OUTPUT_HTML="${OUTPUT_DIR}/${DATE}-report.html"
OUTPUT_PDF="${OUTPUT_DIR}/${DATE}-report.pdf"

echo "=========================================="
echo "生成健康报告: ${DATE}"
echo "=========================================="
echo ""

# 检查文件
if [[ ! -f "$HEALTH_FILE" ]]; then
    echo "❌ 未找到 Health 数据文件: $HEALTH_FILE"
    exit 1
fi

if [[ ! -f "$WORKOUT_FILE" ]]; then
    echo "⚠️ 未找到 Workout 数据文件"
    WORKOUT_FILE="/dev/null"
fi

echo "生成 HTML 报告..."
python3 "${SCRIPT_DIR}/generate_report_final.py" \
    --health "$HEALTH_FILE" \
    --workout "$WORKOUT_FILE" \
    --output "$OUTPUT_HTML" \
    --date "$DATE"

echo "生成 PDF..."
python3 "${SCRIPT_DIR}/generate_pdf_playwright.py" "$OUTPUT_HTML" "$OUTPUT_PDF"

echo ""
echo "=========================================="
echo "✅ 报告生成完成！"
echo "HTML: $OUTPUT_HTML"
echo "PDF:  $OUTPUT_PDF"
echo "=========================================="
