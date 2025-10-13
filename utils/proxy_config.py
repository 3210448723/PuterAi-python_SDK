"""统一的 Puter 访问代理配置

所有向 *.puter.com 发起的 HTTP(S) 请求都应通过此处返回的代理。

默认代理: 127.0.0.1:10809 (可通过环境变量 PUTER_PROXY 覆盖)

Usage:
    from proxy_config import get_puter_proxies
    requests.get(url, proxies=get_puter_proxies())

如果需要临时禁用代理，可设置环境变量 DISABLE_PUTER_PROXY=1
"""

from __future__ import annotations
import os
from typing import Dict, Optional

_PROXY_ENV_KEY = "PUTER_PROXY"  # 允许用户自定义，如: http://127.0.0.1:10809 或 socks5://127.0.0.1:10809
_DISABLE_ENV_KEY = "DISABLE_PUTER_PROXY"

def get_puter_proxy_address() -> Optional[str]:
    """获取代理地址 (字符串形式)

    返回示例: 'http://127.0.0.1:10809'
    当禁用或未配置时返回 None
    """
    if os.getenv(_DISABLE_ENV_KEY, "0") in {"1", "true", "True"}:
        return None
    return os.getenv(_PROXY_ENV_KEY, "http://127.0.0.1:10809").strip() or None


def get_puter_proxies() -> Optional[Dict[str, str]]:
    """返回 requests 库可直接使用的 proxies 参数

    形如: {"http": "http://127.0.0.1:10809", "https": "http://127.0.0.1:10809"}
    若未启用代理则返回 None
    """
    addr = get_puter_proxy_address()
    if not addr:
        return None
    return {"http": addr, "https": addr}


__all__ = ["get_puter_proxies", "get_puter_proxy_address"]
