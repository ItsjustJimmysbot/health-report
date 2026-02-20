# 🏥 Health Agent Skill

AI-powered daily health report generator for OpenClaw.

## Overview

Automatically generates personalized health reports from your Apple Health data, analyzes trends with AI, and delivers PDF reports to your email daily.

## ✨ Features

- 📊 **Automatic Data Collection** - Reads Apple Health from Google Drive sync
- 🤖 **AI Analysis** - Personalized insights using LLM (default: Kimi K2.5)
- 📄 **Bilingual Reports** - Chinese and English PDF reports
- 📧 **Email Delivery** - Daily reports sent automatically
- ⏰ **Scheduled** - Runs daily at 12:30 PM (configurable)
- 🔒 **Privacy First** - All data processed locally

## 🚀 Quick Start

### 1. Prerequisites

- macOS with Mail.app configured
- Google Drive Desktop (syncing Health Auto Export)
- Health Auto Export app on iOS
- Google Fit account

### 2. Install

```bash
git clone https://github.com/YOUR_USERNAME/health-agent-skill.git
cd health-agent-skill
bash install.sh
```

Follow the interactive wizard to configure:
- Data paths
- Email recipient
- AI model preferences

### 3. Test

```bash
health-agent test
```

### 4. Enable Daily Reports

```bash
health-agent setup-cron
```

## 📖 Documentation

- [Installation Guide](docs/INSTALL.md)
- [Configuration](docs/CONFIG.md)
- [Customization](docs/CUSTOMIZE.md)
- [Troubleshooting](docs/TROUBLESHOOTING.md)

## 🔧 Customization

Edit templates in `~/.config/health-agent/templates/` to personalize:
- Report layout
- Color schemes
- Additional sections
- AI analysis prompts

## 📊 Data Sources

| Source | Data | Frequency |
|--------|------|-----------|
| Apple Health | HRV, Heart Rate, Steps, Energy | Real-time |
| Google Fit | Sleep, Activity | Daily sync |
| AI Analysis | Insights, Recommendations | Daily |

## 🤖 AI Models

**Default: Kimi K2.5** (Recommended)
- Excellent Chinese comprehension
- Cost-effective
- Sufficient for health analysis

**Alternatives:**
- GPT-4o - Best reasoning, higher cost
- Claude 3.5 Sonnet - Balanced performance

## 🔒 Privacy

- All health data stays on your machine
- Only AI analysis uses external API
- No data retention by third parties
- You control all your data

## 📝 License

MIT License - See [LICENSE](LICENSE)

## 🤝 Contributing

Contributions welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) first.

## 💬 Support

- GitHub Issues: [Report Bug](https://github.com/YOUR_USERNAME/health-agent-skill/issues)
- OpenClaw Docs: https://docs.openclaw.ai

---

**Disclaimer**: This tool is for personal health tracking only. Always consult healthcare professionals for medical advice.
