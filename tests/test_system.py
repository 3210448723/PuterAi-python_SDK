#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
系统测试脚本

测试代理和Token管理功能是否正常工作
"""

import sys
import os

# 测试脚本使用测试模式，避免操作生产 token_pool.json
os.environ.setdefault('TEST_MODE', '1')

# 添加项目路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

def test_config_manager():
    """测试配置管理器"""
    print("🔧 测试配置管理器...")
    try:
        from utils import get_config_manager
        config = get_config_manager()
        
        proxy_config = config.get_proxy_config()
        token_config = config.get_token_config()
        
        print(f"  代理配置: {proxy_config}")
        print(f"  Token配置: {token_config}")
        print("  ✅ 配置管理器正常")
        return True
    except Exception as e:
        print(f"  ❌ 配置管理器错误: {e}")
        return False

def test_proxy_manager():
    """测试代理管理器"""
    print("🌐 测试代理管理器...")
    try:
        from utils import get_proxy_manager
        proxy_manager = get_proxy_manager()
        
        stats = proxy_manager.get_proxy_stats()
        print(f"  代理统计: {stats}")
        print("  ✅ 代理管理器正常")
        return True
    except Exception as e:
        print(f"  ❌ 代理管理器错误: {e}")
        return False

def test_token_manager():
    """测试Token管理器"""
    print("🔑 测试Token管理器...")
    try:
        from utils import get_token_manager
        token_manager = get_token_manager()
        
        stats = token_manager.get_token_stats()
        print(f"  Token统计: {stats}")
        print("  ✅ Token管理器正常")
        return True
    except Exception as e:
        print(f"  ❌ Token管理器错误: {e}")
        return False

def test_imports():
    """测试所有导入"""
    print("📦 测试模块导入...")
    try:
        # 测试utils包导入
        import utils
        from utils import get_config_manager, get_proxy_manager, get_token_manager
        
        print("  ✅ 所有模块导入正常")
        return True
    except Exception as e:
        print(f"  ❌ 模块导入错误: {e}")
        return False

def main():
    """主函数"""
    print("🧪 PuterAI 系统测试")
    print("=" * 30)
    
    tests = [
        test_imports,
        test_config_manager,
        test_proxy_manager,
        test_token_manager
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print(f"📊 测试结果: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 所有测试通过，系统可以正常使用")
        return True
    else:
        print("❌ 部分测试失败，请检查错误信息")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
