#!/usr/bin/env bash
#
# 每日健康分析与报告生成脚本
# 由 cron 每日 12:00 触发，生成健康分析报告
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WORKSPACE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
TOKEN_FILE="${HOME}/.openclaw/credentials/google-fit-token.json"
CRED_FILE="${HOME}/.openclaw/credentials/google-fit-credentials.json"

# 日期计算
TODAY=$(date +%F)
YESTERDAY=$(date -v-1d +%F)
WEEK_AGO=$(date -v-7d +%F)
MONTH_AGO=$(date -v-30d +%F)

echo "=== 每日健康分析 [$TODAY 12:00] ==="
echo "分析日期: $YESTERDAY"

# 检查凭证
if [[ ! -f "$TOKEN_FILE" ]] || [[ ! -f "$CRED_FILE" ]]; then
  echo "Error: Google Fit credentials not found"
  exit 1
fi

# 获取 access token
REFRESH_TOKEN=$(jq -r '.refresh_token' "$TOKEN_FILE")
CLIENT_ID=$(jq -r '.installed.client_id' "$CRED_FILE")
CLIENT_SECRET=$(jq -r '.installed.client_secret' "$CRED_FILE")

TOKEN_RESPONSE=$(curl -s -X POST https://oauth2.googleapis.com/token \
  -d "refresh_token=${REFRESH_TOKEN}" \
  -d "client_id=${CLIENT_ID}" \
  -d "client_secret=${CLIENT_SECRET}" \
  -d "grant_type=refresh_token")

ACCESS_TOKEN=$(echo "$TOKEN_RESPONSE" | jq -r '.access_token')

if [[ "$ACCESS_TOKEN" == "null" || -z "$ACCESS_TOKEN" ]]; then
  echo "Error: Failed to refresh token"
  exit 1
fi

# 时间范围（昨天全天，毫秒）
DAY_START=$(date -v-1d -v0H -v0M -v0S +%s)000
DAY_END=$(date -v-1d -v23H -v59M -v59S +%s)000

# 获取各类健康数据
fetch_metric() {
  local data_type="$1"
  local data_source="$2"
  
  curl -s -X POST "https://www.googleapis.com/fitness/v1/users/me/dataset:aggregate" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{
      \"aggregateBy\": [{\"dataTypeName\": \"$data_type\", \"dataSourceId\": \"$data_source\"}],
      \"bucketByTime\": {\"durationMillis\": 86400000},
      \"startTimeMillis\": ${DAY_START},
      \"endTimeMillis\": ${DAY_END}
    }" | jq -r '.bucket[0].dataset[0].point[0].value[0].intVal // .bucket[0].dataset[0].point[0].value[0].fpVal // 0'
}

echo "Fetching data for $YESTERDAY..."

STEPS=$(fetch_metric "com.google.step_count.delta" "derived:com.google.step_count.delta:com.google.android.gms:estimated_steps")
CALORIES=$(fetch_metric "com.google.calories.expended" "derived:com.google.calories.expended:com.google.android.gms:merge_calories_expended" | cut -d. -f1)
ACTIVE_MIN=$(fetch_metric "com.google.active_minutes" "derived:com.google.active_minutes:com.google.android.gms:merge_active_minutes")
HEART_RATE=$(fetch_metric "com.google.heart_rate.bpm" "derived:com.google.heart_rate.bpm:com.google.android.gms:merge_heart_rate_bpm" | cut -d. -f1)

# 获取睡眠数据
SLEEP_RESPONSE=$(curl -s -X GET "https://www.googleapis.com/fitness/v1/users/me/sessions?startTime=${YESTERDAY}T00:00:00.000Z&endTime=${YESTERDAY}T23:59:59.999Z&activityType=72" \
  -H "Authorization: Bearer $ACCESS_TOKEN")

SLEEP_MINUTES=$(echo "$SLEEP_RESPONSE" | jq '[.session[] | ((.endTimeMillis | tonumber) - (.startTimeMillis | tonumber)) / 60000] | add // 0' | cut -d. -f1)
SLEEP_HOURS=$(echo "$SLEEP_MINUTES / 60" | bc)

# 获取运动会话
SESSIONS_RESPONSE=$(curl -s -X GET "https://www.googleapis.com/fitness/v1/users/me/sessions?startTime=${YESTERDAY}T00:00:00.000Z&endTime=${YESTERDAY}T23:59:59.999Z" \
  -H "Authorization: Bearer $ACCESS_TOKEN")

# 生成分析报告
REPORT_FILE="$WORKSPACE_DIR/memory/health-daily/${YESTERDAY}.md"
mkdir -p "$WORKSPACE_DIR/memory/health-daily"

cat > "$REPORT_FILE" << EOF
# 每日健康报告 - ${YESTERDAY}

**分析时间**: ${TODAY} 12:00  
**数据来源**: Google Fit API

---

## 📊 昨日数据 (${YESTERDAY})

### 基础指标
| 指标 | 数值 | 目标 | 达成率 |
|------|------|------|--------|
| 步数 | ${STEPS} | 8,000 | $(echo "scale=1; $STEPS / 8000 * 100" | bc)% |
| 卡路里 | ${CALORIES} kcal | - | - |
| 活跃时间 | ${ACTIVE_MIN} min | 60 min | $(echo "scale=1; $ACTIVE_MIN / 60 * 100" | bc)% |
| 睡眠 | ${SLEEP_HOURS}h ($((${SLEEP_MINUTES}%60))m) | 7-8h | - |
| 平均心率 | ${HEART_RATE} bpm | - | - |

### 运动详情
EOF

# 添加运动会话详情
echo "$SESSIONS_RESPONSE" | jq -r '.session[] | 
  select(.activityType != 72) |
  "- **\(.name)**: \(.startTimeMillis | tonumber / 1000 | strftime("%H:%M"))-\(.endTimeMillis | tonumber / 1000 | strftime("%H:%M")) ($(echo "((.endTimeMillis | tonumber) - (.startTimeMillis | tonumber)) / 60000" | bc)分钟)"
' >> "$REPORT_FILE" 2>/dev/null || echo "- 无详细运动记录" >> "$REPORT_FILE"

cat >> "$REPORT_FILE" << EOF

---

## 🏃 运动强度评估
EOF

# 运动强度评估逻辑
if [[ $STEPS -ge 10000 ]] && echo "$SESSIONS_RESPONSE" | jq -e '.session[] | select(.activityType == 80)' >/dev/null; then
  INTENSITY="高"
  INTENSITY_SCORE=10
elif [[ $STEPS -ge 8000 ]] && [[ $ACTIVE_MIN -ge 60 ]]; then
  INTENSITY="中高"
  INTENSITY_SCORE=8
elif [[ $STEPS -ge 6000 ]]; then
  INTENSITY="中"
  INTENSITY_SCORE=6
elif [[ $STEPS -ge 4000 ]]; then
  INTENSITY="低"
  INTENSITY_SCORE=4
else
  INTENSITY="极低"
  INTENSITY_SCORE=2
fi

echo "**强度等级**: ${INTENSITY} (评分: ${INTENSITY_SCORE}/10)" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

if [[ $INTENSITY_SCORE -ge 8 ]]; then
  echo "✅ 运动量充足，保持良好状态" >> "$REPORT_FILE"
elif [[ $INTENSITY_SCORE -ge 6 ]]; then
  echo "⚡ 运动量尚可，可适当增加强度" >> "$REPORT_FILE"
else
  echo "⚠️ 运动量不足，建议增加日常活动" >> "$REPORT_FILE"
fi

cat >> "$REPORT_FILE" << EOF

---

## 💤 睡眠评估

**睡眠时长**: ${SLEEP_HOURS}小时 $((${SLEEP_MINUTES}%60))分钟

EOF

# 睡眠评估
if [[ $SLEEP_MINUTES -ge 420 ]] && [[ $SLEEP_MINUTES -le 540 ]]; then
  SLEEP_QUALITY="良好"
  SLEEP_SCORE=8
elif [[ $SLEEP_MINUTES -ge 360 ]]; then
  SLEEP_QUALITY="一般"
  SLEEP_SCORE=6
else
  SLEEP_QUALITY="不足"
  SLEEP_SCORE=4
fi

echo "**质量评估**: ${SLEEP_QUALITY} (评分: ${SLEEP_SCORE}/10)" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

if [[ $SLEEP_SCORE -ge 8 ]]; then
  echo "✅ 睡眠充足，有助于身体恢复" >> "$REPORT_FILE"
elif [[ $SLEEP_SCORE -ge 6 ]]; then
  echo "⚡ 睡眠尚可，建议今晚提早入睡" >> "$REPORT_FILE"
else
  echo "⚠️ 睡眠不足，优先级：今晚必须早睡！" >> "$REPORT_FILE"
fi

cat >> "$REPORT_FILE" << EOF

---

## 🍽️ 饮食评估

> 待补充：用户需私发昨日饮食记录

**当前状态**: 暂无饮食数据

---

## 📝 身体备注

> 待补充：皮肤状态、精力水平、情绪等其他信息

**当前状态**: 暂无备注

---

## 📈 昨日总体评分

| 维度 | 权重 | 得分 | 加权分 |
|------|------|------|--------|
| 运动 | 30% | ${INTENSITY_SCORE} | $(echo "scale=1; $INTENSITY_SCORE * 0.3" | bc) |
| 睡眠 | 30% | ${SLEEP_SCORE} | $(echo "scale=1; $SLEEP_SCORE * 0.3" | bc) |
| 饮食 | 20% | - | 待评估 |
| 整体 | 20% | - | 待评估 |

**总分**: $(echo "scale=1; ($INTENSITY_SCORE + $SLEEP_SCORE) * 0.3" | bc)/6.0 (不含饮食与整体状态)

---

## 💡 今日建议

### 运动建议
EOF

# 今日运动建议
if [[ $INTENSITY_SCORE -lt 6 ]]; then
  echo "- **目标**: 补足昨日运动量，目标 10,000+ 步" >> "$REPORT_FILE"
  echo "- **形式**: 爬楼梯 40-50 分钟" >> "$REPORT_FILE"
  echo "- **时间**: 建议午休 12:30-13:30 进行" >> "$REPORT_FILE"
elif [[ $INTENSITY_SCORE -ge 8 ]]; then
  echo "- **目标**: 维持状态，目标 8,000+ 步" >> "$REPORT_FILE"
  echo "- **形式**: 适度活动，如步行或轻度爬楼梯" >> "$REPORT_FILE"
  if echo "$SESSIONS_RESPONSE" | jq -e '.session[] | select(.activityType == 80)' >/dev/null; then
    echo "- **力量训练**: 昨天已做，今天可休息或轻量训练" >> "$REPORT_FILE"
  else
    echo "- **力量训练**: 建议今天安排 20-30 分钟" >> "$REPORT_FILE"
  fi
else
  echo "- **目标**: 8,000 步 + 60 分钟活跃" >> "$REPORT_FILE"
  echo "- **形式**: 爬楼梯 30-40 分钟" >> "$REPORT_FILE"
fi

cat >> "$REPORT_FILE" << 'ENDOFSECTION'

### 睡眠建议
ENDOFSECTION

if [[ $SLEEP_SCORE -lt 6 ]]; then
  echo "- **优先级**: 🔴 最高 - 今晚必须早睡！" >> "$REPORT_FILE"
  echo "- **目标**: 22:30 前入睡，保证 7+ 小时" >> "$REPORT_FILE"
  echo "- **建议**: 21:30 开始减少屏幕使用，22:00 准备入睡" >> "$REPORT_FILE"
else
  echo "- **目标**: 保持规律，22:30-23:00 入睡" >> "$REPORT_FILE"
  echo "- **建议**: 维持当前作息节奏" >> "$REPORT_FILE"
fi

cat >> "$REPORT_FILE" << EOF

### 饮食建议
- 待根据用户饮食记录补充

---

## 📊 趋势分析

> 注：需积累至少7天数据后生成周趋势

**数据点**: 第1天记录

EOF

echo "✅ 报告已生成: $REPORT_FILE"

# 同步到共享记忆
mkdir -p "$WORKSPACE_DIR/memory/shared"
{
  echo
  echo "## [${TODAY} 12:00] health"
  echo "- 日期: ${YESTERDAY}"
  echo "- 步数: ${STEPS}"
  echo "- 卡路里: ${CALORIES} kcal"
  echo "- 活跃时间: ${ACTIVE_MIN} min"
  echo "- 睡眠: ${SLEEP_HOURS}h"
  echo "- 平均心率: ${HEART_RATE} bpm"
  echo "- 运动强度: ${INTENSITY} (${INTENSITY_SCORE}/10)"
  echo "- 睡眠质量: ${SLEEP_QUALITY} (${SLEEP_SCORE}/10)"
  echo "- 状态: done"
} >> "$WORKSPACE_DIR/memory/shared/health-shared.md"

echo "✅ 数据已同步到 memory/shared/health-shared.md"

# Git 提交
cd "$WORKSPACE_DIR"
if [[ -n $(git status --porcelain memory/ memory/shared/ 2>/dev/null) ]]; then
  git add memory/
  git commit -m "chore(health): daily report for ${YESTERDAY}" || true
  git push || echo "⚠️ Push failed"
fi

echo "✅ 每日健康分析完成"
