#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
系统状态检查工具

检查代理池、Token池和系统配置的状态
"""

import os
import sys
import logging
from datetime import datetime

# 添加项目根目录到路径
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from utils.proxy_manager import get_proxy_manager
from utils.token_manager import get_token_manager
from utils.config_manager import get_config_manager


def check_system_status():
    """检查系统状态"""
    print("🔍 系统状态检查")
    print("=" * 50)
    
    try:
        # 检查配置
        config = get_config_manager()
        print(f"📋 配置文件: {config.config_file}")
        
        # 检查代理池
        print("\n🌐 代理池状态:")
        proxy_manager = get_proxy_manager()
        proxy_stats = proxy_manager.get_proxy_stats()
        
        print(f"  总代理数: {proxy_stats['total_proxies']}")
        print(f"  可用代理: {proxy_stats['verified_proxies']}")
        print(f"  未验证代理: {proxy_stats['unverified_proxies']}")
        print(f"  存储文件: {proxy_stats['proxy_file']}")
        
        if proxy_stats['verified_proxies'] == 0:
            print("  ⚠️ 警告: 没有可用的代理IP")
        elif proxy_stats['verified_proxies'] < 3:
            print("  ⚠️ 警告: 可用代理数量较少")
        else:
            print("  ✅ 代理池状态良好")
        
        # 检查Token池
        print("\n🔑 Token池状态:")
        token_manager = get_token_manager()
        token_stats = token_manager.get_token_stats()
        
        print(f"  总Token数: {token_stats['total_tokens']}")
        print(f"  活跃Token: {token_stats['active_tokens']}")
        print(f"  耗尽Token: {token_stats['exhausted_tokens']}")
        print(f"  无效Token: {token_stats['invalid_tokens']}")
        print(f"  当前索引: {token_stats['current_index']}")
        print(f"  存储文件: {token_stats['token_file']}")
        
        if token_stats['active_tokens'] == 0:
            print("  ❌ 错误: 没有可用的Token")
        elif token_stats['active_tokens'] == 1:
            print("  ⚠️ 警告: 只有1个可用Token，建议增加备用Token")
        else:
            print("  ✅ Token池状态良好")
        
        # 检查当前Token
        current_token = token_manager.get_current_token()
        if current_token:
            print(f"  当前Token: {current_token[:8]}...")
        else:
            print("  ❌ 无法获取当前Token")
        
        # 整体状态评估
        print("\n📊 整体状态:")
        if proxy_stats['verified_proxies'] > 0 and token_stats['active_tokens'] > 0:
            print("  ✅ 系统运行正常，所有组件可用")
            return True
        elif token_stats['active_tokens'] > 0:
            print("  ⚠️ Token可用但代理不足，可能影响注册功能")
            return False
        elif proxy_stats['verified_proxies'] > 0:
            print("  ❌ 代理可用但没有Token，无法提供服务")
            return False
        else:
            print("  ❌ 系统资源不足，需要初始化")
            return False
            
    except Exception as e:
        print(f"❌ 状态检查失败: {e}")
        return False


def clean_invalid_resources():
    """清理无效资源"""
    print("\n🧹 清理无效资源...")
    
    try:
        # 清理无效Token
        token_manager = get_token_manager()
        token_manager.cleanup_invalid_tokens()
        print("✅ Token清理完成")
        
        print("✅ 资源清理完成")
        
    except Exception as e:
        print(f"❌ 清理失败: {e}")


def main():
    """主函数"""
    print(f"🕒 检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 检查系统状态
    status_ok = check_system_status()
    
    # 清理无效资源
    clean_invalid_resources()
    
    # 如果状态不正常，提供建议
    if not status_ok:
        print("\n💡 建议操作:")
        print("  1. 运行系统初始化: python init_system.py")
        print("  2. 手动注册Token: python register_enhanced.py --count 3")
        print("  3. 检查网络连接和代理设置")
    
    return status_ok


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
