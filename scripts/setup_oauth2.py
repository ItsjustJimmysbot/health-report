#!/usr/bin/env python3
"""Gmail OAuth2 授权设置脚本

使用方法:
    python3 scripts/setup_oauth2.py

流程:
    1. 引导用户在 Google Cloud Console 创建 OAuth2 凭证
    2. 生成授权 URL，用户浏览器完成授权
    3. 获取 refresh_token 并保存到 config.json

注意:
    - refresh_token 长期有效（直到用户撤销权限）
    - 只需运行一次，后续使用 refresh_token 自动获取 access_token
"""

import json
import webbrowser
from pathlib import Path
from urllib.parse import urlencode, parse_qs, urlparse

import requests


def setup_gmail_oauth2():
    """引导用户完成 Gmail OAuth2 授权流程"""
    print("=" * 60)
    print("Gmail OAuth2 授权设置")
    print("=" * 60)
    
    # 1. 获取 Client ID 和 Secret
    print("\n📖 步骤 1: 创建 OAuth2 凭证")
    print("-" * 60)
    print("1. 访问 Google Cloud Console:")
    print("   https://console.cloud.google.com/apis/credentials")
    print("\n2. 创建新项目或选择现有项目")
    print("\n3. 启用 Gmail API:")
    print("   - 左侧菜单: APIs & Services > Library")
    print("   - 搜索 'Gmail API' 并启用")
    print("\n4. 创建 OAuth2 凭证:")
    print("   - 左侧菜单: APIs & Services > Credentials")
    print("   - 点击 'Create Credentials' > 'OAuth client ID'")
    print("   - 应用类型选择 'Desktop app'")
    print("   - 名称填写 'Health Report'")
    print("   - 点击 'Create'")
    print("\n5. 下载或复制 Client ID 和 Client Secret")
    
    client_id = input("\n📝 请输入 Client ID: ").strip()
    client_secret = input("📝 请输入 Client Secret: ").strip()
    
    if not client_id or not client_secret:
        print("❌ Client ID 和 Client Secret 不能为空")
        return
    
    # 2. 生成授权 URL
    redirect_uri = "http://localhost:8080/callback"
    scope = "https://www.googleapis.com/auth/gmail.send"
    
    auth_url = "https://accounts.google.com/o/oauth2/v2/auth"
    params = {
        'client_id': client_id,
        'redirect_uri': redirect_uri,
        'scope': scope,
        'response_type': 'code',
        'access_type': 'offline',
        'prompt': 'consent'  # 强制获取 refresh_token
    }
    
    full_url = f"{auth_url}?{urlencode(params)}"
    
    print("\n📖 步骤 2: 浏览器授权")
    print("-" * 60)
    print("正在打开浏览器，请完成授权...")
    webbrowser.open(full_url)
    
    print("\n⚠️  注意: 授权完成后，浏览器会跳转到 localhost:8080（可能显示无法访问）")
    print("    这是正常的，只需从地址栏复制完整 URL 即可")
    
    # 3. 获取授权码
    print("\n📖 步骤 3: 获取授权码")
    print("-" * 60)
    callback_url = input("📝 请粘贴浏览器地址栏的完整 URL: ").strip()
    
    # 4. 交换 access_token 和 refresh_token
    parsed = urlparse(callback_url)
    query_params = parse_qs(parsed.query)
    
    if 'error' in query_params:
        print(f"❌ 授权失败: {query_params['error'][0]}")
        return
    
    code = query_params.get('code', [''])[0]
    
    if not code:
        print("❌ 无法从 URL 中提取授权码")
        print(f"   URL: {callback_url[:100]}...")
        return
    
    print("\n🔄 正在换取访问令牌...")
    
    token_url = "https://oauth2.googleapis.com/token"
    data = {
        'code': code,
        'client_id': client_id,
        'client_secret': client_secret,
        'redirect_uri': redirect_uri,
        'grant_type': 'authorization_code'
    }
    
    try:
        response = requests.post(token_url, data=data, timeout=30)
        response.raise_for_status()
        token_data = response.json()
    except Exception as e:
        print(f"❌ 获取令牌失败: {e}")
        return
    
    if 'refresh_token' not in token_data:
        print("❌ 未获取到 refresh_token")
        print("   可能原因：用户之前已授权过，Google 不会再次提供 refresh_token")
        print("   解决方法：访问 https://myaccount.google.com/permissions")
        print("            撤销该应用的权限，然后重新运行此脚本")
        return
    
    print("✅ 成功获取 refresh_token!")
    
    # 5. 获取发件人邮箱
    print("\n📖 步骤 4: 配置发件人邮箱")
    print("-" * 60)
    sender_email = input("📝 请输入发件人邮箱 (如 your-name@gmail.com): ").strip()
    
    if not sender_email:
        print("❌ 发件人邮箱不能为空")
        return
    
    # 6. 保存配置
    config_updates = {
        "email_config": {
            "provider_priority": ["oauth2", "smtp", "mail_app", "local"],
            "oauth2": {
                "enabled": True,
                "provider": "gmail",
                "client_id": client_id,
                "client_secret": client_secret,
                "refresh_token": token_data['refresh_token'],
                "sender_email": sender_email
            }
        }
    }
    
    # 查找现有配置
    config_paths = [
        Path(__file__).parent.parent / "config.json",
        Path.home() / '.openclaw' / 'workspace-health' / 'config.json',
    ]
    
    config_path = None
    existing_config = {}
    
    for p in config_paths:
        if p.exists():
            config_path = p
            try:
                with open(p, 'r', encoding='utf-8') as f:
                    existing_config = json.load(f)
            except Exception:
                pass
            break
    
    if not config_path:
        config_path = config_paths[0]
        config_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 合并配置
    if 'email_config' in existing_config:
        existing_config['email_config'].update(config_updates['email_config'])
    else:
        existing_config['email_config'] = config_updates['email_config']
    
    # 保存
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(existing_config, f, ensure_ascii=False, indent=2)
    
    print("\n" + "=" * 60)
    print("✅ 配置完成!")
    print("=" * 60)
    print(f"\n配置已保存到: {config_path}")
    print("\n📋 重要提示:")
    print("   - refresh_token 长期有效，无需重复授权")
    print("   - 如需撤销权限，访问: https://myaccount.google.com/permissions")
    print("\n🧪 测试邮件发送:")
    print(f"   python3 scripts/send_health_report_email.py 2026-03-01 0")


if __name__ == '__main__':
    try:
        setup_gmail_oauth2()
    except KeyboardInterrupt:
        print("\n\n❌ 操作已取消")
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")