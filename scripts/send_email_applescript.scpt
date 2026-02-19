#!/usr/bin/osascript
--
-- 使用 macOS Mail.app 发送健康报告
--

on run argv
    -- 获取参数
    set pdfFile to item 1 of argv
    set recipientEmail to item 2 of argv
    
    -- 如果没有指定收件人，使用默认
    if recipientEmail is "" then
        set recipientEmail to "revolutionljk@gmail.com"
    end if
    
    -- 获取文件名作为日期
    set fileName to name of (info for (pdfFile as POSIX file))
    set reportDate to do shell script "echo " & quoted form of fileName & " | grep -oE '[0-9]{4}-[0-9]{2}-[0-9]{2}' || date '+%Y-%m-%d'"
    
    tell application "Mail"
        -- 确保 Mail 在运行
        if not running then launch
        delay 1
        
        -- 创建新邮件
        set newMessage to make new outgoing message
        
        tell newMessage
            -- 设置邮件内容
            set subject to "每日健康报告 - " & reportDate
            set content to "你好，

这是你的每日健康报告 (" & reportDate & ")。

报告包含以下内容：
• 心血管指标 (心率、HRV、血氧等)
• 运动数据分析
• 睡眠质量评估
• 恢复度评分
• 个性化建议

详细的 PDF 报告请查看附件。

祝健康！

---
由 Health Agent 自动生成
"
            
            -- 添加收件人
            make new to recipient at end of to recipients with properties {address:recipientEmail}
            
            -- 添加附件
            try
                make new attachment with properties {file name:pdfFile} at after last paragraph
            on error
                -- 如果上面失败，尝试另一种方式
                tell content
                    make new attachment with properties {file name:pdfFile}
                end tell
            end try
        end tell
        
        -- 发送邮件
        send newMessage
        
        return "✅ 邮件已发送到 " & recipientEmail
    end tell
end run
