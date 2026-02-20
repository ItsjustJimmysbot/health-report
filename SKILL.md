---
name: health-agent
description: "AI-powered daily health report generator. Parses Apple Health data, analyzes with AI, generates PDF reports, and sends via email. Supports bilingual (Chinese/English) reports."
homepage: https://github.com/YOUR_USERNAME/health-agent-skill
metadata:
  {
    "openclaw":
      {
        "emoji": "🏥",
        "requires": { "bins": ["himalaya", "osascript", "python3"] },
        "install":
          [
            {
              "id": "setup",
              "kind": "script",
              "script": "install.sh",
              "label": "Interactive Setup Wizard",
            },
          ],
      },
  }
---

# Health Agent Skill

An automated health reporting system that generates personalized daily health reports from Apple Health and Google Fit data.

## Features

- 📊 **Automated Data Collection**: Reads Apple Health data from Google Drive sync
- 🤖 **AI-Powered Analysis**: Uses LLM (default: Kimi K2.5) for personalized insights
- 📄 **Bilingual Reports**: Generates both Chinese and English PDF reports
- 📧 **Email Delivery**: Automatically sends reports to your email
- ⏰ **Daily Schedule**: Runs automatically at 12:30 PM (configurable)
- 📱 **Multiple Data Sources**: Apple Health (HRV, steps, energy) + Google Fit (sleep)

## Prerequisites

Before installing this skill, ensure you have:

### 1. Google Drive Desktop
- Download from: https://www.google.com/drive/download/
- Sign in with your Google account
- Enable sync for Health Auto Export folder

### 2. Health Auto Export (iOS App)
- Install from App Store: https://apps.apple.com/app/health-auto-export/id1115567069
- Configure auto-export to Google Drive
- Set export format to JSON
- Schedule daily export (recommended: 11:00 PM)

### 3. Google Fit
- Install on your phone
- Enable sleep tracking
- Complete OAuth authentication (handled during setup)

### 4. macOS Mail.app (for email delivery)
- Configure with your email account
- Supports Gmail, Outlook, iCloud, etc.

## Installation

### Step 1: Run the Interactive Setup

```bash
cd ~/health-agent-skill
bash install.sh
```

The wizard will guide you through:
- Language selection (Chinese/English)
- Path configuration
- Email recipient setup
- AI model selection (default: Kimi K2.5)
- API key configuration (optional)

### Step 2: Test the Setup

```bash
health-agent test
```

This will generate a test report for the current date.

### Step 3: Enable Daily Automation

```bash
health-agent setup-cron
```

This sets up the daily report generation at 12:30 PM.

## Usage

### Generate Reports Manually

```bash
# Generate reports for yesterday
health-agent generate yesterday

# Generate reports for specific date
health-agent generate 2024-02-20

# Generate comparison report
health-agent compare 2024-02-19 2024-02-20
```

### Send Reports via Email

```bash
# Send yesterday's reports
health-agent email send

# Send specific date
health-agent email send --date 2024-02-20
```

### Customize Templates

Edit the HTML templates to personalize your reports:

```bash
# Template location
~/.config/health-agent/templates/

# Files
├── daily-report-zh.html    # Chinese daily report
├── daily-report-en.html    # English daily report
└── comparison-report.html   # Comparison report
```

You can add:
- Custom CSS styling
- Additional sections
- Personalized recommendations
- Your own branding

### View Configuration

```bash
health-agent config show
```

### Edit Configuration

```bash
# Edit the config file directly
nano ~/.config/health-agent/config.env

# Or use the CLI
health-agent config set RECIPIENT_EMAIL newemail@example.com
```

## Data Flow

```
1. Apple Health (iPhone)
        ↓
2. Health Auto Export App
        ↓
3. Google Drive Sync
        ↓
4. This Skill (Data Parsing)
        ↓
5. AI Analysis (Kimi/GPT/Claude)
        ↓
6. PDF Generation
        ↓
7. Email Delivery
```

## AI Model Recommendation

### Default: Kimi K2.5 (Recommended)
- **Why**: Excellent value for money
- **Strengths**: Strong Chinese comprehension, sufficient for health data analysis
- **Speed**: Fast response time
- **Cost**: Most economical option

### Alternative: GPT-4o
- **Why**: Most advanced model
- **Strengths**: Superior reasoning, better at pattern recognition
- **Cost**: Higher pricing

### Alternative: Claude 3.5 Sonnet
- **Why**: Balanced performance
- **Strengths**: Good at structured analysis
- **Cost**: Mid-range pricing

## File Structure

```
~/.config/health-agent/
├── config.env              # Main configuration
├── templates/              # Report templates
│   ├── daily-report-zh.html
│   ├── daily-report-en.html
│   └── comparison-report.html
├── data/                   # Cached data
└── logs/                   # Execution logs

~/Documents/Health Reports/  # PDF output directory
├── 2024-02-20-report-zh.pdf
├── 2024-02-20-report-en.pdf
└── ...
```

## Troubleshooting

### Issue: Health data files not found
**Solution**: Check Google Drive sync status
```bash
ls -la "~/Google Drive/Health Auto Export/Health Data/"
```

### Issue: Email sending fails
**Solution**: Check Mail.app configuration
```bash
# Test Mail.app
osascript -e 'tell application "Mail" to return name of first account'
```

### Issue: PDF generation fails
**Solution**: Check Python dependencies
```bash
pip install -r requirements.txt
```

### Issue: Outbox has stuck messages
**Solution**: Clear the outbox
```bash
health-agent email clear-outbox
```

## Advanced Customization

### Adding Custom Metrics

Edit `scripts/custom_metrics.py`:

```python
def calculate_custom_score(data):
    # Your custom calculation
    return score
```

### Changing Report Schedule

```bash
# Edit cron job
crontab -e

# Default: 12:30 PM daily
30 12 * * * health-agent generate yesterday && health-agent email send
```

### Multi-Recipient Support

Edit `~/.config/health-agent/config.env`:

```bash
RECIPIENT_EMAIL="user1@example.com,user2@example.com"
```

## Privacy & Security

- All data is processed locally on your machine
- Health data is not sent to any third-party servers (except AI analysis)
- Email credentials are stored in macOS Keychain
- You can use local LLMs for complete privacy

## Contributing

Contributions welcome! Please submit pull requests.

## License

MIT License - See LICENSE file for details

## Support

- GitHub Issues: https://github.com/YOUR_USERNAME/health-agent-skill/issues
- Documentation: See `docs/` directory
- OpenClaw Docs: https://docs.openclaw.ai

---

**Note**: This skill is designed for personal health tracking. Always consult healthcare professionals for medical advice.
