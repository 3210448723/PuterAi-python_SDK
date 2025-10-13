#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PuterAI 管理工具

提供系统管理功能的统一入口
"""

import sys
import os
import argparse
import asyncio

# 添加项目路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)


def init_system():
    """初始化系统"""
    print("🚀 正在初始化系统...")
    try:
        from init_system import main
        return asyncio.run(main())
    except Exception as e:
        print(f"❌ 初始化失败: {e}")
        return False


def check_status():
    """检查系统状态"""
    print("🔍 检查系统状态...")
    try:
        from utils.status_checker import main
        return main()
    except Exception as e:
        print(f"❌ 状态检查失败: {e}")
        return False


def register_tokens(count=3):
    """注册Token"""
    print(f"🔑 正在注册 {count} 个Token...")
    try:
        from register_enhanced import register_multiple_tokens
        success_count = asyncio.run(register_multiple_tokens(count))
        if success_count > 0:
            print(f"✅ 成功注册了 {success_count} 个Token")
            return True
        else:
            print("❌ 没有成功注册任何Token")
            return False
    except Exception as e:
        print(f"❌ Token注册失败: {e}")
        return False


def verify_tokens():
    """验证所有Token"""
    print("🔍 验证所有Token...")
    try:
        from utils import get_token_manager
        token_manager = get_token_manager()
        token_manager.verify_all_tokens()
        
        stats = token_manager.get_token_stats()
        print(f"📊 验证结果: {stats['active_tokens']}/{stats['total_tokens']} 个Token可用")
        return stats['active_tokens'] > 0
    except Exception as e:
        print(f"❌ Token验证失败: {e}")
        return False


def verify_proxies():
    """验证所有代理"""
    print("🌐 验证所有代理...")
    try:
        from utils import get_proxy_manager
        proxy_manager = get_proxy_manager()
        proxy_manager.verify_all_proxies()
        
        stats = proxy_manager.get_proxy_stats()
        print(f"📊 验证结果: {stats['verified_proxies']}/{stats['total_proxies']} 个代理可用")
        return stats['verified_proxies'] > 0
    except Exception as e:
        print(f"❌ 代理验证失败: {e}")
        return False


def refresh_proxies():
    """刷新代理池"""
    print("🔄 刷新代理池...")
    try:
        from utils import get_proxy_manager
        proxy_manager = get_proxy_manager()
        proxy_manager.refresh_proxy_pool(pages=3)
        
        stats = proxy_manager.get_proxy_stats()
        print(f"📊 刷新结果: 获得 {stats['total_proxies']} 个代理")
        return True
    except Exception as e:
        print(f"❌ 代理刷新失败: {e}")
        return False


def start_server():
    """启动服务器"""
    print("🎯 启动PuterAI代理服务器...")
    try:
        os.chdir(os.path.join(current_dir, 'API'))
        os.system('python openai_server.py')
    except Exception as e:
        print(f"❌ 服务器启动失败: {e}")
        return False


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='PuterAI 管理工具')
    parser.add_argument('command', choices=[
        'init', 'status', 'register', 'verify-tokens', 
        'verify-proxies', 'refresh-proxies', 'start'
    ], help='要执行的命令')
    parser.add_argument('--count', type=int, default=3, help='注册Token的数量')
    
    args = parser.parse_args()
    
    print("🔧 PuterAI 管理工具")
    print("=" * 30)
    
    success = False
    
    if args.command == 'init':
        success = init_system()
    elif args.command == 'status':
        success = check_status()
    elif args.command == 'register':
        success = register_tokens(args.count)
    elif args.command == 'verify-tokens':
        success = verify_tokens()
    elif args.command == 'verify-proxies':
        success = verify_proxies()
    elif args.command == 'refresh-proxies':
        success = refresh_proxies()
    elif args.command == 'start':
        success = start_server()
    
    if success:
        print("✅ 操作完成")
    else:
        print("❌ 操作失败")
    
    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
