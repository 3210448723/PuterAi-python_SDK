#!/usr/bin/env python3
"""
基础聊天对话示例

演示如何使用PuterAI代理服务器进行基础的聊天对话。
"""

import openai
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

def main():
    # 配置OpenAI客户端指向本地代理服务器
    client = openai.OpenAI(
        api_key=os.getenv("API_TOKEN", "your-puter-api-token"),
        base_url="http://localhost:9595/v1"
    )
    
    print("🤖 PuterAI聊天对话示例")
    print("=" * 40)
    
    try:
        # 基础聊天
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "user", "content": "你好！请简单介绍一下自己。"}
            ]
        )
        
        print("🤖 AI回复:")
        print(response.choices[0].message.content)
        print()
        
        # 流式聊天
        print("🔄 流式响应示例:")
        print("-" * 30)
        
        stream = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "user", "content": "请用一段话描述人工智能的发展前景"}
            ],
            stream=True
        )
        
        for chunk in stream:
            if chunk.choices[0].delta.content:
                print(chunk.choices[0].delta.content, end="", flush=True)
        print("\n")
        
        # 函数调用示例
        print("🔧 函数调用示例:")
        print("-" * 30)
        
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "description": "获取指定城市的天气信息",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "city": {
                                "type": "string",
                                "description": "城市名称，例如：北京、上海"
                            }
                        },
                        "required": ["city"]
                    }
                }
            }
        ]
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "user", "content": "北京今天天气怎么样？"}
            ],
            tools=tools
        )
        
        message = response.choices[0].message
        if message.tool_calls:
            print(f"AI想要调用函数: {message.tool_calls[0].function.name}")
            print(f"参数: {message.tool_calls[0].function.arguments}")
        else:
            print("AI回复:", message.content)
            
    except Exception as e:
        print(f"❌ 错误: {e}")
        print("请确保:")
        print("1. 代理服务器正在运行 (python API/openai_server.py)")
        print("2. 已设置正确的API_TOKEN环境变量")

if __name__ == "__main__":
    main()
