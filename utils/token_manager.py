#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Token管理器

负责管理多个API Token，包括验证、轮换、自动注册等功能
"""

import json
import os
import threading
import logging
import requests
from pathlib import Path
try:  # 引入统一代理
    from .proxy_config import get_puter_proxies  # type: ignore
    _PUTER_PROXIES = get_puter_proxies()
except Exception:
    _PUTER_PROXIES = None
from typing import Dict, Optional
from datetime import datetime
from dotenv import load_dotenv, set_key


class TokenManager:
    """Token管理器"""
    
    def __init__(self, token_file: Optional[str] = None, max_tokens: Optional[int] = None):
        """
        初始化Token管理器
        
        Args:
            token_file: Token池存储文件（可选，默认从配置读取）
            max_tokens: 最大Token数量（可选，默认从配置读取）
        """
        # 延迟导入避免循环依赖
        from .config_manager import get_config_manager
        
        # 获取配置
        config = get_config_manager()
        token_config = config.get_token_config()
        
        # 运行模式判定：测试模式 / 生产模式
        env_test_flag = os.getenv('TEST_MODE', '').lower() in ('1', 'true', 'yes')
        app_env = os.getenv('APP_ENV', '').lower()
        self.is_test_mode = env_test_flag or app_env in ('test', 'testing', 'ci')

        base_pool_file = token_file or token_config['pool_file']
        try:
            base_path = Path(base_pool_file)
            if self.is_test_mode:
                # 在测试模式下使用单独文件： token_pool.test.json （与原文件同目录）
                if base_path.name.endswith('.json'):
                    test_name = base_path.stem + '.test.json'
                else:
                    test_name = base_path.name + '.test'
                self.token_file = str(base_path.with_name(test_name))
            else:
                self.token_file = str(base_path)
        except Exception:
            # 回退原逻辑
            self.token_file = base_pool_file
        self.max_tokens = max_tokens or token_config['max_tokens']
        self.token_pool: Dict[str, Dict] = {}
        self.current_token_index = 0
        self.lock = threading.Lock()
        self.logger = logging.getLogger(__name__)
        
        # 加载现有Token池
        self.load_token_pool()
        
        # 如果没有Token，尝试从环境变量加载
        if not self.token_pool:
            self.load_from_env()

        # 启动时清理可疑 / 占位 token（防止被错误加入池导致循环轮换）
        self._purge_suspect_tokens()

    # ---------------- 内部通用辅助 -----------------
    def _mode_tag(self) -> str:
        return 'TEST' if getattr(self, 'is_test_mode', False) else 'PROD'

    def _valid_tokens_locked(self):
        """在已持有 self.lock 的情况下返回当前有效 token 列表 (实际token字符串)。"""
        return [
            self.token_pool[token_id]['token'] for token_id, data in self.token_pool.items()
            if data.get('is_valid', True) and data.get('status') == 'active'
        ]

    # ---------------- 辅助: 可疑token判定 -----------------
    @staticmethod
    def _is_suspect(token: str) -> bool:
        if not token:
            return True
        low = token.lower()
        if len(token) < 20:
            return True
        patterns = ["test", "none", "placeholder", "your-put", "your_put", "your-puter", "demo", "example", "empty"]
        return any(p in low for p in patterns)

    def _purge_suspect_tokens(self):
        removed = []
        with self.lock:
            for tk in list(self.token_pool.keys()):
                if self._is_suspect(self.token_pool[tk]['token']):
                    removed.append(tk[:8])
                    del self.token_pool[tk]
            if removed:
                self.logger.warning(f"启动清理可疑Token: {removed}")
                self.current_token_index = 0
                self.save_token_pool()
    
    def load_token_pool(self) -> None:
        """从文件加载Token池"""
        try:
            if os.path.exists(self.token_file):
                with open(self.token_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.token_pool = data.get('tokens', {})
                    self.current_token_index = data.get('current_index', 0)
                self.logger.info(f"[{self._mode_tag()}] 已加载 {len(self.token_pool)} 个Token (文件: {self.token_file})")
            else:
                self.logger.info("Token池文件不存在，将创建新的Token池")
                # 确保目录存在
                os.makedirs(os.path.dirname(self.token_file), exist_ok=True)
        except Exception as e:
            self.logger.error(f"加载Token池失败: {e}")
            self.token_pool = {}
    
    def save_token_pool(self) -> None:
        """保存Token池到文件"""
        try:
            # 注意：这里不使用 self.lock，因为调用者已经持有锁
            data = {
                'tokens': self.token_pool,
                'current_index': self.current_token_index,
                'last_updated': datetime.now().isoformat(),
                'total_count': len(self.token_pool)
            }
            with open(self.token_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            self.logger.info(f"已保存 {len(self.token_pool)} 个Token到文件")
        except Exception as e:
            self.logger.error(f"保存Token池失败: {e}")
    
    def load_from_env(self) -> None:
        """从环境变量加载主Token"""
        load_dotenv()
        main_token = os.getenv('API_TOKEN')
        if main_token and not self._is_suspect(main_token):
            self.add_token(main_token, is_primary=True)
            self.logger.info(f"[{self._mode_tag()}] 从环境变量加载了主Token")
        elif main_token:
            self.logger.warning("环境变量API_TOKEN看似为占位/测试，已忽略")
    
    def add_token(self, token: str, is_primary: bool = False, proxy_info: Optional[Dict] = None) -> None:
        """
        添加Token到池中
        
        Args:
            token: API Token名称，不一定等于实际使用的Token，self.token_pool[token]['token']才是实际值
            is_primary: 是否为主Token
            proxy_info: 获取此Token时使用的代理信息
        """
        # 生产模式/通用阻止可疑 token
        if self._is_suspect(token) and not self.is_test_mode:
            self.logger.warning("拒绝添加可疑/占位Token (已忽略)")
            return

        with self.lock:
            # 避免重复添加（使用内部存储的完整token键值比对）
            if token in self.token_pool:
                self.logger.warning(f"Token已存在: {token[:8]}...")
                return
            
            self.token_pool[token] = {
                'token': token,  # 实际使用的Token
                'is_primary': is_primary,
                'added_time': datetime.now().isoformat(),
                'last_used': None,
                'last_verified': None,
                'usage_count': 0,
                'is_valid': True,
                'error_count': 0,
                'proxy_info': proxy_info or {},
                'status': 'active'  # active, exhausted, invalid
            }
            
            self.logger.info(f"[{self._mode_tag()}] 添加Token: {token[:8]}... (主Token: {is_primary})")
            
            # 如果是主Token，更新.env文件
            if is_primary:
                self.update_env_token(token)
            
            self.save_token_pool()
    
    def remove_token(self, token: str) -> None:
        """
        移除无效Token
        
        Args:
            token: 要移除的Token
        """
        with self.lock:
            if token in self.token_pool:
                del self.token_pool[token]
                self.logger.warning(f"移除无效Token: {token[:8]}...")
                self.save_token_pool()
        
        # 在锁外切换到下一个Token，避免死锁
        self.switch_to_next_token()
    
    def mark_token_invalid(self, token: str, error_info: Optional[str] = None) -> None:
        """
        标记Token为无效
        
        Args:
            token: Token
            error_info: 错误信息
        """
        with self.lock:
            if token in self.token_pool:
                token_data = self.token_pool[token]
                token_data['is_valid'] = False
                token_data['status'] = 'invalid'
                token_data['error_count'] += 1
                token_data['last_error'] = {
                    'time': datetime.now().isoformat(),
                    'info': error_info
                }
                
                self.logger.warning(f"标记Token无效: {token[:8]}... - {error_info}")
                self.save_token_pool()
        
        # 在锁外切换到下一个有效Token，避免死锁
    
    def mark_token_exhausted(self, token: str) -> None:
        """
        标记Token用量耗尽
        
        Args:
            token: Token
        """
        with self.lock:
            if token in self.token_pool:
                token_data = self.token_pool[token]
                token_data['status'] = 'exhausted'
                token_data['exhausted_time'] = datetime.now().isoformat()
                
                self.logger.warning(f"标记Token用量耗尽: {token[:8]}...")
                self.save_token_pool()
    
    def mark_token_used(self, token: str, success: bool = True) -> None:
        """
        标记Token使用情况
        
        Args:
            token: Token
            success: 是否使用成功
        """
        should_mark_invalid = False
        
        with self.lock:
            if token in self.token_pool:
                token_data = self.token_pool[token]
                token_data['last_used'] = datetime.now().isoformat()
                token_data['usage_count'] += 1
                
                if not success:
                    token_data['error_count'] += 1
                    # 如果错误次数过多，标记为需要失效
                    if token_data['error_count'] >= 5:
                        should_mark_invalid = True
                
                self.save_token_pool()
        
        # 在锁外处理Token失效，避免死锁
        if should_mark_invalid:
            self.mark_token_invalid(token, "连续错误次数过多")
    
    def get_current_token(self) -> Optional[str]:
        """
        获取当前可用的Token
        
        Returns:
            str: 当前Token或None
        """
        current_token = None
        
        with self.lock:
            valid_tokens = self._valid_tokens_locked()
            self.logger.debug(f"当前有效Token序列({len(valid_tokens)}): {[t[:8] for t in valid_tokens]} index={self.current_token_index}")
            
            if not valid_tokens:
                self.logger.warning("没有可用的Token")
                return None
            
            # 如果当前索引超出范围，重置为0
            if self.current_token_index >= len(valid_tokens):
                self.current_token_index = 0
            
            current_token = valid_tokens[self.current_token_index]
        
        # 在锁外更新使用信息，避免死锁
        if current_token:
            self.mark_token_used(current_token, True)
        
        return current_token
    
    def switch_to_next_token(self) -> Optional[str]:
        """
        切换到下一个可用Token
        
        Returns:
            str: 下一个Token或None
        """
        with self.lock:
            valid_tokens = self._valid_tokens_locked()
            if not valid_tokens:
                self.logger.warning("switch_to_next_token: 无有效Token可切换")
                return None
            prev_index = self.current_token_index
            self.current_token_index = (self.current_token_index + 1) % len(valid_tokens)
            next_token = valid_tokens[self.current_token_index]
            self.logger.info(f"切换到Token: {next_token[:8]}... (prev_index={prev_index} -> new_index={self.current_token_index})")
            self.logger.debug(f"切换后有效Token序列: {[t[:8] for t in valid_tokens]}")
        # 锁外更新 .env
        self.update_env_token(next_token)
        return next_token
    
    def update_env_token(self, token: str) -> None:
        """
        更新.env文件中的主Token
        
        Args:
            token: 要设置的Token
        """
        try:
            env_file = '.env'
            
            # 确保.env文件存在
            if not os.path.exists(env_file):
                with open(env_file, 'w') as f:
                    f.write('')
            
            # 更新API_TOKEN
            set_key(env_file, 'API_TOKEN', token)
            
            # 重新加载环境变量
            load_dotenv(override=True)
            
            self.logger.info(f"[{self._mode_tag()}] 已更新.env中的API_TOKEN: {token[:8]}...")
            
        except Exception as e:
            self.logger.error(f"更新.env文件失败: {e}")
    
    def verify_token(self, token: str) -> bool:
        """
        验证Token是否有效
        
        Args:
            token: 要验证的Token
            
        Returns:
            bool: Token是否有效
        """
        try:
            # 使用Puter API测试Token
            headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json',
                'Accept': '*/*',
                'Origin': 'https://docs.puter.com',
                'Referer': 'https://docs.puter.com/',
                'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
            }
            
            test_payload = {
                "interface": "puter-chat-completion",
                "driver": "openai-completion", 
                "method": "complete",
                "args": {
                    "messages": [{"role": "user", "content": "hi"}],
                    "model": "gpt-4.1-nano",
                    "max_tokens": 5
                }
            }
            
            response = requests.post(
                'https://api.puter.com/drivers/call',
                headers=headers,
                json=test_payload,
                timeout=30,
                proxies=_PUTER_PROXIES
            )
            
            # 更新验证时间（在锁内进行）
            with self.lock:
                if token in self.token_pool:
                    self.token_pool[token]['last_verified'] = datetime.now().isoformat()
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    self.logger.info(f"Token验证成功: {token[:8]}...")
                    return True
                else:
                    error_info = data.get('error', {})
                    if 'usage-limited' in str(error_info):
                        self.logger.warning(f"Token用量耗尽: {token[:8]}...")
                        # 在锁外调用，避免死锁
                        self.mark_token_exhausted(token)
                    else:
                        self.logger.warning(f"Token验证失败: {token[:8]}... - {error_info}")
                        # 在锁外调用，避免死锁
                        self.mark_token_invalid(token, str(error_info))
                    return False
            else:
                self.logger.warning(f"Token验证失败，状态码: {response.status_code}")
                # 在锁外调用，避免死锁
                self.mark_token_invalid(token, f"HTTP {response.status_code}")
                return False
                
        except Exception as e:
            self.logger.error(f"验证Token时出错: {e}")
            return False
    
    def verify_all_tokens(self) -> None:
        """验证所有Token"""
        self.logger.info("开始验证所有Token...")
        invalid_tokens = []
        
        for token in list(self.token_pool.keys()):
            if not self.verify_token(token):
                invalid_tokens.append(token)
        
        self.logger.info(f"Token验证完成，发现 {len(invalid_tokens)} 个无效Token")
        self.save_token_pool()
    
    def get_token_stats(self) -> Dict:
        """
        获取Token池统计信息
        
        Returns:
            dict: 统计信息
        """
        with self.lock:
            total = len(self.token_pool)
            active = len([t for t in self.token_pool.values() if t.get('status') == 'active'])
            exhausted = len([t for t in self.token_pool.values() if t.get('status') == 'exhausted'])
            invalid = len([t for t in self.token_pool.values() if t.get('status') == 'invalid'])
            
            return {
                'total_tokens': total,
                'active_tokens': active,
                'exhausted_tokens': exhausted,
                'invalid_tokens': invalid,
                'current_index': self.current_token_index,
                'token_file': self.token_file,
                'last_updated': datetime.now().isoformat()
            }
    
    def cleanup_invalid_tokens(self) -> None:
        """清理无效Token"""
        with self.lock:
            invalid_tokens = [
                token for token, data in self.token_pool.items()
                if not data.get('is_valid', True) or data.get('status') == 'invalid'
            ]
            
            for token in invalid_tokens:
                del self.token_pool[token]
            
            if invalid_tokens:
                self.logger.info(f"清理了 {len(invalid_tokens)} 个无效Token")
                self.save_token_pool()
    
    def ensure_tokens_available(self, min_count: int = 2) -> bool:
        """
        确保有足够的可用Token
        
        Args:
            min_count: 最少需要的Token数量
            
        Returns:
            bool: 是否有足够的Token
        """
        active_count = len([
            t for t in self.token_pool.values() 
            if t.get('status') == 'active' and t.get('is_valid', True)
        ])
        
        if active_count < min_count:
            self.logger.warning(f"可用Token不足 ({active_count}/{min_count})")
            return False
        
        return True


# 全局Token管理器实例
_token_manager = None


def get_token_manager() -> TokenManager:
    """获取全局Token管理器实例"""
    global _token_manager
    if _token_manager is None:
        _token_manager = TokenManager()
    return _token_manager


if __name__ == "__main__":
    # 测试Token管理器
    import logging
    logging.basicConfig(level=logging.INFO)
    
    manager = TokenManager()
    
    # 显示统计信息
    stats = manager.get_token_stats()
    print(f"📊 Token统计: {stats}")
    
    # 获取当前Token
    current = manager.get_current_token()
    if current:
        print(f"🔑 当前Token: {current[:8]}...")
    else:
        print("❌ 没有可用Token")
