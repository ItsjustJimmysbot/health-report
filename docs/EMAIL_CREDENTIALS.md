# 🔐 邮箱安全凭证管理

## 存储位置

### macOS 钥匙串 (Keychain)
**服务名**: `himalaya-outlook-imap`  
**账户**: `itestmolt@outlook.com`  
**存储时间**: 2026-02-20  
**用途**: Outlook IMAP/SMTP 应用专用密码

**访问命令**:
```bash
security find-generic-password -s himalaya-outlook-imap -w
```

**更新命令**:
```bash
security add-generic-password \
  -s himalaya-outlook-imap \
  -a "itestmolt@outlook.com" \
  -w "新密码" \
  -T "" \
  -U
```

---

## ⚠️ 当前状态

### 严重限制 - 2026-02-20
**Microsoft 已完全阻止 Outlook.com 的 Basic Auth**

- ❌ IMAP 接收: 被阻止 (BasicAuthBlocked)
- ❌ SMTP 发送: 被阻止 (TLS handshake 失败)
- ⚠️ 即使使用应用专用密码也无法连接

**Microsoft 官方政策**: 从 2022 年底开始，逐步淘汰 Basic Auth，强制使用 OAuth2。

---

## 🔧 可行解决方案

### 方案 1: 切换到 Gmail (推荐 ✓)

Gmail 仍支持应用专用密码：

**配置步骤**:
1. 开启 Gmail 双重验证
2. 创建应用专用密码
3. 配置 Himalaya:

```toml
[accounts.gmail]
email = "your@gmail.com"
display-name = "Health Agent"
default = true

[accounts.gmail.backend]
type = "imap"
host = "imap.gmail.com"
port = 993
encryption.type = "tls"
login = "your@gmail.com"
auth.type = "password"
auth.cmd = "security find-generic-password -s himalaya-gmail -w"

[accounts.gmail.message.send.backend]
type = "smtp"
host = "smtp.gmail.com"
port = 465
encryption.type = "tls"
login = "your@gmail.com"
auth.type = "password"
auth.cmd = "security find-generic-password -s himalaya-gmail -w"
```

**优点**: 
- ✅ IMAP 正常工作
- ✅ SMTP 发送正常
- ✅ 应用专用密码支持良好

### 方案 2: 使用 Microsoft Graph API

通过 REST API 访问 Outlook：

```bash
# 需要 Azure AD 应用注册
# 使用 curl 或专用工具调用 Graph API
```

**复杂性**: 高
**稳定性**: 高

### 方案 3: 使用其他邮件服务商

- **Fastmail**: 支持 IMAP/SMTP + 应用密码
- **ProtonMail**: 需要桥接应用
- **Zoho Mail**: 支持应用专用密码

---

## 📋 标准流程建议

由于 Outlook 的限制，建议：

1. **短期**: 配置 Gmail 用于邮件收发
2. **中期**: 考虑 Microsoft Graph API 集成
3. **长期**: 评估专用邮件服务商

**相关文件**:
- 配置文件: `~/.config/himalaya/config.toml`
- 密码存储: macOS 钥匙串 `himalaya-outlook-imap` (当前不可用)
- 本文档: `docs/EMAIL_CREDENTIALS.md`

---

## 🔒 安全提醒

- 应用专用密码存储在 macOS 钥匙串中
- 即使当前无法使用，密码仍安全存储
- 如需切换到 Gmail，建议使用相同方式存储
- 定期轮换（建议每 90 天）

---

## 📝 操作记录

**2026-02-20**:
- 存储 Outlook 应用专用密码到钥匙串
- 尝试 IMAP 连接失败 (BasicAuthBlocked)
- 尝试 SMTP 发送失败 (TLS handshake)
- 结论: Microsoft 已完全阻止 Basic Auth
- 建议: 切换到 Gmail

---

**最后更新**: 2026-02-20
