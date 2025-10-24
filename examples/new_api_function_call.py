"""
puter.com现在有另一种请求格式
"""
import requests
import json
import os

PUTER_API = "https://api.puter.com/drivers/call"

AUTH_TOKEN = os.getenv("API_TOKEN", "your-puter-api-token")

headers = {
    "accept": "*/*",
    "content-type": "text/plain;actually=json",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36 Edg/129.0.0.0",
    'Origin': 'https://docs.puter.com',
    "referer": "https://docs.puter.com/"
}

def test_puter_support(messages):
    payload = {
        "interface": "puter-chat-completion",
        "driver": "openai-completion",
        "test_mode": False,
        "method": "complete",
        "args": {
            "messages": messages,
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": "get_weather",
                        "description": "Get current weather for a given location",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "location": {
                                    "type": "string",
                                    "description": "City name e.g. Paris, London"
                                }
                            },
                            "required": ["location"]
                        }
                    }
                }
            ],
        },
        "auth_token": AUTH_TOKEN
    }

    r = requests.post(PUTER_API, headers=headers, data=json.dumps(payload),proxies={"http": "http://127.0.0.1:10809", "https": "http://127.0.0.1:10809"})
    try:
        resp = r.json()
    except Exception:
        resp = {"error": "Invalid JSON", "text": r.text}
    return resp


# ---- 测试1：旧版纯字符串 content ----
old_messages = [
    {"content": "What's the weather in Paris?"}
]
resp_old = test_puter_support(old_messages)
print("🟢 旧格式响应：")
print(json.dumps(resp_old, indent=2, ensure_ascii=False))


# ---- 测试2：新版多段式 content ----
new_messages = [
    {
        "content": [
            {"type": "text", "text": "What's the weather in Paris?"},
            {"type": "text", "text": "Please use the get_weather function."}
        ]
    }
]
resp_new = test_puter_support(new_messages)
print("\n🟠 新格式响应：")
print(json.dumps(resp_new, indent=2, ensure_ascii=False))