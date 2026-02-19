#!/bin/bash
#
# Outlook 应用密码设置脚本
# 指导用户设置应用密码并存储到 macOS 钥匙串
#

echo "=========================================="
echo "  Outlook 邮箱配置向导"
echo "  邮箱: itestmolt@outlook.com"
echo "=========================================="
echo ""

echo "📋 步骤 1: 获取应用密码"
echo "------------------------"
echo "微软不再允许直接使用邮箱密码，需要创建'应用密码'。"
echo ""
echo "请按以下步骤操作:"
echo ""
echo "1. 在浏览器中打开:"
echo "   https://account.microsoft.com"
echo ""
echo "2. 登录邮箱: itestmolt@outlook.com"
echo ""
echo "3. 进入 '安全' → '高级安全选项'"
echo ""
echo "4. 确保已开启'双重验证' (如果未开启，先开启)"
echo ""
echo "5. 返回安全页面，找到 '应用密码' → '创建新的应用密码'"
echo ""
echo "6. 名称填写: Health Agent"
echo ""
echo "7. 复制生成的 16 位密码 (类似: abcd efgh ijkl mnop)"
echo ""
read -p "按回车键继续..."
echo ""

echo "📋 步骤 2: 存储密码到钥匙串"
echo "----------------------------"
echo ""
echo "请输入你刚才复制的应用密码 (输入时不显示):"
read -s APP_PASSWORD
echo ""

if [[ -z "$APP_PASSWORD" ]]; then
    echo "❌ 密码不能为空"
    exit 1
fi

# 存储到 macOS 钥匙串
echo "🔄 正在存储密码到钥匙串..."
if security add-generic-password \
    -s "himalaya-outlook" \
    -a "itestmolt@outlook.com" \
    -w "$APP_PASSWORD" \
    -U 2>&1; then
    echo ""
    echo "✅ 密码已安全存储到钥匙串"
else
    echo ""
    echo "⚠️ 存储失败，尝试更新现有密码..."
    security delete-generic-password -s "himalaya-outlook" 2>/dev/null || true
    security add-generic-password \
        -s "himalaya-outlook" \
        -a "itestmolt@outlook.com" \
        -w "$APP_PASSWORD" 2>&1 && echo "✅ 密码已更新" || echo "❌ 存储失败"
fi

echo ""
echo "📋 步骤 3: 测试配置"
echo "-------------------"
echo ""
echo "正在测试邮件配置..."

if himalaya account list 2>/dev/null | grep -q "outlook"; then
    echo "✅ 账户配置已加载"
    
    # 尝试获取收件箱列表 (测试连接)
    echo ""
    echo "🔄 测试连接..."
    if himalaya envelope list --limit 1 2>/dev/null | head -1; then
        echo ""
        echo "✅ 连接成功!"
    else
        echo ""
        echo "⚠️ 连接测试失败，可能是密码错误"
        echo "   请检查应用密码是否正确"
    fi
else
    echo "⚠️ 未找到 outlook 账户配置"
fi

echo ""
echo "=========================================="
echo "  配置完成!"
echo "=========================================="
echo ""
echo "使用方法:"
echo "  发送健康报告:"
echo "    bash ~/.openclaw/workspace-health/scripts/send_health_report.sh"
echo ""
echo "  或指定报告:"
echo "    bash ~/.openclaw/workspace-health/scripts/send_health_report.sh /path/to/report.pdf"
echo ""
echo "  或发送到其他邮箱:"
echo "    bash ~/.openclaw/workspace-health/scripts/send_health_report.sh report.pdf other@email.com"
echo ""
