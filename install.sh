#!/bin/bash
#
# Health Agent Skill - CLI 安装向导
# 支持中文/英文双语引导
#

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 默认语言
LANG="zh"

# 欢迎信息
show_welcome() {
    if [ "$LANG" = "zh" ]; then
        echo -e "${GREEN}================================${NC}"
        echo -e "${GREEN}  Health Agent Skill 安装向导  ${NC}"
        echo -e "${GREEN}================================${NC}"
        echo ""
        echo "本向导将帮助您配置健康报告自动化系统。"
        echo ""
    else
        echo -e "${GREEN}================================${NC}"
        echo -e "${GREEN}  Health Agent Skill Installer  ${NC}"
        echo -e "${GREEN}================================${NC}"
        echo ""
        echo "This wizard will help you configure the health report automation system."
        echo ""
    fi
}

# 选择语言
select_language() {
    echo -e "${BLUE}请选择语言 / Please select language:${NC}"
    echo "1) 中文 (Chinese) - 默认"
    echo "2) English"
    read -p "[1-2]: " lang_choice
    
    case $lang_choice in
        2)
            LANG="en"
            ;;
        *)
            LANG="zh"
            ;;
    esac
    echo ""
}

# 检查前置条件
check_prerequisites() {
    if [ "$LANG" = "zh" ]; then
        echo -e "${YELLOW}>>> 步骤 1: 检查前置条件${NC}"
        echo ""
        echo "在使用本系统之前，请确保您已完成以下设置："
        echo ""
        echo "1. ${GREEN}Google Drive${NC} - 用于同步 Apple Health 数据"
        echo "   - 下载并安装 Google Drive 桌面版"
        echo "   - 登录您的 Google 账户"
        echo "   - 确保 Health Auto Export 文件夹已同步"
        echo ""
        echo "2. ${GREEN}Health Auto Export${NC} - iOS 应用"
        echo "   - 在 iPhone/iPad 上安装 Health Auto Export"
        echo "   - 配置自动导出到 Google Drive"
        echo "   - 确保每天自动生成 JSON 文件"
        echo ""
        echo "3. ${GREEN}Google Fit${NC} - 用于睡眠数据"
        echo "   - 在手机上安装 Google Fit"
        echo "   - 授权访问睡眠数据"
        echo "   - 完成 API 认证（后续步骤）"
        echo ""
        read -p "是否已完成以上设置？(y/N): " confirm
    else
        echo -e "${YELLOW}>>> Step 1: Check Prerequisites${NC}"
        echo ""
        echo "Before using this system, please ensure you have completed:"
        echo ""
        echo "1. ${GREEN}Google Drive${NC} - For syncing Apple Health data"
        echo "   - Download and install Google Drive Desktop"
        echo "   - Sign in with your Google account"
        echo "   - Ensure Health Auto Export folder is synced"
        echo ""
        echo "2. ${GREEN}Health Auto Export${NC} - iOS App"
        echo "   - Install Health Auto Export on iPhone/iPad"
        echo "   - Configure auto-export to Google Drive"
        echo "   - Ensure daily JSON files are generated"
        echo ""
        echo "3. ${GREEN}Google Fit${NC} - For sleep data"
        echo "   - Install Google Fit on your phone"
        echo "   - Authorize access to sleep data"
        echo "   - Complete API authentication (next steps)"
        echo ""
        read -p "Have you completed the above? (y/N): " confirm
    fi
    
    if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
        if [ "$LANG" = "zh" ]; then
            echo -e "${RED}请完成前置设置后再运行本向导。${NC}"
        else
            echo -e "${RED}Please complete the prerequisites first.${NC}"
        fi
        exit 1
    fi
    echo ""
}

# 配置路径
configure_paths() {
    if [ "$LANG" = "zh" ]; then
        echo -e "${YELLOW}>>> 步骤 2: 配置路径${NC}"
        echo ""
        echo "请配置以下路径："
        echo ""
    else
        echo -e "${YELLOW}>>> Step 2: Configure Paths${NC}"
        echo ""
        echo "Please configure the following paths:"
        echo ""
    fi
    
    # Health Auto Export 路径
    if [ "$LANG" = "zh" ]; then
        read -p "Health Auto Export 数据路径 [默认: ~/Google Drive/Health Auto Export/Health Data/]: " health_path
    else
        read -p "Health Auto Export data path [default: ~/Google Drive/Health Auto Export/Health Data/]: " health_path
    fi
    health_path=${health_path:-"~/Google Drive/Health Auto Export/Health Data/"}
    
    # 输出路径
    if [ "$LANG" = "zh" ]; then
        read -p "PDF 报告输出路径 [默认: ~/Documents/Health Reports/]: " output_path
    else
        read -p "PDF report output path [default: ~/Documents/Health Reports/]: " output_path
    fi
    output_path=${output_path:-"~/Documents/Health Reports/"}
    
    # 展开 ~
    health_path=$(eval echo "$health_path")
    output_path=$(eval echo "$output_path")
    
    export HEALTH_PATH="$health_path"
    export OUTPUT_PATH="$output_path"
    
    echo ""
}

# 配置邮箱
configure_email() {
    if [ "$LANG" = "zh" ]; then
        echo -e "${YELLOW}>>> 步骤 3: 配置邮件${NC}"
        echo ""
        echo "配置邮件接收地址（用于接收每日健康报告）："
        read -p "收件邮箱地址: " email
    else
        echo -e "${YELLOW}>>> Step 3: Configure Email${NC}"
        echo ""
        echo "Configure email recipient (for daily health reports):"
        read -p "Recipient email: " email
    fi
    
    if [ -z "$email" ]; then
        if [ "$LANG" = "zh" ]; then
            echo -e "${RED}邮箱地址不能为空！${NC}"
        else
            echo -e "${RED}Email address cannot be empty!${NC}"
        fi
        exit 1
    fi
    
    export RECIPIENT_EMAIL="$email"
    echo ""
}

# 配置模型
configure_model() {
    if [ "$LANG" = "zh" ]; then
        echo -e "${YELLOW}>>> 步骤 4: 选择 AI 模型${NC}"
        echo ""
        echo "请选择用于生成个性化分析的 AI 模型："
        echo ""
        echo "1) ${GREEN}Kimi K2.5 (推荐)${NC} - 默认"
        echo "   - 性价比高，中文理解能力强"
        echo "   - 足够用于健康数据分析"
        echo "   - 速度快，成本低"
        echo ""
        echo "2) GPT-4o"
        echo "   - OpenAI 最新模型"
        echo "   - 分析能力更强，但成本较高"
        echo ""
        echo "3) Claude 3.5 Sonnet"
        echo "   - Anthropic 模型"
        echo "   - 推理能力强"
        echo ""
        read -p "请选择 [1-3，默认: 1]: " model_choice
    else
        echo -e "${YELLOW}>>> Step 4: Select AI Model${NC}"
        echo ""
        echo "Please select the AI model for personalized analysis:"
        echo ""
        echo "1) ${GREEN}Kimi K2.5 (Recommended)${NC} - Default"
        echo "   - Great value, strong Chinese comprehension"
        echo "   - Sufficient for health data analysis"
        echo "   - Fast and cost-effective"
        echo ""
        echo "2) GPT-4o"
        echo "   - OpenAI's latest model"
        echo "   - Stronger analysis, but more expensive"
        echo ""
        echo "3) Claude 3.5 Sonnet"
        echo "   - Anthropic model"
        echo "   - Strong reasoning capabilities"
        echo ""
        read -p "Select [1-3, default: 1]: " model_choice
    fi
    
    case $model_choice in
        2)
            MODEL="gpt-4o"
            MODEL_NAME="GPT-4o"
            ;;
        3)
            MODEL="claude-3-5-sonnet"
            MODEL_NAME="Claude 3.5 Sonnet"
            ;;
        *)
            MODEL="kimi-coding/k2p5"
            MODEL_NAME="Kimi K2.5"
            ;;
    esac
    
    export AI_MODEL="$MODEL"
    
    if [ "$LANG" = "zh" ]; then
        echo ""
        echo -e "已选择模型: ${GREEN}$MODEL_NAME${NC}"
    else
        echo ""
        echo -e "Selected model: ${GREEN}$MODEL_NAME${NC}"
    fi
    echo ""
}

# 配置 API Key
configure_api() {
    if [ "$LANG" = "zh" ]; then
        echo -e "${YELLOW}>>> 步骤 5: 配置 API${NC}"
        echo ""
        echo "请选择您使用的 AI 服务提供商："
        echo ""
        echo "1) OpenClaw Gateway (推荐) - 默认"
        echo "   - 无需额外配置，使用系统默认"
        echo ""
        echo "2) OpenAI API"
        echo "   - 需要 OpenAI API Key"
        echo ""
        echo "3) Kimi API (Moonshot)"
        echo "   - 需要 Moonshot API Key"
        echo ""
        read -p "请选择 [1-3，默认: 1]: " api_choice
    else
        echo -e "${YELLOW}>>> Step 5: Configure API${NC}"
        echo ""
        echo "Please select your AI service provider:"
        echo ""
        echo "1) OpenClaw Gateway (Recommended) - Default"
        echo "   - No additional config needed, uses system default"
        echo ""
        echo "2) OpenAI API"
        echo "   - Requires OpenAI API Key"
        echo ""
        echo "3) Kimi API (Moonshot)"
        echo "   - Requires Moonshot API Key"
        echo ""
        read -p "Select [1-3, default: 1]: " api_choice
    fi
    
    case $api_choice in
        2)
            if [ "$LANG" = "zh" ]; then
                read -p "请输入 OpenAI API Key: " api_key
            else
                read -p "Enter OpenAI API Key: " api_key
            fi
            export API_PROVIDER="openai"
            export API_KEY="$api_key"
            ;;
        3)
            if [ "$LANG" = "zh" ]; then
                read -p "请输入 Moonshot API Key: " api_key
            else
                read -p "Enter Moonshot API Key: " api_key
            fi
            export API_PROVIDER="kimi"
            export API_KEY="$api_key"
            ;;
        *)
            export API_PROVIDER="openclaw"
            export API_KEY="default"
            ;;
    esac
    echo ""
}

# 生成配置文件
generate_config() {
    if [ "$LANG" = "zh" ]; then
        echo -e "${YELLOW}>>> 步骤 6: 生成配置${NC}"
        echo ""
    else
        echo -e "${YELLOW}>>> Step 6: Generate Configuration${NC}"
        echo ""
    fi
    
    # 创建配置文件
    cat > ~/.config/health-agent/config.env << EOF
# Health Agent Skill 配置
# 生成时间: $(date '+%Y-%m-%d %H:%M:%S')

# 数据路径
HEALTH_DATA_PATH="$HEALTH_PATH"
OUTPUT_PATH="$OUTPUT_PATH"

# 邮件设置
RECIPIENT_EMAIL="$RECIPIENT_EMAIL"

# AI 模型
AI_MODEL="$AI_MODEL"
API_PROVIDER="$API_PROVIDER"
API_KEY="$API_KEY"

# 时区
TIMEZONE="Asia/Shanghai"

# 报告时间
REPORT_TIME="12:30"
EOF

    # 创建目录
    mkdir -p "$OUTPUT_PATH"
    mkdir -p ~/.config/health-agent
    
    if [ "$LANG" = "zh" ]; then
        echo -e "${GREEN}✅ 配置文件已生成: ~/.config/health-agent/config.env${NC}"
        echo ""
    else
        echo -e "${GREEN}✅ Configuration saved to: ~/.config/health-agent/config.env${NC}"
        echo ""
    fi
}

# 安装完成
show_completion() {
    if [ "$LANG" = "zh" ]; then
        echo -e "${GREEN}================================${NC}"
        echo -e "${GREEN}     安装完成！🎉              ${NC}"
        echo -e "${GREEN}================================${NC}"
        echo ""
        echo "配置摘要："
        echo "  📊 数据源: $HEALTH_PATH"
        echo "  📁 输出目录: $OUTPUT_PATH"
        echo "  📧 收件邮箱: $RECIPIENT_EMAIL"
        echo "  🤖 AI 模型: $MODEL_NAME"
        echo ""
        echo "下一步："
        echo "  1. 运行 'health-agent setup-cron' 设置定时任务"
        echo "  2. 运行 'health-agent test' 测试生成报告"
        echo "  3. 查看 'health-agent docs' 了解更多功能"
        echo ""
        echo "📖 自定义模板："
        echo "  您可以编辑 ~/.config/health-agent/templates/ 中的 HTML 模板"
        echo "  添加更多内容、个性化建议等"
        echo ""
        echo "💡 提示："
        echo "  所有配置都可以在 OpenClaw 中通过修改 ~/.config/health-agent/config.env 来调整"
    else
        echo -e "${GREEN}================================${NC}"
        echo -e "${GREEN}     Installation Complete! 🎉  ${NC}"
        echo -e "${GREEN}================================${NC}"
        echo ""
        echo "Configuration Summary:"
        echo "  📊 Data source: $HEALTH_PATH"
        echo "  📁 Output directory: $OUTPUT_PATH"
        echo "  📧 Recipient: $RECIPIENT_EMAIL"
        echo "  🤖 AI Model: $MODEL_NAME"
        echo ""
        echo "Next steps:"
        echo "  1. Run 'health-agent setup-cron' to schedule daily reports"
        echo "  2. Run 'health-agent test' to test report generation"
        echo "  3. See 'health-agent docs' for more features"
        echo ""
        echo "📖 Customize Templates:"
        echo "  Edit HTML templates in ~/.config/health-agent/templates/"
        echo "  to add more content, personalized recommendations, etc."
        echo ""
        echo "💡 Tip:"
        echo "  All configurations can be adjusted in OpenClaw by editing ~/.config/health-agent/config.env"
    fi
}

# 主流程
main() {
    select_language
    show_welcome
    check_prerequisites
    configure_paths
    configure_email
    configure_model
    configure_api
    generate_config
    show_completion
}

# 运行
main
