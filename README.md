# Health Agent V5.1 - 每日健康报告专业版

基于 Apple Health 数据与 OpenClaw 大模型分析的个人健康管理系统。V5.1 版本引入了严格的时间戳过滤逻辑和 V2 Medical 医疗感模板，确保数据与分析 100% 对齐。

---

## 🚀 快速安装

### 1. 基础环境准备
在你的 OpenClaw 运行环境中执行：
```bash
cd ~/.openclaw
git clone -b agent-health https://github.com/ItsjustJimmysbot/health-report.git workspace-health
cd workspace-health
pip3 install -r requirements.txt
playwright install chromium
```

### 2. 数据路径配置
确保你的 [Health Auto Export](https://apps.apple.com/us/app/health-auto-export-json-csv/id111556706) 导出的 JSON 文件同步到了以下路径：
*   `~/我的云端硬盘/Health Auto Export/Health Data/`
*   `~/我的云端硬盘/Health Auto Export/Workout Data/`

### 3. OpenClaw 定时任务 (Cron) 配置
在 OpenClaw 中添加日报任务，建议时间 `12:10`（确保当日数据已同步完成）。

**指令内容模板：**
```text
【每日健康日报 - V5.1 标准化流程】
1. 提取数据：读取昨日 Health JSON。
2. AI 分析：基于当日真实数值（HRV、步数等）生成详细分析（每项≥150字）。
3. 关键写入：必须使用 write 工具直接将 JSON 写入 ai_analysis.json（禁止使用 edit）。
4. 渲染生成：
   cd ~/.openclaw/workspace-health/scripts && \
   python3 generate_v5_medical_dashboard.py $(date -v-1d +%Y-%m-%d) < ../ai_analysis.json
5. 发送邮件：
   python3 send_health_report_email.py $(date -v-1d +%Y-%m-%d)
```

---

## ✨ V5.1 核心特性

*   **真·数据对齐**：彻底修正了 Apple Health 跨天导出的偏移问题。通过对原始数据执行 `00:00-23:59` 严格时间戳过滤，确保 26 号的报告里只有 26 号的数据。
*   **医疗级 UI**：采用全新的 V2 Medical 紫色主题模板，包含评分卡片、11 项核心指标表、Chart.js 动态心率曲线和深度睡眠结构分析。
*   **原子化工作流**：将原本不稳定的 `edit` 局部替换逻辑升级为全量 `write` JSON 模式，杜绝了在高并发或长文本下的文件编辑冲突。
*   **跨夜睡眠归属**：完善了睡眠统计逻辑，自动抓取 `当日 20:00` 至 `次日 12:00` 的睡眠记录并归属为当日恢复指标。

---

## 🛠️ 常用命令

*   **测试数据提取**：`python3 scripts/extract_data_v5.py YYYY-MM-DD`
*   **手动补发邮件**：`python3 scripts/send_health_report_email.py YYYY-MM-DD`
*   **验证渲染环境**：`python3 scripts/verify_v5_environment.py`

---

## 📝 开发者规范 (V5.1)
*   **禁止编造**：数据缺失时必须显示 `--`，严禁 AI 估算比例。
*   **字数红线**：AI 指标分析段落必须在 150-200 字，核心行动建议 250-300 字。
*   **单日单源**：每份报告必须仅依赖当日产生的 Data Cache JSON。

---

## 许可证
MIT License
