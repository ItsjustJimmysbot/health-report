# Google Fit API Integration (Preparation)

> Status: Awaiting OAuth Credentials

## Required Setup Steps

### 1) Enable Google Fit API in Cloud Console
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Select project: **my first project**
3. Navigate to: APIs & Services → Library
4. Search and enable: **Fitness API**

### 2) Create OAuth 2.0 Credentials
1. APIs & Services → Credentials
2. Click **Create Credentials** → **OAuth 2.0 Client ID**
3. Application type: **Desktop app** (or Web app if preferred)
4. Name: `openclaw-health-agent`
5. Download the JSON file (client_secret_xxx.json)

### 3) Store Credentials Securely
```bash
# Place the downloaded JSON here:
mkdir -p ~/.openclaw/credentials
cp ~/Downloads/client_secret_*.json ~/.openclaw/credentials/google-fit-credentials.json
chmod 600 ~/.openclaw/credentials/google-fit-credentials.json
```

### 4) Required Scopes for Health Agent
- `https://www.googleapis.com/auth/fitness.activity.read`
- `https://www.googleapis.com/auth/fitness.body.read`
- `https://www.googleapis.com/auth/fitness.sleep.read`
- `https://www.googleapis.com/auth/fitness.heart_rate.read`

### 5) Test Connection
After setup, run:
```bash
gcloud auth application-default login --scopes \
  https://www.googleapis.com/auth/fitness.activity.read,\
  https://www.googleapis.com/auth/fitness.body.read,\
  https://www.googleapis.com/auth/fitness.sleep.read
```

## Data Sync Plan

| Metric | Source | Frequency | Storage |
|--------|--------|-----------|---------|
| Steps | Fit | Daily | memory/shared/health-shared.md |
| Heart Rate | Fit | Daily | memory/shared/health-shared.md |
| Sleep | Fit | Daily | memory/shared/health-shared.md |
| Calories | Fit | Daily | memory/shared/health-shared.md |

## Next Steps (After Credentials Ready)
1. [ ] Download and place credentials
2. [ ] Run OAuth flow
3. [ ] Create sync script: `scripts/sync-google-fit.sh`
4. [ ] Add to HEARTBEAT.md automation
5. [ ] Test data retrieval

## Reference
- [Google Fit REST API Docs](https://developers.google.com/fit/rest/v1/reference)
- [OAuth 2.0 for Desktop Apps](https://developers.google.com/identity/protocols/oauth2/native-app)
