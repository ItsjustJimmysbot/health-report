# 📧 Mail.app 邮件操作标准流程

## 概述

使用 macOS 自带 Mail.app 进行邮件收发，无需额外处理 IMAP/SMTP 认证。

**优势**:
- ✅ 系统集成，稳定可靠
- ✅ 已配置好账户，无需额外认证
- ✅ 支持附件发送
- ✅ 支持 AppleScript 自动化

---

## 配置信息

**邮件客户端**: Mail.app (系统自带)  
**账户类型**: Exchange (Outlook.com)  
**邮箱地址**: itestmolt@outlook.com

**已配置邮箱**:
- 收件箱 (Inbox)
- 发件箱 (Outbox)
- 草稿 (Drafts)
- 已发送邮件 (Sent)
- 已删除邮件 (Trash)
- 存档 (Archive)
- 等...

---

## 操作脚本

**脚本路径**: `scripts/mail_operations.sh`

### 功能列表

#### 1. 查看收件箱
```bash
bash scripts/mail_operations.sh list [数量]
```

**示例**:
```bash
# 查看最新 10 封邮件
bash scripts/mail_operations.sh list

# 查看最新 5 封邮件
bash scripts/mail_operations.sh list 5
```

**输出格式**:
```
✓ | 邮件主题 | 发件人 | 日期
```

#### 2. 发送邮件
```bash
bash scripts/mail_operations.sh send "收件人" "主题" "内容"
```

**示例**:
```bash
bash scripts/mail_operations.sh send \
  "recipient@example.com" \
  "测试邮件" \
  "这是邮件正文内容"
```

#### 3. 搜索邮件
```bash
bash scripts/mail_operations.sh search "关键词"
```

**示例**:
```bash
bash scripts/mail_operations.sh search "健康报告"
```

#### 4. 发送健康报告（带附件）
```bash
bash scripts/mail_operations.sh report "PDF路径" "日期"
```

**示例**:
```bash
bash scripts/mail_operations.sh report \
  "/path/to/2026-02-20-report-zh.pdf" \
  "2026-02-20"
```

---

## 直接 AppleScript 操作

### 发送简单邮件
```applescript
osascript << 'EOF'
tell application "Mail"
    set newMessage to make new outgoing message with properties {
        subject: "邮件主题",
        content: "邮件正文内容"
    }
    tell newMessage
        make new to recipient with properties {address: "recipient@example.com"}
        send
    end tell
end tell
EOF
```

### 发送带附件的邮件
```applescript
osascript << 'EOF'
tell application "Mail"
    set newMessage to make new outgoing message with properties {
        subject: "健康报告",
        content: "请查收附件中的健康报告。"
    }
    tell newMessage
        make new to recipient with properties {address: "itestmolt@outlook.com"}
        tell content
            make new attachment with properties {file name: "/path/to/report.pdf"}
        end tell
        send
    end tell
end tell
EOF
```

### 读取最新邮件
```applescript
osascript << 'EOF'
tell application "Mail"
    set latestMessage to first message of inbox
    return "Subject: " & (subject of latestMessage) & "\n" & \
           "From: " & (sender of latestMessage) & "\n" & \
           "Date: " & (date received of latestMessage)
end tell
EOF
```

### 统计未读邮件数
```applescript
osascript << 'EOF'
tell application "Mail"
    set unreadCount to count of (messages of inbox whose read status is false)
    return "未读邮件: " & unreadCount & " 封"
end tell
EOF
```

---

## 自动化集成

### 每日报告邮件发送

在 `generate_daily_reports.sh` 中添加：

```bash
# 发送健康报告邮件
REPORT_DATE="2026-02-20"
REPORT_PATH="${OUTPUT_DIR}/${REPORT_DATE}-report-zh.pdf"

if [ -f "$REPORT_PATH" ]; then
    bash ${WORKSPACE}/scripts/mail_operations.sh report "$REPORT_PATH" "$REPORT_DATE"
    echo "✅ 健康报告邮件已发送" >> "$LOG_FILE"
fi
```

### 心跳检查：未读邮件提醒

```bash
# 检查是否有新的健康相关邮件
UNREAD_HEALTH=$(osascript << 'EOF'
tell application "Mail"
    set healthMessages to {}
    set allMessages to messages of inbox whose read status is false
    repeat with msg in allMessages
        if subject of msg contains "健康" or subject of msg contains "Health" then
            set end of healthMessages to subject of msg
        end if
    end repeat
    return count of healthMessages
end tell
EOF
)

if [ "$UNREAD_HEALTH" -gt 0 ]; then
    echo "📧 您有 $UNREAD_HEALTH 封未读的健康相关邮件"
fi
```

---

## 安全注意事项

1. **账户安全**: Mail.app 使用系统钥匙串存储密码，安全可靠
2. **发送限制**: 注意邮件服务商的发送频率限制
3. **附件大小**: 通常限制 20-25MB，PDF 报告需控制大小
4. **隐私保护**: 健康报告包含敏感信息，注意收件人地址正确

---

## 故障排除

### 问题 1: Mail.app 未运行
**解决**: AppleScript 会自动启动 Mail.app，但首次可能需要手动授权

### 问题 2: 发送失败
**检查**:
- 网络连接
- 邮箱账户状态
- 收件人地址格式

### 问题 3: 附件发送失败
**解决**: 检查文件路径和文件是否存在

---

## 相关文件

- 操作脚本: `scripts/mail_operations.sh`
- 健康报告生成: `scripts/generate_daily_reports.sh`
- 本文档: `docs/MAIL_APP_STANDARD.md`

---

**最后更新**: 2026-02-20  
**状态**: ✅ 已验证可用
