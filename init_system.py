#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
系统初始化脚本

初始化代理池和Token池，确保系统有足够的资源运行
"""

import os
import sys
import asyncio
import logging
from datetime import datetime

# 添加项目根目录到路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'logs/init_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def init_proxy_pool():
    """初始化代理池"""
    try:
        from utils import get_proxy_manager
        
        logger.info("🌐 开始初始化代理池...")
        proxy_manager = get_proxy_manager()
        
        # 检查现有代理数量
        stats = proxy_manager.get_proxy_stats()
        logger.info(f"📊 代理池状态: {stats}")
        
        # 如果代理不足，获取更多
        if stats['verified_proxies'] < 5:
            logger.info("代理数量不足，开始获取新代理...")
            proxy_manager.refresh_proxy_pool(pages=3)
            proxy_manager.verify_all_proxies()
            
            # 更新统计
            stats = proxy_manager.get_proxy_stats()
            logger.info(f"📊 代理池更新后状态: {stats}")
        
        logger.info("✅ 代理池初始化完成")
        return True
        
    except Exception as e:
        logger.error(f"❌ 代理池初始化失败: {e}")
        return False


def init_token_pool():
    """初始化Token池"""
    try:
        from utils import get_token_manager
        
        logger.info("🔑 开始初始化Token池...")
        token_manager = get_token_manager()
        
        # 检查现有Token数量
        stats = token_manager.get_token_stats()
        logger.info(f"📊 Token池状态: {stats}")
        
        # 验证现有Token
        if stats['total_tokens'] > 0:
            logger.info("验证现有Token...")
            token_manager.verify_all_tokens()
            
            # 更新统计
            stats = token_manager.get_token_stats()
            logger.info(f"📊 Token池验证后状态: {stats}")
        
        logger.info("✅ Token池初始化完成")
        return True
        
    except Exception as e:
        logger.error(f"❌ Token池初始化失败: {e}")
        return False


async def register_initial_tokens(count: int = 3):
    """注册初始Token"""
    try:
        logger.info(f"🚀 开始注册 {count} 个初始Token...")
        
        # 导入增强版注册功能
        from register_enhanced import register_multiple_tokens
        
        success_count = await register_multiple_tokens(count)
        
        if success_count > 0:
            logger.info(f"✅ 成功注册了 {success_count} 个Token")
            return True
        else:
            logger.warning("❌ 没有成功注册任何Token")
            return False
            
    except Exception as e:
        logger.error(f"❌ Token注册失败: {e}")
        return False


def ensure_directories():
    """确保必要的目录存在"""
    directories = ['logs', 'data']
    
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory)
            logger.info(f"创建目录: {directory}")


def check_dependencies():
    """检查依赖包"""
    required_packages = [
        'playwright',
        'requests',
        'flask',
        'flask_cors', # flask-cors
        'dotenv'  # python-dotenv
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        logger.warning(f"缺少依赖包: {missing_packages}")
        logger.info("请运行: pip install -r requirements.txt")
        return False
    
    logger.info("✅ 所有依赖包已安装")
    return True


async def main():
    """主函数"""
    logger.info("🚀 开始系统初始化...")
    logger.info("=" * 50)
    
    # 确保目录存在
    ensure_directories()
    
    # 检查依赖
    if not check_dependencies():
        logger.error("❌ 依赖检查失败")
        logger.info("请运行: pip install -r requirements.txt")
        logger.info("然后安装Playwright浏览器: playwright install chromium") 
        return False
    
    # 初始化代理池
    proxy_success = init_proxy_pool()
    
    # 初始化Token池
    token_success = init_token_pool()
    
    # 如果Token不足，尝试注册新的
    if token_success:
        from utils import get_token_manager
        token_manager = get_token_manager()
        stats = token_manager.get_token_stats()
        
        if stats['active_tokens'] < 2:
            logger.info("活跃Token不足，开始注册新Token...")
            if proxy_success:
                await register_initial_tokens(3)
            else:
                logger.warning("代理池初始化失败，跳过Token注册")
    
    # 显示最终状态
    logger.info("=" * 50)
    logger.info("🏁 系统初始化完成")
    
    try:
        from utils import get_proxy_manager, get_token_manager
        
        proxy_stats = get_proxy_manager().get_proxy_stats()
        token_stats = get_token_manager().get_token_stats()
        
        logger.info(f"📊 最终状态:")
        logger.info(f"   代理池: {proxy_stats['verified_proxies']}/{proxy_stats['total_proxies']} 个可用")
        logger.info(f"   Token池: {token_stats['active_tokens']}/{token_stats['total_tokens']} 个可用")
        
        if proxy_stats['verified_proxies'] > 0 and token_stats['active_tokens'] > 0:
            logger.info("✅ 系统准备就绪")
            return True
        else:
            logger.warning("⚠️ 系统资源不足，可能影响正常运行")
            return False
            
    except Exception as e:
        logger.error(f"❌ 获取最终状态失败: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
