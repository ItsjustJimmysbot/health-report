# 健康报告自动化流程标准

## 📋 报告类型（固定两种）

### 1. 单日报告 (Daily Report)
**生成时间**: 每天 12:30  
**内容**: 昨日健康数据详细分析

**包含内容**:
- Recovery Score 概览
- 心血管指标 (HRV、静息心率)
- 运动数据 (步数、活动能量、锻炼)
- 睡眠分析
- AI 个性化建议
- 数据修正说明 (如适用)

**语言版本**:
- 中文版: `YYYY-MM-DD-report-zh.pdf`
- 英文版: `YYYY-MM-DD-report-en.pdf`

---

### 2. 对比报告 (Comparison Report)
**生成时间**: 每天 12:30  
**内容**: 前天 vs 昨天 数据对比分析

**包含内容**:
- 两日数据并排展示
- 变化趋势分析
- AI 模式识别 (如"过度透支-身体代偿")
- 个性化建议 (基于对比结果)

**语言版本**:
- 中文版: `YYYY-MM-DD-vs-YYYY-MM-DD-comparison-zh.pdf`
- 英文版: `YYYY-MM-DD-vs-YYYY-MM-DD-comparison-en.pdf`

---

## ⏰ 自动化时间表

### 每日任务 (12:30 UTC+8)

```
12:30 执行: generate_daily_reports.sh
  ├── 1. 获取昨日数据 (Apple Health + Google Fit)
  ├── 2. 获取前天数据 (Apple Health + Google Fit)
  ├── 3. 数据验证和清洗
  ├── 4. 生成昨日单日报告 (中文)
  ├── 5. 生成昨日单日报告 (英文)
  ├── 6. 生成对比报告 (中文)
  ├── 7. 生成对比报告 (英文)
  ├── 8. 发送 Discord 通知
  └── 9. 上传 PDF 到共享目录
```

**四份报告清单**:
1. `YYYY-MM-DD-report-zh.pdf` - 昨日单日 (中文)
2. `YYYY-MM-DD-report-en.pdf` - 昨日单日 (英文)
3. `YYYY-MM-DD-vs-YYYY-MM-DD-comparison-zh.pdf` - 对比 (中文)
4. `YYYY-MM-DD-vs-YYYY-MM-DD-comparison-en.pdf` - 对比 (英文)

---

## 📊 数据获取流程

### 1. Apple Health 数据
**来源**: Health Auto Export (Google Drive)  
**路径**: `~/我的云端硬盘/Health Auto Export/Health Data/HealthAutoExport-YYYY-MM-DD.json`

**提取指标**:
- HRV (heart_rate_variability) → ms
- 静息心率 (resting_heart_rate) → bpm
- 步数 (step_count) → 步
- 活动能量 (active_energy) → **kJ，需转换为 kcal (÷4.184)**
- 锻炼时间 (apple_exercise_time) → min
- 基础代谢 (basal_energy_burned) → kJ (参考)

### 2. Google Fit 数据
**来源**: Google Fit API  
**提取指标**:
- 睡眠 (Sessions API, activityType=72)
- 心率 (aggregate)

### 3. 数据处理步骤
```python
# 1. 读取 Apple Health JSON
# 2. 提取各项指标 (注意单位转换 kJ→kcal)
# 3. 调用 Google Fit API 获取睡眠
# 4. 时区转换 (UTC → UTC+8)
# 5. 数据验证 (检查异常值)
# 6. 生成报告
```

---

## 🔧 单位转换规范

### 活动能量 (Active Energy)
**Apple Health 原始单位**: kJ (千焦)  
**报告单位**: kcal (千卡)  
**转换公式**: `kcal = kJ ÷ 4.184`

**示例**:
```
原始: 2,358.7 kJ
转换: 2,358.7 ÷ 4.184 = 563.7 kcal
```

**错误警示**:
- ❌ 直接显示 kJ 数值作为 kcal
- ✅ 必须转换后再显示

---

## 🤖 AI 分析调用

### 触发条件
每次生成报告时自动调用

### 调用方式
```python
sessions_spawn(
    agentId="health",
    model="kimi-coding/k2p5",
    task="基于以下健康数据生成个性化分析报告...",
    runTimeoutSeconds=120
)
```

### 分析维度
1. **数据变化洞察** (对比报告)
2. **个性化目标** (步数、睡眠)
3. **饮食建议** (基于状态调整)
4. **生理指标解读** (HRV、心率)
5. **模式识别** (透支-代偿等)

---

## 🎨 报告设计规范

### 页面设置
- 格式: A4
- 边距: 10mm
- 字体: PingFang SC / Microsoft YaHei
- 颜色: 支持打印 (print-color-adjust: exact)

### 必备元素
1. **页眉**: 标题 + 日期 + 数据来源 + 时区
2. **修正徽章** (如适用): "✅ 单位已修正 (kJ→kcal)"
3. **AI 徽章**: "🤖 AI 个性化分析"
4. **页脚**: 数据来源 + 时区 + AI分析 + 生成时间

### 颜色系统
- 主色: `#667eea` (紫蓝渐变)
- 成功/优秀: `#28a745` (绿色)
- 警告/一般: `#f0ad4e` (黄色)
- 危险/不足: `#dc3545` (红色)

---

## 📁 文件命名规范

### 中文报告
- 单日: `YYYY-MM-DD-report-zh.pdf`
- 对比: `YYYY-MM-DD-vs-YYYY-MM-DD-comparison-zh.pdf`

### 英文报告
- 单日: `YYYY-MM-DD-report-en.pdf`
- 对比: `YYYY-MM-DD-vs-YYYY-MM-DD-comparison-en.pdf`

### 存储路径
```
/Users/jimmylu/.openclaw/workspace/shared/health-reports/upload/
```

---

## 📂 关键路径参考 (重要!)

### 1. Apple Health 数据源 (Google Drive)
**基础路径**: `/Users/jimmylu/我的云端硬盘/Health Auto Export/`

**健康数据**: 
```
/Users/jimmylu/我的云端硬盘/Health Auto Export/Health Data/HealthAutoExport-YYYY-MM-DD.json
```

**锻炼数据**:
```
/Users/jimmylu/我的云端硬盘/Health Auto Export/Workout Data/
```

**注意**: 
- 文件每天由 Health Auto Export 应用自动生成
- 命名格式: `HealthAutoExport-YYYY-MM-DD.json`
- 时区: 数据使用设备时区 (需转换为 UTC+8)

### 2. 工作空间目录
**根目录**: `/Users/jimmylu/.openclaw/workspace-health/`

**子目录**:
```
/Users/jimmylu/.openclaw/workspace-health/
├── data/                          # 解析后的数据文件
├── docs/                          # 文档
│   ├── REPORT_AUTOMATION.md      # 本文档
│   ├── MAIL_APP_STANDARD.md      # 邮件操作文档
│   └── EMAIL_CREDENTIALS.md      # 邮箱凭证文档
├── memory/                        # AI 分析结果
│   └── ai-analysis-YYYY-MM-DD.md
├── scripts/                       # 自动化脚本
│   ├── generate_daily_reports.sh
│   ├── mail_operations.sh
│   └── generate_all_reports.py
├── logs/                          # 运行日志
│   └── daily_reports.log
└── shared/                        # 共享输出
    └── health-reports/
        └── upload/                # PDF 报告输出目录
```

### 3. 报告输出路径
**PDF 输出**: `/Users/jimmylu/.openclaw/workspace/shared/health-reports/upload/`

**文件命名示例**:
```
2026-02-20-report-zh.pdf
2026-02-20-report-en.pdf
2026-02-19-vs-2026-02-20-comparison-zh.pdf
2026-02-19-vs-2026-02-20-comparison-en.pdf
```

### 4. 配置文件
**Himalaya 邮件**: `~/.config/himalaya/config.toml`

**Mail.app 账户**: 系统偏好设置 → 邮件

---

## ✅ 质量检查清单

生成报告前必须检查:
- [ ] 所有时间带 UTC+8 标注
- [ ] HRV 来源是 Apple Health
- [ ] **活动能量已转换 kJ→kcal**
- [ ] 睡眠时间已转换时区
- [ ] AI 分析已调用
- [ ] 中文/英文版本完整
- [ ] PDF 中文显示正常

---

## 🚀 自动化脚本

### 主脚本: `scripts/generate_daily_reports.sh`
**功能**: 每日 12:30 自动生成四份报告

**执行流程**:
1. 计算昨日和前天日期
2. 检查 Apple Health 导出文件
3. 调用数据解析脚本
4. 调用 AI 分析
5. 生成四份 PDF
6. 发送 Discord 通知
7. **发送邮件通知 (可选)** - 使用 Mail.app

### 邮件发送 (Mail.app)

**收件人**: `revolutionljk@gmail.com`  
**发送方式**: macOS Mail.app AppleScript  
**发送时间**: 每天 12:35 (报告生成后 5 分钟)

**邮件内容**:
- 主题: "每日健康报告 - YYYY-MM-DD"
- 附件: 4 份 PDF 报告
- 正文: 报告摘要 + AI 关键洞察

**发送脚本** (`scripts/send_daily_email.scpt`):
```applescript
tell application "Mail"
    -- 发送中文单日报告
    set msg1 to make new outgoing message with properties {subject:"每日健康报告 - " & yesterday, content:"请查收昨日的健康报告（中文版）。"}
    tell msg1
        make new to recipient with properties {address:"revolutionljk@gmail.com"}
        tell content
            make new attachment with properties {file name:reportPathZh}
        end tell
        send
    end tell
    
    delay 2
    
    -- 发送英文单日报告
    set msg2 to make new outgoing message with properties {subject:"Daily Health Report - " & yesterday, content:"Please find attached your daily health report (English version)."}
    tell msg2
        make new to recipient with properties {address:"revolutionljk@gmail.com"}
        tell content
            make new attachment with properties {file name:reportPathEn}
        end tell
        send
    end tell
    
    delay 2
    
    -- 发送中文对比报告
    set msg3 to make new outgoing message with properties {subject:"健康对比报告 - " & dayBefore & " vs " & yesterday, content:"请查收近两日的健康对比分析报告。"}
    tell msg3
        make new to recipient with properties {address:"revolutionljk@gmail.com"}
        tell content
            make new attachment with properties {file name:comparisonPathZh}
        end tell
        send
    end tell
    
    delay 2
    
    -- 发送英文对比报告
    set msg4 to make new outgoing message with properties {subject:"Health Comparison Report - " & dayBefore & " vs " & yesterday, content:"Please find attached the comparison report."}
    tell msg4
        make new to recipient with properties {address:"revolutionljk@gmail.com"}
        tell content
            make new attachment with properties {file name:comparisonPathEn}
        end tell
        send
    end tell
end tell
```

**注意事项**:
- 每封邮件间隔 2 秒，避免触发频率限制
- 如发件箱卡住，使用 `scripts/clear_outbox.scpt` 清理
- 如账户被限制，等待 24 小时或切换 Gmail

**详细文档**: `docs/MAIL_APP_STANDARD.md`

### Cron 配置
```bash
# 每天 12:30 UTC+8 执行
30 12 * * * cd /Users/jimmylu/.openclaw/workspace-health && bash scripts/generate_daily_reports.sh >> logs/daily_reports.log 2>&1
```

---

**版本**: 3.0  
**更新日期**: 2026-02-21  
**生效日期**: 2026-02-21  
**维护者**: Health Agent  
**邮件收件人**: revolutionljk@gmail.com
