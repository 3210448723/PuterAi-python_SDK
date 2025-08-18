#!/usr/bin/env python3
"""
文本转语音示例

演示如何使用PuterAI代理服务器将文本转换为语音。
"""

import openai
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

def main():
    # 配置OpenAI客户端
    client = openai.OpenAI(
        api_key=os.getenv("API_TOKEN", "your-puter-api-token"),
        base_url="http://localhost:9595/v1"
    )
    
    print("🔊 PuterAI文本转语音示例")
    print("=" * 40)
    
    try:
        # 示例1: 基础TTS
        print("🎤 生成语音文件...")
        response = client.audio.speech.create(
            model="tts-1",
            voice="alloy",
            input="Hello world! 这是一个测试。PuterAI文本转语音功能正常工作。"
        )
        
        # 保存音频文件
        filename = "speech_basic.mp3"
        with open(filename, "wb") as f:
            f.write(response.content)
        
        print(f"✅ 语音文件已保存为: {filename}")
        print()
        
        # 示例2: 不同声音示例
        voices = ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]
        text = "欢迎使用PuterAI语音合成服务！"
        
        print("🎭 不同声音效果演示...")
        for voice in voices[:3]:  # 只演示3个声音以节省时间
            print(f"  正在生成 {voice} 声音...")
            response = client.audio.speech.create(
                model="tts-1",
                voice=voice,
                input=text
            )
            
            filename = f"speech_{voice}.mp3"
            with open(filename, "wb") as f:
                f.write(response.content)
            print(f"  ✅ 已保存: {filename}")
        
        print()
        
        # 示例3: 高质量模型和语速控制
        print("🚀 高质量模型和语速控制...")
        response = client.audio.speech.create(
            model="tts-1-hd",  # 高质量模型
            voice="nova",
            input="这是使用高质量TTS模型生成的语音，音质更加清晰自然。",
            speed=1.2  # 稍快的语速
        )
        
        filename = "speech_hd.mp3"
        with open(filename, "wb") as f:
            f.write(response.content)
        
        print(f"✅ 高质量语音文件已保存为: {filename}")
        
        # 示例4: 不同音频格式
        print("\n🎵 不同音频格式示例...")
        formats = ["mp3", "opus", "aac", "flac"]
        
        for fmt in formats[:2]:  # 演示2种格式
            print(f"  生成 {fmt.upper()} 格式...")
            response = client.audio.speech.create(
                model="tts-1",
                voice="alloy",
                input=f"这是{fmt.upper()}格式的音频文件。",
                response_format=fmt
            )
            
            filename = f"speech_format.{fmt}"
            with open(filename, "wb") as f:
                f.write(response.content)
            print(f"  ✅ 已保存: {filename}")
            
    except Exception as e:
        print(f"❌ 错误: {e}")
        print("请确保:")
        print("1. 代理服务器正在运行 (python API/openai_server.py)")
        print("2. 已设置正确的API_TOKEN环境变量")

if __name__ == "__main__":
    main()
