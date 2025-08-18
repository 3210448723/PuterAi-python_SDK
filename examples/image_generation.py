#!/usr/bin/env python3
"""
图像生成示例

演示如何使用PuterAI代理服务器生成图像。
"""

import openai
import os
import base64
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

def main():
    # 配置OpenAI客户端
    client = openai.OpenAI(
        api_key=os.getenv("API_TOKEN", "your-puter-api-token"),
        base_url="http://localhost:9595/v1"
    )
    
    print("🖼️ PuterAI图像生成示例")
    print("=" * 40)
    
    try:
        # 示例1: 生成图像并返回URL
        print("🎨 生成图像 (URL格式)...")
        response = client.images.generate(
            prompt="一只在彩虹上跳舞的独角兽，卡通风格，色彩鲜艳",
            size="1024x1024",
            response_format="url"
        )
        
        print(f"✅ 图像生成成功!")
        print(f"图像URL: {response.data[0].url}")
        print()
        
        # 示例2: 生成图像并保存为文件
        print("💾 生成图像并保存为文件...")
        response = client.images.generate(
            prompt="一个现代化的城市天际线，夜景，霓虹灯闪烁",
            size="1024x1024",
            response_format="b64_json"
        )
        
        # 解码base64并保存
        image_data = base64.b64decode(response.data[0].b64_json)
        filename = "generated_image.png"
        
        with open(filename, "wb") as f:
            f.write(image_data)
        
        print(f"✅ 图像已保存为: {filename}")
        print()
        
        # 示例3: 批量生成图像
        print("🔄 批量生成图像...")
        response = client.images.generate(
            prompt="可爱的小动物，不同种类，卡通风格",
            n=2,  # 生成2张图像
            size="512x512",
            response_format="url"
        )
        
        print(f"✅ 批量生成完成，共 {len(response.data)} 张图像:")
        for i, image in enumerate(response.data, 1):
            print(f"  图像 {i}: {image.url}")
            
    except Exception as e:
        print(f"❌ 错误: {e}")
        print("请确保:")
        print("1. 代理服务器正在运行 (python API/openai_server.py)")
        print("2. 已设置正确的API_TOKEN环境变量")

if __name__ == "__main__":
    main()
