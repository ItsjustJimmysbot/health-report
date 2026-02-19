#!/bin/bash
#
# AI 分析配置向导
# 配置 OpenAI、Anthropic 或其他 AI API
#

set -e

CREDENTIALS_DIR="${HOME}/.openclaw/credentials"
mkdir -p "$CREDENTIALS_DIR"

CONFIG_FILE="$CREDENTIALS_DIR/ai-config.conf"

echo "=========================================="
echo "  🤖 AI 分析配置向导"
echo "=========================================="
echo ""
echo "本向导将帮助您配置 AI API，用于生成个性化的健康建议。"
echo ""
echo "💡 如果不配置 AI，系统将使用内置的模板化分析，"
echo "   但输出内容会较为通用，不够个性化。"
echo ""

# 检查现有配置
if [[ -f "$CONFIG_FILE" ]]; then
    echo "⚠️  检测到已有 AI 配置"
    read -p "是否重新配置？(y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "保持现有配置"
        exit 0
    fi
fi

echo ""
echo "请选择 AI 提供商："
echo ""
echo "1) OpenAI (GPT-4o / GPT-4o-mini)"
echo "   - 优点: 响应快，质量好"
echo "   - 价格: ~$0.002-0.01/次"
echo ""
echo "2) Anthropic (Claude 3.5 Haiku)"
echo "   - 优点: 分析详细，理解上下文好"
echo "   - 价格: ~$0.002-0.005/次"
echo ""
echo "3) Google Gemini"
echo "   - 优点: 免费额度充足"
echo "   - 价格: 免费版足够使用"
echo ""
echo "0) 跳过配置（使用模板化分析）"
echo ""

read -p "请输入选项 (0-3): " choice

case $choice in
    1)
        PROVIDER="openai"
        echo ""
        echo "您选择了 OpenAI"
        echo ""
        echo "📋 获取 API Key 步骤："
        echo "1. 访问 https://platform.openai.com/api-keys"
        echo "2. 登录您的 OpenAI 账号"
        echo "3. 点击 'Create new secret key'"
        echo "4. 复制生成的 API Key"
        echo ""
        read -p "请输入 OpenAI API Key: " API_KEY
        echo ""
        read -p "请输入模型名称 (默认: gpt-4o-mini): " MODEL
        MODEL=${MODEL:-gpt-4o-mini}
        ;;
        
    2)
        PROVIDER="anthropic"
        echo ""
        echo "您选择了 Anthropic Claude"
        echo ""
        echo "📋 获取 API Key 步骤："
        echo "1. 访问 https://console.anthropic.com/"
        echo "2. 登录您的账号"
        echo "3. 进入 Settings → API Keys"
        echo "4. 点击 'Create Key'"
        echo ""
        read -p "请输入 Anthropic API Key: " API_KEY
        echo ""
        read -p "请输入模型名称 (默认: claude-3-5-haiku-20241022): " MODEL
        MODEL=${MODEL:-claude-3-5-haiku-20241022}
        ;;
        
    3)
        PROVIDER="gemini"
        echo ""
        echo "您选择了 Google Gemini"
        echo ""
        echo "📋 获取 API Key 步骤："
        echo "1. 访问 https://aistudio.google.com/app/apikey"
        echo "2. 登录您的 Google 账号"
        echo "3. 点击 'Create API Key'"
        echo ""
        read -p "请输入 Gemini API Key: " API_KEY
        echo ""
        read -p "请输入模型名称 (默认: gemini-1.5-flash): " MODEL
        MODEL=${MODEL:-gemini-1.5-flash}
        ;;
        
    0)
        echo ""
        echo "跳过 AI 配置，将使用模板化分析。"
        echo "您随时可以运行此脚本重新配置。"
        
        # 保存为 template 模式
        cat > "$CONFIG_FILE" <> EOF
HEALTH_AI_PROVIDER=template
HEALTH_AI_API_KEY=
HEALTH_AI_MODEL=
EOF
        
        echo ""
        echo "✅ 配置已保存"
        exit 0
        ;;
        
    *)
        echo "❌ 无效选项"
        exit 1
        ;;
esac

# 验证 API Key
if [[ -z "$API_KEY" ]]; then
    echo "❌ API Key 不能为空"
    exit 1
fi

# 保存配置
cat > "$CONFIG_FILE" <> EOF
HEALTH_AI_PROVIDER=$PROVIDER
HEALTH_AI_API_KEY=$API_KEY
HEALTH_AI_MODEL=$MODEL
EOF

echo ""
echo "✅ AI 配置已保存！"
echo ""
echo "配置信息："
echo "  提供商: $PROVIDER"
echo "  模型: $MODEL"
echo ""
echo "📁 配置文件: $CONFIG_FILE"
echo ""

# 询问是否测试
read -p "是否测试 AI 连接？(y/n): " -n 1 -r
echo

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo "🧪 测试 AI 连接..."
    
    cd "$(dirname "$0")/.."
    
    python3 <> 'PYTEST'
import sys
sys.path.insert(0, 'scripts')
from ai_analyzer import HealthAIAnalyzer

analyzer = HealthAIAnalyzer()
if analyzer.is_configured():
    print("✅ AI 配置正确")
    print(f"   提供商: {analyzer.provider}")
    print(f"   模型: {analyzer.model}")
else:
    print("❌ AI 配置有问题")
PYTEST
    
    echo ""
    echo "💡 下次生成报告时将使用 AI 分析"
fi

echo ""
echo "=========================================="
echo "  🎉 配置完成！"
echo "=========================================="
echo ""
echo "提示："
echo "  - 每日报告将使用 AI 生成个性化建议"
echo "  - 如需修改配置，重新运行此脚本"
echo "  - 配置保存在: ~/.openclaw/credentials/ai-config.conf"
echo ""
