#!/bin/bash
#
# 发送健康报告邮件脚本
# 用法: ./send_health_report.sh [报告文件] [收件人邮箱]
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WORKSPACE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# 默认报告：最新生成的 PDF
DEFAULT_REPORT="$WORKSPACE_DIR/../workspace/shared/health-reports/pdf/2026-02-18-report-final.pdf"
REPORT_FILE="${1:-$DEFAULT_REPORT}"

# 默认收件人
RECIPIENT="${2:-itestmolt@outlook.com}"

# 如果没有指定报告，使用最新的
if [[ ! -f "$REPORT_FILE" ]]; then
    # 尝试查找最新报告
    REPORT_FILE=$(ls -t "$WORKSPACE_DIR/../workspace/shared/health-reports/pdf/"/*.pdf 2>/dev/null | head -n 1 || true)
    if [[ -z "$REPORT_FILE" ]]; then
        echo "❌ 没有找到 PDF 报告文件"
        echo "用法: $0 [报告文件.pdf] [收件人邮箱]"
        exit 1
    fi
fi

# 提取日期
DATE=$(basename "$REPORT_FILE" | grep -oE '[0-9]{4}-[0-9]{2}-[0-9]{2}' || date +%Y-%m-%d)

echo "📧 准备发送健康报告..."
echo "   报告文件: $REPORT_FILE"
echo "   收件人: $RECIPIENT"
echo "   日期: $DATE"

# 创建邮件内容
MAIL_CONTENT="你好，

这是你的每日健康报告 (${DATE})。

报告包含以下内容：
- 心血管指标 (心率、HRV、血氧等)
- 运动数据分析
- 睡眠质量评估
- 恢复度评分
- 个性化建议

详细的 PDF 报告请查看附件。

祝健康！

---
由 Health Agent 自动生成
发送时间: $(date '+%Y-%m-%d %H:%M')"

# 发送邮件
echo ""
echo "🔄 正在发送邮件..."

if himalaya message send --to "$RECIPIENT" \
    --subject "每日健康报告 - ${DATE}" \
    --attachment "$REPORT_FILE" \
    --body "$MAIL_CONTENT" 2>&1; then
    echo ""
    echo "✅ 邮件发送成功!"
    echo "   收件人: $RECIPIENT"
    echo "   主题: 每日健康报告 - ${DATE}"
    echo "   附件: $(basename "$REPORT_FILE")"
else
    echo ""
    echo "❌ 邮件发送失败"
    echo ""
    echo "可能的原因:"
    echo "1. 应用密码未设置"
    echo "2. 网络连接问题"
    echo "3. Outlook SMTP 限制"
    echo ""
    echo "请先运行设置脚本: bash $WORKSPACE_DIR/scripts/setup_outlook_password.sh"
    exit 1
fi
