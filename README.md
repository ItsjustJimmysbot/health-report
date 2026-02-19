# Health Report - 每日健康报告

自动生成精美的每日健康报告，整合 Apple Health 和 Google Fit 数据。

![报告示例](assets/screenshot.png)

## 功能特点

- 📊 **可视化报告**: 包含心率趋势、睡眠分析、运动记录等图表
- 📧 **自动邮件**: 每天 12:30 自动发送前一天的报告
- 🔐 **数据隐私**: 所有数据本地处理，不上传到第三方服务器
- 📱 **多数据源**: 整合 Apple Watch、iPhone 和 Google Fit 数据

## 系统要求

- macOS 12.0+
- Python 3.9+
- Apple Health（iPhone + Apple Watch）
- Google 账号

## 📚 详细教程

| 步骤 | 教程 | 说明 |
|------|------|------|
| 1 | 📱 [Health Auto Export 配置](docs/health-auto-export-setup.md) | iPhone 数据导出到 Google Drive |
| 2 | 🔑 [Google Fit API 配置](docs/google-fit-setup.md) | Google Cloud 项目创建和授权 |
| 3 | ⚙️ [交互式安装](#方式一交互式安装推荐) | 完成系统配置 |

## 快速开始

### 方式一：交互式安装（推荐）

```bash
git clone https://github.com/YOUR_USERNAME/health-report.git
cd health-report
./install.sh
```

然后按照提示完成配置。

### 方式二：手动安装

#### 1. 克隆仓库

```bash
git clone https://github.com/YOUR_USERNAME/health-report.git
cd health-report
```

#### 2. 安装依赖

```bash
pip3 install -r requirements.txt
playwright install chromium
```

#### 3. 配置数据源

**步骤 A：设置 Apple Health 数据导出**

1. 在 iPhone 上下载 [Health Auto Export](https://apps.apple.com/us/app/health-auto-export-json-csv/id111556706) 应用
2. 打开应用，点击右上角设置图标 ⚙️
3. 选择 "Export Settings"
4. 设置导出格式为 **JSON**
5. 选择导出频率为 **Daily**（每日）
6. 开启 "Auto Sync to Cloud"
7. 选择 **Google Drive** 作为同步目标
8. 登录你的 Google 账号并授权
9. 设置导出路径为：`Health Auto Export/`

**步骤 B：设置 Google Fit API**

1. 访问 [Google Cloud Console](https://console.cloud.google.com/)
2. 创建新项目：
   - 点击项目选择器
   - 点击 "New Project"
   - 输入项目名称（如：health-report）
   - 点击 "Create"
3. 启用 Fitness API：
   - 进入 "APIs & Services" → "Library"
   - 搜索 "Fitness API"
   - 点击 "Enable"
4. 创建 OAuth 凭证：
   - 进入 "APIs & Services" → "Credentials"
   - 点击 "Create Credentials" → "OAuth client ID"
   - 选择应用类型 "Desktop app"
   - 输入名称 "Health Report"
   - 点击 "Create"
   - 下载 JSON 凭证文件（client_secret_*.json）

#### 4. 运行配置向导

```bash
./setup.sh
```

向导会引导你：
- 设置 Google Drive 本地同步路径
- 导入 Google Fit API 凭证
- 授权 Google Fit 访问
- 配置邮件发送设置
- 设置每日定时任务

#### 5. 测试运行

```bash
./scripts/daily_health_report_auto.sh
```

如果配置正确，你会收到一封测试邮件。

## 配置说明

### 配置文件位置

配置文件存储在：`~/.openclaw/credentials/`

- `google-fit-credentials.json` - Google OAuth 凭证
- `google-fit-token.json` - Google Fit 访问令牌

### 自定义设置

编辑 `scripts/daily_health_report_auto.sh`：

```bash
# 修改收件邮箱
RECIPIENT="your-email@example.com"

# 修改报告时间（cron 格式）
# 默认：30 12 * * * （每天 12:30）
```

### 数据文件位置

确保 Google Drive 本地同步路径正确：

```
~/我的云端硬盘/Health Auto Export/
├── Health Data/
│   └── HealthAutoExport-YYYY-MM-DD.json
└── Workout Data/
    └── HealthAutoExport-YYYY-MM-DD.json
```

## 报告内容

每日报告包含：

| 模块 | 数据来源 | 说明 |
|------|----------|------|
| 恢复度评分 | HRV + 睡眠 + 步数 | 综合评估身体恢复状态 |
| 睡眠分析 | Google Fit | 20:00-次日 12:00 的睡眠数据 |
| 全天心率 | Apple Health | 24 小时心率趋势 |
| 锻炼心率 | Apple Health | 运动期间心率区间 |
| 活动数据 | Apple Health | 步数、爬楼、距离、卡路里 |
| 运动记录 | Apple Health | 每次运动的详细数据 |
| 健康建议 | AI 生成 | 基于数据的个性化建议 |

## 故障排除

### 问题：没有收到邮件

**解决**：
1. 检查 macOS Mail.app 是否已配置邮箱
2. 运行 `./scripts/daily_health_report_auto.sh` 查看错误信息
3. 检查 `~/.openclaw/workspace-health/logs/daily_report.log`

### 问题：睡眠数据为空

**解决**：
1. 确保 Google Fit 已授权访问
2. 运行 `./scripts/setup-google-fit-auth.sh` 重新授权
3. 检查 Health Auto Export 是否正在同步到 Google Drive

### 问题：PDF 中文显示乱码

**解决**：
确保已安装 Playwright 和 Chromium：
```bash
pip3 install playwright
playwright install chromium
```

### 问题：找不到数据文件

**解决**：
1. 检查 Google Drive 是否正确同步到本地
2. 运行配置向导重新设置路径：
   ```bash
   ./setup.sh
   ```

## 隐私说明

- 所有健康数据仅存储在本地
- Google Fit API 仅用于读取睡眠数据
- 邮件通过 macOS Mail.app 本地发送
- 不会将数据上传到任何第三方服务器

## 技术栈

- Python 3.9+
- Playwright (PDF 生成)
- Chart.js (数据可视化)
- Google Fit API (睡眠数据)
- Apple Health Export (运动和健康数据)

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！

## 更新日志

### v1.0.0 (2026-02-20)
- 初始版本发布
- 支持 Apple Health 数据导入
- 支持 Google Fit 睡眠数据
- 自动生成 PDF 报告
- 邮件自动发送
- 每日定时任务
