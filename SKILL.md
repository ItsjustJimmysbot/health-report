---
name: health-agent
description: "AI-powered daily health report generator with bilingual support. Integrates Apple Health and Google Fit data, uses LLM for personalized analysis, generates PDF reports, and sends via email."
homepage: https://github.com/ItsjustJimmysbot/health-report
author: Jimmy
version: 2.0.0
requires:
  bins: ["python3", "osascript"]
  python_packages: ["playwright", "chart.js"]
  system: ["Mail.app"]
---

# Health Agent Skill - OpenClaw Edition

## Overview

A complete health reporting automation system that runs within OpenClaw, leveraging its agent infrastructure for AI analysis and task scheduling.

## Features

- 📊 **Automated Data Collection**: Reads Apple Health from Google Drive
- 🤖 **AI Analysis**: Uses OpenClaw's `sessions_spawn` to call LLM (default: Kimi K2.5)
- 📄 **Bilingual Reports**: Chinese and English PDF reports with Chart.js visualizations
- 📧 **Email Delivery**: Sends reports via Mail.app
- ⏰ **Scheduled Execution**: Uses OpenClaw cron for daily 12:30 runs
- 🔄 **Comparison Reports**: Day-over-day analysis with AI insights

## Architecture

```
OpenClaw Cron (12:30 daily)
    ↓
Agent Task: generate_health_reports
    ↓
1. Parse Apple Health JSON
2. Call Kimi AI (sessions_spawn)
3. Generate 4 PDFs (Playwright + Chart.js)
4. Send Email (AppleScript)
5. Discord Notification
```

## Installation

### Step 1: Prerequisites

Ensure these are configured before installing:

1. **Google Drive Desktop** syncing Health Auto Export
2. **Health Auto Export** iOS app with daily JSON export
3. **Google Fit** with sleep data
4. **Mail.app** with configured email account

### Step 2: Configure Paths

Edit `config/paths.env`:

```bash
# Required: Path to Health Auto Export data
HEALTH_DATA_PATH="/path/to/your/Google Drive/Health Auto Export/Health Data/"

# Required: Output directory for PDFs
OUTPUT_PATH="/path/to/output/directory/"

# Required: Email recipient
RECIPIENT_EMAIL="your-email@example.com"
```

### Step 3: Install Skill

```bash
# Clone to OpenClaw workspace
cd ~/.openclaw/workspace
git clone https://github.com/ItsjustJimmysbot/health-report.git health-agent

# Or copy to existing workspace
cp -r health-agent/* ~/.openclaw/workspace-health/
```

### Step 4: Setup Cron Job

The skill will register a cron job automatically. To manually configure:

```bash
openclaw cron add \
  --name "daily-health-report" \
  --schedule "30 12 * * *" \
  --timezone "Asia/Shanghai" \
  --agent "health" \
  --task "Generate daily health reports for yesterday and day before yesterday"
```

## Usage

### Automatic (Recommended)

Reports are automatically generated and sent daily at 12:30 PM.

### Manual Generation

```bash
# Via OpenClaw CLI
openclaw agent health --task "Generate health report for 2024-02-20"

# Or directly
python3 ~/.openclaw/workspace-health/scripts/generate_multilingual_report.py \
  --date 2024-02-20 \
  --lang zh
```

### View Reports

PDFs are saved to your configured `OUTPUT_PATH` and emailed automatically.

## Configuration

### AI Model Selection

Default: **Kimi K2.5** (`kimi-coding/k2p5`)

Why Kimi K2.5?
- Excellent Chinese language understanding
- Cost-effective for health data analysis
- Fast response times
- Sufficient reasoning for pattern recognition

To change model, edit the agent configuration in OpenClaw.

### Customizing Templates

HTML templates are embedded in `scripts/generate_multilingual_report.py`.

To customize:
1. Copy the template section to a new file
2. Modify CSS, layout, or add sections
3. Update the script to use your template

### Adding Custom Metrics

Edit `scripts/generate_multilingual_report.py`:

```python
def calculate_custom_score(data):
    # Your custom calculation
    return score
```

## Data Flow

1. **Apple Health** (iPhone) → Health Auto Export app
2. **Health Auto Export** → Google Drive sync
3. **OpenClaw Agent** reads JSON from Google Drive path
4. **Kimi AI** analyzes data via `sessions_spawn`
5. **Playwright** generates PDFs with Chart.js charts
6. **Mail.app** sends emails via AppleScript
7. **Discord** receives completion notification

## File Structure

```
~/.openclaw/workspace-health/
├── scripts/
│   ├── generate_multilingual_report.py  # Main report generator
│   ├── ai_analyzer.py                   # AI analysis wrapper
│   ├── i18n.py                          # Internationalization
│   ├── generate_daily_reports.sh        # Daily execution script
│   └── send_daily_email.sh              # Email sending script
├── config/
│   └── paths.env                        # User configuration
├── docs/
│   ├── REPORT_AUTOMATION.md             # Automation guide
│   ├── REPORT_STANDARD.md               # Report design standards
│   └── MAIL_APP_STANDARD.md             # Email setup guide
└── logs/
    └── daily_reports.log                # Execution logs
```

## Troubleshooting

### Issue: "Health data file not found"

Check Google Drive sync:
```bash
ls -la "${HEALTH_DATA_PATH}/HealthAutoExport-$(date -v-1d '+%Y-%m-%d').json"
```

### Issue: "AI analysis failed"

Verify OpenClaw can spawn subagents:
```bash
openclaw agent health --model kimi-coding/k2p5 --task "test"
```

### Issue: "PDF generation failed"

Install Playwright browsers:
```bash
playwright install chromium
```

### Issue: "Email not sending"

Check Mail.app configuration:
```bash
osascript -e 'tell application "Mail" to return name of first account'
```

## Privacy & Security

- All health data processed locally
- AI analysis uses temporary subagents
- No data retention by third parties
- Email credentials stored in macOS Keychain
- PDFs saved to user-controlled directory

## Customization in OpenClaw

Users can modify behavior by editing:

1. **Report Templates**: Edit HTML in `generate_multilingual_report.py`
2. **AI Prompts**: Modify `ai_analyzer.py` system prompts
3. **Scoring Logic**: Update score calculation functions
4. **Email Content**: Customize email templates

Example: Adding a custom section
```python
# In generate_multilingual_report.py
custom_section = f"""
<div class="custom-section">
    <h3>My Custom Metric</h3>
    <p>{health_data.get('custom_value', 'N/A')}</p>
</div>
"""
html += custom_section
```

## Updates

To update the skill:

```bash
cd ~/.openclaw/workspace-health
git pull origin main
```

## License

MIT License - See LICENSE file

## Support

- GitHub Issues: https://github.com/ItsjustJimmysbot/health-report/issues
- OpenClaw Docs: https://docs.openclaw.ai
