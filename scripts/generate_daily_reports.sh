#!/bin/bash
#
# Daily Health Report Generator
# 每天 12:30 自动生成并发送四份报告
#

set -e

WORKSPACE="/Users/jimmylu/.openclaw/workspace-health"
OUTPUT_DIR="${WORKSPACE}/shared/health-reports/upload"
LOG_FILE="${WORKSPACE}/logs/daily_reports.log"
RECIPIENT="revolutionljk@gmail.com"

# 确保日志目录存在
mkdir -p "$(dirname "$LOG_FILE")"

echo "========================================" >> "$LOG_FILE"
echo "$(date '+%Y-%m-%d %H:%M:%S') - 开始每日报告生成" >> "$LOG_FILE"

# 计算日期
YESTERDAY=$(date -v-1d '+%Y-%m-%d')
DAY_BEFORE=$(date -v-2d '+%Y-%m-%d')

echo "生成报告日期:"
echo "  昨天: $YESTERDAY"
echo "  前天: $DAY_BEFORE"
echo "  昨天: $YESTERDAY" >> "$LOG_FILE"
echo "  前天: $DAY_BEFORE" >> "$LOG_FILE"

# 检查 Apple Health 导出文件
echo ""
echo "📂 检查数据源文件..."
HEALTH_FILE_1="/Users/jimmylu/我的云端硬盘/Health Auto Export/Health Data/HealthAutoExport-${DAY_BEFORE}.json"
HEALTH_FILE_2="/Users/jimmylu/我的云端硬盘/Health Auto Export/Health Data/HealthAutoExport-${YESTERDAY}.json"

if [ ! -f "$HEALTH_FILE_1" ]; then
    echo "⚠️ 警告: 找不到 ${DAY_BEFORE} 的健康数据文件" >> "$LOG_FILE"
    echo "⚠️ 路径: $HEALTH_FILE_1"
else
    echo "✅ 找到 ${DAY_BEFORE} 数据文件"
fi

if [ ! -f "$HEALTH_FILE_2" ]; then
    echo "⚠️ 警告: 找不到 ${YESTERDAY} 的健康数据文件" >> "$LOG_FILE"
    echo "⚠️ 路径: $HEALTH_FILE_2"
else
    echo "✅ 找到 ${YESTERDAY} 数据文件"
fi

# 生成报告
echo ""
echo "📊 生成健康报告..."
cd "$WORKSPACE"

# 调用 Python 脚本生成报告
python3 scripts/generate_all_reports.py "$DAY_BEFORE" "$YESTERDAY" >> "$LOG_FILE" 2>&1

if [ $? -eq 0 ]; then
    echo "✅ 报告生成成功" >> "$LOG_FILE"
else
    echo "❌ 报告生成失败" >> "$LOG_FILE"
    exit 1
fi

# 检查生成的文件
REPORTS=(
    "${OUTPUT_DIR}/${YESTERDAY}-report-zh.pdf"
    "${OUTPUT_DIR}/${YESTERDAY}-report-en.pdf"
    "${OUTPUT_DIR}/${DAY_BEFORE}-vs-${YESTERDAY}-comparison-zh.pdf"
    "${OUTPUT_DIR}/${DAY_BEFORE}-vs-${YESTERDAY}-comparison-en.pdf"
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
bash "${WORKSPACE}/scripts/send_daily_email.sh" >> "$LOG_FILE" 2>&1

if [ $? -eq 0 ]; then
    echo "✅ 邮件发送成功" >> "$LOG_FILE"
else
    echo "⚠️ 邮件发送可能失败，请检查发件箱" >> "$LOG_FILE"
fi

# 发送 Discord 通知（可选）
echo ""
echo "💬 发送 Discord 通知..."
echo "📊 每日健康报告已生成并发送" >> "$LOG_FILE"
echo "  - 昨日报告: ${YESTERDAY}-report-zh.pdf / en.pdf" >> "$LOG_FILE"
echo "  - 对比报告: ${DAY_BEFORE}-vs-${YESTERDAY}-comparison-zh.pdf / en.pdf" >> "$LOG_FILE"
echo "  - 邮件已发送到: ${RECIPIENT}" >> "$LOG_FILE"

echo ""
echo "$(date '+%Y-%m-%d %H:%M:%S') - 每日报告流程完成" >> "$LOG_FILE"
echo "========================================" >> "$LOG_FILE"

echo ""
echo "🎉 所有任务完成！"
echo "时间: $(date '+%Y-%m-%d %H:%M:%S')"
