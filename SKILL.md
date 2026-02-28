---
name: health-report
description: 基于 Apple Health 数据的 AI 健康分析报告生成工具。支持从 Health Auto Export 导出的 JSON 中提取 HRV、步数、睡眠等 11 项核心指标，并利用大模型进行深度分析，最终通过 V2 Medical 模板渲染为精美的 PDF 报告并自动发送邮件。使用场景：(1) 生成昨日/今日健康日报，(2) 分析周/月健康趋势，(3) 监控 HRV、静息心率等关键生理指标。
---

# Health Report

此 Skill 能够将 Apple Health 的原始导出数据转化为深度、个性化的健康报告。

## 🚀 快速启动

### 1. 生成日报 (Daily Report)
运行以下逻辑流程：
1. **提取数据**：读取 `HealthAutoExport-YYYY-MM-DD.json`。
2. **AI 分析**：根据提取的数值生成 150-200 字的指标分析及 250-300 字的行动建议。
3. **渲染 PDF**：
   ```bash
   python3 scripts/generate_v5_medical_dashboard.py <日期> < ai_analysis.json
   ```
4. **发送邮件**：
   ```bash
   python3 send_health_report_email.py <日期>
   ```

### 2. 生成周报/月报
周报和月报会自动汇总 `cache/daily/` 下的缓存数据：
```bash
# 周报
python3 scripts/generate_weekly_monthly_medical.py weekly <开始日期> <结束日期> < ai_analysis.json
# 月报
python3 scripts/generate_weekly_monthly_medical.py monthly <年份-月份> < ai_analysis.json
```

## 🛠️ 核心脚本

- `scripts/extract_data_v5.py`: 负责数据提取与严格的时间戳过滤。
- `scripts/generate_v5_medical_dashboard.py`: 日报生成主脚本，包含 V5.1 逻辑。
- `scripts/generate_weekly_monthly_medical.py`: 趋势报告生成脚本。
- `scripts/send_health_report_email.py`: 邮件分发脚本。

## 📝 V5.1 强制规范

- **严格对齐**：日报必须对原始数据执行 `00:00-23:59` 过滤，剔除次日干扰。
- **跨夜睡眠**：睡眠窗口定义为当日 20:00 至次日 12:00。
- **禁止估算**：数据缺失处必须显示 `--`，严禁 AI 编造。
- **原子写入**：必须使用 `write` 工具全量更新 `ai_analysis.json`，禁止 `edit` 局部替换。

## 🎨 模板说明

- `templates/DAILY_TEMPLATE_MEDICAL_V2.html`: 医疗感紫色主题日报模板。
- `templates/WEEKLY_TEMPLATE_MEDICAL.html`: 周报汇总模板。
- `templates/MONTHLY_TEMPLATE_MEDICAL.html`: 月报回顾模板。
