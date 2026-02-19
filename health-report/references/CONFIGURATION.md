# Health Report Configuration Guide

## Prerequisites

1. **Apple Health Data Export**
   - Install "Health Auto Export" app on iPhone
   - Configure daily export to Google Drive
   - Export path: `~/我的云端硬盘/Health Auto Export/`

2. **Google Fit API Setup**
   - Run `setup-google-fit-auth.sh` to configure credentials
   - Credentials stored in: `~/.openclaw/credentials/`

3. **macOS Mail.app**
   - Must be configured with sender email account
   - Used for sending daily reports

## Directory Structure

```
~/我的云端硬盘/Health Auto Export/
├── Health Data/
│   └── HealthAutoExport-YYYY-MM-DD.json
└── Workout Data/
    └── HealthAutoExport-YYYY-MM-DD.json
```

## Daily Report Contents

Each daily report includes:

- **Recovery Score** (0-100): Based on HRV, sleep, and activity
- **Sleep Analysis**: Duration, efficiency, stages (from Google Fit 20:00-12:00)
- **Heart Rate**: All-day trend and workout zones
- **Activity Metrics**: Steps, floors, distance, calories
- **Exercise Records**: Workout type, duration, heart rate
- **Recommendations**: Personalized health advice

## Customization

### Email Recipient
Edit `daily_health_report_auto.sh`:
```bash
RECIPIENT="your-email@example.com"
```

### Report Time
Default: Daily at 12:30
To change, edit crontab:
```bash
crontab -e
# Change: 30 12 * * * ...
```

### Sleep Data Window
Default: 20:00 to next day 12:00
Edit `generate_report_final.py` if needed.

## Troubleshooting

### No Workout Data
- Normal if no exercise recorded
- Report will show empty workout section

### No Sleep Data
- Check Google Fit credentials
- Verify Health Auto Export is syncing

### PDF Generation Fails
- Ensure Playwright is installed: `pip3 install playwright`
- Ensure Chromium is installed: `playwright install chromium`

## Data Sources

| Data | Source | File |
|------|--------|------|
| Steps, HRV, RHR | Apple Health | Health Data/*.json |
| Workouts | Apple Health | Workout Data/*.json |
| Sleep | Google Fit | API (20:00-12:00) |
| Heart Rate Series | Apple Health | Health Data/*.json |
