#!/usr/bin/env bash
set -euo pipefail

# Google Fit Data Sync Script
# Fetches daily health metrics and appends to shared memory

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WORKSPACE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
TOKEN_FILE="${HOME}/.openclaw/credentials/google-fit-token.json"
CRED_FILE="${HOME}/.openclaw/credentials/google-fit-credentials.json"

if [[ ! -f "$TOKEN_FILE" ]]; then
  echo "Error: No token file. Run setup-google-fit-auth.sh first."
  exit 1
fi

# Refresh token if needed
REFRESH_TOKEN=$(jq -r '.refresh_token' "$TOKEN_FILE")
CLIENT_ID=$(jq -r '.installed.client_id' "$CRED_FILE")
CLIENT_SECRET=$(jq -r '.installed.client_secret' "$CRED_FILE")

# Get new access token using refresh token
TOKEN_RESPONSE=$(curl -s -X POST https://oauth2.googleapis.com/token \
  -d "refresh_token=${REFRESH_TOKEN}" \
  -d "client_id=${CLIENT_ID}" \
  -d "client_secret=${CLIENT_SECRET}" \
  -d "grant_type=refresh_token")

ACCESS_TOKEN=$(echo "$TOKEN_RESPONSE" | jq -r '.access_token')

if [[ "$ACCESS_TOKEN" == "null" || -z "$ACCESS_TOKEN" ]]; then
  echo "Error: Failed to refresh access token. Run setup again."
  exit 1
fi

# Calculate time range (yesterday 00:00 to 23:59 in nanoseconds)
END_TIME=$(date -v-1d +%s)000000000
START_TIME=$(date -v-2d +%s)000000000

TODAY=$(date +%F)
YESTERDAY=$(date -v-1d +%F)

# Function to fetch aggregate data
fetch_aggregate() {
  local data_type="$1"
  local data_source="$2"
  
  curl -s -X POST "https://www.googleapis.com/fitness/v1/users/me/dataset:aggregate" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{
      \"aggregateBy\": [{
        \"dataTypeName\": \"$data_type\",
        \"dataSourceId\": \"$data_source\"
      }],
      \"bucketByTime\": { \"durationMillis\": 86400000 },
      \"startTimeMillis\": $((${START_TIME}/1000000)),
      \"endTimeMillis\": $((${END_TIME}/1000000))
    }"
}

echo "Fetching Google Fit data for $YESTERDAY..."

# Fetch steps
STEPS_RESPONSE=$(fetch_aggregate "com.google.step_count.delta" "derived:com.google.step_count.delta:com.google.android.gms:estimated_steps")
STEPS=$(echo "$STEPS_RESPONSE" | jq -r '.bucket[0].dataset[0].point[0].value[0].intVal // 0')

# Fetch calories (optional)
CALORIES_RESPONSE=$(fetch_aggregate "com.google.calories.expended" "derived:com.google.calories.expended:com.google.android.gms:merge_calories_expended")
CALORIES=$(echo "$CALORIES_RESPONSE" | jq -r '.bucket[0].dataset[0].point[0].value[0].fpVal // 0' | cut -d. -f1)

# Fetch heart rate (optional)
HEART_RATE_RESPONSE=$(fetch_aggregate "com.google.heart_rate.bpm" "derived:com.google.heart_rate.bpm:com.google.android.gms:merge_heart_rate_bpm")
HEART_RATE_AVG=$(echo "$HEART_RATE_RESPONSE" | jq -r '.bucket[0].dataset[0].point[0].value[0].fpVal // 0' | cut -d. -f1)

# Fetch sleep (optional, from sleep segments)
SLEEP_RESPONSE=$(curl -s -X GET "https://www.googleapis.com/fitness/v1/users/me/dataSources/derived:com.google.sleep.segment:com.google.android.gms:merged/sessions?startTime=${START_TIME}000000&endTime=${END_TIME}000000" \
  -H "Authorization: Bearer $ACCESS_TOKEN")
SLEEP_HOURS=$(echo "$SLEEP_RESPONSE" | jq '[.session[] | select(.activityType == 72) | ((.endTimeMillis | tonumber) - (.startTimeMillis | tonumber)) / 3600000] | add // 0' | cut -d. -f1)

# Build structured entry for shared memory
mkdir -p "$WORKSPACE_DIR/memory/shared"

{
  echo
  echo "## [$TODAY 00:00] health"
  echo "- 日期: $YESTERDAY"
  echo "- 步数: $STEPS"
  echo "- 卡路里: ${CALORIES} kcal"
  echo "- 平均心率: ${HEART_RATE_AVG} bpm"
  echo "- 睡眠时长: ${SLEEP_HOURS} 小时"
  echo "- 状态: done"
} >> "$WORKSPACE_DIR/memory/shared/health-shared.md"

echo "✅ Data synced to memory/shared/health-shared.md"

# Git commit changes
cd "$WORKSPACE_DIR"
if ! git diff --quiet memory/shared/health-shared.md 2>/dev/null; then
  git add memory/shared/health-shared.md
  git commit -m "chore(health): sync Google Fit data for $YESTERDAY"
  git push || true
fi
