#!/usr/bin/env bash
#
# 每日健康分析与报告生成脚本
# 由 cron 每日 12:00 触发，生成健康分析报告
# 数据源: Google Fit + Apple Health (via Health Auto Export)
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WORKSPACE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
TOKEN_FILE="${HOME}/.openclaw/credentials/google-fit-token.json"
CRED_FILE="${HOME}/.openclaw/credentials/google-fit-credentials.json"
APPLE_HEALTH_DIR="${HOME}/Desktop/health"

# 日期计算
TODAY=$(date +%F)
YESTERDAY=$(date -v-1d +%F)
WEEK_AGO=$(date -v-7d +%F)
MONTH_AGO=$(date -v-30d +%F)

echo "=== 每日健康分析 [$TODAY 12:00] ==="
echo "分析日期: $YESTERDAY"
echo ""

# ============================================
# 读取 Apple Health 数据 (Health Auto Export)
# ============================================
echo "📱 Checking Apple Health data..."

APPLE_HEALTH_FILE="${APPLE_HEALTH_DIR}/health-${YESTERDAY}.json"
APPLE_HEALTH_LATEST="${APPLE_HEALTH_DIR}/latest.json"

HRV_AVG="N/A"
HRV_SCORE=0
RESTING_HR="N/A"
RESPIRATORY_RATE="N/A"
SPO2_AVG="N/A"
APPLE_SLEEP_MINUTES=0
APPLE_SLEEP_DEEP=0
APPLE_SLEEP_REM=0

if [[ -f "$APPLE_HEALTH_FILE" ]]; then
  echo "✅ Found Apple Health data: health-${YESTERDAY}.json"
  AH_FILE="$APPLE_HEALTH_FILE"
elif [[ -f "$APPLE_HEALTH_LATEST" ]]; then
  echo "⚠️ Using latest.json (may not be yesterday's data)"
  AH_FILE="$APPLE_HEALTH_LATEST"
else
  echo "⚠️ No Apple Health data found"
  AH_FILE=""
fi

if [[ -n "$AH_FILE" && -f "$AH_FILE" ]]; then
  # 读取 HRV
  HRV_AVG=$(jq -r '.metrics.heartRateVariability.avg // "N/A"' "$AH_FILE" 2>/dev/null)
  HRV_MIN=$(jq -r '.metrics.heartRateVariability.min // "N/A"' "$AH_FILE" 2>/dev/null)
  HRV_MAX=$(jq -r '.metrics.heartRateVariability.max // "N/A"' "$AH_FILE" 2>/dev/null)
  
  # 读取静息心率
  RESTING_HR=$(jq -r '.metrics.restingHeartRate.value // "N/A"' "$AH_FILE" 2>/dev/null)
  
  # 读取呼吸频率
  RESPIRATORY_RATE=$(jq -r '.metrics.respiratoryRate.avg // "N/A"' "$AH_FILE" 2>/dev/null)
  
  # 读取血氧
  SPO2_AVG=$(jq -r '.metrics.oxygenSaturation.avg // "N/A"' "$AH_FILE" 2>/dev/null)
  
  # 读取 Apple Health 睡眠数据
  APPLE_SLEEP_MINUTES=$(jq -r '.metrics.sleep.totalMinutes // 0' "$AH_FILE" 2>/dev/null)
  APPLE_SLEEP_DEEP=$(jq -r '.metrics.sleep.deepMinutes // 0' "$AH_FILE" 2>/dev/null)
  APPLE_SLEEP_REM=$(jq -r '.metrics.sleep.remMinutes // 0' "$AH_FILE" 2>/dev/null)
  APPLE_SLEEP_EFFICIENCY=$(jq -r '.metrics.sleep.efficiency // 0' "$AH_FILE" 2>/dev/null)
  
  echo "  HRV: ${HRV_AVG}ms | RHR: ${RESTING_HR}bpm | RR: ${RESPIRATORY_RATE}/min | SpO2: ${SPO2_AVG}%"
  echo "  Sleep: ${APPLE_SLEEP_MINUTES}min (Deep: ${APPLE_SLEEP_DEEP}, REM: ${APPLE_SLEEP_REM})"
fi

echo ""

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

# 计算 Recovery Score (基于可用数据)
RECOVERY_SCORE=0
RECOVERY_STATUS="未知"
RECOVERY_COLOR="⚪"

if [[ "$HRV_AVG" != "N/A" && -n "$HRV_AVG" ]]; then
  # HRV 评估 (简化版，正常范围 40-60ms)
  HRV_VAL=$(echo "$HRV_AVG" | cut -d. -f1)
  if [[ $HRV_VAL -ge 50 ]]; then
    HRV_SCORE=10
  elif [[ $HRV_VAL -ge 40 ]]; then
    HRV_SCORE=7
  elif [[ $HRV_VAL -ge 30 ]]; then
    HRV_SCORE=5
  else
    HRV_SCORE=3
  fi
  
  # 综合 Recovery Score (简化算法)
  RECOVERY_SCORE=$(( (SLEEP_SCORE * 40 + HRV_SCORE * 35 + INTENSITY_SCORE * 25) / 100 ))
  
  if [[ $RECOVERY_SCORE -ge 7 ]]; then
    RECOVERY_STATUS="良好"
    RECOVERY_COLOR="🟢"
  elif [[ $RECOVERY_SCORE -ge 4 ]]; then
    RECOVERY_STATUS="一般"
    RECOVERY_COLOR="🟡"
  else
    RECOVERY_STATUS="较差"
    RECOVERY_COLOR="🔴"
  fi
else
  # 没有 HRV 数据时，使用简化 Recovery Score
  RECOVERY_SCORE=$(( (SLEEP_SCORE * 50 + INTENSITY_SCORE * 50) / 100 ))
  if [[ $RECOVERY_SCORE -ge 7 ]]; then
    RECOVERY_STATUS="良好"
    RECOVERY_COLOR="🟢"
  elif [[ $RECOVERY_SCORE -ge 4 ]]; then
    RECOVERY_STATUS="一般"
    RECOVERY_COLOR="🟡"
  else
    RECOVERY_STATUS="较差"
    RECOVERY_COLOR="🔴"
  fi
fi

cat > "$REPORT_FILE" << EOF
# 每日健康报告 - ${YESTERDAY}

**分析时间**: ${TODAY} 12:00  
**数据来源**: Google Fit API + Apple Health (Watch)

---

## 🔋 今日状态速览 (Recovery Score)

\`\`\`
┌────────────────────────────────────────┐
│                                        │
│      ${RECOVERY_COLOR} Recovery Score                    │
│                                        │
│         ┌─────────┐                    │
│         │   ${RECOVERY_SCORE}0%   │  ← ${RECOVERY_STATUS}        │
│         │  ${RECOVERY_STATUS}  │                    │
│         └─────────┘                    │
│                                        │
│  ${RECOVERY_COLOR} ${RECOVERY_STATUS}区域: 
EOF

if [[ $RECOVERY_SCORE -ge 7 ]]; then
  echo "可承受高强度训练" >> "$REPORT_FILE"
elif [[ $RECOVERY_SCORE -ge 4 ]]; then
  echo "建议降低训练强度，专注恢复" >> "$REPORT_FILE"
else
  echo "优先休息，避免高强度训练" >> "$REPORT_FILE"
fi

cat >> "$REPORT_FILE" << EOF
│                                        │
└────────────────────────────────────────┘
\`\`\`

### 昨日核心指标
| 指标 | 数值 | 目标 | 状态 |
|------|------|------|------|
| 步数 | ${STEPS} | 8,000 | $(if [[ $STEPS -ge 8000 ]]; then echo "✅"; else echo "⚠️"; fi) |
| 活跃时间 | ${ACTIVE_MIN} min | 60 min | $(if [[ $ACTIVE_MIN -ge 60 ]]; then echo "✅"; else echo "⚠️"; fi) |
| 睡眠 | ${SLEEP_HOURS}h ($((${SLEEP_MINUTES}%60))m) | 7-8h | $(if [[ $SLEEP_MINUTES -ge 420 ]]; then echo "✅"; else echo "🔴"; fi) |
| 平均心率 | ${HEART_RATE} bpm | - | - |
EOF

# 添加 Apple Health 数据（如果有）
if [[ "$HRV_AVG" != "N/A" ]]; then
cat >> "$REPORT_FILE" << EOF
| HRV | ${HRV_AVG} ms | 40-60 | $(if [[ $(echo "$HRV_AVG >= 40" | bc) -eq 1 && $(echo "$HRV_AVG <= 60" | bc) -eq 1 ]]; then echo "✅"; else echo "⚠️"; fi) |
| 静息心率 | ${RESTING_HR} bpm | 55-70 | $(if [[ "$RESTING_HR" != "N/A" && $(echo "$RESTING_HR >= 55" | bc) -eq 1 && $(echo "$RESTING_HR <= 70" | bc) -eq 1 ]]; then echo "✅"; elif [[ "$RESTING_HR" != "N/A" && $(echo "$RESTING_HR < 75" | bc) -eq 1 ]]; then echo "⚠️"; else echo "🔴"; fi) |
EOF
fi

if [[ "$RESPIRATORY_RATE" != "N/A" ]]; then
cat >> "$REPORT_FILE" << EOF
| 呼吸频率 | ${RESPIRATORY_RATE} /min | 12-20 | $(if [[ $(echo "$RESPIRATORY_RATE >= 12" | bc) -eq 1 && $(echo "$RESPIRATORY_RATE <= 20" | bc) -eq 1 ]]; then echo "✅"; else echo "⚠️"; fi) |
EOF
fi

if [[ "$SPO2_AVG" != "N/A" ]]; then
cat >> "$REPORT_FILE" << EOF
| 血氧 | ${SPO2_AVG}% | 95-100% | $(if [[ $(echo "$SPO2_AVG >= 95" | bc) -eq 1 ]]; then echo "✅"; else echo "🔴"; fi) |
EOF
fi

cat >> "$REPORT_FILE" << EOF

---

## 📊 详细数据分析

### 🏃 运动表现
| 指标 | 数值 | 评估 |
|------|------|------|
| 步数 | ${STEPS} | 目标完成 $(echo "scale=1; $STEPS / 8000 * 100" | bc)% |
| 卡路里 | ${CALORIES} kcal | - |
| 活跃时间 | ${ACTIVE_MIN} min | $(if [[ $ACTIVE_MIN -ge 60 ]]; then echo "✅ 超额完成"; else echo "待提升"; fi) |
| 平均心率 | ${HEART_RATE} bpm | $(if [[ $HEART_RATE -gt 0 && $HEART_RATE -lt 100 ]]; then echo "静息心率正常"; else echo "-"; fi) |

**运动强度**: ${INTENSITY} (评分: ${INTENSITY_SCORE}/10)

EOF

# 添加运动会话详情
cat >> "$REPORT_FILE" << EOF

**运动详情**:
EOF
echo "$SESSIONS_RESPONSE" | jq -r '.session[] | 
  select(.activityType != 72) |
  "- **\(.name)**: \(.startTimeMillis | tonumber / 1000 | strftime("%H:%M"))-\(.endTimeMillis | tonumber / 1000 | strftime("%H:%M"))"' >> "$REPORT_FILE" 2>/dev/null || echo "- 无详细运动记录" >> "$REPORT_FILE"

cat >> "$REPORT_FILE" << EOF

**强度解读**:
EOF

if [[ $INTENSITY_SCORE -ge 8 ]]; then
  echo "✅ 运动量充足，身体适应性良好。继续保持当前节奏。" >> "$REPORT_FILE"
elif [[ $INTENSITY_SCORE -ge 6 ]]; then
  echo "⚡ 运动量尚可，但距离目标仍有提升空间。建议增加日常步行或轻度活动。" >> "$REPORT_FILE"
else
  echo "⚠️ 运动量不足，长期可能影响心肺功能和代谢健康。建议从每天增加 2,000 步开始。" >> "$REPORT_FILE"
fi

cat >> "$REPORT_FILE" << EOF

---

### 💤 睡眠分析

EOF

# 如果有 Apple Health 详细睡眠数据，展示睡眠架构
if [[ $APPLE_SLEEP_MINUTES -gt 0 ]]; then
  APPLE_SLEEP_HOURS=$((APPLE_SLEEP_MINUTES / 60))
  APPLE_SLEEP_MINS=$((APPLE_SLEEP_MINUTES % 60))
  DEEP_PCT=$((APPLE_SLEEP_DEEP * 100 / APPLE_SLEEP_MINUTES))
  REM_PCT=$((APPLE_SLEEP_REM * 100 / APPLE_SLEEP_MINUTES))
  
cat >> "$REPORT_FILE" << EOF
**睡眠架构 (Apple Watch)**:
\`\`\`
总睡眠: ${APPLE_SLEEP_HOURS}h ${APPLE_SLEEP_MINS}m

深度睡眠  🟣 $(printf '%*s' $((DEEP_PCT/5)) '' | tr ' ' '█')$(printf '%*s' $((20-DEEP_PCT/5)) '' | tr ' ' '░')  ${DEEP_PCT}% (目标 15-20%)
REM 睡眠  🟢 $(printf '%*s' $((REM_PCT/5)) '' | tr ' ' '█')$(printf '%*s' $((20-REM_PCT/5)) '' | tr ' ' '░')  ${REM_PCT}% (目标 20-25%)
其他睡眠  🔵 (浅睡 + 清醒)

效率: ${APPLE_SLEEP_EFFICIENCY}%
\`\`\`

EOF
else
  # 使用 Google Fit 的简化睡眠数据
cat >> "$REPORT_FILE" << EOF
**睡眠时长**: ${SLEEP_HOURS}小时 $((${SLEEP_MINUTES}%60))分钟

EOF
fi

cat >> "$REPORT_FILE" << EOF
**质量评估**: ${SLEEP_QUALITY} (评分: ${SLEEP_SCORE}/10)

EOF

if [[ $SLEEP_SCORE -ge 8 ]]; then
  echo "✅ 睡眠充足且质量良好，有助于身体恢复和认知功能维持。" >> "$REPORT_FILE"
elif [[ $SLEEP_SCORE -ge 6 ]]; then
  echo "⚡ 睡眠尚可，但距离理想状态有差距。建议今晚提前 30 分钟准备入睡。" >> "$REPORT_FILE"
else
  echo "⚠️ **睡眠严重不足！** 这会影响你的恢复、情绪和专注力。今晚优先级：必须早睡！" >> "$REPORT_FILE"
fi

cat >> "$REPORT_FILE" << EOF

---

### ❤️ 恢复度分析 (Recovery)

EOF

if [[ "$HRV_AVG" != "N/A" ]]; then
cat >> "$REPORT_FILE" << EOF
**心率变异性 (HRV)**:
- 平均值: ${HRV_AVG} ms
- 范围: ${HRV_MIN} - ${HRV_MAX} ms
- 评估: $(if [[ $(echo "$HRV_AVG >= 50" | bc) -eq 1 ]]; then echo "✅ 良好 - 自主神经系统恢复良好"; elif [[ $(echo "$HRV_AVG >= 40" | bc) -eq 1 ]]; then echo "⚡ 一般 - 恢复中，注意休息"; else echo "🔴 偏低 - 身体压力较大"; fi)

HRV 反映自主神经系统的恢复状态。较高的 HRV 通常意味着更好的恢复和压力适应能力。

EOF
fi

if [[ "$RESTING_HR" != "N/A" ]]; then
cat >> "$REPORT_FILE" << EOF
**静息心率**: ${RESTING_HR} bpm
- 基线参考: 65 bpm
- 趋势: $(if [[ $(echo "$RESTING_HR <= 65" | bc) -eq 1 ]]; then echo "✅ 低于/等于基线，恢复良好"; elif [[ $(echo "$RESTING_HR <= 70" | bc) -eq 1 ]]; then echo "⚡ 略高于基线，注意恢复"; else echo "🔴 明显高于基线，优先休息"; fi)

EOF
fi

if [[ "$RESPIRATORY_RATE" != "N/A" ]]; then
cat >> "$REPORT_FILE" << EOF
**呼吸频率**: ${RESPIRATORY_RATE} 次/分钟
- 正常范围: 12-20 次/分钟
- 评估: $(if [[ $(echo "$RESPIRATORY_RATE >= 12 && $RESPIRATORY_RATE <= 20" | bc) -eq 1 ]]; then echo "✅ 正常"; else echo "⚠️ 需关注"; fi)

EOF
fi

if [[ "$SPO2_AVG" != "N/A" ]]; then
cat >> "$REPORT_FILE" << EOF
**血氧饱和度**: ${SPO2_AVG}%
- 正常范围: 95-100%
- 评估: $(if [[ $(echo "$SPO2_AVG >= 95" | bc) -eq 1 ]]; then echo "✅ 正常"; else echo "🔴 偏低 - 如持续请就医"; fi)

EOF
fi

cat >> "$REPORT_FILE" << EOF
---
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
  echo "- Recovery Score: ${RECOVERY_SCORE}/10 (${RECOVERY_STATUS})"
  echo "- 步数: ${STEPS}"
  echo "- 卡路里: ${CALORIES} kcal"
  echo "- 活跃时间: ${ACTIVE_MIN} min"
  echo "- 睡眠: ${SLEEP_HOURS}h ($((${SLEEP_MINUTES}%60))m)"
  echo "- 平均心率: ${HEART_RATE} bpm"
  echo "- 运动强度: ${INTENSITY} (${INTENSITY_SCORE}/10)"
  echo "- 睡眠质量: ${SLEEP_QUALITY} (${SLEEP_SCORE}/10)"
  if [[ "$HRV_AVG" != "N/A" ]]; then
    echo "- HRV: ${HRV_AVG}ms"
  fi
  if [[ "$RESTING_HR" != "N/A" ]]; then
    echo "- 静息心率: ${RESTING_HR}bpm"
  fi
  if [[ "$RESPIRATORY_RATE" != "N/A" ]]; then
    echo "- 呼吸频率: ${RESPIRATORY_RATE}/min"
  fi
  if [[ "$SPO2_AVG" != "N/A" ]]; then
    echo "- 血氧: ${SPO2_AVG}%"
  fi
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
