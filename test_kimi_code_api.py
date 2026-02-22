import urllib.request
import json

# 使用Kimi Code API
api_key = "sk-kimi-qhWlL4ICFUQskAEryqnGRxKwj7oWFYcueuedkjSWcCwnktzEUyCgFpZOMGUmymk0"
url = "https://api.kimi.com/coding/chat/completions"

headers = {
    'Authorization': f'Bearer {api_key}',
    'Content-Type': 'application/json'
}

data = {
    'model': 'kimi-k2-5',
    'messages': [{'role': 'user', 'content': '你好，请简单回复"OK"'}],
    'max_tokens': 10
}

try:
    req = urllib.request.Request(url, data=json.dumps(data).encode(), headers=headers, method='POST')
    with urllib.request.urlopen(req, timeout=30) as resp:
        result = json.loads(resp.read().decode())
        print('✅ API调用成功!')
        print(f"回复: {result['choices'][0]['message']['content']}")
except urllib.error.HTTPError as e:
    print(f'❌ HTTP {e.code}: {e.reason}')
    print(e.read().decode())
except Exception as e:
    print(f'❌ Error: {e}')
