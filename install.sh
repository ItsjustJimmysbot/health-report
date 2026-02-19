#!/bin/bash
#
# Health Report - 交互式安装脚本
#

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印函数
print_header() {
    echo ""
    echo "=========================================="
    echo -e "${BLUE}$1${NC}"
    echo "=========================================="
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# 检查 Python
print_header "检查系统环境"
if ! command -v python3 &> /dev/null; then
    print_error "未找到 Python3，请先安装 Python 3.9+"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
print_success "Python 版本: $PYTHON_VERSION"

# 检查 macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    print_warning "此工具专为 macOS 设计，其他系统可能无法正常工作"
    read -p "是否继续安装？(y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

print_success "系统检查通过"

# 安装依赖
print_header "步骤 1/5: 安装 Python 依赖"
print_info "正在安装必要的 Python 包..."

pip3 install playwright pyyaml --break-system-packages 2>/dev/null || pip3 install playwright pyyaml --user

print_success "Python 依赖安装完成"

# 安装 Chromium
print_header "步骤 2/5: 安装 Chromium 浏览器"
print_info "Playwright 需要 Chromium 来生成 PDF 报告..."
playwright install chromium

print_success "Chromium 安装完成"

# 配置 Google Drive 路径
print_header "步骤 3/5: 配置 Google Drive 同步路径"
print_info "Health Auto Export 应用会将数据同步到 Google Drive"
echo ""
echo "请确保："
echo "  1. 已在 iPhone 上安装 Health Auto Export 应用"
echo "  2. 已配置每日自动导出到 Google Drive"
echo "  3. Google Drive 已同步到本地电脑"
echo ""

DEFAULT_PATH="${HOME}/我的云端硬盘/Health Auto Export"
read -p "请输入 Health Auto Export 的本地路径 [$DEFAULT_PATH]: " HEALTH_PATH
HEALTH_PATH=${HEALTH_PATH:-$DEFAULT_PATH}

if [[ ! -d "$HEALTH_PATH" ]]; then
    print_warning "路径不存在: $HEALTH_PATH"
    print_info "请先在 iPhone 上完成配置并等待同步"
    read -p "是否继续安装？(y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# 保存配置
CREDENTIALS_DIR="${HOME}/.openclaw/credentials"
mkdir -p "$CREDENTIALS_DIR"
echo "$HEALTH_PATH" > "$CREDENTIALS_DIR/health-report-path.conf"

print_success "路径配置已保存: $HEALTH_PATH"

# Google Fit API 设置
print_header "步骤 4/5: 配置 Google Fit API"
print_info "Google Fit 用于获取睡眠数据"
echo ""
echo "你需要完成以下步骤："
echo ""
echo -e "${YELLOW}1. 访问 Google Cloud Console:${NC}"
echo "   https://console.cloud.google.com/"
echo ""
echo -e "${YELLOW}2. 创建新项目:${NC}"
echo "   - 点击项目选择器 → New Project"
echo "   - 项目名称: health-report"
echo "   - 点击 Create"
echo ""
echo -e "${YELLOW}3. 启用 Fitness API:${NC}"
echo "   - 进入 APIs & Services → Library"
echo "   - 搜索 'Fitness API' 并点击 Enable"
echo ""
echo -e "${YELLOW}4. 创建 OAuth 凭证:${NC}"
echo "   - 进入 APIs & Services → Credentials"
echo "   - 点击 Create Credentials → OAuth client ID"
echo "   - 应用类型: Desktop app"
echo "   - 名称: Health Report"
echo "   - 点击 Create"
echo ""
echo -e "${YELLOW}5. 下载凭证文件:${NC}"
echo "   - 点击 Download JSON"
echo "   - 保存为 client_secret.json"
echo ""

read -p "是否已完成上述步骤？(y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    read -p "请输入 client_secret.json 的完整路径: " CLIENT_SECRET_PATH
    
    if [[ -f "$CLIENT_SECRET_PATH" ]]; then
        cp "$CLIENT_SECRET_PATH" "$CREDENTIALS_DIR/google-fit-credentials.json"
        print_success "凭证文件已保存"
    else
        print_error "文件不存在: $CLIENT_SECRET_PATH"
        print_warning "你可以稍后运行 ./setup-google-fit.sh 来配置"
    fi
else
    print_warning "你可以稍后运行 ./setup-google-fit.sh 来配置"
fi

# 邮件配置
print_header "步骤 5/5: 配置邮件发送"
print_info "报告将通过 macOS Mail.app 发送"
echo ""

read -p "请输入接收报告的邮箱地址: " EMAIL
if [[ -n "$EMAIL" ]]; then
    echo "$EMAIL" > "$CREDENTIALS_DIR/health-report-email.conf"
    print_success "邮箱已保存: $EMAIL"
else
    print_warning "未设置邮箱，你可以稍后编辑 scripts/daily_health_report_auto.sh"
fi

# 设置定时任务
print_header "设置每日定时任务"
read -p "是否设置每天 12:30 自动发送报告？(y/n): " -n 1 -r
echo

if [[ $REPLY =~ ^[Yy]$ ]]; then
    SCRIPT_PATH="$(pwd)/scripts/daily_health_report_auto.sh"
    LOG_PATH="$(pwd)/logs/daily_report.log"
    mkdir -p "$(pwd)/logs"
    
    # 添加 cron 任务
    (crontab -l 2>/dev/null | grep -v "daily_health_report_auto" || true; \
     echo "30 12 * * * $SCRIPT_PATH >> $LOG_PATH 2>&1") | crontab -
    
    print_success "定时任务已设置: 每天 12:30"
else
    print_info "已跳过定时任务设置"
    print_info "你可以稍后手动运行: ./scripts/daily_health_report_auto.sh"
fi

# 完成
print_header "安装完成！"
echo ""
print_success "Health Report 已成功安装"
echo ""
echo -e "${BLUE}下一步:${NC}"
echo ""
echo "1. 测试运行："
echo "   ./scripts/daily_health_report_auto.sh"
echo ""
echo "2. 查看日志："
echo "   tail -f logs/daily_report.log"
echo ""
echo "3. 手动生成报告："
echo "   ./scripts/generate_single_report.sh YYYY-MM-DD"
echo ""
echo "4. 修改配置："
echo "   编辑 scripts/daily_health_report_auto.sh"
echo ""
print_info "感谢使用 Health Report！"
