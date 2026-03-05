# Health Report 故障排查指南

> 本文档汇总了 Health Report V5.9.x 的常见问题及解决方案。
> 完整安装和使用说明请参见 [README.md](README.md)。

---

## 📋 快速诊断清单

遇到问题时，请按顺序检查：

1. [ ] 运行 `python3 scripts/validate_config.py` 检查配置
2. [ ] 运行 `python3 scripts/verify_v5_environment.py` 检查环境
3. [ ] 确认 Health Auto Export 数据文件已同步到配置路径
4. [ ] 检查日志文件 `~/.openclaw/workspace-health/logs/health_report.log`

---

## 🔴 配置问题

### 问题："config.json 配置验证警告"

**症状：**
运行脚本时显示配置验证警告。

**解决：**
```bash
python3 scripts/validate_config.py
```
根据提示修复配置问题。常见错误：
- `version` 字段格式不正确（应为 `5.8.x` 或 `5.9.x`）
- `members` 数组为空或超过3人
- `language` 不是 `CN` 或 `EN`
- `email` 格式不正确
- `age`/`height_cm`/`weight_kg` 超出合理范围

---

### 问题："找不到 config.json"

**症状：**
```
Error: 配置文件不存在
```

**解决：**
1. 确认已复制 `config.json.example` 为 `config.json`：
   ```bash
   cd ~/.openclaw/skills/health-report
   cp config.json.example config.json
   ```
2. 检查配置文件位置（按优先级）：
   - 仓库根目录 `config.json`
   - `~/.openclaw/workspace-health/config.json`

---

## 🔴 数据提取问题

### 问题："数据文件不存在"

**症状：**
```
数据文件不存在: ~/Health Auto Export/Health Data/HealthAutoExport-2026-03-01.json
```

**解决：**
1. 确认 Health Auto Export App 已正确导出数据
2. 检查 `config.json` 中的路径配置：
   ```json
   {
     "health_dir": "~/Health Auto Export/Health Data",
     "workout_dir": "~/Health Auto Export/Workout Data"
   }
   ```
3. 确认路径存在：
   ```bash
   ls -la ~/Health\ Auto\ Export/Health\ Data/
   ```

---

### 问题："睡眠数据缺失或显示为 0"

**症状：**
报告中睡眠时长显示为 0 或 "--"。

**原因：**
Apple Health 的睡眠数据存储在次日文件中。例如，3月1日晚上的睡眠记录在 3月2日的数据文件中。

**解决：**
1. 确认 `sleep_config.read_mode` 配置正确：
   - `"next_day"`：读取次日文件（适合早上生成报告）
   - `"same_day"`：读取当天文件（适合晚上生成报告）
2. 检查睡眠数据确实存在于 Health Auto Export 导出文件中

---

### 问题："活动能量显示为 0"

**症状：**
报告中活动能量显示为 0 或非常小的数值。

**原因：**
V5.8.0 及更早版本使用 `active_energy_burned` 字段名，新版 Health Auto Export 使用 `active_energy`。

**解决：**
确保使用 V5.8.1+ 版本，已自动修复字段名兼容问题。

---

### 问题："多成员数据提取失败"

**症状：**
提取第二个或第三个成员数据时报错。

**解决：**
1. 确认 `config.json` 中已配置多个成员：
   ```json
   {
     "members": [
       {"name": "成员1", ...},
       {"name": "成员2", ...}
     ]
   }
   ```
2. 检查成员索引是否越界（有效范围：0-2，最多3人）
3. 成员索引越界时会自动回退到第一个成员，并打印警告信息
4. 使用 `all` 参数提取所有成员：
   ```bash
   python3 scripts/extract_data_v5.py 2026-03-01 all
   ```

---

## 🔴 报告生成问题

### 问题："ai_analysis.json 不见了"

**症状：**
运行日报/周报/月报脚本后，仓库根目录的 `ai_analysis.json` 被删除。

**原因：**
这是设计内 Feature：
- `generate_v5_medical_dashboard.py`
- `generate_weekly_monthly_medical.py`

在启动时会自动清理旧 `ai_analysis.json`，避免误用历史分析结果。

**解决：**
- 不要依赖仓库中持久化的 `ai_analysis.json`
- 每次都通过标准输入传入当次分析文件，例如：
  ```bash
  python3 scripts/generate_v5_medical_dashboard.py 2026-03-01 < ai_analysis.json
  ```

### 问题："报告生成成功但内容为空/太少"

**症状：**
PDF 生成了，但 AI 分析内容很少或没有。

**原因：**
AI 分析字数未达到 `analysis_limits` 要求，且 `validation_mode` 为 `strict`。

**解决：**
1. 临时改为 `warn` 模式（跳过字数检查）：
   ```json
   "validation_mode": "warn"
   ```
2. 或重新生成符合字数要求的 AI 分析：
   - 指标分析：150-200 字
   - 核心建议：250-300 字
   - 日报总字数：≥500 字

---

### 问题："语言配置不匹配"

**症状：**
```
语言配置不匹配: 设置为 EN(英文), 但检测到 XX 个中文汉字
```

**原因：**
AI 分析内容的语言与 `config.json` 中的 `language` 设置不一致。

**解决：**
1. 如果 `language` 为 `CN`，AI 应以中文为主（允许少量英文术语）
2. 如果 `language` 为 `EN`，AI 应以英文为主（允许少量指标术语）
3. 临时改为 `warn` 模式跳过检测（不推荐长期使用）

---

### 问题："周报/月报趋势图空白"

**症状：**
PDF 中 Chart.js 趋势图显示为空白。

**原因：**
趋势图依赖 CDN `https://cdn.jsdelivr.net/npm/chart.js`，离线环境无法加载。

**解决：**
- 在线环境：确保网络可以访问 jsdelivr CDN
- 离线环境：将 Chart.js 下载到本地，修改模板中的引用路径

---

### 问题："找不到模板文件"

**症状：**
```
FileNotFoundError: 找不到模板文件。尝试了以下路径...
```

**原因：**
1. 模板文件确实不存在
2. 语言代码不匹配（如配置了 `EN` 但缺少英文模板）

**解决：**
1. 检查 `templates/` 目录下存在对应模板：
   - 日报中文：`DAILY_TEMPLATE_MEDICAL_V2.html`
   - 日报英文：`DAILY_TEMPLATE_MEDICAL_V2_EN.html`
   - 周报中文：`WEEKLY_TEMPLATE_MEDICAL.html`
   - 周报英文：`WEEKLY_TEMPLATE_MEDICAL_EN.html`
   - 月报中文：`MONTHLY_TEMPLATE_MEDICAL.html`
   - 月报英文：`MONTHLY_TEMPLATE_MEDICAL_EN.html`
2. 如果缺少模板，系统会回退到默认模板并显示警告

---

## 🔴 邮件发送问题

### 问题："邮件发送失败"

**症状：**
报告生成成功但邮件未收到。

**解决：**
1. 检查邮件配置：
   ```bash
   python3 scripts/validate_config.py
   ```
2. 查看详细错误日志：`~/.openclaw/workspace-health/logs/health_report.log`
3. 检查发送方式优先级：
   ```json
   "provider_priority": ["oauth2", "smtp", "mail_app", "local"]
   ```
4. 使用本地模式测试（不发送邮件）：
   ```json
   "email_config": {
     "local": {"enabled": true, "output_dir": "~/reports"}
   }
   ```

---

### 问题："Gmail OAuth2 授权失败"

**症状：**
运行 `setup_oauth2.py` 时授权失败。

**常见错误及解决：**

| 错误信息 | 原因 | 解决 |
|---------|------|------|
| 未获取到 refresh_token | 用户之前已授权过 | 访问 https://myaccount.google.com/permissions 撤销权限后重试 |
| 授权失败: access_denied | 用户点击了拒绝 | 重新运行脚本，确保点击"允许" |
| 无法从 URL 中提取授权码 | 复制了错误的 URL | 确保复制的是浏览器地址栏的完整 URL（包含 code= 参数） |
| 连接超时 | 网络问题 | 检查网络连接，或尝试使用代理 |

---

### 问题："SMTP 发送失败"

**症状：**
使用 SMTP 配置时发送失败。

**解决：**
1. 确认使用的是「应用专用密码」，不是 Gmail 登录密码
2. 检查 `smtp` 配置：
   ```json
   "smtp": {
     "enabled": true,
     "server": "smtp.gmail.com",
     "port": 587,
     "use_tls": true
   }
   ```
3. 对于 Gmail，确保已在账户设置中开启"不够安全的应用访问"或使用应用专用密码

---

## 🔴 定时任务问题

### 问题："Cron 任务不执行"

**症状：**
配置了定时任务但报告未自动生成。

**解决：**
1. 检查 OpenClaw 网关是否运行正常
2. 验证 date 命令格式（macOS vs Linux）：
   - macOS: `date -v-1d +%Y-%m-%d`
   - Linux: `date -d 'yesterday' +%Y-%m-%d`
3. 检查任务指令是否正确，建议先手动执行测试
4. 查看 OpenClaw 日志排查错误

---

## 🔴 其他问题

### 问题："评分与预期不符"

**症状：**
健康评分看起来不合理。

**说明：**
V5.8.1+ 使用个性化评分算法，基于年龄、性别、BMI 计算。同一体征对不同人群的评分可能不同。

---

### 问题："如何查看详细日志"

**解决：**

1. 首先查看终端输出（实时错误信息）
2. 同时检查日志文件：`{log_dir}/health_report.log`（默认 `~/.openclaw/workspace-health/logs/health_report.log`）

查看实时日志：
```bash
tail -f ~/.openclaw/workspace-health/logs/health_report.log
```

---

## 🆘 获取帮助

如果以上方法无法解决问题：

1. 收集以下信息：
   - 操作系统版本（macOS/Linux）
   - Python 版本：`python3 --version`
   - 配置文件（脱敏后）
   - 错误日志
   - 执行的命令

2. 在 GitHub Issues 中提交问题：
   https://github.com/ItsjustJimmysbot/health-report/issues

---

## 📚 相关文档

- [README.md](README.md) - 完整安装和使用说明
- [SKILL.md](SKILL.md) - OpenClaw Agent 快速参考
- [config.schema.json](config.schema.json) - 配置 JSON Schema
