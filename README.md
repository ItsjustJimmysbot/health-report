# Health Agent V5.7.0 - OpenClaw 专业健康分析 Skill

这是一个正式封装的 **OpenClaw Skill**，旨在将 Apple Health 原始数据转化为深度、医疗感的个人健康分析报告。

---

## 🚀 快速安装与 Skill 启用

### 🔄 更新到最新版本（已安装用户）

如果你已经安装了旧版本，可以通过以下方式更新：

**方式 1：使用 Git 命令（推荐）**
```bash
cd ~/.openclaw/skills/health-report
git pull origin main
```

**方式 2：让 OpenClaw Agent 帮你更新**
直接在 OpenClaw 对话中告诉 Agent：
> "请帮我更新 health-report skill"

**方式 3：重新克隆（如果本地有修改冲突）**
```bash
cd ~/.openclaw/skills
rm -rf health-report
git clone https://github.com/ItsjustJimmysbot/health-report.git health-report
cd health-report
pip3 install -r requirements.txt
```

### 1. 基础环境准备
在你的 OpenClaw 运行环境中执行：
```bash
cd ~/.openclaw/skills
git clone https://github.com/ItsjustJimmysbot/health-report.git health-report
cd health-report
pip3 install -r requirements.txt
playwright install chromium
```

### 2. Skill 发现
安装完成后，OpenClaw 会自动通过 `SKILL.md` 发现并启用此 Skill。

### 3. 配置文件 (config.json)
首次使用前，请编辑 `config.json` 配置你的数据路径：

```json
{
  "version": "5.7.0",
  "members": [
    {
      "name": "Jimmy",
      "age": 30,
      "gender": "male",
      "height_cm": 175,
      "weight_kg": 70,
      "health_dir": "~/我的云端硬盘/Health Auto Export/Health Data",
      "workout_dir": "~/我的云端硬盘/Health Auto Export/Workout Data",
      "email": "your-email@example.com"
    }
  ],
  "analysis_limits": {
    "metric_min_words": 150,
    "metric_max_words": 200,
    "action_min_words": 250,
    "action_max_words": 300,
    "daily_min_words": 500,
    "weekly_min_words": 800,
    "monthly_min_words": 1000
  },
  "email_config": {
    "smtp_server": "smtp.gmail.com",
    "smtp_port": 587,
    "sender_email": "your_email@gmail.com",
    "password": "your_app_password"
  },
  "receiver_email": "target_email@example.com",
  "language": "CN",
  "validation_mode": "strict",
  "output_dir": "~/.openclaw/workspace/shared/health-reports/upload",
  "cache_dir": "~/.openclaw/workspace/shared/health-reports/cache"
}
```

**配置说明：**
- `health_dir`: Apple Health 数据导出路径
- `workout_dir`: 运动数据导出路径
- `email`: 报告接收邮箱
- `email_config`: 邮件发送配置（SMTP服务器、端口、发件邮箱、密码）
- `language`: 报告界面语言（`CN`=中文, `EN`=英文）

### 4. 数据准备
确保你的 [Health Auto Export](https://apps.apple.com/us/app/health-auto-export-json-csv/id111556706) 导出的 JSON 文件同步到了配置的路径中。

### 5. OpenClaw 定时任务 (Cron) 配置
在 OpenClaw 中添加日报任务，建议时间 `12:10`（确保当日数据已同步完成）。

**指令内容模板：**
```text
【每日健康日报 - V5.7.0 标准化流程】
1. 读取 config.json：获取配置的 Health 路径以及 language 字段 (CN 或 EN)
2. 提取数据：从 Health 路径提取当日数据
3. AI 分析：基于当日真实数值（HRV、步数等）生成详细分析（每项≥150字）。**如果 language 为 EN，则必须全篇使用纯英文输出；如果为 CN，则使用纯中文。**
4. 关键写入：使用 write 工具将 JSON 写入 ai_analysis.json
5. 渲染生成：
   cd ~/.openclaw/workspace-health/scripts && \
   python3 generate_v5_medical_dashboard.py $(date -v-1d +%Y-%m-%d) < ../ai_analysis.json
6. 发送邮件：
   python3 send_health_report_email.py $(date -v-1d +%Y-%m-%d)
```

### 6. 周报定时任务 (Weekly Cron)
建议每周一上午 9:00 生成上周周报，汇总 7 天数据。

**Cron 设置：**
- 时间：`0 9 * * 1` (每周一 9:00)

**指令内容模板：**
```text
【每周健康周报 - V5.7.0 标准化流程】
1. 读取 config.json：获取 language 字段 (CN 或 EN)
2. 计算日期：获取上周一至上周日日期
   START_DATE=$(date -v-7d +%Y-%m-%d)
   END_DATE=$(date -v-1d +%Y-%m-%d)
3. AI 分析：基于整周数据趋势生成周报分析。**如果 language 为 EN，则必须全篇使用纯英文输出；如果为 CN，则使用纯中文。**
4. 关键写入：使用 write 工具将 JSON 写入 weekly_analysis.json
5. 渲染生成：
   cd ~/.openclaw/workspace-health/scripts && \
   python3 generate_weekly_monthly_medical.py weekly $START_DATE $END_DATE < ../weekly_analysis.json
6. 发送邮件：发送周报 PDF 到配置邮箱
```

### 7. 月报定时任务 (Monthly Cron)
建议每月 1 日上午 10:00 生成上月月报，汇总整月数据。

**Cron 设置：**
- 时间：`0 10 1 * *` (每月 1 日 10:00)

**指令内容模板：**
```text
【每月健康月报 - V5.7.0 标准化流程】
1. 读取 config.json：获取 language 字段 (CN 或 EN)
2. 计算月份：获取上月年份和月份
   YEAR=$(date -v-1m +%Y)
   MONTH=$(date -v-1m +%m)
3. AI 分析：基于整月数据趋势生成月报深度分析。**如果 language 为 EN，则必须全篇使用纯英文输出；如果为 CN，则使用纯中文。**
4. 关键写入：使用 write 工具将 JSON 写入 monthly_analysis.json
5. 渲染生成：
   cd ~/.openclaw/workspace-health/scripts && \
   python3 generate_weekly_monthly_medical.py monthly $YEAR $MONTH < ../monthly_analysis.json
6. 发送邮件：发送月报 PDF 到配置邮箱
```

**注意：** 周报和月报的 AI 分析 JSON 需包含 `recommendations` 数组（优先级建议），格式如下：
```json
{
  "trend_analysis": "本周 HRV 呈现...",
  "recommendations": [
    {"priority": "high", "title": "优先保证睡眠", "content": "建议每晚..."},
    {"priority": "medium", "title": "增加有氧运动", "content": "建议每周..."}
  ]
}
```

---

## ✨ V5.7.0 核心特性

*   **多语言支持 (新增)**：支持中英文界面切换，通过 `config.json` 的 `language` 字段一键切换（CN/EN）
*   **配置化路径**：所有脚本统一从 `config.json` 读取数据路径，无需修改代码
*   **真·数据对齐**：彻底修正了 Apple Health 跨天导出的偏移问题。日间活动从当日文件读取，睡眠数据从次日文件读取
*   **医疗级 UI**：采用全新的 V2 Medical 紫色主题模板，包含评分卡片、11 项核心指标表、Chart.js 动态心率曲线和深度睡眠结构分析
*   **原子化工作流**：将原本不稳定的 `edit` 局部替换逻辑升级为全量 `write` JSON 模式
*   **跨夜睡眠归属**：完善了睡眠统计逻辑，自动抓取 `当日 20:00` 至 `次日 12:00` 的睡眠记录并归属为当日恢复指标
*   **医疗级 UI**：采用全新的 V2 Medical 紫色主题模板，包含评分卡片、11 项核心指标表、Chart.js 动态心率曲线和深度睡眠结构分析
*   **原子化工作流**：将原本不稳定的 `edit` 局部替换逻辑升级为全量 `write` JSON 模式
*   **跨夜睡眠归属**：完善了睡眠统计逻辑，自动抓取 `当日 20:00` 至 `次日 12:00` 的睡眠记录并归属为当日恢复指标

---

## 🛠️ 常用命令

*   **测试数据提取**：`python3 scripts/extract_data_v5.py YYYY-MM-DD`
*   **生成日报**：`python3 scripts/generate_v5_medical_dashboard.py YYYY-MM-DD < ai_analysis.json`
*   **生成周报/月报**：`python3 scripts/generate_weekly_monthly_medical.py weekly|monthly ...`
*   **手动补发邮件**：`python3 scripts/send_health_report_email.py YYYY-MM-DD`
*   **验证渲染环境**：`python3 scripts/verify_v5_environment.py`

---

## 📝 开发者规范 (V5.7.0)
*   **配置优先**：所有路径必须从 `config.json` 读取，禁止硬编码
*   **禁止编造**：数据缺失时必须显示 `--`，严禁 AI 估算比例
*   **字数红线**：AI 指标分析段落必须在 150-200 字，核心行动建议 250-300 字
*   **单日单源**：每份报告必须仅依赖当日产生的 Data Cache JSON

---

## 📁 配置文件说明

### config.json 结构
```json
{
  "version": "5.7.0",
  "members": [
    {
      "name": "Jimmy",
      "age": 30,
      "gender": "male",
      "height_cm": 175,
      "weight_kg": 70,
      "health_dir": "~/我的云端硬盘/Health Auto Export/Health Data",
      "workout_dir": "~/我的云端硬盘/Health Auto Export/Workout Data",
      "email": "your-email@example.com"
    }
  ],
  "analysis_limits": {
    "metric_min_words": 150,
    "metric_max_words": 200,
    "action_min_words": 250,
    "action_max_words": 300,
    "daily_min_words": 500,
    "weekly_min_words": 800,
    "monthly_min_words": 1000
  },
  "email_config": {
    "smtp_server": "smtp.gmail.com",
    "smtp_port": 587,
    "sender_email": "your_email@gmail.com",
    "password": "your_app_password"
  },
  "receiver_email": "target_email@example.com",
  "language": "CN",
  "validation_mode": "strict",
  "output_dir": "~/.openclaw/workspace/shared/health-reports/upload",
  "cache_dir": "~/.openclaw/workspace/shared/health-reports/cache"
}
```

### 👥 多成员配置（最多3人）

支持为家庭成员分别生成健康报告，只需在 `members` 数组中添加多个成员：

```json
{
  "version": "5.7.0",
  "members": [
    {
      "name": "爸爸",
      "age": 45,
      "gender": "male",
      "height_cm": 178,
      "weight_kg": 75,
      "health_dir": "~/HealthData/Dad/Health Data",
      "workout_dir": "~/HealthData/Dad/Workout Data",
      "email": "dad@example.com"
    },
    {
      "name": "妈妈",
      "age": 42,
      "gender": "female",
      "height_cm": 165,
      "weight_kg": 58,
      "health_dir": "~/HealthData/Mom/Health Data",
      "workout_dir": "~/HealthData/Mom/Workout Data",
      "email": "mom@example.com"
    },
    {
      "name": "孩子",
      "age": 15,
      "gender": "male",
      "height_cm": 170,
      "weight_kg": 55,
      "health_dir": "~/HealthData/Kid/Health Data",
      "workout_dir": "~/HealthData/Kid/Workout Data",
      "email": "kid@example.com"
    }
  ],
  "analysis_limits": {...},
  "email_config": {...},
  "language": "CN"
}
```

**✅ V5.7.0+ 完整多成员支持：**

现在支持一次提取所有成员的数据！

**提取单个成员：**
```bash
# 提取第一个成员数据（默认）
python3 scripts/extract_data_v5.py 2026-03-01

# 提取第二个成员数据
python3 scripts/extract_data_v5.py 2026-03-01 1

# 提取第三个成员数据
python3 scripts/extract_data_v5.py 2026-03-01 2
```

**提取所有成员（V5.7.0+）：**
```bash
# 使用 all 参数提取所有成员的数据
python3 scripts/extract_data_v5.py 2026-03-01 all

# 输出将包含每个成员的数据，格式如下：
# {
#   "date": "2026-03-01",
#   "members_count": 3,
#   "members": [
#     {"profile": {...}, "hrv": {...}, ...},  # 成员1
#     {"profile": {...}, "hrv": {...}, ...},  # 成员2
#     {"profile": {...}, "hrv": {...}, ...}   # 成员3
#   ]
# }
```

**在定时任务中使用（推荐）：**
在 OpenClaw 定时任务指令中使用 `all` 参数，一次生成所有成员的报告：
```text
【每日健康日报 - V5.7.0 全成员流程】
1. 读取 config.json：获取所有成员配置
2. 提取数据：为每个成员分别提取数据
   python3 scripts/extract_data_v5.py $(date -v-1d +%Y-%m-%d) all
3. AI 分析：为每个成员分别生成分析报告（考虑年龄、性别、BMI等个性化因素）
4. 渲染生成：为每个成员生成独立 PDF 报告
5. 发送邮件：分别发送给每个成员配置的邮箱
```

### 🌐 多语言支持 (V5.7.0 新增)

通过 `config.json` 中的 `language` 字段切换报告语言：

- `"language": "CN"` - 中文界面（睡眠质量、运动记录、评级等）
- `"language": "EN"` - 英文界面（Sleep Quality / Workout Records / Excellent / Good 等）

**切换步骤：**
1. 编辑 `config.json` 修改 `language` 字段
2. 重新生成报告即可自动切换语言

**支持翻译的界面元素：**
- 所有标题（睡眠质量、运动记录、11项核心指标等）
- 评分评级（Excellent / Good / Average / Normal）
- 运动状态标签（Completed / 已完成）
- 心率图表标签（Heart Rate / Avg / Max / Time）
- 睡眠状态（Normal / Insufficient Data）
- 日期格式（2026年2月 / Feb 2026）

---

## 许可证
MIT License

---

# Health Agent V5.7.0 - OpenClaw Professional Health Analysis Skill [English]

A formally packaged **OpenClaw Skill** that transforms raw Apple Health data into in-depth, medical-grade personal health analysis reports.

---

## 🚀 Quick Installation & Skill Activation

### 🔄 Updating to Latest Version (For Existing Users)

If you have already installed a previous version, update using one of these methods:

**Method 1: Using Git Commands (Recommended)**
```bash
cd ~/.openclaw/skills/health-report
git pull origin main
```

**Method 2: Ask Your OpenClaw Agent**
Simply tell your OpenClaw Agent in conversation:
> "Please update the health-report skill for me"

**Method 3: Re-clone (If Local Conflicts Exist)**
```bash
cd ~/.openclaw/skills
rm -rf health-report
git clone https://github.com/ItsjustJimmysbot/health-report.git health-report
cd health-report
pip3 install -r requirements.txt
```

### 1. Prerequisites
Execute in your OpenClaw environment:
```bash
cd ~/.openclaw/skills
git clone https://github.com/ItsjustJimmysbot/health-report.git health-report
cd health-report
pip3 install -r requirements.txt
playwright install chromium
```

### 2. Skill Discovery
After installation, OpenClaw will automatically discover and enable this Skill via `SKILL.md`.

### 3. Configuration File (config.json)
Before first use, edit `config.json` to configure your data paths:

```json
{
  "version": "5.7.0",
  "members": [
    {
      "name": "Jimmy",
      "age": 30,
      "gender": "male",
      "height_cm": 175,
      "weight_kg": 70,
      "health_dir": "~/My Cloud Drive/Health Auto Export/Health Data",
      "workout_dir": "~/My Cloud Drive/Health Auto Export/Workout Data",
      "email": "your-email@example.com"
    }
  ],
  "analysis_limits": {
    "metric_min_words": 150,
    "metric_max_words": 200,
    "action_min_words": 250,
    "action_max_words": 300,
    "daily_min_words": 500,
    "weekly_min_words": 800,
    "monthly_min_words": 1000
  },
  "email_config": {
    "smtp_server": "smtp.gmail.com",
    "smtp_port": 587,
    "sender_email": "your_email@gmail.com",
    "password": "your_app_password"
  },
  "receiver_email": "target_email@example.com",
  "language": "EN",
  "validation_mode": "strict",
  "output_dir": "~/.openclaw/workspace/shared/health-reports/upload",
  "cache_dir": "~/.openclaw/workspace/shared/health-reports/cache"
}
```

**Configuration Notes:**
- `health_dir`: Apple Health data export path
- `workout_dir`: Workout data export path
- `email`: Report recipient email
- `email_config`: Email sending configuration (SMTP server, port, sender email, password)
- `language`: Report interface language (`CN`=Chinese, `EN`=English)
- `age`, `gender`, `height_cm`, `weight_kg`: Personal profile for AI analysis (BMI calculation, age/gender-specific heart rate references)

### 4. Data Preparation
Ensure your [Health Auto Export](https://apps.apple.com/us/app/health-auto-export-json-csv/id111556706) exported JSON files are synced to the configured paths.

### 5. OpenClaw Scheduled Tasks (Cron) Configuration
Add a daily report task in OpenClaw, recommended time `12:10` (to ensure daily data sync is complete).

**Daily Report Task Template:**
```text
[Daily Health Report - V5.7.0 Standardized Process]
1. Read config.json: Get configured Health path and language field (CN or EN)
2. Extract Data: Extract daily data from Health path
3. AI Analysis: Generate detailed analysis based on actual values (HRV, steps, etc.) with ≥150 words per metric. If language is EN, output must be in pure English; if CN, use pure Chinese.
4. Critical Write: Use write tool to save JSON to ai_analysis.json
5. Render Generation:
   cd ~/.openclaw/workspace-health/scripts && \\
   python3 generate_v5_medical_dashboard.py $(date -v-1d +%Y-%m-%d) < ../ai_analysis.json
6. Send Email:
   python3 send_health_report_email.py $(date -v-1d +%Y-%m-%d)
```

### 6. Weekly Report Scheduled Task
Recommended every Monday at 9:00 AM to generate last week's report, summarizing 7 days of data.

**Cron Setting:**
- Time: `0 9 * * 1` (Every Monday at 9:00)

### 7. Monthly Report Scheduled Task
Recommended on the 1st of each month at 10:00 AM to generate last month's report, summarizing the entire month.

**Cron Setting:**
- Time: `0 10 1 * *` (1st of each month at 10:00)

---

## ✨ V5.7.0 Core Features

*   **Multi-language Support (New)**: Supports Chinese and English interface switching via `config.json` `language` field (CN/EN)
*   **Profile Data (New)**: Support for `age`, `gender`, `height_cm`, `weight_kg` in member config for personalized AI analysis
*   **Smart Email Fallback (New)**: Automatic cascade - Mail.app → Gmail SMTP → Generic SMTP → Local copy
*   **Configuration-based Paths**: All scripts read data paths from `config.json`, no code modification needed
*   **True Data Alignment**: Fixed Apple Health cross-day export offset issues. Daytime activities read from current day file, sleep data reads from next day file
*   **Medical-grade UI**: New V2 Medical purple theme template with rating cards, 11 core metrics table, Chart.js dynamic heart rate curves, and deep sleep structure analysis
*   **Atomic Workflow**: Upgraded from unstable `edit` partial replacement to full `write` JSON mode
*   **Cross-night Sleep Attribution**: Improved sleep statistics logic, automatically captures sleep records from `20:00 current day` to `12:00 next day` and attributes to current day recovery metrics

---

## 🛠️ Common Commands

*   **Test Data Extraction**: `python3 scripts/extract_data_v5.py YYYY-MM-DD`
*   **Generate Daily Report**: `python3 scripts/generate_v5_medical_dashboard.py YYYY-MM-DD < ai_analysis.json`
*   **Generate Weekly/Monthly Report**: `python3 scripts/generate_weekly_monthly_medical.py weekly|monthly ...`
*   **Manual Email Resend**: `python3 scripts/send_health_report_email.py YYYY-MM-DD`
*   **Verify Render Environment**: `python3 scripts/verify_v5_environment.py`

---

## 📝 Developer Specifications (V5.7.0)
*   **Config Priority**: All paths must be read from `config.json`, no hardcoding
*   **No Fabrication**: When data is missing, display `--`, strictly prohibit AI estimation
*   **Word Count Requirements**: AI metric analysis paragraphs must be 150-200 words, core action recommendations 250-300 words
*   **Single Day Single Source**: Each report must only rely on the current day's Data Cache JSON

---

## 📁 Configuration File Structure

### config.json
```json
{
  "version": "5.7.0",
  "members": [
    {
      "name": "Jimmy",
      "age": 30,
      "gender": "male",
      "height_cm": 175,
      "weight_kg": 70,
      "health_dir": "~/My Cloud Drive/Health Auto Export/Health Data",
      "workout_dir": "~/My Cloud Drive/Health Auto Export/Workout Data",
      "email": "your-email@example.com"
    }
  ],
  "analysis_limits": {
    "metric_min_words": 150,
    "metric_max_words": 200,
    "action_min_words": 250,
    "action_max_words": 300,
    "daily_min_words": 500,
    "weekly_min_words": 800,
    "monthly_min_words": 1000
  },
  "email_config": {
    "smtp_server": "smtp.gmail.com",
    "smtp_port": 587,
    "sender_email": "your_email@gmail.com",
    "password": "your_app_password"
  },
  "receiver_email": "target_email@example.com",
  "language": "EN",
  "validation_mode": "strict",
  "output_dir": "~/.openclaw/workspace/shared/health-reports/upload",
  "cache_dir": "~/.openclaw/workspace/shared/health-reports/cache"
}
```

### 🌐 Multi-language Support (V5.7.0)

Switch report language via `language` field in `config.json`:

- `"language": "CN"` - Chinese interface (Sleep Quality, Workout Records, ratings, etc.)
- `"language": "EN"` - English interface (Sleep Quality / Workout Records / Excellent / Good, etc.)

**Switch Steps:**
1. Edit `config.json` to modify the `language` field
2. Regenerate the report to automatically switch languages

**Supported Translated Elements:**
- All titles (Sleep Quality, Workout Records, 11 Core Metrics, etc.)
- Rating levels (Excellent / Good / Average / Normal)
- Workout status labels (Completed / 已完成)
- Heart rate chart labels (Heart Rate / Avg / Max / Time)
- Sleep status (Normal / Insufficient Data)
- Date formats (2026年2月 / Feb 2026)

---

## License
MIT License
