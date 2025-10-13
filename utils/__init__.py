"""utils 包初始化

该目录提供代理、token、配置等管理工具模块。确保作为包可被 `from utils import ...` 导入。
如果后续需要在包级暴露工厂函数，可在此处统一导出。
"""

# 可选：尝试导出常用入口（容错导入）
try:  # pragma: no cover - 容错导入
    from .proxy_manager import get_proxy_manager  # type: ignore
except Exception:  # noqa: E722
    pass

try:  # pragma: no cover
    from .token_manager import get_token_manager  # type: ignore
except Exception:  # noqa: E722
    pass

# 显式导出（如果上方导入失败，对应名称不会出现在globals里，但这里静态列出便于IDE补全）
__all__ = [
    'get_proxy_manager',
    'get_token_manager'
]
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Utils模块初始化

提供统一的模块导入接口
"""

from .config_manager import get_config_manager
from .proxy_manager import get_proxy_manager  
from .token_manager import get_token_manager

__all__ = [
    'get_config_manager',
    'get_proxy_manager', 
    'get_token_manager'
]
