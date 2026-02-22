import urllib.request
import json

# 使用新提供的Kimi API密钥
api_key = "sk-kimi-qhWlL4ICFUQskAEryqnGRxKwj7oWFYcueuedkjSWcCwnktzEUyCgFpZOMGUmymk0"

url = 'https://api.moonshot.cn/v1/chat/completions'
headers = {
    'Authorization': f'Bearer {api_key}',
    'Content-Type': 'application/json'
}

data = {
    'model': 'kimi-coding/k2p5',
    'messages': [{'role': 'user', 'content': 'Hello, please reply with OK'}],
    'max_tokens': 10
}

try:
    req = urllib.request.Request(url, data=json.dumps(data).encode(), headers=headers, method='POST')
    with urllib.request.urlopen(req, timeout=15) as resp:
        print('SUCCESS')
        result = json.loads(resp.read().decode())
        print(result['choices'][0]['message']['content'])
except urllib.error.HTTPError as e:
    print(f'HTTP Error {e.code}: {e.reason}')
    print(e.read().decode())
except Exception as e:
    print(f'Error: {e}')
