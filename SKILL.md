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
  "version": "5.9.1",
  "members": [
    {
      "name": "Jimmy",
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
    "monthly_min_words": 1000
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
    "require_ai_for_selected": false
  }
}
```

- `members[*].email` 可选；为空时使用 `receiver_email`。
- `sleep_config.read_mode`:
  - `next_day`: 读取次日文件（适合晚上8点到次日中午的睡眠）
  - `same_day`: 读取当天文件（适合跨午夜睡眠数据在当日文件的情况）
- `analysis_limits`: AI 分析长度限制（可选 `monthly_trend_min_words`，默认150）。
- `report_metrics`: 日报指标表选择与展示策略。

## 3) 标准命令
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

### 字段命名对照表

| 数据提取字段 | AI JSON 字段 | 说明 |
|-------------|-------------|------|
| `active_energy_kcal` | `active_energy` | 活动能量（千卡）|
| `resting_hr` | `resting_hr` | 静息心率（bpm）|
| `hrv` | `hrv` | 心率变异性（ms）|
| `steps` | `steps` | 步数 |
| `distance_km` | `distance` | 步行/跑步距离（公里）|
| `spo2` | `spo2` | 血氧饱和度（%）|
| `basal_energy_kcal` | `basal` | 基础代谢能量（千卡）|
| `respiratory_rate` | `respiratory` | 呼吸率（次/分钟）|
| `flights_climbed` | `flights` | 爬楼层数 |
| `stand_time_min` | `stand` | 站立时间（分钟）|
| `sleep.total_hours` | `sleep` | 睡眠时长（小时）|
| `workouts` | `workout` | 运动记录 |
| `workout` | `workout` | 运动分析文本（必填） |

注意：AI 分析 JSON 中使用简写形式，如 `active_energy` 而非 `active_energy_kcal`。

## 4) AI 分析字段要求（日报）

### 硬性必填（缺少会报错）
- `sleep`
- `workout`（即使当天无运动也要有文本）
- `priority.title` `priority.problem` `priority.action` `priority.expectation`
- `ai2_title` `ai2_problem` `ai2_action` `ai2_expectation`
- `ai3_title` `ai3_problem` `ai3_action` `ai3_expectation`
- `breakfast` `lunch` `dinner` `snack`

### 指标分析字段（建议完整提供）
`hrv` `resting_hr` `steps` `distance` `active_energy` `spo2` `flights` `stand` `basal` `respiratory` `sleep` `workout`

> 当 `report_metrics.require_ai_for_selected=true` 时，已选指标若映射到 `ai_key` 且缺失，会触发校验错误。

## 5) 必须遵守
- `language` 与 AI 输出语言需一致（CN/EN）。
- `analysis_limits` 会被脚本校验；`validation_mode` 影响长度/语言阈值校验（CN按字数，EN按单词数）。
- 当 `report_metrics.require_ai_for_selected=true` 时，缺失已选指标 AI 段落也走同一校验通道（strict 报错 / warn 警告继续）。
- 月报趋势对比使用上月平均值，且上月可用缓存数据需 ≥15 天，否则趋势默认持平。
- 多成员默认最多处理前 3 位。
- 详细规则、限制与排障请查 `README.md`。

---
如需：完整安装说明 / OAuth2 详细步骤 / 全量字段解释 / 故障排查，请查看 `README.md`。