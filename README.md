# Health Agent V5.4.0 - OpenClaw 专业健康分析 Skill

这是一个正式封装的 **OpenClaw Skill**，旨在将 Apple Health 原始数据转化为深度、医疗感的个人健康分析报告。

---

## 🚀 快速安装与 Skill 启用

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
  "version": "5.4.0",
  "members": [
    {
      "name": "默认用户",
      "health_dir": "~/我的云端硬盘/Health Auto Export/Health Data",
      "workout_dir": "~/我的云端硬盘/Health Auto Export/Workout Data",
      "email": "your-email@example.com"
    }
  ],
  "analysis_limits": {
    "metric_min_words": 150,
    "metric_max_words": 200,
    "action_min_words": 250,
    "action_max_words": 300
  },
  "email_config": {
    "smtp_server": "smtp.gmail.com",
    "smtp_port": 587,
    "sender_email": "sender@example.com",
    "password": "应用专用密码"
  },
  "language": "CN"
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
【每日健康日报 - V5.4.0 标准化流程】
1. 提取数据：读取 config.json 配置的 Health 路径
2. AI 分析：基于当日真实数值（HRV、步数等）生成详细分析（每项≥150字）
3. 关键写入：使用 write 工具将 JSON 写入 ai_analysis.json
4. 渲染生成：
   cd ~/.openclaw/workspace-health/scripts && \
   python3 generate_v5_medical_dashboard.py $(date -v-1d +%Y-%m-%d) < ../ai_analysis.json
5. 发送邮件：
   python3 send_health_report_email.py $(date -v-1d +%Y-%m-%d)
```

---

## ✨ V5.4.0 核心特性

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

## 📝 开发者规范 (V5.4.0)
*   **配置优先**：所有路径必须从 `config.json` 读取，禁止硬编码
*   **禁止编造**：数据缺失时必须显示 `--`，严禁 AI 估算比例
*   **字数红线**：AI 指标分析段落必须在 150-200 字，核心行动建议 250-300 字
*   **单日单源**：每份报告必须仅依赖当日产生的 Data Cache JSON

---

## 📁 配置文件说明

### config.json 结构
```json
{
  "version": "5.4.0",
  "members": [
    {
      "name": "成员名称",
      "health_dir": "Health数据路径",
      "workout_dir": "Workout数据路径",
      "email": "报告接收邮箱"
    }
  ],
  "analysis_limits": {
    "metric_min_words": 150,
    "metric_max_words": 200,
    "action_min_words": 250,
    "action_max_words": 300
  },
  "email_config": {
    "smtp_server": "smtp.gmail.com",
    "smtp_port": 587,
    "sender_email": "sender@example.com",
    "password": "应用专用密码"
  },
  "language": "CN"
}
```

### 🌐 多语言支持 (V5.4.0 新增)

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
