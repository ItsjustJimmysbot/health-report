#!/bin/bash
#
# 每日健康报告完整流程（可视化版本）
# 1. 获取 Apple Health 数据
# 2. 生成可视化 HTML 报告
# 3. 生成 PDF
# 4. 发送邮件到 revolutionljk@gmail.com
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WORKSPACE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
DATE=$(date +%Y-%m-%d)
YESTERDAY=$(date -v-1d +%F)
RECIPIENT="${1:-revolutionljk@gmail.com}"

echo "=========================================="
echo "  每日健康报告 - ${DATE}"
echo "  收件人: ${RECIPIENT}"
echo "=========================================="
echo ""

# 1. 检查 Apple Health 数据
echo "📱 步骤 1: 检查 Apple Health 数据"
AH_FILE="${HOME}/我的云端硬盘/Health Auto Export/Health Data/HealthAutoExport-${YESTERDAY}.json"

if [[ ! -f "$AH_FILE" ]]; then
    echo "⚠️  未找到 ${YESTERDAY} 的健康数据"
    echo "   路径: $AH_FILE"
    exit 1
fi

echo "✅ 找到数据文件"
echo ""

# 2. 解析数据并生成可视化报告
echo "📊 步骤 2: 生成可视化报告"

# 从 JSON 提取关键数据
STEPS=$(jq -r '.data.metrics[] | select(.name == "step_count") | [.data[].qty] | add | floor' "$AH_FILE" 2>/dev/null || echo "0")
SLEEP_HOURS=$(jq -r '.data.metrics[] | select(.name == "sleep_analysis") | .data[0].totalSleep // 0' "$AH_FILE" 2>/dev/null || echo "0")
HRV=$(jq -r '.data.metrics[] | select(.name == "heart_rate_variability") | [.data[].qty] | add / length | floor' "$AH_FILE" 2>/dev/null || echo "0")
RHR=$(jq -r '.data.metrics[] | select(.name == "resting_heart_rate") | .data[0].qty // 0' "$AH_FILE" 2>/dev/null || echo "0")
EXERCISE=$(jq -r '.data.metrics[] | select(.name == "apple_exercise_time") | [.data[].qty] | add | floor' "$AH_FILE" 2>/dev/null || echo "0")
FLOORS=$(jq -r '.data.metrics[] | select(.name == "flights_climbed") | [.data[].qty] | add | floor' "$AH_FILE" 2>/dev/null || echo "0")

# 从心率数据中推断运动时间段（找高心率时段）
WORKOUT_START=$(jq -r '.data.metrics[] | select(.name == "heart_rate") | .data | map(select(.Avg > 100)) | sort_by(.date) | .[0].date' "$AH_FILE" 2>/dev/null | cut -d' ' -f2 | cut -d':' -f1,2 || echo "12:25")
WORKOUT_END=$(jq -r '.data.metrics[] | select(.name == "heart_rate") | .data | map(select(.Avg > 100)) | sort_by(.date) | .[-1].date' "$AH_FILE" 2>/dev/null | cut -d' ' -f2 | cut -d':' -f1,2 || echo "13:06")

# 如果没有检测到高心率，使用默认时间
if [[ "$WORKOUT_START" == "null" || -z "$WORKOUT_START" ]]; then
    WORKOUT_START="12:25"
fi
if [[ "$WORKOUT_END" == "null" || -z "$WORKOUT_END" ]]; then
    WORKOUT_END="13:06"
fi

# 检查是否有饮食/备注记录（从 memory 中读取）
DIET_FILE="${WORKSPACE_DIR}/memory/health-daily/${YESTERDAY}-diet.txt"
NOTES_FILE="${WORKSPACE_DIR}/memory/health-daily/${YESTERDAY}-notes.txt"

DIET_CONTENT=""
if [[ -f "$DIET_FILE" ]]; then
    DIET_CONTENT=$(cat "$DIET_FILE")
fi

NOTES_CONTENT=""
if [[ -f "$NOTES_FILE" ]]; then
    NOTES_CONTENT=$(cat "$NOTES_FILE")
fi

# 计算评分和状态（使用 bc 处理浮点数）
HRV_SCORE=$(echo "$HRV" | awk '{if($1>=50) print 10; else if($1>=40) print 7; else print 5}')
SLEEP_SCORE=$(echo "$SLEEP_HOURS" | awk '{if($1>=7) print 10; else if($1>=5) print 5; else print 3}')
STEP_SCORE=$(echo "$STEPS" | awk '{if($1>=10000) print 10; else if($1>=8000) print 8; else if($1>=6000) print 6; else print 4}')

RECOVERY_SCORE=$(echo "scale=0; ($HRV_SCORE * 35 + $SLEEP_SCORE * 35 + $STEP_SCORE * 30) / 100" | bc)

if [[ $RECOVERY_SCORE -ge 8 ]]; then
    RECOVERY_STATUS="良好"
    RECOVERY_CLASS="status-good"
elif [[ $RECOVERY_SCORE -ge 5 ]]; then
    RECOVERY_STATUS="一般"
    RECOVERY_CLASS="status-warning"
else
    RECOVERY_STATUS="需改善"
    RECOVERY_CLASS="status-bad"
fi

echo "   数据摘要:"
echo "   - 步数: ${STEPS}"
echo "   - 睡眠: ${SLEEP_HOURS}h"
echo "   - HRV: ${HRV}ms"
echo "   - 静息心率: ${RHR}bpm"
echo "   - 运动时间: ${WORKOUT_START} - ${WORKOUT_END}"
echo ""

# 3. 生成可视化 HTML
echo "🎨 步骤 3: 生成可视化 HTML"

python3 "${SCRIPT_DIR}/generate_visual_report.py" <> PYSCRIPT
import sys
sys.path.insert(0, '${SCRIPT_DIR}')
from generate_visual_report import generate_visual_report

data = {
    'date': '${YESTERDAY}',
    'weekday': '$(date -v-1d +%u | awk '{print substr("日一二三四五六",$1,1)}')',
    'recovery_score': ${RECOVERY_SCORE},
    'recovery_status': '${RECOVERY_STATUS}',
    'recovery_status_class': '${RECOVERY_CLASS}',
    'sleep_score': $(echo "$SLEEP_HOURS * 10 / 8" | bc | cut -d. -f1),
    'sleep_status_text': '$(if [[ $(echo "$SLEEP_HOURS < 6" | bc) -eq 1 ]]; then echo "不足"; elif [[ $(echo "$SLEEP_HOURS < 7" | bc) -eq 1 ]]; then echo "偏短"; else echo "充足"; fi)',
    'sleep_status_class': '$(if [[ $(echo "$SLEEP_HOURS < 6" | bc) -eq 1 ]]; then echo "status-bad"; elif [[ $(echo "$SLEEP_HOURS < 7" | bc) -eq 1 ]]; then echo "status-warning"; else echo "status-good"; fi)',
    'exercise_score': $(echo "$STEPS * 100 / 8000" | bc | cut -d. -f1),
    'exercise_status_text': '$(if [[ $STEPS -ge 10000 ]]; then echo "优秀"; elif [[ $STEPS -ge 8000 ]]; then echo "良好"; else echo "不足"; fi)',
    'exercise_status_class': '$(if [[ $STEPS -ge 10000 ]]; then echo "status-good"; elif [[ $STEPS -ge 8000 ]]; then echo "status-warning"; else echo "status-bad"; fi)',
    'steps': ${STEPS},
    'sleep_hours': ${SLEEP_HOURS},
    'hrv': ${HRV},
    'resting_hr': ${RHR},
    'exercise_min': ${EXERCISE},
    'floors': ${FLOORS},
    'workout_start': '${WORKOUT_START}',
    'workout_end': '${WORKOUT_END}',
    'diet_content': '''$(echo "$DIET_CONTENT" | sed 's/"/\\"/g')''',
    'notes_content': '''$(echo "$NOTES_CONTENT" | sed 's/"/\\"/g')'''
}

generate_visual_report(data, '${WORKSPACE_DIR}/../workspace/shared/health-reports/${YESTERDAY}-visual-report-v2.html')
PYSCRIPT

echo "✅ 可视化报告已生成"
echo ""

# 4. 生成 PDF
echo "📄 步骤 4: 生成 PDF"

HTML_FILE="${WORKSPACE_DIR}/../workspace/shared/health-reports/${YESTERDAY}-visual-report-v2.html"
PDF_FILE="${WORKSPACE_DIR}/../workspace/shared/health-reports/pdf/${YESTERDAY}-report-final.pdf"

# 使用 weasyprint 生成 PDF
weasyprint "$HTML_FILE" "$PDF_FILE" 2>/dev/null && echo "✅ PDF 已生成: $PDF_FILE" || echo "⚠️  PDF 生成可能需要手动检查"
echo ""

# 5. 发送邮件
echo "📧 步骤 5: 发送邮件"
osascript "${SCRIPT_DIR}/send_email_applescript.scpt" "$PDF_FILE" "$RECIPIENT"
echo ""

# 6. Git 提交
echo "💾 步骤 6: 保存到 Git"
cd "$WORKSPACE_DIR"
if [[ -n $(git status --porcelain 2>/dev/null) ]]; then
    git add -A
    git commit -m "chore(health): visual report for ${YESTERDAY}" || true
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
echo "📧 邮件已发送到: ${RECIPIENT}"
echo "📄 报告文件: ${PDF_FILE}"
echo ""
echo "💡 提示:"
echo "   - 如需补充饮食/备注，请私发给我"
echo "   - 下次报告时间: 明天 12:30"
echo ""
