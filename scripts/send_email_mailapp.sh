#!/bin/bash
#
# 使用 macOS Mail.app 发送健康报告
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WORKSPACE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# 默认报告文件
DEFAULT_REPORT="$WORKSPACE_DIR/../workspace/shared/health-reports/pdf/2026-02-18-report-final.pdf"
REPORT_FILE="${1:-$DEFAULT_REPORT}"

# 默认收件人
RECIPIENT="${2:-itestmolt@outlook.com}"

# 如果没有指定报告，使用最新的
if [[ ! -f "$REPORT_FILE" ]]; then
    REPORT_FILE=$(ls -t "$WORKSPACE_DIR/../workspace/shared/health-reports/pdf/"/*.pdf 2>/dev/null | head -n 1 || true)
    if [[ -z "$REPORT_FILE" ]]; then
        echo "❌ 没有找到 PDF 报告文件"
        exit 1
    fi
fi

# 检查 Mail.app 是否可用
if ! ls /Applications/Mail.app/Contents/MacOS/Mail >/dev/null 2>&1; then
    echo "❌ Mail.app 未找到"
    exit 1
fi

echo "📧 准备发送健康报告..."
echo "   报告文件: $REPORT_FILE"
echo "   收件人: $RECIPIENT"
echo ""

# 运行 AppleScript
osascript "$SCRIPT_DIR/send_email_applescript.scpt" "$REPORT_FILE" "$RECIPIENT"

echo ""
echo "✅ 邮件发送完成！"
echo "   请检查 Mail.app 的发件箱确认发送状态"
