#!/bin/bash
#
# 记录用户私发的饮食/备注信息
# 用法: record_health_note.sh [diet|notes] "内容"
#

set -euo pipefail

TYPE="${1:-}"
CONTENT="${2:-}"
DATE=$(date +%Y-%m-%d)
WORKSPACE_DIR="${HOME}/.openclaw/workspace-health"
NOTES_DIR="${WORKSPACE_DIR}/memory/health-daily"

mkdir -p "$NOTES_DIR"

if [[ -z "$TYPE" || -z "$CONTENT" ]]; then
    echo "用法: $0 [diet|notes] '内容'"
    echo ""
    echo "示例:"
    echo "  $0 diet '早餐: 燕麦粥+鸡蛋'"
    echo "  $0 notes '今天精力很好，皮肤状态不错'"
    exit 1
fi

FILE="${NOTES_DIR}/${DATE}-${TYPE}.txt"

# 追加内容，带时间戳
TIMESTAMP=$(date '+%H:%M')
echo "[${TIMESTAMP}] ${CONTENT}" >> "$FILE"

echo "✅ 已记录到 ${DATE}-${TYPE}.txt"
echo "   内容: ${CONTENT}"
