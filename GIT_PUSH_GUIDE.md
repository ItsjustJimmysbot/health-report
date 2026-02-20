# 🚀 推送到 Git 仓库指南

## 步骤 1: 在 GitHub/GitLab 创建仓库

1. 访问 https://github.com/new
2. 输入仓库名称: `health-agent-skill`
3. 选择 "Public" 或 "Private"
4. **不要** 初始化 README（我们已经有 README.md）
5. 点击 "Create repository"

## 步骤 2: 初始化本地 Git 仓库

```bash
cd ~/health-agent-skill

# 初始化 Git
git init

# 添加所有文件
git add .

# 提交
git commit -m "Initial commit: Health Agent Skill v1.0

Features:
- Automated health report generation from Apple Health
- AI-powered analysis (Kimi K2.5 by default)
- Bilingual reports (Chinese/English)
- Email delivery via Mail.app
- Interactive CLI setup wizard
- Daily scheduled execution

Includes:
- install.sh - Interactive setup wizard
- SKILL.md - OpenClaw skill manifest
- Python scripts for data parsing and PDF generation
- HTML templates for reports
- Documentation and examples"
```

## 步骤 3: 推送到远程

```bash
# 添加远程仓库（替换 YOUR_USERNAME）
git remote add origin https://github.com/YOUR_USERNAME/health-agent-skill.git

# 推送
git branch -M main
git push -u origin main
```

## 步骤 4: 创建 Tag（版本发布）

```bash
# 创建版本标签
git tag -a v1.0.0 -m "Release v1.0.0 - Initial stable release

- Complete health report automation
- Bilingual support
- Email delivery
- CLI setup wizard"

# 推送标签
git push origin v1.0.0
```

## 步骤 5: 验证

访问: `https://github.com/YOUR_USERNAME/health-agent-skill`

检查：
- ✅ 所有文件已上传
- ✅ README 显示正确
- ✅ LICENSE 是 MIT
- ✅ 没有敏感信息泄露

## 🔒 安全检查清单

推送前确认：

- [ ] 没有真实邮箱地址（使用 `<YOUR_EMAIL>` 占位符）
- [ ] 没有 API Key（使用占位符）
- [ ] 没有个人路径（使用 `<YOUR_PATH>` 占位符）
- [ ] .gitignore 包含敏感文件
- [ ] 没有 PDF 或生成的报告
- [ ] 没有日志文件

## 📋 项目结构检查

```
health-agent-skill/
├── .gitignore           ✅ 忽略敏感文件
├── LICENSE              ✅ MIT License
├── README.md            ✅ 项目说明
├── SKILL.md             ✅ OpenClaw 技能清单
├── install.sh           ✅ 交互式安装向导
├── scripts/             ✅ 核心脚本
│   ├── generate_report.py
│   └── send_email.sh
├── templates/           ✅ 报告模板（占位符）
├── docs/                ✅ 文档
│   ├── INSTALL.md
│   ├── CONFIG.md
│   └── CUSTOMIZE.md
└── examples/            ✅ 示例配置
    └── config.example.env
```

## 🔄 后续更新

当你更新代码时：

```bash
cd ~/health-agent-skill

# 查看改动
git status

# 添加改动
git add .

# 提交
git commit -m "Update: Add new feature X

- Description of changes
- Why this change was made"

# 推送
git push origin main

# 更新版本标签（如果是大版本）
git tag -a v1.1.0 -m "Release v1.1.0"
git push origin v1.1.0
```

## 📦 发布到 OpenClaw Skill Hub

如果你想让其他 OpenClaw 用户更容易发现：

1. 完善 README 和文档
2. 录制演示视频或 GIF
3. 提交到 OpenClaw Community Forum
4. 申请加入官方 Skill Hub

## 💡 分享给朋友

朋友可以这样安装：

```bash
# 方法 1: 直接克隆
git clone https://github.com/YOUR_USERNAME/health-agent-skill.git
cd health-agent-skill
bash install.sh

# 方法 2: 通过 OpenClaw（如果加入 Hub）
openclaw skill install health-agent
```

---

## 常见问题

### Q: 不小心推送了敏感信息怎么办？

**A**: 立即撤销并清理历史

```bash
# 撤销最后一次提交（如果还没 push）
git reset --soft HEAD~1

# 如果已经 push，需要强制覆盖（谨慎！）
git reset --hard HEAD~1
git push --force origin main

# 更安全的做法：使用 git-filter-repo 清理历史
# https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository
```

### Q: 可以只分享给自己用吗？

**A**: 可以！设置为 Private 仓库即可。

### Q: 如何更新已安装的 Skill？

**A**: 
```bash
cd ~/health-agent-skill
git pull origin main
bash install.sh  # 重新配置（如果需要）
```

---

**完成后，你的朋友就可以使用你的 Health Agent Skill 了！** 🎉
