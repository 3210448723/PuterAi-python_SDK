#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强版注册脚本

支持使用代理IP进行注册，管理多个Token
"""

import asyncio
import json
import os
import sys
import time
import logging
from typing import Optional, Tuple
from playwright.async_api import async_playwright

# 添加utils目录到路径
current_dir = os.path.dirname(os.path.abspath(__file__))
utils_dir = os.path.join(current_dir, 'utils')
sys.path.insert(0, utils_dir)

# 类型检查忽略，因为可能使用不同的实现
try:
    from utils import get_proxy_manager, get_token_manager  # type: ignore
    MANAGERS_AVAILABLE = True
except ImportError:
    # 如果无法导入，创建简单的替代实现
    print("警告：无法导入代理和Token管理器，使用简化版本")
    MANAGERS_AVAILABLE = False
    
    class DummyProxyManager:
        def ensure_proxy_available(self, count): return False
        def get_all_available_proxies(self): return []
        def get_available_proxy(self): return None
        def mark_proxy_used(self, ip, port, success): pass
        def remove_proxy(self, ip, port): pass
        def refresh_proxy_pool(self): pass
    
    class DummyTokenManager:
        def add_token(self, token, is_primary=False, proxy_info=None): pass
    
    def get_proxy_manager(): return DummyProxyManager()  # type: ignore
    def get_token_manager(): return DummyTokenManager()  # type: ignore


# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def get_signup_token_with_proxy(proxy_ip: Optional[str] = None, proxy_port: Optional[int] = None) -> Tuple[Optional[str], str]:
    """
    使用代理获取注册Token
    
    Args:
        proxy_ip: 代理IP地址
        proxy_port: 代理端口
        
    Returns:
        tuple: (token, status_message)
    """
    async with async_playwright() as p:
        # 配置浏览器启动参数
        launch_options = {
            'headless': True,
            'args': ['--no-sandbox', '--disable-setuid-sandbox']
        }
        
        # 统一代理覆盖: 按需求强制所有 puter.com 流量走本地 127.0.0.1:10809
        # 若需恢复原逻辑，可设置环境变量 DISABLE_PUTER_FIXED_PROXY=1
        force_fixed = os.getenv("DISABLE_PUTER_FIXED_PROXY", "0") not in {"1", "true", "True"}
        fixed_proxy = os.getenv("PUTER_PROXY", "http://127.0.0.1:10809")
        if force_fixed:
            launch_options['proxy'] = { 'server': fixed_proxy }
            logger.info(f"(统一) 使用固定代理: {fixed_proxy}")
        elif proxy_ip and proxy_port:
            launch_options['proxy'] = { 'server': f'http://{proxy_ip}:{proxy_port}' }
            logger.info(f"使用动态代理: {proxy_ip}:{proxy_port}")
        
        try:
            browser = await p.chromium.launch(**launch_options)
            
            # 创建新的浏览器上下文
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                viewport={'width': 1920, 'height': 1080},
                locale='en-US'
            )
            
            page = await context.new_page()
            token = None
            status_message = ""

            async def handle_response(response):
                nonlocal token, status_message
                
                if response.url == "https://puter.com/signup" and response.request.method == "POST":
                    logger.info(f"检测到 signup 响应，状态码: {response.status}")
                    
                    try:
                        # 获取响应文本
                        response_text = await response.text()
                        logger.debug(f"响应内容: {response_text[:500]}...")
                        
                        # 检查是否被限制注册
                        if "You are not allowed to sign up" in response_text:
                            token = None
                            status_message = "IP被限制注册"
                            logger.warning("IP被限制注册")
                            return
                        
                        # 检查状态码
                        if 200 <= response.status < 300:
                            response_data = await response.json()
                            token = response_data.get("token")
                            if token:
                                status_message = "注册成功"
                                logger.info(f"成功获取到 token: {token[:8]}...")
                            else:
                                status_message = "响应中没有token"
                                logger.warning("响应中没有token")
                        else:
                            status_message = f"注册失败，状态码: {response.status}"
                            logger.warning(status_message)
                            
                    except Exception as e:
                        status_message = f"处理响应失败: {e}"
                        logger.error(status_message)
                        
                elif "signup" in response.url:
                    logger.debug(f"其他 signup 相关请求: {response.url}, 状态码: {response.status}")

            page.on("response", handle_response)
            
            # 访问网站
            logger.info("正在访问 https://puter.com/...")
            await page.goto("https://puter.com/", wait_until="networkidle", timeout=120000)
            
            # 等待页面完全加载
            await asyncio.sleep(3)
            
            # 等待自动注册流程
            logger.info("等待自动注册流程...")
            await asyncio.sleep(10)
            
            await browser.close()
            
            return token, status_message
            
        except Exception as e:
            logger.error(f"注册过程中出错: {e}")
            return None, f"注册出错: {str(e)}"


async def register_multiple_tokens(target_count: int = 3) -> int:
    """
    注册多个Token
    
    Args:
        target_count: 目标Token数量
        
    Returns:
        int: 成功注册的Token数量
    """
    if not MANAGERS_AVAILABLE:
        logger.error("管理器不可用，无法注册Token")
        return 0
    
    proxy_manager = get_proxy_manager()
    token_manager = get_token_manager()
    
    # 确保有足够的代理
    if not proxy_manager.ensure_proxy_available(target_count):
        logger.error("没有足够的可用代理IP")
        return 0
    
    # 获取可用代理列表
    available_proxies = proxy_manager.get_all_available_proxies()
    if not available_proxies:
        logger.error("没有可用的代理IP")
        return 0
    
    logger.info(f"开始注册 {target_count} 个Token，可用代理: {len(available_proxies)}")
    
    success_count = 0
    proxy_index = 0
    
    for i in range(target_count):
        # 选择代理
        if proxy_index >= len(available_proxies):
            logger.warning("代理IP不足，尝试获取更多代理...")
            proxy_manager.refresh_proxy_pool()
            available_proxies = proxy_manager.get_all_available_proxies()
            proxy_index = 0
            
            if not available_proxies:
                logger.error("无法获取更多代理IP")
                break
        
        proxy_ip, proxy_port = available_proxies[proxy_index]
        proxy_index += 1
        
        logger.info(f"正在使用代理 {proxy_ip}:{proxy_port} 注册第 {i+1} 个Token...")
        
        try:
            # 使用代理注册
            token, status_message = await get_signup_token_with_proxy(proxy_ip, proxy_port)
            
            if token:
                # 添加Token到管理器
                proxy_info = {
                    'ip': proxy_ip,
                    'port': proxy_port,
                    'registered_time': time.time()
                }
                
                token_manager.add_token(
                    token, 
                    is_primary=(success_count == 0),  # 第一个Token设为主Token
                    proxy_info=proxy_info
                )
                
                # 标记代理使用成功
                proxy_manager.mark_proxy_used(proxy_ip, str(proxy_port), success=True)
                
                success_count += 1
                logger.info(f"✅ 第 {i+1} 个Token注册成功: {token[:8]}...")
                
            else:
                logger.warning(f"❌ 第 {i+1} 个Token注册失败: {status_message}")
                
                # 如果是IP被限制，移除该代理
                if "IP被限制" in status_message or "not allowed" in status_message:
                    proxy_manager.remove_proxy(proxy_ip, str(proxy_port))
                    logger.warning(f"移除被限制的代理: {proxy_ip}:{proxy_port}")
                else:
                    # 标记代理使用失败
                    proxy_manager.mark_proxy_used(proxy_ip, str(proxy_port), success=False)
            
            # 等待一段时间避免请求过于频繁
            await asyncio.sleep(5)
            
        except Exception as e:
            logger.error(f"注册第 {i+1} 个Token时出错: {e}")
            proxy_manager.mark_proxy_used(proxy_ip, str(proxy_port), success=False)
    
    logger.info(f"注册完成，成功: {success_count}/{target_count}")
    return success_count


async def register_single_token_with_best_proxy() -> Optional[str]:
    """
    使用最佳代理注册单个Token
    
    Returns:
        str: 成功注册的Token或None
    """
    if not MANAGERS_AVAILABLE:
        logger.error("管理器不可用，无法注册Token")
        return None
    
    proxy_manager = get_proxy_manager()
    token_manager = get_token_manager()
    
    # 获取最佳代理
    proxy = proxy_manager.get_available_proxy()
    if not proxy:
        logger.error("没有可用的代理IP")
        return None
    
    proxy_ip, proxy_port = proxy  # type: ignore
    logger.info(f"使用代理 {proxy_ip}:{proxy_port} 注册Token...")
    
    try:
        # 注册Token
        token, status_message = await get_signup_token_with_proxy(proxy_ip, proxy_port)
        
        if token:
            # 添加到Token管理器
            proxy_info = {
                'ip': proxy_ip,
                'port': proxy_port,
                'registered_time': time.time()
            }
            
            token_manager.add_token(token, is_primary=True, proxy_info=proxy_info)
            proxy_manager.mark_proxy_used(proxy_ip, str(proxy_port), success=True)
            
            logger.info(f"✅ Token注册成功: {token[:8]}...")
            return token
        else:
            logger.warning(f"❌ Token注册失败: {status_message}")
            
            # 如果是IP被限制，移除该代理
            if "IP被限制" in status_message or "not allowed" in status_message:
                proxy_manager.remove_proxy(proxy_ip, str(proxy_port))
            else:
                proxy_manager.mark_proxy_used(proxy_ip, str(proxy_port), success=False)
            
            return None
            
    except Exception as e:
        logger.error(f"注册Token时出错: {e}")
        proxy_manager.mark_proxy_used(proxy_ip, str(proxy_port), success=False)
        return None


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='增强版Token注册脚本')
    parser.add_argument('--count', type=int, default=1, help='要注册的Token数量')
    parser.add_argument('--multiple', action='store_true', help='注册多个Token')
    args = parser.parse_args()
    
    if args.multiple or args.count > 1:
        # 注册多个Token
        target_count = max(args.count, 3)
        success_count = asyncio.run(register_multiple_tokens(target_count))
        
        if success_count > 0:
            logger.info(f"🎉 成功注册了 {success_count} 个Token")
            sys.exit(0)
        else:
            logger.error("❌ 没有成功注册任何Token")
            sys.exit(1)
    else:
        # 注册单个Token（兼容原版本）
        token = asyncio.run(register_single_token_with_best_proxy())
        
        if token:
            logger.info(f"🎉 Token注册成功: {token}")
            sys.exit(0)
        else:
            logger.error("❌ Token注册失败")
            sys.exit(1)


if __name__ == "__main__":
    main()
