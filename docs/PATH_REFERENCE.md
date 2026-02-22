# 📂 健康报告系统 - 关键路径速查表

**最后更新**: 2026-02-21  
**用途**: 快速查找所有重要文件路径

---

## 🗂️ 数据源路径

### Apple Health Auto Export (Google Drive)
```
/Users/jimmylu/我的云端硬盘/Health Auto Export/
├── Health Data/
│   └── HealthAutoExport-YYYY-MM-DD.json    ← 每日健康数据
└── Workout Data/
    └── WorkoutExport-YYYY-MM-DD.json       ← 锻炼数据
```

**重要提示**:
- 文件名格式: `HealthAutoExport-2026-02-20.json`
- 数据单位: **kJ** (千焦)，需转换为 kcal
- 时区: 设备本地时区，需转换为 UTC+8

---

## 🏠 工作空间路径

### 根目录
```
/Users/jimmylu/.openclaw/workspace-health/
```

### 子目录结构
```
workspace-health/
├── 📁 data/                           # 解析后的 JSON 数据
│   ├── final_2026-02-20.json
│   └── corrected_with_basal_*.json
│
├── 📁 docs/                           # 文档
│   ├── REPORT_AUTOMATION.md          ← 自动化流程标准
│   ├── REPORT_STANDARD.md            ← 报告设计标准
│   ├── MAIL_APP_STANDARD.md          ← 邮件操作指南
│   ├── EMAIL_CREDENTIALS.md          ← 邮箱凭证管理
│   ├── EMAIL_ISSUE_LOG.md            ← 邮件问题记录
│   └── OUTLOOK_IMAP_FIX.md           ← Outlook 修复指南
│
├── 📁 memory/                         # AI 分析结果
│   ├── ai-analysis-YYYY-MM-DD.md
│   └── shared/                       # 共享记忆
│       ├── SHARED_CONSTRAINTS.md
│       ├── SHARED_DECISIONS.md
│       ├── SHARED_RISKS.md
│       └── SHARED_TODOS.md
│
├── 📁 scripts/                        # 自动化脚本 ⭐
│   ├── generate_daily_reports.sh     ← 主脚本（每天12:30）
│   ├── send_daily_email.sh           ← 邮件发送脚本
│   ├── mail_operations.sh            ← 邮件操作工具
│   ├── generate_all_reports.py       ← Python 报告生成
│   └── heartbeat_memory_sync.sh      ← 心跳同步脚本
│
├── 📁 logs/                           # 运行日志
│   └── daily_reports.log
│
├── 📁 data/                           # 最终数据
│   ├── final_YYYY-MM-DD.json
│   └── corrected_*.json
│
└── 📁 shared/health-reports/upload/   # PDF 输出目录 ⭐
    ├── 2026-02-20-report-zh.pdf
    ├── 2026-02-20-report-en.pdf
    ├── 2026-02-19-vs-2026-02-20-comparison-zh.pdf
    └── 2026-02-19-vs-2026-02-20-comparison-en.pdf
```

---

## 📄 报告输出路径

### PDF 文件命名规范
```
{YYYY-MM-DD}-report-zh.pdf                      # 中文单日
{YYYY-MM-DD}-report-en.pdf                      # 英文单日
{YYYY-MM-DD}-vs-{YYYY-MM-DD}-comparison-zh.pdf  # 中文对比
{YYYY-MM-DD}-vs-{YYYY-MM-DD}-comparison-en.pdf  # 英文对比
```

### 完整路径示例
```
/Users/jimmylu/.openclaw/workspace/shared/health-reports/upload/2026-02-20-report-zh.pdf
/Users/jimmylu/.openclaw/workspace/shared/health-reports/upload/2026-02-20-report-en.pdf
/Users/jimmylu/.openclaw/workspace/shared/health-reports/upload/2026-02-19-vs-2026-02-20-comparison-zh.pdf
/Users/jimmylu/.openclaw/workspace/shared/health-reports/upload/2026-02-19-vs-2026-02-20-comparison-en.pdf
```

---

## ⚙️ 配置文件路径

### 邮件配置
```
~/.config/himalaya/config.toml         # Himalaya CLI 配置
```

### 钥匙串密码
```bash
# 查看存储的密码
security find-generic-password -s himalaya-outlook-imap -w

# 服务名: himalaya-outlook-imap
# 账户: itestmolt@outlook.com
# 用途: Outlook IMAP/SMTP（当前被 Microsoft 限制）
```

### Mail.app 账户
```
系统偏好设置 → 邮件 → 账户
```

---

## 🚀 关键脚本使用

### 主脚本 - 每日报告生成
```bash
# 完整路径
bash /Users/jimmylu/.openclaw/workspace-health/scripts/generate_daily_reports.sh

# 功能
- 生成 4 份 PDF 报告
- 发送邮件到 revolutionljk@gmail.com
- 记录日志到 logs/daily_reports.log
```

### 邮件发送脚本
```bash
# 完整路径
bash /Users/jimmylu/.openclaw/workspace-health/scripts/send_daily_email.sh

# 收件人: revolutionljk@gmail.com
# 发送 4 封邮件（每封间隔 2 秒）
```

### 邮件操作工具
```bash
# 查看收件箱
bash /Users/jimmylu/.openclaw/workspace-health/scripts/mail_operations.sh list 10

# 搜索邮件
bash /Users/jimmylu/.openclaw/workspace-health/scripts/mail_operations.sh search "关键词"
```

---

## 📊 数据流程图

```
1. 数据源读取
   /Users/jimmylu/我的云端硬盘/Health Auto Export/Health Data/
   └── HealthAutoExport-YYYY-MM-DD.json

2. 数据解析 & 转换
   workspace-health/scripts/generate_all_reports.py
   └── 转换 kJ → kcal
   └── 时区转换 UTC → UTC+8

3. AI 分析
   workspace-health/memory/ai-analysis-YYYY-MM-DD.md

4. PDF 生成
   workspace-health/shared/health-reports/upload/
   └── 4 份 PDF 报告

5. 邮件发送
   revolutionljk@gmail.com
   └── 4 封邮件（带附件）

6. Discord 通知
   #health 频道
```

---

## ⏰ 定时任务

### Cron 配置
```bash
# 每天 12:30 UTC+8 执行
30 12 * * * /Users/jimmylu/.openclaw/workspace-health/scripts/generate_daily_reports.sh
```

### 任务详情
- **名称**: daily-health-report
- **时间**: 每天 12:30 (北京时间)
- **功能**: 生成报告 + 发送邮件
- **下次执行**: 明天 12:30

---

## 🐛 故障排除路径

### 问题 1: 找不到 Health 数据文件
**检查路径**:
```bash
ls -la "/Users/jimmylu/我的云端硬盘/Health Auto Export/Health Data/"
```

### 问题 2: 邮件发送失败
**检查发件箱**:
```bash
osascript -e 'tell application "Mail" to count messages of outbox'
```

**清理发件箱**:
```bash
osascript /tmp/clear_outbox.scpt
```

### 问题 3: PDF 生成失败
**检查输出目录**:
```bash
ls -la /Users/jimmylu/.openclaw/workspace/shared/health-reports/upload/
```

### 问题 4: 查看日志
```bash
tail -f /Users/jimmylu/.openclaw/workspace-health/logs/daily_reports.log
```

---

## 📞 联系信息

- **收件邮箱**: revolutionljk@gmail.com
- **Discord 频道**: #health
- **报告时间**: 每天 12:30 (北京时间)

---

**建议**: 将此文件加入书签，方便快速查找路径！
