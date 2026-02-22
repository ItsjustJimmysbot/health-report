# Outlook IMAP/SMTP 配置修复指南

## 问题诊断

**错误信息**: `AUTHENTICATE failed` / `LOGIN failed`

**根本原因**: Outlook.com 需要应用专用密码（App Password）进行 IMAP/SMTP 认证

---

## 解决方案

### 步骤 1: 开启 Microsoft 账户双重验证

1. 访问 https://account.microsoft.com
2. 登录你的 Outlook 账户
3. 进入 **安全** → **高级安全选项**
4. 开启 **双重验证**

### 步骤 2: 创建应用专用密码

1. 在同一页面，找到 **应用密码** 或 **创建新的应用密码**
2. 点击 **创建新的应用密码**
3. 给这个密码起个名字，例如 "Himalaya Mail"
4. 复制生成的 16 位密码（格式类似：abcd efgh ijkl mnop）

### 步骤 3: 更新 macOS 钥匙串

```bash
# 删除旧密码
security delete-generic-password -s himalaya-outlook

# 添加新密码（将 YOUR_APP_PASSWORD 替换为实际的应用密码）
security add-generic-password \
  -s himalaya-outlook \
  -a "itestmolt@outlook.com" \
  -w "YOUR_APP_PASSWORD" \
  -T "" \
  -U
```

### 步骤 4: 验证配置

```bash
# 测试 IMAP 连接
himalaya folder list

# 测试收件箱
himalaya envelope list
```

---

## 替代方案: 使用明文密码（不推荐长期使用）

如果不想使用钥匙串，可以直接在配置文件中写入密码（注意安全）：

```toml
[accounts.outlook.backend]
type = "imap"
host = "outlook.office365.com"
port = 993
encryption.type = "tls"
login = "itestmolt@outlook.com"
auth.type = "password"
auth.raw = "你的应用专用密码"
```

---

## 常见问题

### Q: 为什么不能用主密码？
A: Microsoft 出于安全考虑，第三方邮件客户端必须使用应用专用密码。

### Q: 应用密码和主密码有什么区别？
A: 应用密码是 16 位随机字符串，只能用于特定应用，不能登录网页版。

### Q: 一个应用密码可以用于多台设备吗？
A: 可以，但建议每个设备/应用创建单独的密码，便于管理。

---

## 其他可能的配置

### 如果仍然失败，尝试更改主机地址

有些地区可能需要使用：
- `imap-mail.outlook.com` (端口 993)
- `outlook.office365.com` (端口 993)

### 检查账户 IMAP 访问权限

1. 登录 https://outlook.com
2. 设置 → 邮件 → 同步邮件
3. 确保 "让设备和应用使用 POP" 或 IMAP 选项已开启

---

**需要我帮你执行步骤 3 更新钥匙串吗？** 请提供应用专用密码。
