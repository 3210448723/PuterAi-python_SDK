#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
代理IP管理器

负责获取、验证、管理代理IP池，并在注册时提供可用的代理IP
"""

import json
import os
import time
import threading
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime

# 导入同目录下的模块
from .check_proxy_ip import check_proxy_ip
from .MultiThreadTestProxyIP import main as get_proxy_ips


class ProxyManager:
    """代理IP管理器"""
    
    def __init__(self, proxy_file: Optional[str] = None, max_proxies: Optional[int] = None):
        """
        初始化代理管理器
        
        Args:
            proxy_file: 代理池存储文件（可选，默认从配置读取）
            max_proxies: 最大代理数量（可选，默认从配置读取）
        """
        # 延迟导入避免循环依赖
        from .config_manager import get_config_manager
        
        # 获取配置
        config = get_config_manager()
        proxy_config = config.get_proxy_config()
        
        self.proxy_file = proxy_file or proxy_config['pool_file']
        self.max_proxies = max_proxies or proxy_config['max_proxies']
        self.proxy_pool: Dict[str, Dict] = {}
        self.lock = threading.Lock()
        self.logger = logging.getLogger(__name__)
        
        # 加载现有代理池
        self.load_proxy_pool()
    
    def load_proxy_pool(self) -> None:
        """从文件加载代理池"""
        try:
            if os.path.exists(self.proxy_file):
                with open(self.proxy_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.proxy_pool = data.get('proxies', {})
                    self.logger.info(f"已加载 {len(self.proxy_pool)} 个代理IP")
            else:
                self.logger.info("代理池文件不存在，将创建新的代理池")
                # 确保目录存在
                os.makedirs(os.path.dirname(self.proxy_file), exist_ok=True)
        except Exception as e:
            self.logger.error(f"加载代理池失败: {e}")
            self.proxy_pool = {}
    
    def save_proxy_pool(self) -> None:
        """保存代理池到文件"""
        try:
            # 注意：这里不使用 self.lock，因为调用者已经持有锁
            data = {
                'proxies': self.proxy_pool,
                'last_updated': datetime.now().isoformat(),
                'total_count': len(self.proxy_pool)
            }
            with open(self.proxy_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            self.logger.info(f"已保存 {len(self.proxy_pool)} 个代理IP到文件")
        except Exception as e:
            self.logger.error(f"保存代理池失败: {e}")
    
    def add_proxy(self, ip: str, port: str, verified: bool = False) -> None:
        """
        添加代理IP到池中
        
        Args:
            ip: 代理IP地址
            port: 代理端口
            verified: 是否已验证
        """
        with self.lock:
            proxy_key = f"{ip}:{port}"
            self.proxy_pool[proxy_key] = {
                'ip': ip,
                'port': int(port),
                'verified': verified,
                'added_time': datetime.now().isoformat(),
                'last_used': None,
                'success_count': 0,
                'fail_count': 0
            }
            self.logger.info(f"添加代理: {proxy_key}")
    
    def remove_proxy(self, ip: str, port: Optional[str] = None) -> None:
        """
        移除无效的代理IP
        
        Args:
            ip: 代理IP地址，可以是完整的ip:port格式
            port: 代理端口（可选）
        """
        with self.lock:
            # 如果ip包含端口信息
            if ':' in ip and port is None:
                proxy_key = ip
            else:
                proxy_key = f"{ip}:{port}"
            
            if proxy_key in self.proxy_pool:
                del self.proxy_pool[proxy_key]
                self.logger.warning(f"移除无效代理: {proxy_key}")
                self.save_proxy_pool()
    
    def mark_proxy_used(self, ip: str, port: str, success: bool = True) -> None:
        """
        标记代理使用情况
        
        Args:
            ip: 代理IP地址
            port: 代理端口
            success: 是否使用成功
        """
        with self.lock:
            proxy_key = f"{ip}:{port}"
            if proxy_key in self.proxy_pool:
                proxy = self.proxy_pool[proxy_key]
                proxy['last_used'] = datetime.now().isoformat()
                if success:
                    proxy['success_count'] += 1
                else:
                    proxy['fail_count'] += 1
                    # 如果失败次数太多，移除该代理
                    if proxy['fail_count'] >= 3:
                        self.logger.warning(f"代理 {proxy_key} 失败次数过多，将被移除")
                        del self.proxy_pool[proxy_key]
                
                self.save_proxy_pool()
    
    def verify_proxy(self, ip: str, port: str) -> bool:
        """
        验证单个代理IP是否可用
        
        Args:
            ip: 代理IP地址
            port: 代理端口
            
        Returns:
            bool: 代理是否可用
        """
        try:
            return check_proxy_ip(ip, int(port))
        except Exception as e:
            self.logger.error(f"验证代理 {ip}:{port} 失败: {e}")
            return False
    
    def verify_all_proxies(self) -> None:
        """验证所有代理IP"""
        self.logger.info("开始验证所有代理IP...")
        invalid_proxies = []
        
        for proxy_key, proxy_data in self.proxy_pool.items():
            ip = proxy_data['ip']
            port = proxy_data['port']
            
            if self.verify_proxy(ip, str(port)):
                proxy_data['verified'] = True
                proxy_data['last_verified'] = datetime.now().isoformat()
                self.logger.info(f"代理 {proxy_key} 验证成功")
            else:
                invalid_proxies.append(proxy_key)
                self.logger.warning(f"代理 {proxy_key} 验证失败")
        
        # 移除无效代理
        for proxy_key in invalid_proxies:
            del self.proxy_pool[proxy_key]
        
        self.save_proxy_pool()
        self.logger.info(f"代理验证完成，移除了 {len(invalid_proxies)} 个无效代理")
    
    def get_available_proxy(self) -> Optional[Tuple[str, int]]:
        """
        获取一个可用的代理IP
        
        Returns:
            tuple: (ip, port) 或 None
        """
        with self.lock:
            # 优先选择已验证且使用较少的代理
            available_proxies = [
                (key, data) for key, data in self.proxy_pool.items()
                if data.get('verified', False)
            ]
            
            if not available_proxies:
                # 如果没有已验证的代理，尝试使用未验证的
                available_proxies = list(self.proxy_pool.items())
            
            if not available_proxies:
                return None
            
            # 按使用次数排序，选择使用较少的
            available_proxies.sort(key=lambda x: x[1].get('success_count', 0))
            
            proxy_key, proxy_data = available_proxies[0]
            return proxy_data['ip'], proxy_data['port']
    
    def get_all_available_proxies(self) -> List[Tuple[str, int]]:
        """
        获取所有可用的代理IP
        
        Returns:
            list: [(ip, port), ...] 代理列表
        """
        with self.lock:
            proxies = []
            for proxy_data in self.proxy_pool.values():
                if proxy_data.get('verified', False):
                    proxies.append((proxy_data['ip'], proxy_data['port']))
            return proxies
    
    def refresh_proxy_pool(self, pages: int = 3) -> None:
        """
        刷新代理池，获取新的代理IP
        
        Args:
            pages: 要抓取的页数
        """
        self.logger.info(f"开始刷新代理池，抓取 {pages} 页...")
        
        try:
            # 使用现有的多线程代理获取功能
            page = 1
            new_proxies_count = 0
            
            while page <= pages and len(self.proxy_pool) < self.max_proxies:
                self.logger.info(f"正在获取第 {page} 页代理...")
                
                # 调用现有的代理获取函数
                ip_port_dict = get_proxy_ips(page)
                
                # 添加新代理到池中
                for ip, port in ip_port_dict.items():
                    if len(self.proxy_pool) >= self.max_proxies:
                        break
                    
                    proxy_key = f"{ip}:{port}"
                    if proxy_key not in self.proxy_pool:
                        self.add_proxy(ip, port, verified=True)  # 假设获取到的都是已验证的
                        new_proxies_count += 1
                
                page += 1
                time.sleep(1)  # 避免请求过于频繁
            
            self.save_proxy_pool()
            self.logger.info(f"代理池刷新完成，新增 {new_proxies_count} 个代理")
            
        except Exception as e:
            self.logger.error(f"刷新代理池失败: {e}")
    
    def ensure_proxy_available(self, min_count: int = 3) -> bool:
        """
        确保有足够的可用代理
        
        Args:
            min_count: 最少需要的代理数量
            
        Returns:
            bool: 是否有足够的代理
        """
        available_count = len([
            p for p in self.proxy_pool.values() 
            if p.get('verified', False)
        ])
        
        if available_count < min_count:
            self.logger.warning(f"可用代理不足 ({available_count}/{min_count})，开始刷新代理池...")
            self.refresh_proxy_pool()
            
            # 验证新获取的代理
            self.verify_all_proxies()
            
            available_count = len([
                p for p in self.proxy_pool.values() 
                if p.get('verified', False)
            ])
        
        return available_count >= min_count
    
    def get_proxy_stats(self) -> Dict:
        """
        获取代理池统计信息
        
        Returns:
            dict: 统计信息
        """
        with self.lock:
            total = len(self.proxy_pool)
            verified = len([p for p in self.proxy_pool.values() if p.get('verified', False)])
            
            return {
                'total_proxies': total,
                'verified_proxies': verified,
                'unverified_proxies': total - verified,
                'proxy_file': self.proxy_file,
                'last_updated': datetime.now().isoformat()
            }


# 全局代理管理器实例
_proxy_manager = None


def get_proxy_manager() -> ProxyManager:
    """获取全局代理管理器实例"""
    global _proxy_manager
    if _proxy_manager is None:
        _proxy_manager = ProxyManager()
    return _proxy_manager


if __name__ == "__main__":
    # 测试代理管理器
    import logging
    logging.basicConfig(level=logging.INFO)
    
    manager = ProxyManager()
    
    # 确保有足够的代理
    if manager.ensure_proxy_available(3):
        print("✅ 代理池准备就绪")
        
        # 显示统计信息
        stats = manager.get_proxy_stats()
        print(f"📊 代理统计: {stats}")
        
        # 获取一个可用代理
        proxy = manager.get_available_proxy()
        if proxy:
            print(f"🌐 可用代理: {proxy[0]}:{proxy[1]}")
        else:
            print("❌ 没有可用代理")
    else:
        print("❌ 无法获取足够的代理IP")
