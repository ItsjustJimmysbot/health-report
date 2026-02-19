---
name: health-report
description: Generate daily health reports from Apple Health and Google Fit data. Creates visual HTML/PDF reports with recovery scores, sleep analysis, heart rate trends, activity metrics, and personalized recommendations. Sends automated daily emails at 12:30. Use when users need health data visualization, daily wellness summaries, fitness tracking reports, or automated health monitoring.
---

# Health Report Skill

Generate comprehensive daily health reports from Apple Health and Google Fit data.

## Quick Start

### Generate a Single Report

```bash
python3 scripts/generate_report_final.py \
  --health "${HOME}/我的云端硬盘/Health Auto Export/Health Data/HealthAutoExport-YYYY-MM-DD.json" \
  --workout "${HOME}/我的云端硬盘/Health Auto Export/Workout Data/HealthAutoExport-YYYY-MM-DD.json" \
  --output /path/to/output.html \
  --date YYYY-MM-DD
```

### Generate PDF from HTML

```bash
python3 scripts/generate_pdf_playwright.py input.html output.pdf
```

### Setup Daily Automation

1. Configure Apple Health Auto Export (see [CONFIGURATION.md](references/CONFIGURATION.md))
2. Setup Google Fit credentials
3. Run the daily automation script

## Report Components

### 1. Recovery Score (0-100)
Calculated from:
- HRV (35% weight)
- Sleep duration (35% weight)
- Step count (30% weight)

### 2. Sleep Analysis
- Duration (from Google Fit 20:00-12:00 window)
- Sleep stages (deep, REM, core, awake)
- Sleep efficiency
- Bed/wake times

### 3. Heart Rate
- All-day trend chart
- Workout heart rate zones
- Min/avg/max statistics

### 4. Activity Metrics
- Steps, floors, distance
- Active calories (kJ converted to kcal)
- Basal calories
- Exercise minutes

### 5. Workout Records
- Type, duration, calories
- Heart rate data
- Time range

### 6. Recommendations
- Recovery-based exercise advice
- Sleep improvement suggestions
- Tomorrow's activity goals
- Diet recommendations

## Scripts

### Main Scripts

- `generate_report_final.py` - Main report generator
- `generate_visual_report.py` - HTML visualization
- `generate_pdf_playwright.py` - PDF conversion
- `daily_health_report_auto.sh` - Daily automation
- `send_email_applescript.scpt` - macOS Mail integration

### Usage Examples

See [CONFIGURATION.md](references/CONFIGURATION.md) for setup details.

## Data Flow

```
Apple Health (iPhone)
    ↓ (Health Auto Export)
Google Drive
    ↓ (local sync)
Health Data/*.json + Workout Data/*.json
    ↓ (generate_report_final.py)
HTML Report
    ↓ (generate_pdf_playwright.py)
PDF Report
    ↓ (send_email_applescript.scpt)
Email to User
```

## Notes

- Sleep data comes from Google Fit API (not Apple Health)
- Sleep window: 20:00 to next day 12:00 (for night owls)
- Calories converted from kJ to kcal (× 0.239)
- Reports auto-generated daily at 12:30 via cron
