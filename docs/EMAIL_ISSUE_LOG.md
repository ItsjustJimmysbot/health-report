# ⚠️ 邮件发送问题记录

## 问题描述
**时间**: 2026-02-20 23:55  
**账户**: itestmolt@outlook.com  
**错误**: `WASCL UserAction verdict is not None. Actual verdict is Suspend, ShowTierUpgrade`

## 错误分析

Microsoft Outlook 已**暂停该账户的邮件发送功能**，原因：

1. **发送频率过高** - 短时间内发送多封邮件触发反垃圾机制
2. **账户限制** - 免费账户有发送限额
3. **需要升级/验证** - `ShowTierUpgrade` 提示需要验证或升级账户

## 影响

- ❌ 无法通过 Outlook 发送邮件
- ❌ 15 封邮件卡在发件箱
- ❌ Mail.app 的 Outlook 账户暂时不可用

## 解决方案

### 方案 1: 使用 Gmail（推荐）

**步骤**:
1. 在 Mail.app 中添加 Gmail 账户
2. 使用应用专用密码（更安全）
3. 重新配置邮件发送脚本

**优势**:
- Gmail 发送限额更宽松
- 应用专用密码支持良好
- 更稳定的服务

### 方案 2: 等待/恢复 Outlook 账户

- 等待 24 小时后重试
- 登录 outlook.com 检查账户状态
- 完成身份验证（如果需要）

### 方案 3: 使用其他邮件服务

- Fastmail
- Zoho Mail
- ProtonMail (需要桥接)

## 建议

**立即行动**:
1. 配置 Gmail 作为备用邮件账户
2. 降低发送频率（每次间隔 1-2 分钟）
3. 分批发送（每次不超过 5 封）

**长期规划**:
- 使用专用邮件服务发送自动化报告
- 考虑使用 SendGrid、AWS SES 等邮件服务 API

---

**记录时间**: 2026-02-20  
**状态**: 🔴 Outlook 账户暂停，需要切换邮箱
