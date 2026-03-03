---
name: health-report
description: 基于 Apple Health 数据的 AI 健康分析报告生成工具。支持从 Health Auto Export 导出的 JSON 中提取 HRV、步数、睡眠等 11 项核心指标，并利用大模型进行深度分析，最终通过 V2 Medical 模板渲染为精美的 PDF 报告并自动发送邮件。使用场景：(1) 生成昨日/今日健康日报，(2) 分析周/月健康趋势，(3) 监控 HRV、静息心率等关键生理指标。
---

# Health Report V5.8.1

> 版本说明：当前发布主版本为 **V5.8.1**。V5.8.1 功能在 V5.8.1 继续兼容。

此 Skill 能够将 Apple Health 的原始导出数据转化为深度、个性化的健康报告。

## ✨ V5.8.1 更新亮点

- **🔐 OAuth2 邮件支持**：新增 Gmail OAuth2 认证，比 SMTP 更安全
- **📧 Provider 架构**：支持 OAuth2/SMTP/Mail.app/Local 四种发送方式，可配置优先级和自动 fallback
- **🛌 可配置睡眠读取**：支持 `next_day`（次日文件）和 `same_day`（当天文件）两种模式
- **🐛 数据字段修复**：修复 `active_energy` 字段名，睡眠解析兼容性增强
- **👤 个人档案支持**：AI 分析时参考年龄、性别、身高、体重生成个性化建议
- **🌍 多语言支持**：一键切换中英文报告（CN/EN）
- **👥 多成员支持**：最多支持 3 位家庭成员分别生成报告

## 🚀 快速启动

### 1. 配置文件设置

首先创建或编辑 `config.json` 文件（V5.8.1 新版配置结构）：

```json
{
  "version": "5.8.1",
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

**关键配置项：**
- `health_dir`: Apple Health 数据导出目录（需包含 `HealthAutoExport-YYYY-MM-DD.json` 文件）
- `workout_dir`: Workout 数据导出目录
- `members`: 支持多成员配置（最多3人）
- `language`: 报告语言（`CN`=中文, `EN`=英文）
- `age/gender/height_cm/weight_kg`: 个人档案，用于 AI 生成个性化分析
- `email_config`: 邮件发送配置（V5.8.1 Provider 架构）
  - `provider_priority`: 发送方式优先级 `['oauth2', 'smtp', 'mail_app', 'local']`
  - `oauth2`: Gmail OAuth2 认证（推荐）
  - `smtp`: SMTP 服务器发送
  - `mail_app`: macOS Mail.app（仅 Mac）
  - `local`: 本地保存，不发送邮件
- `sleep_config`: 睡眠数据读取配置
  - `read_mode`: `next_day`（次日文件）或 `same_day`（当天文件）

**OAuth2 快速配置：**
```bash
python3 scripts/setup_oauth2.py
```
交互式引导完成 Google Cloud Console 配置、浏览器授权、自动保存 refresh_token。

**配置路径注意事项：**
- `health_dir` 默认使用 `~/我的云端硬盘/Health Auto Export/Health Data`（Google Drive 中文名）
- 如使用其他云盘（iCloud/OneDrive），请修改为对应路径
- 所有路径支持 `~` 展开为用户主目录

### 硬编码限制说明

以下功能有固定的代码限制：

| 限制项 | 硬编码值 | 说明 |
|--------|----------|------|
| 最大成员数 | 3人 | `MEMBER_COUNT = min(len(MEMBERS), 3)` |
| 睡眠窗口 | 20:00-次日12:00 | 跨夜睡眠归属当日 |
| 趋势阈值 | ±5% | 环比变化 >5% 标记为 increase/decrease |
| 字数验证（周报） | ≥800字 | `weekly_min_words` |
| 字数验证（月报） | ≥1000字 | `monthly_min_words` |
| 趋势评估字数 | ≥150字 | 月报趋势评估单独检查 |

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
   
   **⚠️ 强制要求：AI 分析必须使用 profile 数据**
   
   AI 生成分析时必须遵守以下规则：
   1. **年龄**：必须使用实际 `profile.age`，禁止默认使用30岁
      - 22岁男性的静息心率优秀标准是 <60 bpm
      - 30岁男性的静息心率优秀标准是 <65 bpm
   
   2. **BMI 计算**：必须使用 `profile.height_cm` 和 `profile.weight_kg` 计算
      - BMI = weight_kg / (height_cm/100)^2
      - 必须引用 BMI 值并评估体重状态
   
   3. **步幅验证**：基于身高估算正常步幅（身高cm × 0.414）
      - 验证步数和距离的一致性
   
   4. **个性化能量目标**：基于年龄和体重
      - 22岁、62kg男性：建议 400-500 kcal/天
      - 30岁、70kg男性：建议 450-600 kcal/天
   
   5. **运动建议**：基于 BMI 和年龄
      - BMI < 18.5：侧重增肌力量训练
      - BMI 18.5-24：有氧运动 + 力量训练平衡
      - BMI > 24：侧重有氧减脂
   
   **示例对比：**
   - ❌ 错误："对于30岁男性，建议每日8,000-10,000步"
   - ✅ 正确："以您22岁、身高174cm、体重62kg（BMI 20.5）的年轻体型，建议每日8,000-10,000步，约对应5-6公里"
   
   **检查清单：**
   - [ ] 分析中明确引用了实际年龄（如22岁）而非默认30岁？
   - [ ] 是否计算并引用了 BMI 值？
   - [ ] 能量消耗建议是否基于年龄和体重个性化？
   - [ ] 心率/HRV参考范围是否基于实际年龄？

3. **渲染 PDF**：
   ```bash
   python3 scripts/generate_v5_medical_dashboard.py YYYY-MM-DD < ai_analysis.json
   ```

4. **发送邮件**（可选）：
   ```bash
   python3 scripts/send_health_report_email.py YYYY-MM-DD
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

| 脚本 | 功能说明 |
|------|----------|
| `scripts/extract_data_v5.py` | 从 config.json 配置的路径读取数据，执行严格的时间戳过滤。支持单成员/多成员/全成员 (`all`) 提取 |
| `scripts/generate_v5_medical_dashboard.py` | 日报生成主脚本，自动读取 config.json 配置，渲染 V2 Medical 主题 PDF |
| `scripts/generate_weekly_monthly_medical.py` | 趋势报告生成脚本，支持周报/月报 |
| `scripts/send_health_report_email.py` | 邮件分发脚本，读取 config.json 中的邮件配置，支持多成员邮件发送 |
| `scripts/verify_v5_environment.py` | 环境验证脚本，检查依赖和配置是否正确 |

## 📝 V5.8.1 强制规范

- **配置优先**：所有脚本必须从 `config.json` 读取路径配置，禁止硬编码
- **语言切换**：通过 `config.json` 中的 `language` 字段（CN/EN）切换报告界面语言
- **严格对齐**：日报必须对原始数据执行 `00:00-23:59` 过滤，日间活动从当日文件读取，睡眠从次日文件读取
- **跨夜睡眠**：睡眠窗口定义为当日 20:00 至次日 12:00
- **禁止估算**：数据缺失处必须显示 `--`，严禁 AI 编造
- **原子写入**：必须使用 `write` 工具全量更新 `ai_analysis.json`，禁止 `edit` 局部替换
- **字数红线**：AI 指标分析 150-200 字，行动建议 250-300 字

### 🧮 评分算法（硬编码）

以下评分由代码自动计算，非 AI 生成：

**健康得分公式：**
```
得分 = HRV×30% + 睡眠×25% + 活动×25% + 血氧/呼吸×20%

HRV 评分基准：
- 优秀: >55ms (男性), >60ms (女性)
- 良好: 45-55ms (男性), 50-60ms (女性)  
- 一般: 35-45ms (男性), 40-50ms (女性)
- 偏低: <35ms (男性), <40ms (女性)

睡眠评分基准：
- 优秀: 7.5-9小时且深度睡眠>20%
- 良好: 7-7.5小时或深度睡眠15-20%
- 一般: 6-7小时或深度睡眠10-15%
- 不足: <6小时或深度睡眠<10%
```

**BMI 分类（WHO 标准，硬编码）：**
- < 18.5: 偏瘦
- 18.5-24.9: 正常
- 25.0-29.9: 超重
- ≥ 30.0: 肥胖

**心率参考范围（年龄相关）：**
```
静息心率优秀标准：
- 20-25岁男性: <60 bpm
- 25-30岁男性: <65 bpm  
- 30-35岁男性: <68 bpm
- 女性标准比男性高 5-8 bpm
```

**恢复度计算：**
```
恢复度 = f(HRV趋势, 睡眠时长, 睡眠质量)
- HRV 上升 + 睡眠充足 → 恢复良好
- HRV 下降 + 睡眠不足 → 需要休息
```

## 📁 配置文件详解

### config.json 完整结构

```json
{
  "version": "5.8.1",
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

支持最多 3 个成员的报告生成（提取、生成、发送均统一为最多前 3 位）：

```json
{
  "version": "5.8.1",
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
  "analysis_limits": {...},
  "email_config": {...},
  "receiver_email": "target_email@example.com",
  "language": "CN",
  "validation_mode": "strict",
  "output_dir": "~/.openclaw/workspace/shared/health-reports/upload",
  "cache_dir": "~/.openclaw/workspace/shared/health-reports/cache"
}
```

**提取所有成员数据（V5.8.1+）：**
```bash
python3 scripts/extract_data_v5.py 2026-03-01 all
```

## 🎨 模板说明

- `templates/DAILY_TEMPLATE_MEDICAL_V2.html`: 医疗感紫色主题日报模板（中文）
- `templates/DAILY_TEMPLATE_MEDICAL_V2_EN.html`: 医疗感紫色主题日报模板（英文）
- `templates/WEEKLY_TEMPLATE_MEDICAL.html`: 周报汇总模板（中文）
- `templates/WEEKLY_TEMPLATE_MEDICAL_EN.html`: 周报汇总模板（英文）
- `templates/MONTHLY_TEMPLATE_MEDICAL.html`: 月报回顾模板（中文）
- `templates/MONTHLY_TEMPLATE_MEDICAL_EN.html`: 月报回顾模板（英文）

**多语言支持：** 所有报告模板均提供 CN/EN 双语版本，脚本会根据 `config.json` 中的 `language` 字段自动选择对应模板。

## 📊 提取数据字段说明

### 指标字段

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

### 周报/月报字段

周报和月报使用不同的 JSON 结构，需通过 stdin 传入：

```json
{
  "trend_analysis": "本周/月整体趋势分析（周报≥800字，月报≥1000字）",
  "hrv_analysis": "HRV 深度分析（月报）",
  "sleep_analysis": "睡眠质量分析（月报）", 
  "activity_analysis": "活动量分析（月报）",
  "trend_assessment": "趋势评估与预测（月报≥150字）",
  "recommendations": [
    {
      "priority": "high|medium|low",
      "title": "建议标题",
      "content": "详细建议内容（支持\\n换行）"
    }
  ]
}
```

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
| `ai2_title` | ≥10字 | 第二优先级标题 |
| `ai2_problem` | ≥80字 | 第二优先级问题 |
| `ai2_action` | ≥100字 | 第二优先级行动 |
| `ai2_expectation` | ≥70字 | 第二优先级效果 |
| `ai3_title` | ≥10字 | 第三优先级标题 |
| `ai3_problem` | ≥80字 | 第三优先级问题 |
| `ai3_action` | ≥100字 | 第三优先级行动 |
| `ai3_expectation` | ≥70字 | 第三优先级效果 |
| `breakfast` | ≥30字 | 早餐建议 |
| `lunch` | ≥30字 | 午餐建议 |
| `dinner` | ≥30字 | 晚餐建议 |
| `snack` | ≥30字 | 加餐建议 |

## 🔧 故障排除

### 报告生成失败
1. 检查 `config.json` 是否存在且格式正确
2. 验证 `health_dir` 和 `workout_dir` 路径是否正确
3. 运行 `python3 scripts/verify_v5_environment.py` 检查环境

### 数据提取异常
1. 确认 Health Auto Export 已正确导出数据
2. 检查 JSON 文件是否损坏
3. 验证文件路径在 `config.json` 中配置正确
4. 确认文件名格式为 `HealthAutoExport-YYYY-MM-DD.json`

### 活动能量显示为 0 或缺失
- **原因**：V5.8.1 之前版本使用 `active_energy_burned` 字段名，新版 Health Auto Export 使用 `active_energy`
- **解决**：确保使用 V5.8.1+ 版本，已修复字段名兼容问题
- **验证**：运行 `python3 scripts/extract_data_v5.py YYYY-MM-DD` 检查 `active_energy_kcal` 字段

### 睡眠数据缺失或显示为 0
- **原因**：睡眠数据结构可能在 `data.sleep_analysis` 或 `data.metrics[].sleep_analysis` 中
- **解决**：V5.8.1+ 已增强睡眠数据解析，同时兼容两种数据结构
- **检查**：确认睡眠数据存储在次日文件中（如 2月21日的睡眠在 2月22日文件中）
- **验证**：运行 `python3 scripts/extract_data_v5.py YYYY-MM-DD` 检查 `sleep` 字段

### 多成员数据提取失败
- **原因**：成员索引超出配置范围
- **解决**：V5.8.1+ 已添加边界检查，会自动回退到第一个成员
- **建议**：使用 `all` 参数一次性提取所有成员数据

### 语言配置不匹配
- **现象**：生成的报告语言与 `config.json` 中设置的不一致
- **解决**：确保 AI 分析 JSON 的语言与 `config.json` 中的 `language` 字段严格一致
- **严格模式**：`validation_mode` 为 `strict` 时会检查语言匹配，不匹配会报错

### 报告生成成功但内容为空/太少
- **原因**：AI 分析字数未达到 `analysis_limits` 要求
- **解决**：
  - 检查 `validation_mode` 设置
  - `strict` 模式：必须重新生成足够字数的分析
  - `warn` 模式：可手动编辑 JSON 补充内容后重试

### 评分与预期不符
- **原因**：评分算法基于固定公式，考虑年龄/性别/BMI
- **检查**：确认 `config.json` 中的个人档案数据正确
- **注意**：同一数值对不同年龄/性别的人评分可能不同

## 📚 相关链接

- **GitHub 仓库**: https://github.com/ItsjustJimmysbot/health-report
- **Health Auto Export App**: https://apps.apple.com/us/app/health-auto-export-json-csv/id111556706
- **OpenClaw 文档**: https://docs.openclaw.ai
