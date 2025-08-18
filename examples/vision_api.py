#!/usr/bin/env python3
"""
图像理解示例

演示如何使用PuterAI代理服务器进行图像分析和理解。
"""

import openai
import os
import base64
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

def encode_image_to_base64(image_path):
    """将本地图像文件编码为base64"""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def main():
    # 配置OpenAI客户端
    client = openai.OpenAI(
        api_key=os.getenv("API_TOKEN", "your-puter-api-token"),
        base_url="http://localhost:9595/v1"
    )
    
    print("👁️ PuterAI图像理解示例")
    print("=" * 40)
    
    try:
        # 示例1: 分析在线图像
        print("🌐 分析在线图像...")
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "请详细描述这张图片的内容，包括物体、颜色、场景等。"},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/dd/Gfp-wisconsin-madison-the-nature-boardwalk.jpg/2560px-Gfp-wisconsin-madison-the-nature-boardwalk.jpg"
                            }
                        }
                    ]
                }
            ]
        )
        
        print("🤖 AI分析结果:")
        print(response.choices[0].message.content)
        print()
        
        # 示例2: 分析本地图像 (如果有的话)
        local_image_path = "test_image.jpg"
        if os.path.exists(local_image_path):
            print("📱 分析本地图像...")
            base64_image = encode_image_to_base64(local_image_path)
            
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "这张图片里有什么？请用中文回答。"},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ]
            )
            
            print("🤖 本地图像分析:")
            print(response.choices[0].message.content)
            print()
        else:
            print(f"ℹ️ 未找到本地图像文件: {local_image_path}")
        
        # 示例3: 图像中的文字识别 (OCR)
        print("📝 图像文字识别 (OCR)...")
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "请识别并提取这张图片中的所有文字内容。"},
                        {
                            "type": "image_url",
                            "image_url": {
                                # 使用一个包含文字的示例图片
                                "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/47/PNG_transparency_demonstration_1.png/280px-PNG_transparency_demonstration_1.png"
                            }
                        }
                    ]
                }
            ]
        )
        
        print("📖 文字识别结果:")
        print(response.choices[0].message.content)
        print()
        
        # 示例4: 图像比较
        print("🔍 图像内容问答...")
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "这张图片的主要颜色是什么？适合在什么时候拍摄？"},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/dd/Gfp-wisconsin-madison-the-nature-boardwalk.jpg/2560px-Gfp-wisconsin-madison-the-nature-boardwalk.jpg"
                            }
                        }
                    ]
                }
            ]
        )
        
        print("💡 图像问答结果:")
        print(response.choices[0].message.content)
        
    except Exception as e:
        print(f"❌ 错误: {e}")
        print("请确保:")
        print("1. 代理服务器正在运行 (python API/openai_server.py)")
        print("2. 已设置正确的API_TOKEN环境变量")
        print("3. 使用支持视觉功能的模型 (如 gpt-4o)")

if __name__ == "__main__":
    main()
