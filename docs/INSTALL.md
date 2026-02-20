# Installation Guide

## Prerequisites

### 1. Google Drive Desktop
Download and install from: https://www.google.com/drive/download/

### 2. Health Auto Export (iOS)
Install from App Store and configure:
- Enable auto-export to Google Drive
- Export format: JSON
- Schedule: Daily at 11:00 PM

### 3. Google Fit
- Install on your phone
- Enable sleep tracking
- Complete OAuth setup

## Installation Steps

### Step 1: Clone Repository
```bash
git clone https://github.com/YOUR_USERNAME/health-agent-skill.git
cd health-agent-skill
```

### Step 2: Run Setup Wizard
```bash
bash install.sh
```

### Step 3: Configure Mail.app
Ensure macOS Mail.app has your email account configured.

### Step 4: Test
```bash
health-agent test
```

## Troubleshooting

See TROUBLESHOOTING.md for common issues.
