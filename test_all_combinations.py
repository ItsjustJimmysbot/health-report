import urllib.request
import json

api_key = "sk-kimi-qhWlL4ICFUQskAEryqnGRxKwj7oWFYcueuedkjSWcCwnktzEUyCgFpZOMGUmymk0"

# 更多可能的路径组合
urls = [
    # 基本路径
    "https://api.kimi.com/coding/v1/chat/completions",
    "https://api.kimi.com/v1/coding/chat/completions", 
    "https://api.kimi.com/coding/api/chat",
    "https://api.kimi.com/coding/generate",
    # 带版本
    "https://api.kimi.com/v1/chat/completions",
    "https://api.kimi.com/coding",
    # 不同子域
    "https://coding.api.kimi.com/v1/chat/completions",
    "https://kimi.com/api/coding/v1/chat/completions",
]

headers = {
    'Authorization': f'Bearer {api_key}',
    'Content-Type': 'application/json'
}

# 尝试不同的model名称
models = ['kimi-k2-5', 'k2.5', 'kimi-k2', 'kimi-coding']

for url in urls[:3]:  # 先测试前3个
    for model in models[:2]:  # 先测试前2个model
        data = {'model': model, 'messages': [{'role': 'user', 'content': 'Hi'}], 'max_tokens': 10}
        try:
            print(f"\n尝试: {url} | model: {model}")
            req = urllib.request.Request(url, data=json.dumps(data).encode(), headers=headers, method='POST')
            with urllib.request.urlopen(req, timeout=5) as resp:
                result = json.loads(resp.read().decode())
                print(f"✅ 成功! model={model}")
                print(result['choices'][0]['message']['content'])
                exit(0)
        except urllib.error.HTTPError as e:
            if e.code == 401:
                print(f"❌ 401 认证失败")
                break  # 这个URL认证失败，换下一个URL
            else:
                print(f"❌ {e.code}")
        except Exception as e:
            print(f"❌ {type(e).__name__}")

print("\n所有组合都失败了")
