#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置管理器

统一管理系统配置，包括文件路径、API设置等
"""

import os
import json
from pathlib import Path
from typing import Optional


class ConfigManager:
    """配置管理器"""
    
    def __init__(self):
        # 项目根目录
        self.project_root = Path(__file__).parent.parent
        
        # 数据目录
        self.data_dir = self.project_root / 'data'
        self.logs_dir = self.project_root / 'logs'
        
        # 确保目录存在
        self.data_dir.mkdir(exist_ok=True)
        self.logs_dir.mkdir(exist_ok=True)
        
        # 配置文件路径
        self.config_file = self.data_dir / 'system_config.json'
        
        # 默认配置
        self.default_config = {
            'proxy': {
                'max_proxies': 10,
                'verify_timeout': 30,
                'retry_count': 3,
                'pool_file': str(self.data_dir / 'proxy_pool.json')
            },
            'token': {
                'max_tokens': 50,
                'verify_timeout': 30,
                'pool_file': str(self.data_dir / 'token_pool.json')
            },
            'api': {
                'puter_api_url': 'https://api.puter.com/drivers/call',
                'puter_models_url': 'https://puter.com/puterai/chat/models',
                'default_model': 'gpt-4.1-nano',
                'max_concurrent_requests': 10
            },
            'system': {
                # 默认禁用自动注册，防止未经显式允许的自动创建/注册行为
                'auto_register_enabled': False,
                'auto_cleanup_enabled': True,
                'log_level': 'INFO'
            }
        }
        
        # 加载配置
        self.config = self.load_config()
    
    def load_config(self) -> dict:
        """加载配置文件"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    # 合并默认配置和加载的配置
                    return self.merge_config(self.default_config, config)
            else:
                # 使用默认配置并保存
                self.save_config(self.default_config)
                return self.default_config.copy()
        except Exception as e:
            print(f"加载配置失败: {e}，使用默认配置")
            return self.default_config.copy()
    
    def save_config(self, config: Optional[dict] = None) -> None:
        """保存配置文件"""
        try:
            config_to_save = config or self.config
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config_to_save, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存配置失败: {e}")
    
    def merge_config(self, default: dict, user: dict) -> dict:
        """合并默认配置和用户配置"""
        result = default.copy()
        for key, value in user.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self.merge_config(result[key], value)
            else:
                result[key] = value
        return result
    
    def get(self, key: str, default=None):
        """获取配置值，支持点分隔的键名"""
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def set(self, key: str, value) -> None:
        """设置配置值，支持点分隔的键名"""
        keys = key.split('.')
        config = self.config
        
        for k in keys[:-1]:
            if k not in config or not isinstance(config[k], dict):
                config[k] = {}
            config = config[k]
        
        config[keys[-1]] = value
        self.save_config()
    
    def get_proxy_config(self) -> dict:
        """获取代理配置"""
        return self.config['proxy']
    
    def get_token_config(self) -> dict:
        """获取Token配置"""
        return self.config['token']
    
    def get_api_config(self) -> dict:
        """获取API配置"""
        return self.config['api']
    
    def get_system_config(self) -> dict:
        """获取系统配置"""
        return self.config['system']
    
    def get_data_path(self, filename: str) -> str:
        """获取数据文件的完整路径"""
        return str(self.data_dir / filename)
    
    def get_log_path(self, filename: str) -> str:
        """获取日志文件的完整路径"""
        return str(self.logs_dir / filename)


# 全局配置管理器实例
_config_manager = None


def get_config_manager() -> ConfigManager:
    """获取全局配置管理器实例"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


if __name__ == "__main__":
    # 测试配置管理器
    config = get_config_manager()
    
    print("代理配置:", config.get_proxy_config())
    print("Token配置:", config.get_token_config())
    print("API配置:", config.get_api_config())
    
    # 测试设置和获取
    config.set('test.key', 'test_value')
    print("测试值:", config.get('test.key'))
