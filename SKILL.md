---
name: health-report
description: 基于 Apple Health 数据的 AI 健康分析报告生成工具。支持从 Health Auto Export 导出的 JSON 中提取 HRV、步数、睡眠等 11 项核心指标，并利用大模型进行深度分析，最终通过 V2 Medical 模板渲染为精美的 PDF 报告并自动发送邮件。使用场景：(1) 生成昨日/今日健康日报，(2) 分析周/月健康趋势，(3) 监控 HRV、静息心率等关键生理指标。
---

# Health Report

此 Skill 能够将 Apple Health 的原始导出数据转化为深度、个性化的健康报告。

## 🚀 快速启动

### 1. 配置文件设置

首先创建或编辑 `config.json` 文件：

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

**关键配置项：**
- `health_dir`: Apple Health 数据导出目录
- `workout_dir`: Workout 数据导出目录
- `members`: 支持多成员配置（最多3人）

### 2. 生成日报 (Daily Report)

运行以下逻辑流程：

1. **提取数据**：脚本自动读取 `config.json` 中配置的路径
   ```bash
   python3 scripts/extract_data_v5.py YYYY-MM-DD
   ```

2. **AI 分析**：根据提取的数值生成 150-200 字的指标分析及 250-300 字的行动建议。**注意：AI 分析生成的语言必须与 `config.json` 中的 `language` 字段（CN/EN）严格一致。**

   **使用个人档案数据（V5.6+）：**
   提取的数据 JSON 现在包含 `profile` 字段（年龄、性别、身高、体重），AI 分析时可以参考这些生理基准信息，生成更具个性化的建议：
   ```json
   {
     "profile": {
       "name": "Jimmy",
       "age": 30,
       "gender": "male",
       "height_cm": 175,
       "weight_kg": 70
     },
     "hrv": { "value": 65.2, ... },
     ...
   }
   ```
   
   在 AI 分析提示词中，可以引用这些字段：
   - `profile.age` - 年龄（影响心率、HRV 等指标的正常范围判断）
   - `profile.gender` - 性别（male/female）
   - `profile.height_cm` - 身高（用于 BMI 计算等）
   - `profile.weight_kg` - 体重（用于 BMI 计算、运动消耗评估等）

3. **渲染 PDF**：
   ```bash
   python3 scripts/generate_v5_medical_dashboard.py YYYY-MM-DD < ai_analysis.json
   ```

4. **发送邮件**（可选）：
   ```bash
   python3 send_health_report_email.py YYYY-MM-DD
   ```

### 3. 生成周报/月报 (Weekly/Monthly Report)

周报和月报会自动汇总 `cache/daily/` 下的缓存数据，支持中英文切换。**注意：同样要求 AI 生成分析时，严格遵循 `config.json` 中的语言配置。**

```bash
# 周报 (7天数据汇总)
python3 scripts/generate_weekly_monthly_medical.py weekly <start_date> <end_date> < ai_analysis.json

# 示例：生成 2026-02-24 至 2026-03-02 的周报
python3 scripts/generate_weekly_monthly_medical.py weekly 2026-02-24 2026-03-02 < weekly_analysis.json

# 月报
python3 scripts/generate_weekly_monthly_medical.py monthly <year> <month> < ai_analysis.json

# 示例：生成 2026年2月月报
python3 scripts/generate_weekly_monthly_medical.py monthly 2026 2 < monthly_analysis.json
```

**语言切换：**
周报和月报会根据 `config.json` 中的 `language` 字段自动选择对应语言模板：
- `"language": "CN"` → 中文周报/月报
- `"language": "EN"` → 英文周报/月报

## 🛠️ 核心脚本

- `scripts/extract_data_v5.py`: 从 config.json 配置的路径读取数据，执行严格的时间戳过滤
- `scripts/generate_v5_medical_dashboard.py`: 日报生成主脚本，自动读取 config.json 配置
- `scripts/generate_weekly_monthly_medical.py`: 趋势报告生成脚本
- `scripts/send_health_report_email.py`: 邮件分发脚本，读取 config.json 中的邮件配置
- `scripts/verify_v5_environment.py`: 环境验证脚本

## 📝 V5.7.0 强制规范

- **配置优先**：所有脚本必须从 `config.json` 读取路径配置，禁止硬编码
- **语言切换**：通过 `config.json` 中的 `language` 字段（CN/EN）切换报告界面语言
- **严格对齐**：日报必须对原始数据执行 `00:00-23:59` 过滤，日间活动从当日文件读取，睡眠从次日文件读取
- **跨夜睡眠**：睡眠窗口定义为当日 20:00 至次日 12:00
- **禁止估算**：数据缺失处必须显示 `--`，严禁 AI 编造
- **原子写入**：必须使用 `write` 工具全量更新 `ai_analysis.json`，禁止 `edit` 局部替换

## 📁 配置文件详解

### config.json 完整结构

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

**语言切换说明：**
- `"language": "CN"` - 中文界面（睡眠质量、运动记录、评级：优秀/良好/一般）
- `"language": "EN"` - 英文界面（Sleep Quality / Workout Records / Excellent / Good / Average / Normal）

### 多成员配置

支持最多 3 个成员的报告生成：

```json
{
  "version": "5.7.0",
  "members": [
    {
      "name": "成员1",
      "age": 30,
      "gender": "male",
      "height_cm": 175,
      "weight_kg": 70,
      "health_dir": "~/HealthData/Member1/Health Data",
      "workout_dir": "~/HealthData/Member1/Workout Data",
      "email": "member1@example.com"
    },
    {
      "name": "成员2",
      "age": 28,
      "gender": "female",
      "height_cm": 165,
      "weight_kg": 55,
      "health_dir": "~/HealthData/Member2/Health Data",
      "workout_dir": "~/HealthData/Member2/Workout Data",
      "email": "member2@example.com"
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

## 🎨 模板说明

- `templates/DAILY_TEMPLATE_MEDICAL_V2.html`: 医疗感紫色主题日报模板（中文）
- `templates/DAILY_TEMPLATE_MEDICAL_V2_EN.html`: 医疗感紫色主题日报模板（英文）
- `templates/WEEKLY_TEMPLATE_MEDICAL.html`: 周报汇总模板（中文）
- `templates/WEEKLY_TEMPLATE_MEDICAL_EN.html`: 周报汇总模板（英文）
- `templates/MONTHLY_TEMPLATE_MEDICAL.html`: 月报回顾模板（中文）
- `templates/MONTHLY_TEMPLATE_MEDICAL_EN.html`: 月报回顾模板（英文）

**多语言支持：** 所有报告模板均提供 CN/EN 双语版本，脚本会根据 `config.json` 中的 `language` 字段自动选择对应模板。

## 🔧 故障排除

### 报告生成失败
1. 检查 `config.json` 是否存在且格式正确
2. 验证 `health_dir` 和 `workout_dir` 路径是否正确
3. 运行 `python3 scripts/verify_v5_environment.py` 检查环境

### 数据提取异常
1. 确认 Health Auto Export 已正确导出数据
2. 检查 JSON 文件是否损坏
3. 验证文件路径在 `config.json` 中配置正确
