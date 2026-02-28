# Health Agent V5.1 快速安装指南

## 1. 基础环境
```bash
cd ~/.openclaw
git clone -b agent-health https://github.com/ItsjustJimmysbot/health-report.git workspace-health
cd workspace-health
pip3 install -r requirements.txt
playwright install chromium
```

## 2. 数据路径
确保 Apple Health 导出的 JSON 位于：
`~/我的云端硬盘/Health Auto Export/Health Data/`

## 3. 定时任务 (Cron) 配置
在 OpenClaw 中添加以下任务，建议时间：`10 12 * * *`

**指令内容：**
> 【每日健康日报 - V5.1】
> 1. 提取昨日 Health 数据。
> 2. AI 生成详细分析（每项≥150字）。
> 3. **关键**：使用 `write` 工具直接写入 `ai_analysis.json`。
> 4. 运行生成脚本：
> `cd ~/.openclaw/workspace-health/scripts && python3 generate_v5_medical_dashboard.py $(date -v-1d +%Y-%m-%d) < ../ai_analysis.json`
> 5. 运行发送脚本：
> `python3 send_health_report_email.py $(date -v-1d +%Y-%m-%d)`

## 4. 验证安装
运行：`python3 scripts/extract_data_v5.py 2026-02-27`
若输出 JSON 数据则安装成功。
