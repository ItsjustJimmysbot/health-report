# 🏥 Health Agent Skill for OpenClaw

AI-powered daily health report generator that integrates with OpenClaw infrastructure.

## ✨ Features

- 📊 **Automated Data Collection** - Reads Apple Health data from Google Drive sync
- 🤖 **AI Analysis via OpenClaw** - Uses `sessions_spawn` to call LLM (default: Kimi K2.5)
- 📄 **Bilingual Reports** - Chinese and English PDF reports with Chart.js visualizations
- 📧 **Email Delivery** - Sends reports via Mail.app
- ⏰ **OpenClaw Scheduled Execution** - Daily runs via OpenClaw cron
- 🔄 **Comparison Reports** - Day-over-day analysis with AI insights

## 🏗️ Architecture

```
OpenClaw Cron (12:30 daily)
    ↓
Agent Task: generate_health_reports
    ↓
1. Parse Apple Health JSON from Google Drive
2. Call Kimi AI via sessions_spawn
3. Generate 4 PDFs (Playwright + Chart.js)
4. Send Email via AppleScript
5. Discord Notification
```

## 📋 Prerequisites

Before installing, ensure you have:

1. **Google Drive Desktop** (syncing Health Auto Export folder)
2. **Health Auto Export** iOS app (configured for daily JSON export)
3. **Google Fit** (with sleep tracking enabled)
4. **macOS Mail.app** (with configured email account)
5. **OpenClaw** (installed and configured)

## 🚀 Installation

### Step 1: Clone Repository

```bash
cd ~/.openclaw/workspace
git clone https://github.com/ItsjustJimmysbot/health-report.git health-agent
```

### Step 2: Configure Paths

Copy and edit the configuration:

```bash
cd health-agent
cp config/config.env.template config/config.env
nano config/config.env  # or use your preferred editor
```

Required configuration:
- `HEALTH_DATA_PATH`: Path to Health Auto Export JSON files
- `OUTPUT_PATH`: Where to save generated PDFs
- `RECIPIENT_EMAIL`: Email address to receive reports

### Step 3: Setup OpenClaw Cron

The skill uses OpenClaw's cron system for scheduling. To enable:

```bash
# Via OpenClaw CLI
openclaw cron add \
  --name "daily-health-report" \
  --schedule "30 12 * * *" \
  --timezone "Asia/Shanghai" \
  --agent "health" \
  --task "Generate daily health reports"
```

Or edit OpenClaw configuration directly to add the cron job.

## 🔧 How It Works

### Data Flow

1. **Apple Health** (iPhone) → Health Auto Export app
2. **Health Auto Export** → Google Drive sync
3. **OpenClaw Agent** reads JSON from configured path
4. **Kimi AI** analyzes via `sessions_spawn` subagent
5. **Playwright** generates PDFs with Chart.js charts
6. **Mail.app** sends emails via AppleScript
7. **Discord** receives completion notification

### AI Model

**Default: Kimi K2.5** (`kimi-coding/k2p5`)

Why Kimi K2.5?
- ✅ Excellent Chinese language understanding
- ✅ Cost-effective for health data analysis
- ✅ Fast response times
- ✅ Sufficient reasoning for pattern recognition

To change model, modify the `AI_MODEL` in config or override in OpenClaw agent settings.

## 📝 Usage

### Automatic (Default)

Reports are automatically generated and sent daily at 12:30 PM via OpenClaw cron.

### Manual via OpenClaw

```bash
# Generate report for specific date
openclaw agent health --task "Generate health report for 2024-02-20"

# Or directly run the script
python3 scripts/generate_multilingual_report.py --date 2024-02-20 --lang zh
```

### View Reports

PDFs are saved to your configured `OUTPUT_PATH` and automatically emailed.

## 🎨 Customization

### Modifying Report Templates

HTML templates are embedded in `scripts/generate_multilingual_report.py`. To customize:

1. Copy the template section to a new file
2. Modify CSS, layout, or add sections
3. Update the script to use your template

### Adding Custom Metrics

Edit `scripts/ai_analyzer.py`:

```python
def calculate_custom_score(data):
    # Your custom calculation
    return score
```

### AI Analysis Prompts

Modify prompts in `scripts/ai_analyzer.py` to change how AI analyzes data.

## 📁 File Structure

```
~/.openclaw/workspace-health/
├── scripts/
│   ├── generate_multilingual_report.py  # Main report generator with Chart.js
│   ├── ai_analyzer.py                   # AI analysis wrapper
│   ├── i18n.py                          # Internationalization
│   └── send_daily_email.sh              # Email sending via AppleScript
├── config/
│   └── config.env.template              # Configuration template
├── docs/
│   └── INSTALL.md                       # Installation guide
└── SKILL.md                             # OpenClaw skill manifest
```

## 🐛 Troubleshooting

### "Health data file not found"

Check Google Drive sync:
```bash
ls -la "${HEALTH_DATA_PATH}/HealthAutoExport-$(date -v-1d '+%Y-%m-%d').json"
```

### "AI analysis failed"

Verify OpenClaw can spawn subagents:
```bash
openclaw agent health --model kimi-coding/k2p5 --task "test"
```

### "PDF generation failed"

Install Playwright browsers:
```bash
playwright install chromium
```

### "Email not sending"

Check Mail.app configuration:
```bash
osascript -e 'tell application "Mail" to return name of first account'
```

## 🔒 Privacy & Security

- All health data processed locally on your machine
- AI analysis uses temporary OpenClaw subagents
- No data retention by third parties
- Email credentials stored in macOS Keychain
- PDFs saved to user-controlled directory

## 📄 License

MIT License - See LICENSE file

## 🤝 Contributing

Contributions welcome! Please submit pull requests.

## 💬 Support

- GitHub Issues: https://github.com/ItsjustJimmysbot/health-report/issues
- OpenClaw Docs: https://docs.openclaw.ai
