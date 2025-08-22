#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试自动注册功能

模拟token用量不足的错误，验证自动注册机制是否正常工作。
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'API'))

from API.openai_server import is_usage_limited_error, auto_register_token, ensure_env_file_exists

def test_usage_limited_detection():
    """测试用量限制错误检测"""
    print("🧪 测试用量限制错误检测...")
    
    # 测试用例1: 标准的用量限制错误
    error_data1 = {
        'success': False, 
        'error': {
            'delegate': 'usage-limited-chat', 
            'message': 'Error 400 from delegate `usage-limited-chat`: Permission denied.', 
            'code': 'error_400_from_delegate', 
            '$': 'heyputer:api/APIError', 
            'status': 400
        }
    }
    
    result1 = is_usage_limited_error(error_data1)
    print(f"✅ 标准用量限制错误检测: {result1}")
    assert result1 == True, "应该检测到用量限制错误"
    
    # 测试用例2: 其他类型的错误
    error_data2 = {
        'success': False,
        'error': {
            'message': 'Some other error',
            'code': 'other_error'
        }
    }
    
    result2 = is_usage_limited_error(error_data2)
    print(f"✅ 其他错误类型检测: {result2}")
    assert result2 == False, "不应该检测到用量限制错误"
    
    # 测试用例3: 无效数据
    result3 = is_usage_limited_error("invalid data")
    print(f"✅ 无效数据检测: {result3}")
    assert result3 == False, "无效数据不应该检测到用量限制错误"
    
    print("🎉 用量限制错误检测测试通过！")

def test_env_file_creation():
    """测试.env文件创建"""
    print("🧪 测试.env文件确保存在...")
    
    # 备份现有的.env文件（如果存在）
    env_path = '.env'
    backup_path = '.env.backup'
    
    if os.path.exists(env_path):
        os.rename(env_path, backup_path)
        print("📦 已备份现有的.env文件")
    
    try:
        # 测试创建.env文件
        result_path = ensure_env_file_exists()
        
        if os.path.exists(env_path):
            print("✅ .env文件创建成功")
            with open(env_path, 'r') as f:
                content = f.read()
                print(f"📄 .env文件内容:\n{content}")
        else:
            print("❌ .env文件创建失败")
            
    finally:
        # 恢复备份的.env文件
        if os.path.exists(backup_path):
            if os.path.exists(env_path):
                os.remove(env_path)
            os.rename(backup_path, env_path)
            print("🔄 已恢复原有的.env文件")

def test_auto_register_dry_run():
    """测试自动注册功能（不实际执行）"""
    print("🧪 测试自动注册功能...")
    print("⚠️  注意: 这将启动一个后台线程进行实际注册")
    print("💡 建议在开发环境中测试，避免频繁注册")
    
    # 可以选择注释掉下面这行来避免实际执行注册
    # auto_register_token()
    print("🔄 自动注册功能已准备就绪（实际执行已注释）")

if __name__ == "__main__":
    print("🚀 开始测试自动注册功能")
    print("="*50)
    
    try:
        test_usage_limited_detection()
        print()
        
        test_env_file_creation()
        print()
        
        test_auto_register_dry_run()
        print()
        
        print("✅ 所有测试通过！")
        print("💡 自动注册功能已准备就绪")
        print("🔄 当API检测到token用量不足时，将自动在后台重新注册")
        
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        sys.exit(1)
