# Google Fit API Integration

> Status: **Ready for OAuth Authorization**

## Quick Start (Now Simplified)

### 1) Run Authorization Setup
```bash
cd ~/.openclaw/workspace-health
bash scripts/setup-google-fit-auth.sh
```
This will:
- Open browser for Google authorization
- Guide you to paste the auth code
- Save access token to `~/.openclaw/credentials/google-fit-token.json`

### 2) Test Data Sync
```bash
bash scripts/sync-google-fit.sh
```

### 3) Enable Automatic Sync
Already configured in `HEARTBEAT.md`. Each heartbeat will:
- Refresh access token
- Fetch yesterday's health data
- Append to `memory/shared/health-shared.md`
- Auto-commit and push

---

## Manual Steps (If Script Fails)

### Required Scopes
The scripts request these permissions:
- `fitness.activity.read` (步数)
- `fitness.body.read` (卡路里)
- `fitness.sleep.read` (睡眠)
- `fitness.heart_rate.read` (心率)

### Credentials Location
- Downloaded: `~/Downloads/client_secret_*.json`
- Secured at: `~/.openclaw/credentials/google-fit-credentials.json`
- Token file: `~/.openclaw/credentials/google-fit-token.json` (auto-created)

---

## Data Sync Plan

| 指标 | 来源 | 频率 | 存储位置 |
|------|------|------|----------|
| 步数 | Google Fit | 每日 | `memory/shared/health-shared.md` |
| 卡路里 | Google Fit | 每日 | `memory/shared/health-shared.md` |
| 心率 | Google Fit | 每日 | `memory/shared/health-shared.md` |
| 睡眠 | Google Fit | 每日 | `memory/shared/health-shared.md` |

## Troubleshooting

**"No token file" error**
→ 先运行 `setup-google-fit-auth.sh` 完成授权

**Token expired**
→ `sync-google-fit.sh` 会自动用 refresh_token 续期

**No data returned**
→ 确保手机上的 Google Fit 已同步数据到云端

## References
- [Google Fit REST API](https://developers.google.com/fit/rest/v1/reference)
- [OAuth 2.0 for Desktop Apps](https://developers.google.com/identity/protocols/oauth2/native-app)
