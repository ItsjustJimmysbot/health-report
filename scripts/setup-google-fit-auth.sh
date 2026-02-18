#!/usr/bin/env bash
set -euo pipefail

# Google Fit OAuth Flow Helper
# This script guides through the OAuth authorization flow

echo "=== Google Fit OAuth Setup ==="
echo

CRED_FILE="${HOME}/.openclaw/credentials/google-fit-credentials.json"
TOKEN_FILE="${HOME}/.openclaw/credentials/google-fit-token.json"

if [[ ! -f "$CRED_FILE" ]]; then
  echo "Error: Credentials file not found at $CRED_FILE"
  exit 1
fi

CLIENT_ID=$(jq -r '.installed.client_id' "$CRED_FILE")
CLIENT_SECRET=$(jq -r '.installed.client_secret' "$CRED_FILE")

# Note: For desktop apps, we use the redirect_uri from the credentials
REDIRECT_URI=$(jq -r '.installed.redirect_uris[0]' "$CRED_FILE")

SCOPES="https://www.googleapis.com/auth/fitness.activity.read https://www.googleapis.com/auth/fitness.body.read https://www.googleapis.com/auth/fitness.sleep.read https://www.googleapis.com/auth/fitness.heart_rate.read"

# Build authorization URL
AUTH_URL="https://accounts.google.com/o/oauth2/v2/auth?client_id=${CLIENT_ID}&redirect_uri=${REDIRECT_URI}&response_type=code&scope=${SCOPES// /%20}&access_type=offline&prompt=consent"

echo "1. Opening browser for authorization..."
echo "   URL: $AUTH_URL"
echo

# Try to open browser
if command -v open &> /dev/null; then
  open "$AUTH_URL"
elif command -v xdg-open &> /dev/null; then
  xdg-open "$AUTH_URL"
else
  echo "Please manually open this URL in your browser:"
  echo "$AUTH_URL"
fi

echo "2. After authorizing, you'll get a code (or be redirected to localhost with code=XXX)"
echo "   Paste the authorization code here:"
read -r AUTH_CODE

# Exchange code for token
echo "3. Exchanging code for access token..."

RESPONSE=$(curl -s -X POST https://oauth2.googleapis.com/token \
  -d "code=${AUTH_CODE}" \
  -d "client_id=${CLIENT_ID}" \
  -d "client_secret=${CLIENT_SECRET}" \
  -d "redirect_uri=${REDIRECT_URI}" \
  -d "grant_type=authorization_code")

if echo "$RESPONSE" | jq -e '.access_token' > /dev/null 2>&1; then
  echo "$RESPONSE" | jq '.' > "$TOKEN_FILE"
  chmod 600 "$TOKEN_FILE"
  echo
  echo "✅ Token saved to: $TOKEN_FILE"
  echo "   Access token expires in: $(echo "$RESPONSE" | jq -r '.expires_in') seconds"
  if echo "$RESPONSE" | jq -e '.refresh_token' > /dev/null 2>&1; then
    echo "   Refresh token: ✅ (will auto-renew)"
  fi
else
  echo "❌ Error getting token:"
  echo "$RESPONSE" | jq '.'
  exit 1
fi
