# Health Agent V6.0.5 - OpenClaw 专业健康分析 Skill

> ⚡ 快速执行请看 `SKILL.md`（面向 Agent 的简版说明）  
> 📘 本文档是完整用户手册（安装、配置、排障、最佳实践）。

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
python3 -m playwright install chromium
```

### 2. Skill 发现
安装完成后，OpenClaw 会自动通过 `SKILL.md` 发现并启用此 Skill。

### 3. 配置文件 (config.json)
首次使用前，请编辑 `config.json` 配置你的数据路径（V6.0.5 配置结构）：

```json
{
  "version": "6.0.3",
  "members": [
    {
      "name": "Member1",
      "age": 30,
      "gender": "male",
      "height_cm": 175,
      "weight_kg": 70,
      "health_dir": "~/Health Auto Export/Health Data",
      "workout_dir": "~/Health Auto Export/Workout Data",
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
    "monthly_min_words": 1000,
    "monthly_trend_min_words": 150,
    "lang_en_max_chinese_ratio_strict": 0.15,
    "lang_en_max_chinese_ratio_warn": 0.20,
    "lang_cn_min_chinese_ratio_strict": 0.30,
    "lang_cn_min_chinese_ratio_warn": 0.20
  },
  "email_config": {
    "provider_priority": ["oauth2", "smtp", "mail_app", "local"],
    "oauth2": {
      "enabled": false,
      "provider": "gmail",
      "client_id": "your-client-id.apps.googleusercontent.com",
      "client_secret": "your-client-secret",
      "refresh_token": "your-refresh-token",
      "sender_email": "your-email@gmail.com"
    },
    "smtp": {
      "enabled": false,
      "server": "smtp.gmail.com",
      "port": 587,
      "sender_email": "your-email@gmail.com",
      "password": "your-app-password",
      "use_tls": true
    },
    "mail_app": {
      "enabled": true
    },
    "max_retries": 3,
    "retry_delay": 5,
    "local": {
      "enabled": true,
      "output_dir": "~/.openclaw/workspace/shared/health-reports/upload"
    }
  },
  "receiver_email": "target-email@example.com",
  "language": "CN",
  "validation_mode": "strict",
  "output_dir": "~/.openclaw/workspace/shared/health-reports/upload",
  "cache_dir": "~/.openclaw/workspace/shared/health-reports/cache",
  "sleep_config": {
    "read_mode": "next_day",
    "start_hour": 20,
    "end_hour": 12
  }
}
```

`members[*].email` 可为空，留空时使用 `receiver_email`。

**配置说明：**
- `health_dir`: Apple Health 数据导出路径（需包含 `HealthAutoExport-YYYY-MM-DD.json` 文件）
- `workout_dir`: 运动数据导出路径
- `email`: 成员报告接收邮箱（可选；为空时回退到全局 receiver_email）
- `email_config`: 邮件发送配置（V5.8.1 新版 Provider 架构）
  - `provider_priority`: 发送方式优先级，默认 `['oauth2', 'smtp', 'mail_app', 'local']`
  - `oauth2`: Gmail OAuth2 认证（推荐，最安全）
  - `smtp`: SMTP 服务器发送
  - `mail_app`: macOS Mail.app 发送（仅 Mac）
  - `local`: 保存到本地目录（不发送邮件）
- `language`: 报告界面语言（`CN`=中文, `EN`=英文）
- `sleep_config`: 睡眠数据读取配置
  - `read_mode`: `next_day`（读取次日文件，适合早上生成报告）或 `same_day`（读取当天文件，适合晚上生成报告）
- `age`, `gender`, `height_cm`, `weight_kg`: 个人档案数据，用于 AI 生成个性化分析
- `config.schema.json` 定义结构约束，`scripts/validate_config.py` 会执行 schema + 业务校验。

### 日志配置

- `log_dir`: 错误日志保存目录，默认 `~/.openclaw/workspace-health/logs`
- 通过 `handle_error` 处理的关键错误会同时写入 `health_report.log` 和终端输出（建议脚本主流程异常都统一走 `handle_error`）

### 关于 receiver_email 的说明

`receiver_email` 是**全局回退邮箱**，当某个成员没有配置 `email` 字段时，会使用此地址。

优先级:
1. 成员自己的 `email` 字段 (members[i].email)
2. 全局 `receiver_email` (顶层配置)
3. 如果都没有配置，该成员将不会收到邮件

建议: 为每个成员单独配置 `email`，`receiver_email` 作为备用。

### 4. 邮件发送配置（OAuth2 推荐）

V5.8.1 支持多种邮件发送方式，推荐优先级：**OAuth2 > SMTP > Mail.app > Local**

#### 方式 A：Gmail OAuth2 认证（推荐，最安全）

运行交互式配置脚本：

```bash
cd ~/.openclaw/skills/health-report
python3 scripts/setup_oauth2.py
```

**步骤说明：**
1. 访问 https://console.cloud.google.com/apis/credentials 创建 OAuth2 凭证
2. 启用 Gmail API，创建 Desktop app 类型的 OAuth client ID
3. 输入 Client ID 和 Client Secret
4. 浏览器完成授权，复制回调 URL 粘贴回终端
5. 配置完成，refresh_token 会自动保存到 config.json

**常见报错及解决：**

| 报错信息 | 原因 | 解决方法 |
|---------|------|---------|
| `未获取到 refresh_token` | 用户之前已授权过，Google 不再提供 | 访问 https://myaccount.google.com/permissions 撤销权限后重试 |
| `授权失败: access_denied` | 用户点击了拒绝 | 重新运行脚本，确保点击"允许" |
| `无法从 URL 中提取授权码` | 复制了错误的 URL | 确保复制的是浏览器地址栏的完整 URL（包含 `code=` 参数） |
| `连接超时` | 网络问题 | 检查网络连接，或尝试使用代理 |

#### 方式 B：SMTP 配置（传统方式）

编辑 `config.json` 中的 `email_config.smtp` 部分：

```json
"smtp": {
  "enabled": true,
  "server": "smtp.gmail.com",
  "port": 587,
  "sender_email": "your-email@gmail.com",
  "password": "your-app-password",
  "use_tls": true
}
```

**注意：** Gmail 需要使用「应用专用密码」，不是登录密码。

**兼容旧配置:**
如果你使用的是 V5.8.0 或更早版本的配置,脚本会自动识别顶层的 `sender_email`, `password`, `smtp_server` 字段,无需手动迁移到 `email_config.smtp` 结构。

#### 方式 C：macOS Mail.app（仅 Mac）

```json
"mail_app": {
  "enabled": true
}
```

系统会自动打开 Mail.app 发送邮件。

#### 方式 D：本地保存（不发送邮件）

```json
"max_retries": 3,
"retry_delay": 5,
"local": {
  "enabled": true,
  "output_dir": "~/.openclaw/workspace/shared/health-reports/upload"
}
```

报告将保存到指定目录，不发送邮件。

### 5. 数据准备
确保你的 [Health Auto Export](https://apps.apple.com/us/app/health-auto-export-json-csv/id111556706) 导出的 JSON 文件同步到了配置的路径中。

**数据文件格式要求：**
- 文件名格式：`HealthAutoExport-YYYY-MM-DD.json`
- 活动数据（步数、心率等）存储在当日文件中
- 睡眠数据存储在次日文件中（系统会自动读取）

### 关于时区的说明

**重要**: 本工具使用系统本地时区处理所有时间数据。

- 睡眠数据的时间解析基于运行脚本的机器时区
- 如果 Health Auto Export 导出的数据使用不同时区，可能导致睡眠统计偏差
- 建议: 确保 iPhone、Health Auto Export 设置、和运行本脚本的机器使用相同时区

**sleep_config 说明**:
```json
"sleep_config": {
    "read_mode": "next_day",  // next_day: 读取次日文件筛选当天睡眠; same_day: 读取当天文件
    "start_hour": 20,         // 睡眠窗口开始时间（晚上8点）
    "end_hour": 12            // 睡眠窗口结束时间（次日中午12点）
}
```

此配置定义了睡眠数据的时间窗口:
- 对于 2026-03-01 的睡眠报告
- next_day 模式会读取 2026-03-02 的数据文件
- 筛选时间段: 03-01 20:00 到 03-02 12:00

如果跨越时区使用，请相应调整 `start_hour` 和 `end_hour`。

**路径配置说明：**
- `~/我的云端硬盘/` 是 Google Drive 的默认中文名称
- 如使用 iCloud Drive：`~/Library/Mobile Documents/com~apple~CloudDocs/Health Data`
- 如使用 OneDrive：`~/OneDrive/Health Data`
- 如使用本地目录：`~/Documents/Health Data`

### 6. OpenClaw 定时任务 (Cron) 配置
在 OpenClaw 中添加日报任务，建议时间 `12:10`（确保当日数据已同步完成）。

**📌 兼容性提示（date 命令）**
- **macOS (BSD)**: 使用 `date -v-1d +%Y-%m-%d`
- **Linux (GNU)**: 使用 `date -d 'yesterday' +%Y-%m-%d`

**示例对照：**
- macOS: `date -v-1d +%Y-%m-%d` → 昨天日期
- Linux: `date -d 'yesterday' +%Y-%m-%d` → 昨天日期

### 日期命令速查表

| 功能 | macOS (BSD) | Linux (GNU) |
|------|-------------|-------------|
| 昨天 | `date -v-1d +%Y-%m-%d` | `date -d 'yesterday' +%Y-%m-%d` |
| 上周 | `date -v-7d +%Y-%m-%d` | `date -d '7 days ago' +%Y-%m-%d` |
| 上月 | `date -v-1m +%Y-%m` | `date -d '1 month ago' +%Y-%m` |

**指令内容模板：**
```text
【每日健康日报 - V6.0.5 标准化流程】
1. 读取 config.json：获取配置的 Health 路径以及 language 字段 (CN 或 EN)
2. 提取数据：为所有成员提取当日数据
   # macOS:
   python3 scripts/extract_data_v5.py $(date -v-1d +%Y-%m-%d) all
   # Linux:
   python3 scripts/extract_data_v5.py $(date -d 'yesterday' +%Y-%m-%d) all
3. AI 分析：基于提取的 JSON 数据生成详细分析。**必须严格使用 JSON 中 `profile` 字段的实际个人档案信息（如：年龄{X}岁、性别{Y}、身高{Z}cm、体重{W}kg）、计算BMI并据此给出个性化建议。** 每项指标分析 150-200（CN按字数，EN按单词数），核心建议 250-300（CN按字数，EN按单词数）。**language=EN 时建议全篇英文；系统会按中文占比阈值做语言校验（默认容许少量术语）。language=CN 时应以中文为主。**
   
   **重要字段说明（AI 必须理解）**:
   - `hrv.value`: HRV 平均值，单位毫秒（ms），正常范围 20-100ms，年轻人通常 50-80ms
   - `hrv.measurement_count`: 测量数据点数量（如46 = 当天测量了46次），**这不是评分！**
   - `resting_hr.value`: 静息心率，单位 bpm，正常范围 60-100bpm
   - `steps`: 步数，建议每日 8000-10000 步
   - `active_energy_kcal`: 活动能量，单位千卡（kcal）
   - `sleep.total_hours`: 睡眠总时长，单位小时
   
   **评分说明**:
   - 恢复度评分、睡眠评分、运动评分由代码 calculate_scores() 计算，范围 0-100
   - AI 只分析数据，**禁止自行计算或猜测 0-100 评分**
   - HRV 数据中没有 "points" 评分，只有测量次数（measurement_count）
   
   **运动分析要求（必须遵守）**:
   - 必须检查 `workouts` 数组：如果数组非空，必须详细描述其中的运动记录
   - 描述内容包括：运动类型（如户外跑步、游泳）、时长（分钟）、能量消耗（千卡）、平均心率
   - 示例正确描述：「今日完成2次运动：户外跑步5.2公里（28分钟，消耗320千卡，平均心率145bpm）；力量训练（35分钟，消耗180千卡，平均心率125bpm）」
   - ⚠️ 严禁出现"没有运动"、"无结构化运动"、"未进行运动"等否定描述，当 `workouts` 数组非空时
   - 只有在 `workouts` 数组为空时，才可以描述为"今日无结构化运动记录"
   
   **AI 分析时必须包含以下个性化要素：**
   - 年龄参考：使用 `profile.age` 实际年龄（如30岁），而非默认假设值，参考该年龄段的心率/HRV正常范围
   - BMI计算：使用 `profile.height_cm` 和 `profile.weight_kg` 计算实际BMI（如 BMI 22.3），评估体重状态
   - 运动建议：基于实际BMI和年龄给出适合的运动量和类型
   - 能量消耗：基于实际年龄和体重给出个性化的卡路里消耗目标
   - 步幅估算：基于实际身高估算正常步幅（如身高175cm约步幅72-75cm），验证步数和距离的一致性
   
   **示例（假设数据为22岁/174cm/62kg时）：**
   - ❌ 错误："对于30岁男性，建议每日8,000-10,000步"
   - ✅ 正确："以您22岁、身高174cm、体重62kg（BMI 20.5）的年轻体型，建议每日8,000-10,000步，约对应5-6公里"
4. 关键写入：使用 write 工具将 JSON 写入 ai_analysis.json
5. 渲染生成（从仓库根目录执行）：
   cd ~/.openclaw/skills/health-report && \
   python3 scripts/generate_v5_medical_dashboard.py $(date -v-1d +%Y-%m-%d) < ai_analysis.json
6. 发送邮件（给所有成员）：
   python3 scripts/send_health_report_email.py $(date -v-1d +%Y-%m-%d) all
```

### 6. 周报定时任务 (Weekly Cron)
建议每周一上午 9:00 生成上周周报，汇总 7 天数据。

**Cron 设置：**
- 时间：`0 9 * * 1` (每周一 9:00)

**指令内容模板：**
```text
【每周健康周报 - V6.0.5 标准化流程】
1. 读取 config.json：获取 language 字段 (CN 或 EN)
2. 计算日期：获取上周一至上周日日期
   # macOS:
   START_DATE=$(date -v-7d +%Y-%m-%d)
   END_DATE=$(date -v-1d +%Y-%m-%d)
   # Linux:
   START_DATE=$(date -d '7 days ago' +%Y-%m-%d)
   END_DATE=$(date -d 'yesterday' +%Y-%m-%d)
3. AI 分析：基于整周数据趋势生成周报分析（总长度≥800；CN按字数，EN按单词数）。**language=EN 时建议全篇英文；系统会按中文占比阈值做语言校验（默认容许少量术语）。language=CN 时应以中文为主。**
4. 关键写入：使用 write 工具将 JSON 写入 weekly_analysis.json
5. 渲染生成（从仓库根目录执行）：
   cd ~/.openclaw/skills/health-report && \
   python3 scripts/generate_weekly_monthly_medical.py weekly "$START_DATE" "$END_DATE" < weekly_analysis.json
6. 发送邮件（给所有成员）：
   python3 scripts/send_health_report_email.py $END_DATE all
```

### 7. 月报定时任务 (Monthly Cron)
建议每月 1 日上午 10:00 生成上月月报，汇总整月数据。

**Cron 设置：**
- 时间：`0 10 1 * *` (每月 1 日 10:00)

**指令内容模板：**
```text
【每月健康月报 - V6.0.5 标准化流程】
1. 读取 config.json：获取 language 字段 (CN 或 EN)
2. 计算月份：获取上月年份和月份
   # macOS:
   YEAR=$(date -v-1m +%Y)
   MONTH=$(date -v-1m +%m)
   LAST_DAY=$(date -v-1d +%Y-%m-%d)  # 上月最后一天
   # Linux:
   YEAR=$(date -d '1 month ago' +%Y)
   MONTH=$(date -d '1 month ago' +%m)
   LAST_DAY=$(date -d 'yesterday' +%Y-%m-%d)  # 上月最后一天
3. AI 分析：基于整月数据趋势生成月报深度分析（总长度≥1000；CN按字数，EN按单词数）。**language=EN 时建议全篇英文；系统会按中文占比阈值做语言校验（默认容许少量术语）。language=CN 时应以中文为主。**
4. 关键写入：使用 write 工具将 JSON 写入 monthly_analysis.json
5. 渲染生成（从仓库根目录执行）：
   cd ~/.openclaw/skills/health-report && \
   python3 scripts/generate_weekly_monthly_medical.py monthly "$YEAR" "$MONTH" < monthly_analysis.json
6. 发送邮件（给所有成员）：
   python3 scripts/send_health_report_email.py $LAST_DAY all
```

> 月报趋势环比说明：代码会用"上月平均值"做对比，且要求上月可用缓存数据 **至少 15 天** 才计算环比；不足时趋势默认显示持平。

**注意：** 周报与月报的 AI 分析字段要求不同，请分别提供：

> **🤖 Agent 提示：** 以下 AI 分析 JSON 需要由你（Agent）基于真实健康数据生成，不是调用外部 API，也不是读取文件。你需要：
> 1. 读取缓存数据了解用户本周/本月健康指标
> 2. 基于真实数据生成有意义的分析文本（确保字数达标）
> 3. 通过 `echo '{...}' | python3 scripts/generate_xxx.py` 管道传给脚本
> 
> 详见 `AI_GENERATION_GUIDE.md`

**周报（weekly）最小要求：**
- `trend_analysis` 或 `weekly_analysis`（主体分析，建议总字数≥800字）
- `recommendations` 数组（每项需包含 `priority` / `title` / `content`）

周报示例：
```json
{
  "trend_analysis": "本周 HRV 呈现...",
  "recommendations": [
    {"priority": "high", "title": "优先保证睡眠", "content": "建议每晚..."},
    {"priority": "medium", "title": "增加有氧运动", "content": "建议每周..."}
  ]
}
```

**月报（monthly）最小要求：**
- `hrv_analysis` 或 `monthly_analysis`
- `sleep_analysis`
- `activity_analysis` 或 `key_findings`
- `trend_assessment` 或 `trend_forecast`
- `recommendations` 数组（每项需包含 `priority` / `title` / `content`）

月报示例：
```json
{
  "hrv_analysis": "本月 HRV 整体...",
  "sleep_analysis": "本月睡眠结构...",
  "activity_analysis": "本月活动量...",
  "trend_assessment": "本月整体趋势...",
  "recommendations": [
    {"priority": "high", "title": "先修复睡眠稳定性", "content": "建议..."},
    {"priority": "medium", "title": "提高中低强度有氧频次", "content": "建议..."}
  ]
}
```

**字数验证说明：**
- `validation_mode` **仅影响**长度/语言阈值类校验（metric_min/max_words、action_min/max_words、daily/weekly/monthly_min_words、monthly_trend_min_words）。
- 计数规则：`language=CN` 按“非空白字符数”（近似字数）统计；`language=EN` 按“英文单词数”统计。
- `validation_mode: strict` 时，长度不足/超限会报错退出。
- `validation_mode: warn` 时，长度不足/超限仅警告，继续生成。
- **注意**：缺少硬性必填 AI 字段（如日报的 priority、饮食字段）是硬错误，不受 warn 模式影响，仍会失败。
- `report_metrics.require_ai_for_selected=true` 触发的"已选指标缺少 AI 段落"目前走同一校验通道：strict 报错，warn 警告后继续。
- 日报会校验 `analysis_limits.metric_min_words` 与 `metric_max_words`，并校验 `daily_min_words`。
- 周报/月报总字数下限分别读取 `analysis_limits.weekly_min_words` 与 `analysis_limits.monthly_min_words`。
- 月报中 `trend_assessment` 的最小字数默认 150，可用 `analysis_limits.monthly_trend_min_words` 覆盖。
- 月报 `trend_assessment/trend_forecast` 建议≥150字：`strict` 模式报错，`warn` 模式仅警告并继续生成。
- **语言比例阈值**（可配置）：
  - `lang_en_max_chinese_ratio_strict`: EN严格模式允许的最大中文占比（默认0.15）
  - `lang_en_max_chinese_ratio_warn`: EN警告模式允许的最大中文占比（默认0.20）
  - `lang_cn_min_chinese_ratio_strict`: CN严格模式要求的最小中文占比（默认0.30）
  - `lang_cn_min_chinese_ratio_warn`: CN警告模式要求的最小中文占比（默认0.20）
- 月报趋势长度在 `verify_ai_analysis_monthly()` 中统一校验，避免重复提示。

**邮件发送参数：**

> 邮件主题/正文会跟随 `language`：`CN` 使用中文，`EN` 使用英文。

```bash
# 发送给特定成员（索引从0开始）
python3 scripts/send_health_report_email.py 2026-03-01 0    # 第一个成员
python3 scripts/send_health_report_email.py 2026-03-01 1    # 第二个成员

# 发送给所有成员
python3 scripts/send_health_report_email.py 2026-03-01 all

# 发送指定报告文件
python3 scripts/send_health_report_email.py 2026-03-01 0 report1.pdf report2.pdf
```

---

## ✨ V6.0.5 核心特性（含 5.8.x 兼容修复）

> 版本说明：当前发布主版本为 **V6.0.5**。文中保留的 "V5.8.1" 标识表示该能力在 5.8.1 首次引入并在 5.9.x/6.0.x 继续兼容。

*   **健康评分系统 V6.0.5**：全新五大核心评分指标
    - **Strain (0-21)**: 日心血管负荷评估，基于心率区间和力量训练计算
    - **Recovery (0-100%)**: 晨间恢复度，绿/黄/红三级状态指示
    - **Sleep Performance (0-100%)**: 自适应睡眠需求评估，根据前日负荷动态调整
    - **Body Age**: 基于睡眠、步数、心率等多指标的身体年龄计算
    - **Pace of Aging**: 7天衰老速度趋势分析，逆龄/停龄/正常/加速四级评估

*   **版本号支持**: config.json 支持 5.8.x / 5.9.x / 6.0.x 版本号
*   **数据字段修复 (V5.8.1)**：修复了 `active_energy` 字段名（原 `active_energy_burned`），确保活动能量数据正确提取
*   **睡眠数据结构兼容 (V5.8.1)**：增强睡眠数据解析，同时兼容 `data.sleep_analysis` 和 `data.metrics[].sleep_analysis` 两种数据结构
*   **评分算法个性化 (V5.8.1)**：健康得分基于年龄、性别、BMI 计算，同一体征对不同人群评分不同
*   **字数验证 (V5.8.1)**：支持 strict/warn 两种模式，确保 AI 分析内容质量
*   **多语言支持**：支持中英文界面切换，通过 `config.json` 的 `language` 字段一键切换（CN/EN）。呼吸率在 EN 模式下显示为 `breaths/min`，CN 模式下为 `次/分`。
*   **个人档案数据**：支持 `age`, `gender`, `height_cm`, `weight_kg` 个人档案配置，AI 分析时参考这些数据生成个性化建议
*   **智能邮件回退**：默认优先级 oauth2 → smtp → mail_app → local（可在 provider_priority 自定义）
*   **配置化路径**：所有脚本统一从 `config.json` 读取数据路径，无需修改代码
*   **真·数据对齐**：彻底修正了 Apple Health 跨天导出的偏移问题。日间活动从当日文件读取，睡眠数据从次日文件读取
*   **医疗级 UI**：采用全新的 V2 Medical 紫色主题模板，包含评分卡片、可配置动态指标表（默认12项，可扩展到32项）、心率图和深度睡眠结构分析
*   **原子化工作流**：将原本不稳定的 `edit` 局部替换逻辑升级为全量 `write` JSON 模式
*   **跨夜睡眠归属**：完善了睡眠统计逻辑，自动抓取 `当日 20:00` 至 `次日 12:00` 的睡眠记录并归属为当日恢复指标

### 模板回退策略

系统按以下顺序查找模板（以日报为例）：
1. `DAILY_TEMPLATE_MEDICAL_V2_{LANG}.html`（指定语言版本）
2. `DAILY_TEMPLATE_MEDICAL_{LANG}.html`（语言版，无版本号）
3. `DAILY_TEMPLATE_MEDICAL_V2.html`（默认中文V2版）
4. `DAILY_TEMPLATE_MEDICAL.html`（旧版兜底）

周报/月报同理：`{TYPE}_TEMPLATE_MEDICAL_{LANG}.html` → `{TYPE}_TEMPLATE_MEDICAL.html`

---

## 🛠️ 常用命令

*   **测试数据提取**：`python3 scripts/extract_data_v5.py YYYY-MM-DD`
*   **生成日报**：`python3 scripts/generate_v5_medical_dashboard.py YYYY-MM-DD < ai_analysis.json`
*   **生成周报/月报**：`python3 scripts/generate_weekly_monthly_medical.py weekly|monthly ...`
*   **手动补发邮件**：`python3 scripts/send_health_report_email.py YYYY-MM-DD`（默认会按成员文件名自动匹配该日期关联的日报/周报/月报）
*   **验证渲染环境**：`python3 scripts/verify_v5_environment.py`
*   **配置校验**：`python3 scripts/validate_config.py`
*   **指定文件校验**：`python3 scripts/validate_config.py --config ./config.json --schema ./config.schema.json`

### AI 输入文件自动清理（Feature）

为避免复用旧分析导致"缓存污染"，以下脚本在启动时会自动删除仓库根目录下的 `ai_analysis.json`（如果存在）：

- `scripts/generate_v5_medical_dashboard.py`
- `scripts/generate_weekly_monthly_medical.py`

这是一项**有意设计的功能**。建议始终通过标准输入（`< xxx_analysis.json`）喂入当次 AI 结果，不要依赖仓库里的旧 `ai_analysis.json` 文件。

---

## 📝 开发者规范 (V5.8.1)
*   **配置优先**：所有路径必须从 `config.json` 读取，禁止硬编码
*   **禁止编造**：数据缺失时必须显示 `--`，严禁 AI 估算比例
*   **长度红线**：AI 指标分析段落必须在 150-200（CN按字数，EN按单词数），核心行动建议 250-300（CN按字数，EN按单词数）
*   **数据来源**：日报主要从 Apple Health 当日源文件读取并在生成后写缓存；周/月报从 daily cache 聚合。
*   **模板完整性**：渲染后若仍存在 `{{PLACEHOLDER}}`，脚本会直接报错退出（防止空字段混入正式报告）。

---

## 📁 配置文件说明

配置文件查找顺序（按优先级）：
1. 仓库根目录 `config.json`
2. `~/.openclaw/workspace-health/config.json`

## 邮件配置项补充说明

`email_config` 可选字段：
- `max_retries`: 发送失败重试次数（默认 3）
- `retry_delay`: 重试间隔秒数（默认 5）

## config.json 结构
```json
{
  "version": "6.0.3",
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
    "monthly_min_words": 1000,
    "monthly_trend_min_words": 150,
    "lang_en_max_chinese_ratio_strict": 0.15,
    "lang_en_max_chinese_ratio_warn": 0.20,
    "lang_cn_min_chinese_ratio_strict": 0.30,
    "lang_cn_min_chinese_ratio_warn": 0.20
  },
  "email_config": {
    "provider_priority": ["oauth2", "smtp", "mail_app", "local"],
    "oauth2": {
      "enabled": false,
      "provider": "gmail",
      "client_id": "your-client-id.apps.googleusercontent.com",
      "client_secret": "your-client-secret",
      "refresh_token": "your-refresh-token",
      "sender_email": "your-email@gmail.com"
    },
    "smtp": {
      "enabled": false,
      "server": "smtp.gmail.com",
      "port": 587,
      "sender_email": "your-email@gmail.com",
      "password": "your-app-password",
      "use_tls": true
    },
    "mail_app": {
      "enabled": true
    }
  },
  "receiver_email": "target_email@example.com",
  "language": "CN",
  "validation_mode": "strict",
  "output_dir": "~/.openclaw/workspace/shared/health-reports/upload",
  "cache_dir": "~/.openclaw/workspace/shared/health-reports/cache"
}
```

### analysis_limits 默认值（完整）

| 字段 | 默认值 | 说明 |
|------|--------|------|
| `metric_min_words` | 150 | 单个指标分析最小字数 |
| `metric_max_words` | 200 | 单个指标分析最大字数 |
| `action_min_words` | 250 | 行动建议最小字数 |
| `action_max_words` | 300 | 行动建议最大字数 |
| `daily_min_words` | 500 | 日报总字数下限 |
| `weekly_min_words` | 800 | 周报总字数下限 |
| `monthly_min_words` | 1000 | 月报总字数下限 |
| `monthly_trend_min_words` | 150 | 月报趋势评估最小字数 |
| `lang_en_max_chinese_ratio_strict` | 0.15 | EN严格模式最大中文占比 |
| `lang_en_max_chinese_ratio_warn` | 0.20 | EN警告模式最大中文占比 |
| `lang_cn_min_chinese_ratio_strict` | 0.30 | CN严格模式最小中文占比 |
| `lang_cn_min_chinese_ratio_warn` | 0.20 | CN警告模式最小中文占比 |

### 📊 report_metrics（日报动态指标表）

`report_metrics` 用于控制日报"详细指标分析"区域展示哪些指标、如何排序、是否隐藏无数据行。

```json
"report_metrics": {
  "selected": [
    "hrv", "resting_hr", "steps", "distance", "active_energy", "spo2",
    "flights_climbed", "apple_stand_time", "basal_energy_burned", "respiratory_rate",
    "vo2_max", "apple_exercise_time"
  ],
  "sort_by_importance": true,
  "show_empty_categories": true,
  "show_sleep_in_metrics_table": false,
  "hide_no_data_metrics": true,
  "require_ai_for_selected": true,
  "category_order": [
    "core_health", "cardio_fitness", "sleep_recovery", "activity_mobility",
    "running_advanced", "walking_gait", "stairs_strength", "environment_audio"
  ],
  "importance_overrides": {
    "vo2_max": 10,
    "sleep_total_hours": 10,
    "environmental_audio_exposure": 0
  }
}
```

说明：
- `selected`：选择显示的指标（默认 12 项，可扩展到 32 项）。
- `importance_overrides`：可把某项重要性设为 `0`（从表中移除）。
- `require_ai_for_selected=true`：若某指标映射到 AI 字段且缺失，校验会失败。
- `show_sleep_in_metrics_table`：当前生效字段。旧字段 `include_sleep_metrics_in_table` 仍兼容，但已废弃，建议迁移。

#### 支持的 32 个指标（可用于 `report_metrics.selected`）

- **core_health（10）**：`hrv`, `resting_hr`, `heart_rate_avg`, `steps`, `distance`, `active_energy`, `spo2`, `respiratory_rate`, `apple_stand_time`, `basal_energy_burned`
- **cardio_fitness（2）**：`vo2_max`, `physical_effort`
- **sleep_recovery（4）**：`sleep_total_hours`, `sleep_deep_hours`, `sleep_rem_hours`, `breathing_disturbances`
- **activity_mobility（2）**：`apple_exercise_time`, `apple_stand_hour`
- **stairs_strength（2）**：`flights_climbed`, `stair_speed_up`
- **running_advanced（5）**：`running_speed`, `running_power`, `running_stride_length`, `running_ground_contact_time`, `running_vertical_oscillation`
- **walking_gait（5）**：`walking_speed`, `walking_step_length`, `walking_heart_rate_average`, `walking_asymmetry_percentage`, `walking_double_support_percentage`
- **environment_audio（2）**：`headphone_audio_exposure`, `environmental_audio_exposure`

### report_metrics 五套示例配置（按人群）

仓库已提供 5 个可直接复制使用的配置示例（都在 `examples/config-presets/` 目录）：

| 示例文件 | 指标数 | 适用人群 | 特点 |
|---|---:|---|---|
| `config.example.general-12.json` | 12 | 大多数日常用户 | 轻量核心看板，噪声低、可读性高 |
| `config.example.sleep-focus-16.json` | 16 | 睡眠问题/恢复优先人群 | 强化睡眠分期、呼吸扰动与恢复指标 |
| `config.example.weight-management-18.json` | 18 | 体重管理/代谢优化人群 | 强调活动能量、基础代谢、站立与步行机能 |
| `config.example.runner-advanced-24.json` | 24 | 跑步训练进阶人群 | 增加跑步动力学与睡眠恢复联合观察 |
| `config.example.full-32.json` | 32（全选） | 精细化追踪/研究用途 | 全指标开启；默认 `hide_no_data_metrics=false`，便于完整巡检 |

快速使用方式（示例：切到跑步进阶版）：

```bash
cp examples/config-presets/config.example.runner-advanced-24.json config.json
python3 scripts/validate_config.py --config ./config.json --schema ./config.schema.json
```

> 提示：
> - 如果你不想看到空指标，请把 `hide_no_data_metrics` 设为 `true`。
> - 如果你希望睡眠指标出现在动态指标表中，请把 `show_sleep_in_metrics_table` 设为 `true`。

### 👥 多成员配置（最多3人）

支持为家庭成员分别生成健康报告。**注意：硬编码限制最多3人。**

**邮件发送优先级**：成员配置中的 `email` 字段 > 全局 `receiver_email`。如果成员配置了 email，则使用该地址；否则使用全局 receiver_email。

```json
{
  "version": "6.0.3",
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
    }
  ],
  "analysis_limits": {...},
  "email_config": {...},
  "language": "CN"
}
```

**成员名文件名冲突提醒（safe_member_name）**：
- 报告文件名会使用 `safe_member_name(name)` 作为后缀
- 例如 `A B`、`A/B`、`A_B` 可能都转换为同一个安全名 `A_B`
- 若不同成员转换后同名，`validate_config.py` 会报冲突，请修改成员名称避免覆盖

**✅ V5.8.1+ 完整多成员支持：**

> 当前实现上限：最多处理前 3 位成员（提取 / 生成 / 发送保持一致）。超过 3 位时会打印 warning 并自动截断。

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

**提取所有成员（V5.8.1+）：**
```bash
# 使用 all 参数提取所有成员的数据（最多前 3 位）
python3 scripts/extract_data_v5.py 2026-03-01 all

注意：all 模式最多处理前 3 位成员。

# 输出格式：
# {
#   "date": "2026-03-01",
#   "members_count": 2,
#   "members": [
#     {
#       "date": "2026-03-01",
#       "data_source": "Apple Health",
#       "profile": {"name": "成员1", "age": 30, ...},
#       "hrv": {"value": 45.2, "measurement_count": 10},
#       "resting_hr": {"value": 62},
#       ...
#     },
#     {
#       "date": "2026-03-01",
#       "data_source": "Apple Health", 
#       "profile": {"name": "成员2", "age": 28, ...},
#       "hrv": {"value": 52.1, "measurement_count": 12},
#       ...
#     }
#   ]
# }
# 注意：每个成员的数据包含完整的单日数据结构，profile 在顶层。
```

**在定时任务中使用（推荐）：**
在 OpenClaw 定时任务指令中使用 `all` 参数，一次生成所有成员的报告：
```text
【每日健康日报 - V6.0.5 全成员流程】
1. 读取 config.json：获取所有成员配置
2. 提取数据：为每个成员分别提取数据
   python3 scripts/extract_data_v5.py $(date -v-1d +%Y-%m-%d) all
3. AI 分析：为每个成员分别生成分析报告（考虑年龄、性别、BMI等个性化因素）
4. 渲染生成：为每个成员生成独立 PDF 报告
5. 发送邮件：分别发送给每个成员配置的邮箱
```

### 🌐 多语言支持 (V5.8.1)

通过 `config.json` 中的 `language` 字段切换报告语言：

- `"language": "CN"` - 中文界面（睡眠质量、运动记录、评级等）
- `"language": "EN"` - 英文界面（Sleep Quality / Workout Records / Excellent / Good 等）

**切换步骤：**
1. 编辑 `config.json` 修改 `language` 字段
2. 重新生成报告即可自动切换语言

**支持翻译的界面元素：**
- 所有标题（睡眠质量、运动记录、动态指标分析区等）
- 评分评级（Excellent / Good / Average / Normal）
- 运动状态标签（Completed / 已完成）
- 心率图表标签（Heart Rate / Avg / Max / Time）
- 睡眠状态（Normal / Insufficient Data）
- 日期格式（2026年2月 / Feb 2026）

**重要：** AI 分析语言需与 `language` 配置一致：
- `CN` 模式：应以中文为主
- `EN` 模式：应以英文为主（允许少量指标术语）

当前语言检测基于中文字符占比阈值（默认非 strict 模式下：EN 允许少量中文术语，CN 也允许少量英文术语）。

**严格模式验证：**
当 `validation_mode: strict` 时，脚本会检查：
1. AI 分析语言与配置是否匹配
2. 各字段字数是否达标
3. 必填字段是否齐全

任一检查失败将报错退出，不会生成报告。

---

## 🔧 故障排除

### 报告生成失败
1. 检查 `config.json` 是否存在且格式正确
2. 验证 `health_dir` 和 `workout_dir` 路径是否正确
3. 运行 `python3 scripts/verify_v5_environment.py` 检查环境

### 数据提取异常
1. 确认 Health Auto Export 已正确导出数据
2. 检查 JSON 文件是否损坏
3. 验证文件路径在 `config.json` 中配置正确

### 活动能量显示为 0 或缺失
- **原因**：V5.8.1 之前版本使用 `active_energy_burned` 字段名，新版 Health Auto Export 使用 `active_energy`
- **解决**：确保使用 V5.8.1+ 版本，已修复字段名兼容问题

### 睡眠数据缺失或显示为 0
- **原因**：睡眠数据结构可能在 `data.sleep_analysis` 或 `data.metrics[].sleep_analysis` 中
- **解决**：V5.8.1+ 已增强睡眠数据解析，同时兼容两种数据结构
- **检查**：确认睡眠数据存储在次日文件中（如 2月21日的睡眠在 2月22日文件中）

### 周报/月报趋势图空白
- **原因**：周/月报趋势图依赖 CDN: `https://cdn.jsdelivr.net/npm/chart.js`
- **解决**：离线环境可能图表空白，但 PDF 主体仍可生成；如需完全离线，可将 Chart.js 改为本地静态资源

### 多成员数据提取失败
- **原因**：成员索引超出配置范围
- **解决**：V5.8.1+ 已添加边界检查，会自动回退到第一个成员

### AI分析数据格式要求（多成员）

当使用 `all` 参数提取多成员数据时，AI分析的JSON输入支持以下格式:

**格式1: 单成员对象**（仅有一个成员时）
```json
{
  "hrv": "...",
  "priority": {...}
}
```

**格式2: 成员数组**（推荐）
```json
{
  "members": [
    {"hrv": "...", "priority": {...}},  // 成员0
    {"hrv": "...", "priority": {...}},  // 成员1
    {"hrv": "...", "priority": {...}}   // 成员2
  ]
}
```

**格式3: 成员名映射**（用于严格匹配）
```json
{
  "张三": {"hrv": "...", "priority": {...}},
  "李四": {"hrv": "...", "priority": {...}}
}
```

**匹配优先级（从高到低）:**
1. 成员名完全匹配
2. 安全成员名匹配（safe_member_name转换后）
3. 索引匹配（数组顺序）

**当前生成入口默认严格匹配（strict=True）:**
- 日报/周报/月报脚本都会使用严格模式
- 找不到成员对应 AI 分析时，不会兜底复用第一份分析，而是报错或跳过该成员

**推荐做法**: 使用格式2（members数组），顺序与config.json中的members顺序一致。

### 报告生成成功但内容为空/太少
- **原因**：AI 分析字数未达到 `analysis_limits` 要求，或 `validation_mode` 为 `strict`
- **解决**：
  - 检查 `config.json` 中的 `validation_mode` 设置
  - 改为 `warn` 模式可跳过字数检查（不推荐长期使用）
  - 或重新生成足够字数的 AI 分析

### 评分与预期不符
- **原因**：评分算法基于固定公式，会考虑年龄/性别/BMI 差异
- **示例**：同样的 HRV 50ms，22岁男性评为"一般"，35岁男性可能评为"良好"
- **检查**：确认 `config.json` 中的个人档案数据（age/gender/height/weight）正确

### 邮件发送找不到报告文件
- **原因**: send_health_report_email.py 使用严格文件名匹配,旧文件可能不匹配
- **解决**: 确保报告文件名格式为 `{date}-daily-v5-medical-{safe_name}.pdf`,其中 safe_name 是成员名去除空格和特殊字符后的版本

---

## 📊 数据字段说明

### 提取的指标字段

| 字段名 | 单位 | 说明 |
|--------|------|------|
| `hrv.value` | ms | 心率变异性平均值 |
| `hrv.measurement_count` | 计数 | HRV 数据点数量（测量次数） |
| `resting_hr.value` | bpm | 静息心率 |
| `steps` | 步 | 当日步数 |
| `distance_km` | km | 步行/跑步距离 |
| `active_energy_kcal` | kcal | 活跃能量消耗 |
| `flights_climbed` | 层 | 爬楼层数 |
| `stand_time_min` | 分钟 | 站立时间 |
| `spo2` | % | 血氧饱和度 |
| `basal_energy_kcal` | kcal | 基础代谢能量 |
| `respiratory_rate` | 次/分 | 呼吸频率 |
| `sleep.total_hours` | 小时 | 总睡眠时长 |
| `sleep.deep_hours` | 小时 | 深睡时长 |
| `sleep.core_hours` | 小时 | 核心睡眠时长 |
| `sleep.rem_hours` | 小时 | REM睡眠时长 |
| `sleep.awake_hours` | 小时 | 清醒时长 |

### AI 分析字段必填说明

日报字段分为"硬性必填"和"建议完整提供"两类：

**硬性必填（缺少会报错）**
- `sleep`
- `workout`（即使当天无运动也必须提供文本）
- `priority.title`, `priority.problem`, `priority.action`, `priority.expectation`
- `ai2_title`, `ai2_problem`, `ai2_action`, `ai2_expectation`
- `ai3_title`, `ai3_problem`, `ai3_action`, `ai3_expectation`
- `breakfast`, `lunch`, `dinner`, `snack`

**建议完整提供（默认缺失不阻断，但会影响质量）**
- 指标分析 12 项：`hrv`, `resting_hr`, `steps`, `distance`, `active_energy`, `spo2`, `flights`, `stand`, `basal`, `respiratory`, `sleep`, `workout`
- 若配置 `report_metrics.require_ai_for_selected=true`，则已选指标映射到 AI 字段但缺失时会触发校验失败。

### AI 分析 JSON 字段要求

| 字段名 | 长度要求（默认） | 说明 |
|--------|------------------|------|
| `hrv` ~ `workout`（12项指标段落） | 150-200（CN按字数/EN按单词数）/段 | 建议完整提供；`sleep` / `workout` 同时属于硬性必填 |
| `priority.action` | 250-300（CN按字数/EN按单词数） | 硬性必填 |
| `priority.title` `priority.problem` `priority.expectation` | ≥1 字 | 硬性必填 |
| `ai2_*` / `ai3_*` | ≥1 字 | 硬性必填 |
| `breakfast` `lunch` `dinner` `snack` | ≥1 字 | 硬性必填 |
| `daily_min_words` | 默认 500（来自配置） | 日报总字数下限 |

> 说明：以上阈值可通过 `analysis_limits` 配置覆盖。

---

## 文档职责（避免重复）
- `SKILL.md`：给 Agent 的快速执行卡片（短）
- `README.md`：给用户的完整说明手册（长）

如果两边内容冲突，以 README.md 的完整说明为准，再同步更新 SKILL.md 的摘要。

---

## 许可证
MIT License
