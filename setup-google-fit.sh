#!/bin/bash
#
# 一键设置 Google Fit API 授权
#

set -e

CREDENTIALS_DIR="${HOME}/.openclaw/credentials"
TOKEN_FILE="$CREDENTIALS_DIR/google-fit-token.json"
CRED_FILE="$CREDENTIALS_DIR/google-fit-credentials.json"

# 颜色
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "=========================================="
echo -e "${BLUE}Google Fit API 授权配置${NC}"
echo "=========================================="
echo ""

# 检查凭证文件
if [[ ! -f "$CRED_FILE" ]]; then
    echo -e "${YELLOW}未找到 Google Fit 凭证文件${NC}"
    echo ""
    echo "请先完成以下步骤："
    echo "1. 访问 https://console.cloud.google.com/"
    echo "2. 创建新项目并启用 Fitness API"
    echo "3. 创建 OAuth client ID (Desktop app)"
    echo "4. 下载 client_secret.json"
    echo ""
    read -p "请输入 client_secret.json 的路径: " CLIENT_SECRET_PATH
    
    if [[ ! -f "$CLIENT_SECRET_PATH" ]]; then
        echo "❌ 文件不存在"
        exit 1
    fi
    
    mkdir -p "$CREDENTIALS_DIR"
    cp "$CLIENT_SECRET_PATH" "$CRED_FILE"
    echo -e "${GREEN}✅ 凭证文件已保存${NC}"
fi

# 检查是否已有 token
if [[ -f "$TOKEN_FILE" ]]; then
    echo -e "${YELLOW}已存在访问令牌，是否重新授权？(y/n)${NC}"
    read -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${GREEN}使用现有授权${NC}"
        exit 0
    fi
fi

# Python 授权脚本
python3 << 'PYTHON_SCRIPT'
import json
import os
import sys
import subprocess
from urllib.parse import urlencode, parse_qs, urlparse
import http.server
import socketserver
import threading
import webbrowser

CREDENTIALS_DIR = os.path.expanduser("~/.openclaw/credentials")
TOKEN_FILE = os.path.join(CREDENTIALS_DIR, "google-fit-token.json")
CRED_FILE = os.path.join(CREDENTIALS_DIR, "google-fit-credentials.json")

# 读取凭证
with open(CRED_FILE, 'r') as f:
    cred_data = json.load(f)

client_id = cred_data.get('installed', {}).get('client_id')
client_secret = cred_data.get('installed', {}).get('client_secret')
auth_uri = cred_data.get('installed', {}).get('auth_uri', 'https://accounts.google.com/o/oauth2/auth')
token_uri = cred_data.get('installed', {}).get('token_uri', 'https://oauth2.googleapis.com/token')

if not client_id or not client_secret:
    print("❌ 凭证文件格式错误")
    sys.exit(1)

# 授权范围和重定向 URI
scopes = [
    "https://www.googleapis.com/auth/fitness.sleep.read",
    "https://www.googleapis.com/auth/fitness.activity.read"
]
redirect_uri = "http://localhost:8080/oauth2callback"

# 构建授权 URL
auth_params = {
    "client_id": client_id,
    "redirect_uri": redirect_uri,
    "scope": " ".join(scopes),
    "response_type": "code",
    "access_type": "offline",
    "prompt": "consent"
}

auth_url = f"{auth_uri}?{urlencode(auth_params)}"

print("=" * 50)
print("正在启动授权流程...")
print("=" * 50)
print()
print("请在浏览器中完成授权")
print()

# 启动本地服务器接收回调
auth_code = None

class OAuthHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        global auth_code
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        
        if 'code' in params:
            auth_code = params['code'][0]
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b"""
                <html>
                <body style="font-family: Arial; text-align: center; padding: 50px;">
                    <h1 style="color: green;">✓ 授权成功！</h1>
                    <p>请返回终端查看结果</p>
                </body>
                </html>
            """)
        else:
            self.send_response(400)
            self.end_headers()

    def log_message(self, format, *args):
        pass

def start_server():
    with socketserver.TCPServer(("", 8080), OAuthHandler) as httpd:
        httpd.handle_request()

# 在后台启动服务器
server_thread = threading.Thread(target=start_server)
server_thread.daemon = True
server_thread.start()

# 打开浏览器
webbrowser.open(auth_url)

print("等待授权回调...")
server_thread.join(timeout=120)

if not auth_code:
    print("❌ 授权超时或失败")
    sys.exit(1)

print("🔑 获取到授权码，正在交换访问令牌...")

# 交换授权码获取 token
token_response = subprocess.run([
    'curl', '-s', '-X', 'POST', token_uri,
    '-d', f'code={auth_code}',
    '-d', f'client_id={client_id}',
    '-d', f'client_secret={client_secret}',
    '-d', f'redirect_uri={redirect_uri}',
    '-d', 'grant_type=authorization_code'
], capture_output=True, text=True)

token_data = json.loads(token_response.stdout)

if 'error' in token_data:
    print(f"❌ 获取 token 失败: {token_data.get('error_description', token_data['error'])}")
    sys.exit(1)

# 保存 token
with open(TOKEN_FILE, 'w') as f:
    json.dump(token_data, f, indent=2)

print()
print("=" * 50)
print("✅ Google Fit 授权成功！")
print("=" * 50)
print(f"令牌已保存到: {TOKEN_FILE}")
PYTHON_SCRIPT

echo ""
echo -e "${GREEN}✅ 授权完成${NC}"
echo ""
echo "现在可以运行: ./scripts/daily_health_report_auto.sh"
