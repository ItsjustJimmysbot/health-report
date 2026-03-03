---
name: health-report
description: 基于 Apple Health 数据生成日报/周报/月报，支持多成员与中英文模板，输出 PDF 并可邮件发送。
---

# Health Report（Skill Quick Card）

> 详细文档请看 `README.md`（安装、全量配置、故障排查都在那边）。

## 1) 核心能力
- 提取 Apple Health JSON 数据（支持多成员）
- 生成日报 / 周报 / 月报 PDF
- 支持 CN / EN 模板切换
- 支持 OAuth2 / SMTP / Mail.app / Local 发送

## 2) 最小配置（config.json）
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
      "health_dir": "~/.../Health Data",
      "workout_dir": "~/.../Workout Data",
      "email": "you@example.com"
    }
  ],
  "language": "CN",
  "validation_mode": "strict",
  "output_dir": "~/.openclaw/workspace/shared/health-reports/upload",
  "cache_dir": "~/.openclaw/workspace/shared/health-reports/cache"
}
```

- `members[*].email` 可选；为空时使用 `receiver_email`。
```

## 3) 标准命令
### 日报
```bash
python3 scripts/extract_data_v5.py YYYY-MM-DD [member_index|all]
python3 scripts/generate_v5_medical_dashboard.py YYYY-MM-DD < ai_analysis.json
python3 scripts/send_health_report_email.py YYYY-MM-DD [member_index|all]
```

### 周报
```bash
python3 scripts/generate_weekly_monthly_medical.py weekly START_DATE END_DATE < weekly_analysis.json
```

### 月报
```bash
python3 scripts/generate_weekly_monthly_medical.py monthly YEAR MONTH < monthly_analysis.json
```

## 4) AI 分析最小字段要求
日报必须包含：
- 指标分析（每项150-200字）：`hrv` `resting_hr` `steps` `distance` `active_energy` `spo2` `flights` `stand` `basal` `respiratory` `sleep` `workout`
- 优先级建议（250-300字）：`priority.title` `priority.problem` `priority.action` `priority.expectation`
- 次级建议：`ai2_title` `ai2_problem` `ai2_action` `ai2_expectation` `ai3_title` `ai3_problem` `ai3_action` `ai3_expectation`
- 饮食方案（每项≥30字）：`breakfast` `lunch` `dinner` `snack`

**字段命名说明**：
- 数据提取使用 `active_energy_kcal`（单位：千卡）
- AI 分析 JSON 使用 `active_energy`（简写形式）
- 内部缓存统一使用 `active_energy`

周报必须包含：
- `trend_analysis` 或 `weekly_analysis`（建议≥800字）
- `recommendations` 数组（每项包含 `priority` `title` `content`）

月报必须包含：
- `hrv_analysis` 或 `monthly_analysis`
- `sleep_analysis`
- `activity_analysis` 或 `key_findings`
- `trend_assessment` 或 `trend_forecast`
- `recommendations` 数组（建议整篇≥1000字）

## 5) 必须遵守
- `language` 与 AI 输出语言必须一致（CN/EN）
- `analysis_limits` 阈值会被脚本实际校验（strict 模式不满足将失败）。`validation_mode` 仅影响字数/语言阈值类校验，缺少必填 AI 字段是硬错误，不受 warn 模式影响。
- 多成员默认最多处理前 3 位
- 详细规则、限制与排障请查 `README.md`

---
如需：
- 完整安装说明
- OAuth2 详细步骤
- 全量字段解释
- 故障排查
请查看 `README.md`。