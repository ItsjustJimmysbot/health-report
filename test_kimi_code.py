import urllib.request
import json

# 尝试Kimi Code API的不同端点
api_key = "sk-kimi-qhWlL4ICFUQskAEryqnGRxKwj7oWFYcueuedkjSWcCwnktzEUyCgFpZOMGUmymk0"

# 可能的端点
endpoints = [
    "https://www.kimi.com/api/v1/chat/completions",
    "https://kimi.com/api/v1/chat/completions", 
    "https://api.kimi.com/v1/chat/completions",
    "https://www.kimi.com/v1/chat/completions"
]

headers = {
    'Authorization': f'Bearer {api_key}',
    'Content-Type': 'application/json'
}

data = {
    'model': 'kimi-k2-5',
    'messages': [{'role': 'user', 'content': 'Hello'}],
    'max_tokens': 10
}

for url in endpoints:
    try:
        print(f"\n尝试: {url}")
        req = urllib.request.Request(url, data=json.dumps(data).encode(), headers=headers, method='POST')
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read().decode())
            print(f"✅ 成功!")
            print(result['choices'][0]['message']['content'][:50])
            break
    except urllib.error.HTTPError as e:
        print(f"❌ HTTP {e.code}: {e.reason}")
    except Exception as e:
        print(f"❌ {type(e).__name__}: {str(e)[:50]}")
