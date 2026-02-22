#!/bin/bash
#
# Mail.app 邮件操作脚本
# 使用 macOS 自带 Mail.app 进行邮件收发
#

# 显示收件箱邮件列表
list_inbox() {
    local limit=${1:-10}
    osascript << EOF
tell application "Mail"
    set msgList to {}
    set inboxMessages to messages 1 thru $limit of inbox
    repeat with msg in inboxMessages
        set msgSubject to subject of msg
        set msgSender to sender of msg
        set msgDate to date received of msg
        set msgRead to read status of msg
        set readFlag to ""
        if msgRead then set readFlag to "✓"
        set end of msgList to readFlag & " | " & msgSubject & " | " & msgSender & " | " & msgDate
    end repeat
    return msgList
end tell
EOF
}

# 读取特定邮件内容
read_message() {
    local msg_id=$1
    osascript << EOF
tell application "Mail"
    set targetMessage to message id $msg_id of inbox
    return "Subject: " & (subject of targetMessage) & "\n" & \
           "From: " & (sender of targetMessage) & "\n" & \
           "Date: " & (date received of targetMessage) & "\n" & \
           "Content:\n" & (content of targetMessage)
end tell
EOF
}

# 发送邮件
send_email() {
    local to=$1
    local subject=$2
    local content=$3
    
    osascript << EOF
tell application "Mail"
    set newMessage to make new outgoing message with properties {subject:"$subject", content:"$content"}
    tell newMessage
        make new to recipient at end of to recipients with properties {address:"$to"}
        send
    end tell
    return "邮件已发送"
end tell
EOF
}

# 搜索邮件
search_emails() {
    local keyword=$1
    osascript << EOF
tell application "Mail"
    set foundMessages to {}
    set allMessages to messages of inbox
    repeat with msg in allMessages
        if subject of msg contains "$keyword" then
            set end of foundMessages to (subject of msg) & " | " & (sender of msg)
        end if
    end repeat
    return foundMessages
end tell
EOF
}

# 发送健康报告邮件
send_health_report() {
    local report_path=$1
    local date_str=$2
    
    local subject="每日健康报告 - $date_str"
    local content="您好，\n\n请查收您的每日健康报告。\n\n报告包含以下内容：\n- 心血管指标分析\n- 运动数据统计\n- 睡眠质量评估\n- AI 个性化建议\n\n详细报告请查看附件。\n\n--\n由 Health Agent 自动生成"
    
    osascript << EOF
tell application "Mail"
    set newMessage to make new outgoing message with properties {subject:"$subject", content:"$content"}
    tell newMessage
        make new to recipient at end of to recipients with properties {address:"itestmolt@outlook.com"}
        tell content
            make new attachment with properties {file name:"$report_path"} at after the last word
        end tell
        send
    end tell
    return "健康报告邮件已发送"
end tell
EOF
}

# 主命令处理
case "$1" in
    list)
        list_inbox "${2:-10}"
        ;;
    read)
        read_message "$2"
        ;;
    send)
        send_email "$2" "$3" "$4"
        ;;
    search)
        search_emails "$2"
        ;;
    report)
        send_health_report "$2" "$3"
        ;;
    *)
        echo "Usage: $0 {list [limit]|read <msg_id>|send <to> <subject> <content>|search <keyword>|report <pdf_path> <date>}"
        exit 1
        ;;
esac
