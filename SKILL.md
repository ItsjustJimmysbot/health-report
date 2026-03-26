---
name: health-report
description: 基于 Apple Health 数据生成日报/周报/月报，支持多成员与中英文模板，输出 PDF 并可邮件发送。
---

# Health Report（Skill Quick Card）

> 详细文档请看 `README.md`（安装、全量配置、故障排查都在那边）。

## 1) 核心能力
- 提取 Apple Health JSON 数据（支持多成员，最多 3 位）
- 生成日报 / 周报 / 月报 PDF
- 支持 CN / EN 模板切换
- 支持 OAuth2 / SMTP / Mail.app / Local 发送
- 支持 `report_metrics` 动态指标表（默认 12 项，可扩展到 32 项）

## 2) 最小配置（config.json）
```json
{
  "version": "6.0.6",
  "members": [
    {
      "name": "Member1",
      "age": 30,
      "gender": "male",
      "height_cm": 175,
      "weight_kg": 70,
      "health_dir": "~/Health Auto Export/Health Data",
      "workout_dir": "~/Health Auto Export/Workout Data",
      "email": "you@example.com"
    }
  ],
  "language": "CN",
  "validation_mode": "strict",
  "output_dir": "~/.openclaw/workspace/shared/health-reports/upload",
  "cache_dir": "~/.openclaw/workspace/shared/health-reports/cache",
  "sleep_config": {
    "read_mode": "next_day",
    "start_hour": 20,
    "end_hour": 12
  },
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
  "report_metrics": {
    "selected": [
      "hrv","resting_hr","steps","distance","active_energy","spo2",
      "flights_climbed","apple_stand_time","basal_energy_burned","respiratory_rate",
      "vo2_max","apple_exercise_time"
    ],
    "sort_by_importance": true,
    "show_empty_categories": true,
    "show_sleep_in_metrics_table": false,
    "hide_no_data_metrics": true,
    "require_ai_for_selected": true
  }
}
```

- `members[*].email` 可选；为空时使用 `receiver_email`。
- `sleep_config.read_mode`:
  - `next_day`: 读取次日文件（适合晚上8点到次日中午的睡眠）
  - `same_day`: 读取当天文件（适合跨午夜睡眠数据在当日文件的情况）
- `analysis_limits`: AI 分析长度限制（可选 `monthly_trend_min_words`，默认150）。
- `report_metrics`: 日报指标表选择与展示策略。

## 3) AI 分析生成（Agent 必读！）

**重要：周报/月报需要 AI 分析 JSON，这个 JSON 应该由你（Agent）基于真实健康数据生成。**

### 生成流程

1. **读取健康数据缓存**：
   ```bash
   cat ~/.openclaw/workspace/shared/health-reports/cache/daily/2026-02-24_用户名.json
   ```

2. **你生成 AI 分析 JSON**（基于真实数据）：
   - 周报需要 `trend_analysis` (≥800字) + `recommendations` 数组
   - 月报需要 `hrv_analysis`/`sleep_analysis`/`activity_analysis`/`trend_assessment` (各≥150字)
   
3. **通过 stdin 传给生成脚本**：
   ```bash
   echo '{"members":[{"name":"...","trend_analysis":"..."}]}' | python3 scripts/generate_weekly_monthly_medical.py weekly START_DATE END_DATE
   ```

**详见**: `AI_GENERATION_GUIDE.md`

### 日报 AI 分析字段要求

日报必须为以下指标提供 AI 分析（每项 150-200 字）：

**核心指标**（默认必须）：
- `hrv`, `resting_hr`, `steps`, `distance`, `active_energy`, `spo2`
- `flights`（对应 flights_climbed）, `stand`（对应 apple_stand_time）
- `basal`（对应 basal_energy_burned）, `respiratory`（对应 respiratory_rate）
- `sleep`, `workout`

**如果配置了额外指标**（如 `vo2_max`, `apple_exercise_time` 等），也需要提供对应的 AI 分析。

**优先级建议**（250-300 字）：
- `priority.title`, `priority.problem`, `priority.action`, `priority.expectation`

**次级建议**（每项 ≥100 字）：
- `ai2_title`, `ai2_problem`, `ai2_action`, `ai2_expectation`
- `ai3_title`, `ai3_problem`, `ai3_action`, `ai3_expectation`

**饮食方案**（每项 ≥30 字）：
- `breakfast`, `lunch`, `dinner`, `snack`

### 周报/月报 AI 分析字段

周报必须包含：
- `trend_analysis` 或 `weekly_analysis`（建议≥800字）
- `recommendations` 数组（每项包含 `priority` `title` `content`）

月报必须包含：
- `hrv_analysis`, `sleep_analysis`, `activity_analysis`, `trend_assessment`（各≥150字）
- `recommendations` 数组

### 字段命名对照表

日报指标字段映射（关键指标）:

| 数据字段 | AI JSON 字段 | 说明 |
|---------|-------------|------|
| `hrv` | `hrv` | 心率变异性（ms）|
| `resting_hr` | `resting_hr` | 静息心率（bpm）|
| `steps` | `steps` | 步数 |
| `distance` | `distance` | 行走距离（km）|
| `active_energy` | `active_energy` | 活动能量（kcal）|
| `spo2` | `spo2` | 血氧饱和度（%）|
| `sleep_total_hours` | `sleep` | 睡眠总时长 |
| `workouts` | `workout` | 运动分析 |

> 完整 32 项指标定义请参考代码中 `scripts/generate_v5_medical_dashboard.py` 的 `METRIC_DEFS`

## 4) 标准命令
### 日报
```bash
python3 scripts/extract_data_v5.py YYYY-MM-DD [member_index|all]
python3 scripts/generate_v5_medical_dashboard.py YYYY-MM-DD < ai_analysis.json
python3 scripts/send_health_report_email.py YYYY-MM-DD [member_index|all]
```

# 可选：显式指定配置与schema
python3 scripts/validate_config.py --config ./config.json --schema ./config.schema.json

### 周报
```bash
python3 scripts/generate_weekly_monthly_medical.py weekly START_DATE END_DATE < weekly_analysis.json
```

### 月报
```bash
python3 scripts/generate_weekly_monthly_medical.py monthly YEAR MONTH < monthly_analysis.json
```

### AI 输入文件自动清理（Feature）
- `scripts/generate_v5_medical_dashboard.py` 与 `scripts/generate_weekly_monthly_medical.py` 在启动时会自动删除仓库根目录 `ai_analysis.json`（若存在）。
- 这是有意设计，用于避免复用旧分析结果。
- 请始终用标准输入传入当次分析文件（`< ai_analysis.json` / `< weekly_analysis.json` / `< monthly_analysis.json`）。

### 字段命名对照表（32项完整版）

| 数据提取字段 | AI JSON 字段 | 说明 | 字数要求 |
|-------------|-------------|------|---------|
| `hrv` | `hrv` | 心率变异性（ms） | 150-200字 |
| `resting_hr` | `resting_hr` | 静息心率（bpm） | 150-200字 |
| `heart_rate_avg` | `heart_rate_avg` | 平均心率（bpm） | 150-200字 |
| `steps` | `steps` | 步数 | 150-200字 |
| `distance` | `distance` | 行走距离（km） | 150-200字 |
| `active_energy` | `active_energy` | 活动能量（kcal） | 150-200字 |
| `spo2` | `spo2` | 血氧饱和度（%） | 150-200字 |
| `respiratory_rate` | `respiratory` | 呼吸率（次/分） | 150-200字 |
| `apple_stand_time` | `stand` | 站立时间（分钟） | 150-200字 |
| `basal_energy_burned` | `basal` | 基础代谢（kcal） | 150-200字 |
| `vo2_max` | `vo2_max` | 最大摄氧量 | 150-200字 |
| `physical_effort` | `physical_effort` | 体力消耗率 | 150-200字 |
| `sleep_total_hours` | `sleep` | 睡眠总时长（小时） | 250-300字 |
| `sleep_deep_hours` | `sleep_deep_hours` | 深睡时长（小时） | 150-200字 |
| `sleep_rem_hours` | `sleep_rem_hours` | REM时长（小时） | 150-200字 |
| `breathing_disturbances` | `breathing_disturbances` | 呼吸紊乱指数 | 150-200字 |
| `apple_exercise_time` | `apple_exercise_time` | 锻炼时间（分钟） | 150-200字 |
| `flights_climbed` | `flights` | 爬楼层数 | 150-200字 |
| `apple_stand_hour` | `apple_stand_hour` | 站立小时数 | 150-200字 |
| `stair_speed_up` | `stair_speed_up` | 上楼速度（m/s） | 150-200字 |
| `running_speed` | `running_speed` | 跑步速度（km/h） | 150-200字 |
| `running_power` | `running_power` | 跑步功率（W） | 150-200字 |
| `running_stride_length` | `running_stride_length` | 跑步步幅（cm） | 150-200字 |
| `running_ground_contact_time` | `running_ground_contact_time` | 触地时间（ms） | 150-200字 |
| `running_vertical_oscillation` | `running_vertical_oscillation` | 垂直振幅（cm） | 150-200字 |
| `walking_speed` | `walking_speed` | 步行速度（km/h） | 150-200字 |
| `walking_step_length` | `walking_step_length` | 步行步长（cm） | 150-200字 |
| `walking_heart_rate_average` | `walking_heart_rate_average` | 步行平均心率（bpm） | 150-200字 |
| `walking_asymmetry_percentage` | `walking_asymmetry_percentage` | 步行不对称性（%） | 150-200字 |
| `walking_double_support_percentage` | `walking_double_support_percentage` | 双支撑时间占比（%） | 150-200字 |
| `headphone_audio_exposure` | `headphone_audio_exposure` | 耳机音频暴露（dB） | 150-200字 |
| `environmental_audio_exposure` | `environmental_audio_exposure` | 环境音频暴露（dB） | 150-200字 |

### 必填字段（无则报错）
- `sleep`, `workout`
- `priority.title`, `priority.problem`, `priority.action`, `priority.expectation`
- `ai2_title`, `ai2_problem`, `ai2_action`, `ai2_expectation`
- `ai3_title`, `ai3_problem`, `ai3_action`, `ai3_expectation`
- `breakfast`, `lunch`, `dinner`, `snack`

> **强制AI分析版（V6.0.6）**：所有 `report_metrics.selected` 中的指标必须有对应的 AI 分析字段，字数必须达标（150-200字），否则报错。

## 5) 必须遵守
- `language` 与 AI 输出语言需一致（CN/EN）。
- `analysis_limits` 会被脚本校验；`validation_mode` 影响长度/语言阈值校验（CN按字数，EN按单词数）。
- 当 `report_metrics.require_ai_for_selected=true` 时，缺失已选指标 AI 段落也走同一校验通道（strict 报错 / warn 警告继续）。
- 月报趋势对比使用上月平均值，且上月可用缓存数据需 ≥15 天，否则趋势默认持平。
- 多成员默认最多处理前 3 位。
- 详细规则、限制与排障请查 `README.md`。

---
如需：完整安装说明 / OAuth2 详细步骤 / 全量字段解释 / 故障排查，请查看 `README.md`。