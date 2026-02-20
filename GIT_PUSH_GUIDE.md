# 🚀 Git Push Guide

## Quick Start

```bash
# Clone your existing repo
git clone https://github.com/ItsjustJimmysbot/health-report.git
cd health-report

# Copy the new files
cp -r ~/health-agent-openclaw-skill/* .

# Add and commit
git add .
git commit -m "Update to v2.0: Complete OpenClaw Skill

- Full AI analysis integration via OpenClaw sessions_spawn
- Bilingual report generation (Chinese/English)
- Chart.js visualizations
- Email delivery via Mail.app
- OpenClaw cron scheduling
- Complete documentation"

# Push
git push origin main

# Tag new version
git tag -a v2.0.0 -m "Release v2.0.0 - OpenClaw Skill Edition"
git push origin v2.0.0
```

## Changes from v1.0

### What's New

1. **OpenClaw Integration**
   - Uses `sessions_spawn` for AI analysis
   - Cron-based scheduling
   - Agent-based execution

2. **Complete Implementation**
   - Full PDF generation with Playwright
   - Chart.js visualizations
   - Email automation
   - i18n support

3. **Better Structure**
   - Proper skill manifest (SKILL.md)
   - Configuration templates
   - Complete documentation

## File Structure

```
health-report/
├── SKILL.md                    # OpenClaw skill manifest
├── README.md                   # Main documentation
├── LICENSE                     # MIT License
├── config/
│   └── config.env.template     # Configuration template
├── scripts/
│   ├── generate_multilingual_report.py  # Main generator
│   ├── ai_analyzer.py          # AI analysis module
│   ├── i18n.py                 # Internationalization
│   └── send_daily_email.sh     # Email sending
└── docs/
    └── INSTALL.md              # Installation guide
```

## Installation for Users

After pushing, users can install via:

```bash
cd ~/.openclaw/workspace
git clone https://github.com/ItsjustJimmysbot/health-report.git health-agent

# Configure
cd health-agent
cp config/config.env.template config/config.env
# Edit config.env

# Setup cron via OpenClaw
```
