# Health Agent V5.7.1 - OpenClaw 专业健康分析 Skill

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
首次使用前，请编辑 `config.json` 配置你的数据路径：

```json
{
  "version": "5.7.1",
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
- `health_dir`: Apple Health 数据导出路径（需包含 `HealthAutoExport-YYYY-MM-DD.json` 文件）
- `workout_dir`: 运动数据导出路径
- `email`: 报告接收邮箱
- `email_config`: 邮件发送配置（SMTP服务器、端口、发件邮箱、密码）
- `language`: 报告界面语言（`CN`=中文, `EN`=英文）
- `age`, `gender`, `height_cm`, `weight_kg`: 个人档案数据，用于 AI 生成个性化分析（BMI计算、年龄/性别特定的心率参考范围等）

### 4. 数据准备
确保你的 [Health Auto Export](https://apps.apple.com/us/app/health-auto-export-json-csv/id111556706) 导出的 JSON 文件同步到了配置的路径中。

**数据文件格式要求：**
- 文件名格式：`HealthAutoExport-YYYY-MM-DD.json`
- 活动数据（步数、心率等）存储在当日文件中
- 睡眠数据存储在次日文件中（系统会自动读取）

**路径配置说明：**
- `~/我的云端硬盘/` 是 Google Drive 的默认中文名称
- 如使用 iCloud Drive：`~/Library/Mobile Documents/com~apple~CloudDocs/Health Data`
- 如使用 OneDrive：`~/OneDrive/Health Data`
- 如使用本地目录：`~/Documents/Health Data`

### 5. OpenClaw 定时任务 (Cron) 配置
在 OpenClaw 中添加日报任务，建议时间 `12:10`（确保当日数据已同步完成）。

**指令内容模板：**
```text
【每日健康日报 - V5.7.1 标准化流程】
1. 读取 config.json：获取配置的 Health 路径以及 language 字段 (CN 或 EN)
2. 提取数据：为所有成员提取当日数据
   python3 scripts/extract_data_v5.py $(date -v-1d +%Y-%m-%d) all
3. AI 分析：基于提取的 JSON 数据生成详细分析。**必须严格使用 JSON 中 `profile` 字段的实际个人档案信息（如：年龄{X}岁、性别{Y}、身高{Z}cm、体重{W}kg）、计算BMI并据此给出个性化建议。** 每项指标分析 150-200 字，核心建议 250-300 字。**如果 language 为 EN，则必须全篇使用纯英文输出；如果为 CN，则使用纯中文。**
   
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
5. 渲染生成：
   cd ~/.openclaw/skills/health-report/scripts && \
   python3 generate_v5_medical_dashboard.py $(date -v-1d +%Y-%m-%d) < ../ai_analysis.json
6. 发送邮件（给所有成员）：
   python3 scripts/send_health_report_email.py $(date -v-1d +%Y-%m-%d) all
```

### 6. 周报定时任务 (Weekly Cron)
建议每周一上午 9:00 生成上周周报，汇总 7 天数据。

**Cron 设置：**
- 时间：`0 9 * * 1` (每周一 9:00)

**指令内容模板：**
```text
【每周健康周报 - V5.7.1 标准化流程】
1. 读取 config.json：获取 language 字段 (CN 或 EN)
2. 计算日期：获取上周一至上周日日期
   START_DATE=$(date -v-7d +%Y-%m-%d)
   END_DATE=$(date -v-1d +%Y-%m-%d)
3. AI 分析：基于整周数据趋势生成周报分析（总字数≥800字）。**如果 language 为 EN，则必须全篇使用纯英文输出；如果为 CN，则使用纯中文。**
4. 关键写入：使用 write 工具将 JSON 写入 weekly_analysis.json
5. 渲染生成：
   cd ~/.openclaw/skills/health-report/scripts && \
   python3 generate_weekly_monthly_medical.py weekly "$START_DATE" "$END_DATE" < ../weekly_analysis.json
6. 发送邮件（给所有成员）：
   python3 scripts/send_health_report_email.py $END_DATE all
```

### 7. 月报定时任务 (Monthly Cron)
建议每月 1 日上午 10:00 生成上月月报，汇总整月数据。

**Cron 设置：**
- 时间：`0 10 1 * *` (每月 1 日 10:00)

**指令内容模板：**
```text
【每月健康月报 - V5.7.1 标准化流程】
1. 读取 config.json：获取 language 字段 (CN 或 EN)
2. 计算月份：获取上月年份和月份
   YEAR=$(date -v-1m +%Y)
   MONTH=$(date -v-1m +%m)
   LAST_DAY=$(date -v-1d +%Y-%m-%d)  # 上月最后一天
3. AI 分析：基于整月数据趋势生成月报深度分析（总字数≥1000字）。**如果 language 为 EN，则必须全篇使用纯英文输出；如果为 CN，则使用纯中文。**
4. 关键写入：使用 write 工具将 JSON 写入 monthly_analysis.json
5. 渲染生成：
   cd ~/.openclaw/skills/health-report/scripts && \
   python3 generate_weekly_monthly_medical.py monthly "$YEAR" "$MONTH" < ../monthly_analysis.json
6. 发送邮件（给所有成员）：
   python3 scripts/send_health_report_email.py $LAST_DAY all
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

**字数验证说明：**
- 设置 `validation_mode: strict` 时，字数不足会报错退出
- 设置 `validation_mode: warn` 时，字数不足仅警告，继续生成

**邮件发送参数：**
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

## ✨ V5.7.1 核心特性

*   **数据字段修复 (V5.7.1)**：修复了 `active_energy` 字段名（原 `active_energy_burned`），确保活动能量数据正确提取
*   **睡眠数据结构兼容 (V5.7.1)**：增强睡眠数据解析，同时兼容 `data.sleep_analysis` 和 `data.metrics[].sleep_analysis` 两种数据结构
*   **评分算法个性化 (V5.7.1)**：健康得分基于年龄、性别、BMI 计算，同一体征对不同人群评分不同
*   **字数验证 (V5.7.1)**：支持 strict/warn 两种模式，确保 AI 分析内容质量
*   **多语言支持**：支持中英文界面切换，通过 `config.json` 的 `language` 字段一键切换（CN/EN）
*   **个人档案数据**：支持 `age`, `gender`, `height_cm`, `weight_kg` 个人档案配置，AI 分析时参考这些数据生成个性化建议
*   **智能邮件回退**：自动级联 - Mail.app → Gmail SMTP → 通用 SMTP → 本地副本
*   **配置化路径**：所有脚本统一从 `config.json` 读取数据路径，无需修改代码
*   **真·数据对齐**：彻底修正了 Apple Health 跨天导出的偏移问题。日间活动从当日文件读取，睡眠数据从次日文件读取
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

## 📝 开发者规范 (V5.7.1)
*   **配置优先**：所有路径必须从 `config.json` 读取，禁止硬编码
*   **禁止编造**：数据缺失时必须显示 `--`，严禁 AI 估算比例
*   **字数红线**：AI 指标分析段落必须在 150-200 字，核心行动建议 250-300 字
*   **单日单源**：每份报告必须仅依赖当日产生的 Data Cache JSON

---

## 📁 配置文件说明

### config.json 结构
```json
{
  "version": "5.7.1",
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

支持为家庭成员分别生成健康报告。**注意：硬编码限制最多3人。**

```json
{
  "version": "5.7.1",
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

**✅ V5.7.1+ 完整多成员支持：**

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
【每日健康日报 - V5.7.1 全成员流程】
1. 读取 config.json：获取所有成员配置
2. 提取数据：为每个成员分别提取数据
   python3 scripts/extract_data_v5.py $(date -v-1d +%Y-%m-%d) all
3. AI 分析：为每个成员分别生成分析报告（考虑年龄、性别、BMI等个性化因素）
4. 渲染生成：为每个成员生成独立 PDF 报告
5. 发送邮件：分别发送给每个成员配置的邮箱
```

### 🌐 多语言支持 (V5.7.1)

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

**重要：** AI 分析的语言必须与 `language` 配置严格一致：
- `CN` 模式：AI 必须输出纯中文
- `EN` 模式：AI 必须输出纯英文

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
- **原因**：V5.7.0 之前版本使用 `active_energy_burned` 字段名，新版 Health Auto Export 使用 `active_energy`
- **解决**：确保使用 V5.7.1+ 版本，已修复字段名兼容问题

### 睡眠数据缺失或显示为 0
- **原因**：睡眠数据结构可能在 `data.sleep_analysis` 或 `data.metrics[].sleep_analysis` 中
- **解决**：V5.7.1+ 已增强睡眠数据解析，同时兼容两种数据结构
- **检查**：确认睡眠数据存储在次日文件中（如 2月21日的睡眠在 2月22日文件中）

### 多成员数据提取失败
- **原因**：成员索引超出配置范围
- **解决**：V5.7.1+ 已添加边界检查，会自动回退到第一个成员

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

---

## 📊 数据字段说明

### 提取的指标字段

| 字段名 | 单位 | 说明 |
|--------|------|------|
| `hrv.value` | ms | 心率变异性平均值 |
| `hrv.points` | 计数 | HRV 数据点数量 |
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

### AI 分析 JSON 字段要求

| 字段名 | 字数要求 | 说明 |
|--------|----------|------|
| `hrv` | 150-200字 | HRV 分析 |
| `resting_hr` | 150-200字 | 静息心率分析 |
| `steps` | 150-200字 | 步数分析 |
| `distance` | 150-200字 | 距离分析 |
| `active_energy` | 150-200字 | 活动能量分析 |
| `spo2` | 150-200字 | 血氧分析 |
| `flights` | 150-200字 | 爬楼分析 |
| `stand` | 150-200字 | 站立分析 |
| `basal` | 150-200字 | 基础代谢分析 |
| `respiratory` | 150-200字 | 呼吸率分析 |
| `sleep` | 150-200字 | 睡眠分析 |
| `workout` | 150-200字 | 运动分析 |
| `priority.title` | ≥10字 | 最高优先级标题 |
| `priority.problem` | ≥80字 | 问题识别 |
| `priority.action` | ≥100字 | 行动计划 |
| `priority.expectation` | ≥70字 | 预期效果 |

---

## 许可证
MIT License
