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

if [[ ! -f "$CRED_FILE" ]]; then
  echo "Error: No credentials file. Download from Google Cloud Console."
  exit 1
fi

# Refresh token if needed
REFRESH_TOKEN=$(jq -r '.refresh_token' "$TOKEN_FILE")
CLIENT_ID=$(jq -r '.installed.client_id' "$CRED_FILE")
CLIENT_SECRET=$(jq -r '.installed.client_secret' "$CRED_FILE")

# Get new access token using refresh token
echo "Refreshing access token..."
TOKEN_RESPONSE=$(curl -s -X POST https://oauth2.googleapis.com/token \
  -d "refresh_token=${REFRESH_TOKEN}" \
  -d "client_id=${CLIENT_ID}" \
  -d "client_secret=${CLIENT_SECRET}" \
  -d "grant_type=refresh_token")

ACCESS_TOKEN=$(echo "$TOKEN_RESPONSE" | jq -r '.access_token')

if [[ "$ACCESS_TOKEN" == "null" || -z "$ACCESS_TOKEN" ]]; then
  echo "Error: Failed to refresh access token."
  echo "Response: $TOKEN_RESPONSE"
  exit 1
fi

echo "✅ Access token refreshed"

# Calculate time range (yesterday in milliseconds)
END_TIME=$(date -v-1d +%s)000
START_TIME=$(date -v-2d +%s)000

TODAY=$(date +%F)
YESTERDAY=$(date -v-1d +%F)

echo "Fetching Google Fit data for $YESTERDAY (${START_TIME} to ${END_TIME})..."

# Function to fetch aggregate data
fetch_aggregate() {
  local data_type="$1"
  local data_source="$2"
  
  local response
  response=$(curl -s -X POST "https://www.googleapis.com/fitness/v1/users/me/dataset:aggregate" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{
      \"aggregateBy\": [{
        \"dataTypeName\": \"$data_type\",
        \"dataSourceId\": \"$data_source\"
      }],
      \"bucketByTime\": { \"durationMillis\": 86400000 },
      \"startTimeMillis\": ${START_TIME},
      \"endTimeMillis\": ${END_TIME}
    }")
  
  # Check if response contains error
  if echo "$response" | jq -e '.error' >/dev/null 2>&1; then
    echo "API Error for $data_type: $(echo "$response" | jq -r '.error.message')" >&2
    echo "{}"
  else
    echo "$response"
  fi
}

# Fetch steps
echo "  📊 Fetching steps..."
STEPS_RESPONSE=$(fetch_aggregate "com.google.step_count.delta" "derived:com.google.step_count.delta:com.google.android.gms:estimated_steps")
STEPS=$(echo "$STEPS_RESPONSE" | jq -r '.bucket[0].dataset[0].point[0].value[0].intVal // 0')
echo "     Steps: $STEPS"

# Fetch calories
echo "  🔥 Fetching calories..."
CALORIES_RESPONSE=$(fetch_aggregate "com.google.calories.expended" "derived:com.google.calories.expended:com.google.android.gms:merge_calories_expended")
CALORIES=$(echo "$CALORIES_RESPONSE" | jq -r '.bucket[0].dataset[0].point[0].value[0].fpVal // 0' | cut -d. -f1)
echo "     Calories: $CALORIES"

# Fetch heart rate
echo "  ❤️  Fetching heart rate..."
HEART_RATE_RESPONSE=$(fetch_aggregate "com.google.heart_rate.bpm" "derived:com.google.heart_rate.bpm:com.google.android.gms:merge_heart_rate_bpm")
HEART_RATE_AVG=$(echo "$HEART_RATE_RESPONSE" | jq -r '.bucket[0].dataset[0].point[0].value[0].fpVal // 0' | cut -d. -f1)
echo "     Heart rate: $HEART_RATE_AVG"

# Fetch sleep
echo "  😴 Fetching sleep..."
SLEEP_RESPONSE=$(curl -s -X GET "https://www.googleapis.com/fitness/v1/users/me/sessions?startTime=${YESTERDAY}T00:00:00.000Z&endTime=${YESTERDAY}T23:59:59.999Z&activityType=72" \
  -H "Authorization: Bearer $ACCESS_TOKEN")

if echo "$SLEEP_RESPONSE" | jq -e '.error' >/dev/null 2>&1; then
  echo "     Sleep API error: $(echo "$SLEEP_RESPONSE" | jq -r '.error.message')" >&2
  SLEEP_HOURS=0
else
  SLEEP_HOURS=$(echo "$SLEEP_RESPONSE" | jq '[.session[] | ((.endTimeMillis | tonumber) - (.startTimeMillis | tonumber)) / 3600000] | add // 0' | cut -d. -f1)
fi
echo "     Sleep: ${SLEEP_HOURS}h"

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
if [[ -n $(git status --porcelain memory/shared/health-shared.md 2>/dev/null) ]]; then
  git add memory/shared/health-shared.md
  git commit -m "chore(health): sync Google Fit data for $YESTERDAY" || true
  git push || echo "⚠️  Push failed, but data is saved locally"
fi
