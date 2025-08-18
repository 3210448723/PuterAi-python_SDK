#!/usr/bin/env python3
"""
简单的API测试脚本

测试PuterAI代理服务器的基本功能。
"""

import requests
import json
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

BASE_URL = "http://localhost:9595"
API_TOKEN = os.getenv("API_TOKEN", "test-token")

def test_health():
    """测试健康检查端点"""
    print("🔍 测试健康检查...")
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 服务器健康状态: {data['status']}")
            print(f"   版本: {data['version']}")
            return True
        else:
            print(f"❌ 健康检查失败: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 连接失败: {e}")
        return False

def test_models():
    """测试模型列表"""
    print("\n📋 测试模型列表...")
    try:
        headers = {"Authorization": f"Bearer {API_TOKEN}"}
        response = requests.get(f"{BASE_URL}/v1/models", headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            models = data.get("data", [])
            print(f"✅ 获取到 {len(models)} 个模型")
            # 显示前5个模型
            for model in models[:5]:
                print(f"   - {model['id']}")
            if len(models) > 5:
                print(f"   ... 还有 {len(models) - 5} 个模型")
            return True
        else:
            print(f"❌ 获取模型失败: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 请求失败: {e}")
        return False

def test_chat():
    """测试聊天对话"""
    print("\n💬 测试聊天对话...")
    try:
        headers = {
            "Authorization": f"Bearer {API_TOKEN}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "user", "content": "请简单介绍一下人工智能"}
            ]
        }
        
        response = requests.post(
            f"{BASE_URL}/v1/chat/completions",
            headers=headers,
            json=payload
        )
        
        if response.status_code == 200:
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            print(f"✅ 聊天测试成功")
            print(f"   回复长度: {len(content)} 字符")
            print(f"   回复预览: {content[:100]}...")
            
            # 显示token使用情况
            usage = data.get("usage", {})
            if usage:
                print(f"   Token使用: {usage.get('total_tokens', 'N/A')}")
            return True
        else:
            print(f"❌ 聊天测试失败: {response.status_code}")
            print(f"   错误信息: {response.text}")
            return False
    except Exception as e:
        print(f"❌ 请求失败: {e}")
        return False

def test_image_generation():
    """测试图像生成"""
    print("\n🖼️ 测试图像生成...")
    try:
        headers = {
            "Authorization": f"Bearer {API_TOKEN}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "prompt": "一只可爱的小猫咪",
            "size": "512x512",
            "response_format": "url"
        }
        
        response = requests.post(
            f"{BASE_URL}/v1/images/generations",
            headers=headers,
            json=payload
        )
        
        if response.status_code == 200:
            data = response.json()
            image_url = data["data"][0]["url"]
            print(f"✅ 图像生成测试成功")
            print(f"   图像URL长度: {len(image_url)} 字符")
            return True
        else:
            print(f"❌ 图像生成测试失败: {response.status_code}")
            print(f"   错误信息: {response.text}")
            return False
    except Exception as e:
        print(f"❌ 请求失败: {e}")
        return False

def main():
    print("🧪 PuterAI代理服务器测试")
    print("=" * 40)
    
    # 运行所有测试
    tests = [
        ("健康检查", test_health),
        ("模型列表", test_models),
        ("聊天对话", test_chat),
        ("图像生成", test_image_generation),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        if test_func():
            passed += 1
    
    print(f"\n📊 测试结果: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 所有测试通过！服务器运行正常。")
    else:
        print("⚠️ 部分测试失败，请检查:")
        print("1. 服务器是否正在运行 (python API/openai_server.py)")
        print("2. API_TOKEN是否正确设置")
        print("3. 网络连接是否正常")

if __name__ == "__main__":
    main()
