import urllib.request
import json

api_key = "sk-kimi-qhWlL4ICFUQskAEryqnGRxKwj7oWFYcueuedkjSWcCwnktzEUyCgFpZOMGUmymk0"
base_url = "https://api.kimi.com/coding"

# 尝试不同的路径
paths = [
    "/chat/completions",
    "/v1/chat/completions",
    "/api/v1/chat/completions",
    "/completions",
    "/generate"
]

headers = {
    'Authorization': f'Bearer {api_key}',
    'Content-Type': 'application/json'
}

data = {
    'model': 'kimi-k2-5',
    'messages': [{'role': 'user', 'content': 'Hi'}],
    'max_tokens': 10
}

for path in paths:
    url = base_url + path
    try:
        print(f"\n尝试: {url}")
        req = urllib.request.Request(url, data=json.dumps(data).encode(), headers=headers, method='POST')
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read().decode())
            print(f"✅ 成功!")
            print(result['choices'][0]['message']['content'])
            break
    except urllib.error.HTTPError as e:
        print(f"❌ {e.code}: {e.reason}")
