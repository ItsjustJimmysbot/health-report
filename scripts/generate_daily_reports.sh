#!/bin/bash
#
# Daily Health Report Generator - 中文版 only
# 每天 12:30 自动生成并发送2份中文报告
#

set -e

WORKSPACE="/Users/jimmylu/.openclaw/workspace-health"
OUTPUT_DIR="${WORKSPACE}/shared/health-reports/upload"
LOG_FILE="${WORKSPACE}/logs/daily_reports.log"
RECIPIENT="revolutionljk@gmail.com"

# 确保日志目录存在
mkdir -p "$(dirname "$LOG_FILE")"

echo "========================================" >> "$LOG_FILE"
echo "$(date '+%Y-%m-%d %H:%M:%S') - 开始每日报告生成（中文版）" >> "$LOG_FILE"

# 计算日期
YESTERDAY=$(date -v-1d '+%Y-%m-%d')
DAY_BEFORE=$(date -v-2d '+%Y-%m-%d')

echo "生成报告日期:"
echo "  昨天: $YESTERDAY"
echo "  前天: $DAY_BEFORE"
echo "  昨天: $YESTERDAY" >> "$LOG_FILE"
echo "  前天: $DAY_BEFORE" >> "$LOG_FILE"

# 执行Python脚本生成报告
echo ""
echo "📊 生成健康报告..."
cd "$WORKSPACE"

python3 scripts/generate_daily_reports.py >> "$LOG_FILE" 2>&1

if [ $? -ne 0 ]; then
    echo "❌ 报告生成失败" >> "$LOG_FILE"
    exit 1
fi

# 检查生成的文件（仅中文版）
REPORTS=(
    "${OUTPUT_DIR}/${YESTERDAY}-report-zh.pdf"
    "${OUTPUT_DIR}/${DAY_BEFORE}-vs-${YESTERDAY}-comparison-zh.pdf"
)

echo ""
echo "📄 生成文件清单:"
all_exist=true
for report in "${REPORTS[@]}"; do
    if [ -f "$report" ]; then
        file_size=$(stat -f%z "$report" 2>/dev/null || echo "0")
        echo "  ✅ $(basename "$report") (${file_size} bytes)"
        echo "     路径: $report"
    else
        echo "  ❌ $(basename "$report") - 未找到"
        all_exist=false
    fi
done

if [ "$all_exist" = false ]; then
    echo "❌ 部分报告文件缺失，停止发送邮件" >> "$LOG_FILE"
    exit 1
fi

# 发送邮件
echo ""
echo "📧 发送邮件到 ${RECIPIENT}..."

# 发送单日报告邮件
osascript -e "
tell application \"Mail\"
    set newMessage to make new outgoing message with properties {subject:\"健康日报 - ${YESTERDAY}\", content:\"今日健康报告，请查看附件。\", visible:false}
    tell newMessage
        make new to recipient at end of to recipients with properties {address:\"${RECIPIENT}\"}
        tell content
            make new attachment with properties {file name:\"${OUTPUT_DIR}/${YESTERDAY}-report-zh.pdf\"} at after last paragraph
        end tell
        send
    end tell
end tell
" 2>/dev/null || echo "⚠️ 单日报告邮件发送失败"

sleep 2

# 发送对比报告邮件
osascript -e "
tell application \"Mail\"
    set newMessage to make new outgoing message with properties {subject:\"健康对比报告 - ${DAY_BEFORE} vs ${YESTERDAY}\", content:\"两日健康对比报告，请查看附件。\", visible:false}
    tell newMessage
        make new to recipient at end of to recipients with properties {address:\"${RECIPIENT}\"}
        tell content
            make new attachment with properties {file name:\"${OUTPUT_DIR}/${DAY_BEFORE}-vs-${YESTERDAY}-comparison-zh.pdf\"} at after last paragraph
        end tell
        send
    end tell
end tell
" 2>/dev/null || echo "⚠️ 对比报告邮件发送失败"

echo "✅ 邮件发送完成" >> "$LOG_FILE"

# Discord通知
bash "${WORKSPACE}/scripts/notify_discord.sh" "$YESTERDAY" 2>/dev/null || echo "⚠️ Discord通知失败"

echo ""
echo "$(date '+%Y-%m-%d %H:%M:%S') - 每日报告流程完成" >> "$LOG_FILE"
echo "========================================" >> "$LOG_FILE"

echo ""
echo "🎉 所有任务完成！"
echo "时间: $(date '+%Y-%m-%d %H:%M:%S')"
