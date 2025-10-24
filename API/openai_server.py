#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PuterAI OpenAI兼容代理服务器

这是一个将Puter.js AI API包装为OpenAI Python SDK兼容接口的代理服务器。
支持聊天对话、图像生成、语音合成、图像理解等多种AI功能。

主要功能:
- 🤖 聊天对话 (兼容OpenAI Chat Completions API)
- 🖼️ 图像生成 (兼容OpenAI DALL-E API)  
- 🔊 文本转语音 (兼容OpenAI TTS API)
- 👁️ 图像理解 (兼容OpenAI Vision API)
- ⚡ 流式传输支持
- 🔧 函数调用支持

许可证: MIT License
"""

import os
import time
import json
import uuid
import logging
import requests
import base64
import threading
import subprocess
import sys
import asyncio
from typing import Optional, Tuple
from threading import Semaphore
from functools import wraps
from flask import Flask, request, jsonify, Response, stream_with_context
from flask_cors import CORS
from dotenv import load_dotenv
from logging.handlers import RotatingFileHandler

# 加载环境变量 (期望在环境变量或.env文件中设置API_TOKEN)
load_dotenv()

# 创建Flask应用实例
app = Flask(__name__)
CORS(app)  # 启用跨域资源共享

# ====== 路径处理：确保可以导入utils包 ======
# 之前代码仅将 utils 目录本身加入 sys.path，会导致 Python 在该目录内部查找子模块文件，
# 但若 utils 目录未含 __init__.py 或存在包相对导入需求，推荐把项目根目录(parent_dir)加入 sys.path。
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)
utils_dir = os.path.join(parent_dir, 'utils')  # 保留变量引用（日志或调试可用）

# 导入代理和Token管理器
try:
    from utils import get_proxy_manager, get_token_manager
    _proxy_token_manager_available = True
    print("✅ 代理和Token管理器导入成功")
except ImportError as e:
    print(f"⚠️ 无法导入代理和Token管理器: {e}")
    _proxy_token_manager_available = False

# 导入参数验证工具
from utils.validate_params import validate_messages

# ====== 日志配置部分 ======
def setup_logging():
    """
    配置应用程序日志系统
    
    设置文件和控制台两种日志输出方式：
    - 文件日志：存储在logs/目录，支持日志轮转
    - 控制台日志：实时输出到终端
    """
    # 确保日志目录存在
    if not os.path.exists('logs'):
        os.makedirs('logs')
        app.logger.info("创建日志目录: logs/")

    # 配置文件日志处理器 (支持日志轮转)
    file_handler = RotatingFileHandler(
        'logs/openai_proxy.log', 
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5  # 保留5个备份文件
    )
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s [%(levelname)s] [%(filename)s:%(funcName)s:%(lineno)d] %(message)s'
    ))
    file_handler.setLevel(logging.DEBUG)

    # 配置控制台日志处理器
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(
        '%(asctime)s [%(levelname)s] %(message)s'
    ))
    console_handler.setLevel(logging.INFO)

    # 清除Flask默认的处理器，避免重复日志
    app.logger.handlers.clear()
    
    # 将处理器添加到应用日志器
    app.logger.addHandler(file_handler)
    app.logger.addHandler(console_handler)
    app.logger.setLevel(logging.DEBUG)

    # 降低Flask内置日志级别，减少噪音
    logging.getLogger('werkzeug').setLevel(logging.WARNING)
    
    app.logger.info("日志系统初始化完成")

# 初始化日志系统
setup_logging()

# ====== 常量配置部分 ======

# Puter API配置 & 代理
PUTER_API_URL = "https://api.puter.com/drivers/call"
PUTER_MODELS_URL = "https://puter.com/puterai/chat/models"
try:
    # utils 目录已被加入 sys.path
    from proxy_config import get_puter_proxies  # type: ignore
    _PUTER_PROXIES = get_puter_proxies()
    app.logger.info(f"Puter 代理设置: {_PUTER_PROXIES if _PUTER_PROXIES else '未启用'}")
except Exception as _e:  # pragma: no cover - 导入失败仅记录日志
    _PUTER_PROXIES = None
    app.logger.warning(f"加载代理配置失败: {_e}")

# 默认请求头配置 (模拟真实浏览器请求)
PUTER_HEADERS_TEMPLATE = {
    'Accept': '*/*',
    'Content-Type': 'application/json;charset=UTF-8',
    'Origin': 'https://docs.puter.com',  # 必备
    'Referer': 'https://docs.puter.com/',  # 必备
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
}

# 静态模型列表 (从Puter文档中获取的部分模型)
# 完整列表参见: https://puter.com/puterai/chat/models
PUTER_MODELS_FALLBACK = [
    # OpenAI系列
    "gpt-4o-mini", "gpt-4o", "o1", "o1-mini", "o1-pro", "o3", "o3-mini", "o4-mini",
    "gpt-5", "gpt-5-mini", "gpt-5-nano", "gpt-5-chat-latest", "gpt-4.1", "gpt-4.1-mini",
    "gpt-4.1-nano", "gpt-4.5-preview",
    
    # Anthropic Claude系列
    "claude-sonnet-4", "claude-opus-4", "claude-3-7-sonnet", "claude-3-5-sonnet",
    
    # 其他主流模型
    "deepseek-chat", "deepseek-reasoner", "google/gemini-2.0-flash", "google/gemini-1.5-flash",
    "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo", "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo",
    "meta-llama/Meta-Llama-3.1-405B-Instruct-Turbo", "mistral-large-latest",
    "pixtral-large-latest", "codestral-latest", "google/gemma-2-27b-it", "grok-beta"
]

# OpenAI TTS声音映射到AWS Polly声音
TTS_VOICE_MAPPING = {
    "alloy": "Joanna",      # 中性声音
    "echo": "Matthew",      # 男性声音
    "fable": "Amy",         # 英式女性声音
    "onyx": "Brian",        # 深沉男性声音
    "nova": "Emma",         # 年轻女性声音
    "shimmer": "Olivia"     # 温暖女性声音
}

# 音频格式对应的MIME类型
AUDIO_CONTENT_TYPE_MAPPING = {
    "mp3": "audio/mpeg",
    "opus": "audio/opus", 
    "aac": "audio/aac",
    "flac": "audio/flac"
}

SUSPECT_TOKEN_PATTERNS = [
    "test", "none", "placeholder", "empty", "your-put", "your_put", "your-puter", "demo", "example"
]
MIN_TOKEN_LENGTH = 20

app.logger.info("常量配置加载完成")

# ====== 全局变量部分 ======

# 自动注册锁，防止同时启动多个注册进程
_auto_register_lock = threading.Lock()
_auto_register_in_progress = False
_auto_register_disabled = False  # 标记自动注册是否被禁用（IP被限制时）

# 并发控制：限制同时处理的请求数量为10
MAX_CONCURRENT_REQUESTS = 10
request_semaphore = Semaphore(MAX_CONCURRENT_REQUESTS)

# ====== 工具函数部分 ======

def limit_concurrency(max_requests=MAX_CONCURRENT_REQUESTS):
    """
    限制并发请求数量的装饰器
    
    Args:
        max_requests: 最大并发请求数量
        
    Returns:
        装饰器函数
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 尝试获取信号量，如果无法获取则等待
            if not request_semaphore.acquire(blocking=True, timeout=30):
                app.logger.warning(f"请求超时：并发数已达上限 {max_requests}")
                return jsonify({
                    "error": {
                        "message": f"服务器繁忙，当前并发请求数已达上限 {max_requests}，请稍后重试",
                        "type": "rate_limit_exceeded",
                        "code": "concurrent_limit_exceeded"
                    }
                }), 429
            
            try:
                app.logger.debug(f"请求开始处理，当前并发数: {max_requests - request_semaphore._value}")
                return func(*args, **kwargs)
            finally:
                # 确保在函数执行完成后释放信号量
                request_semaphore.release()
                app.logger.debug(f"请求处理完成，当前并发数: {max_requests - request_semaphore._value}")
        
        return wrapper
    return decorator


def estimate_tokens(text: str, model: str = "gpt-4o-mini") -> int:
    """
    估算文本的token数量
    
    Args:
        text: 要估算的文本
        model: 模型名称 (用于选择适当的编码器)
        
    Returns:
        估算的token数量
        
    Note:
        优先使用tiktoken库进行精确估算，如果不可用则使用简单的字符数除以4的方法
    """
    # 新增：确保 text 为字符串
    if not isinstance(text, str):
        text = str(text) if text is not None else ""
    try:
        import tiktoken
        try:
            # 尝试获取模型对应的编码器
            enc = tiktoken.encoding_for_model(model)
        except Exception:
            # 回退到通用编码器
            enc = tiktoken.get_encoding("o200k_base")
        token_count = len(enc.encode(text or ""))
        app.logger.debug(f"使用tiktoken估算token数量: {token_count}")
        return token_count
    except ImportError:
        # tiktoken不可用时的回退方案: 大约1个token = 4个字符
        token_count = max(1, int(len(text or "") / 4))
        app.logger.debug(f"使用字符数估算token数量: {token_count}")
        return token_count


def is_usage_limited_error(error_data):
    """
    检测是否是token用量不足的错误
    
    Args:
        error_data: 错误数据字典
        
    Returns:
        bool: 如果是用量限制错误返回True
    """
    if not isinstance(error_data, dict):
        return False
    
    # 检查错误类型和消息
    error_info = error_data.get('error', {})
    if isinstance(error_info, dict):
        delegate = error_info.get('delegate', '')
        message = error_info.get('message', '')
        code = error_info.get('code', '')
        
        # 检测特定的用量限制错误
        if (delegate == 'usage-limited-chat' or 
            'usage-limited' in delegate or
            'Permission denied' in message):
            return True
    
    return False


                    
def usage_limited_response(auto_register: bool):
    """在请求上下文中构造用量限制响应，避免模块导入阶段调用jsonify导致的应用上下文错误。

    Args:
        auto_register: 是否已经触发自动注册流程。
    Returns:
        (Response, int): Flask响应对象与HTTP状态码。
    """
    if auto_register:
        msg = "Token用量不足，正在后台自动重新注册。请稍后重试。"
        details = "系统已自动启动token更新流程，请等待1-2分钟后重新发送请求。"
    else:
        msg = "Token用量不足"
        details = "请更换有效Token"
    return jsonify({
        "error": {
            "message": msg,
            "type": "usage_limited_error",
            "details": details,
            "auto_register": auto_register
        }
    }), 429

def auto_register_token():
    """
    在后台异步执行token注册
    
    使用增强版注册系统，支持代理IP轮换和多Token管理。
    使用全局锁机制防止同时启动多个注册进程。
    如果已有注册进程在运行，则跳过本次注册请求。
    如果检测到IP被限制注册，则禁用自动注册功能。
    """
    global _auto_register_in_progress, _auto_register_disabled
    
    # 检查自动注册是否已被禁用
    if _auto_register_disabled:
        app.logger.warning("🚫 自动注册功能已被禁用（IP被限制注册），跳过注册请求")
        return
    
    # 使用非阻塞锁检查是否已有注册进程在运行
    if not _auto_register_lock.acquire(blocking=False):
        app.logger.info("🔄 已有自动注册进程在运行，跳过本次注册请求")
        return
    
    try:
        if _auto_register_in_progress:
            app.logger.info("🔄 已有自动注册进程在运行，跳过本次注册请求")
            return
        
        # 标记注册进程开始
        _auto_register_in_progress = True
        app.logger.info("🔄 检测到token用量不足，开始自动重新注册...")
        
        def register_in_background():
            global _auto_register_in_progress, _auto_register_disabled
            try:
                # 获取当前脚本所在目录
                current_dir = os.path.dirname(os.path.abspath(__file__))
                parent_dir = os.path.dirname(current_dir)  # 上级目录
                
                # 优先使用增强版注册脚本
                enhanced_register_script = os.path.join(parent_dir, 'register_enhanced.py')
                register_script = os.path.join(parent_dir, 'register.py')
                
                # 选择注册脚本
                if _proxy_token_manager_available and os.path.exists(enhanced_register_script):
                    app.logger.info("🚀 使用增强版注册脚本（支持代理和多Token）")
                    script_to_use = enhanced_register_script
                    # 对于增强版脚本，尝试注册多个Token
                    command = [sys.executable, script_to_use, '--count', '3']
                else:
                    app.logger.info("🚀 使用标准注册脚本")
                    script_to_use = register_script
                    command = [sys.executable, script_to_use]
                
                # 检查注册脚本是否存在
                if not os.path.exists(script_to_use):
                    app.logger.error(f"❌ 注册脚本不存在: {script_to_use}")
                    return
                
                # 在新进程中运行注册脚本
                app.logger.info(f"🚀 正在执行注册脚本: {script_to_use}")
                result = subprocess.run(
                    command,
                    cwd=parent_dir,
                    capture_output=True,
                    text=True,
                    timeout=300  # 5分钟超时（增强版需要更多时间）
                )
                
                if result.returncode == 0:
                    app.logger.info("✅ 自动注册成功完成")
                    if result.stdout:
                        app.logger.info(f"注册输出: {result.stdout}")
                    
                    # 如果使用Token管理器，尝试重新加载Token池
                    if _proxy_token_manager_available:
                        try:
                            token_manager = get_token_manager()
                            stats = token_manager.get_token_stats()
                            app.logger.info(f"📊 Token池状态: {stats}")
                        except Exception as e:
                            app.logger.warning(f"重新加载Token池失败: {e}")
                    
                    # 重新加载环境变量
                    load_dotenv(override=True)
                    app.logger.info("🔄 已重新加载环境变量")
                else:
                    app.logger.error(f"❌ 自动注册失败，返回码: {result.returncode}")
                    if result.stderr:
                        app.logger.error(f"错误输出: {result.stderr}")
                    
                    # 检查是否是注册被限制（register.py返回1）
                    if result.returncode == 1:
                        app.logger.warning("🚫 检测到IP被限制注册，禁用自动注册功能")
                        _auto_register_disabled = True
                        app.logger.info("💡 提示：请运行初始化脚本获取代理IP后重新尝试: python init_system.py")
                    
            except subprocess.TimeoutExpired:
                app.logger.error("❌ 自动注册超时（5分钟）")
            except Exception as e:
                app.logger.error(f"❌ 自动注册过程中出错: {str(e)}")
            finally:
                # 注册完成，重置状态
                _auto_register_in_progress = False
                app.logger.info("🔄 自动注册进程已结束")
        
        # 在后台线程中执行注册
        thread = threading.Thread(target=register_in_background, daemon=True)
        thread.start()
        app.logger.info("🔄 已启动后台注册线程")
        
    finally:
        # 释放锁
        _auto_register_lock.release()


def enable_auto_register():
    """
    重新启用自动注册功能
    
    当用户更换网络环境或IP地址后，可以调用此函数重新启用自动注册功能
    """
    global _auto_register_disabled
    
    # 启用自动注册功能
    _auto_register_disabled = False
    app.logger.info("🔄 自动注册功能已重新启用")


def is_auto_register_disabled():
    """
    检查自动注册功能是否被禁用
    
    Returns:
        bool: 如果自动注册被禁用返回True
    """
    return _auto_register_disabled


def ensure_env_file_exists():
    """
    确保.env文件存在，如果不存在则创建
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)
    env_file = os.path.join(parent_dir, '.env')
    
    if not os.path.exists(env_file):
        app.logger.info("📝 .env文件不存在，正在创建...")
        try:
            with open(env_file, 'w') as f:
                f.write('# PuterAI API Token\n')
                f.write('API_TOKEN=""\n')
            app.logger.info(f"✅ 已创建.env文件: {env_file}")
        except Exception as e:
            app.logger.error(f"❌ 创建.env文件失败: {str(e)}")
    
    return env_file


def _is_suspect_token(token: str) -> Tuple[bool, str]:
    """判定 token 是否疑似占位/测试，逻辑需与 token_manager._is_suspect 保持一致。"""
    if not token:
        return True, "空token"
    lowered = token.lower()
    if len(token) < MIN_TOKEN_LENGTH:
        return True, f"长度过短({len(token)})"
    for p in SUSPECT_TOKEN_PATTERNS:
        if p in lowered:
            return True, f"包含可疑片段:{p}"
    return False, ""


def get_effective_api_key():
    """获取有效API密钥，按优先级：请求头 -> Token池 -> 环境变量。

    对请求头中的 token 做可疑过滤：过短或包含 test/none/placeholder/your-put 等片段则忽略，
    自动回退到 Token 池；若池不可用再回退 env。
    """
    source = "none"
    # ---------- 方式1: 请求头 ----------
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        request_api_key = auth_header[7:].strip()
        suspect, reason = _is_suspect_token(request_api_key)
        if suspect:
            app.logger.info(f"过滤请求头Token({request_api_key[:8]}...): {reason} -> 使用池/环境变量")
        else:
            # 校验其在池中状态（如果存在池）
            if _proxy_token_manager_available:
                try:
                    token_manager = get_token_manager()
                    token_data = token_manager.token_pool.get(request_api_key)
                    if token_data and (not token_data.get('is_valid', True) or token_data.get('status') != 'active'):
                        app.logger.warning(f"请求头Token已失效: {request_api_key[:8]}..., 尝试切换")
                        token_manager.remove_token(request_api_key)
                        alt = token_manager.get_current_token()
                        if alt:
                            app.logger.info(f"改用池Token: {alt[:8]}... (请求头失效)")
                            return alt
                        else:
                            app.logger.error("没有可用Token (请求头失效且池为空)")
                            return ''
                except Exception as e:
                    app.logger.error(f"验证请求头Token时出错: {e}")
            app.logger.debug("使用请求头中的API密钥")
            source = "header"
            return request_api_key
    # ---------- 方式2: Token池 ----------
    if _proxy_token_manager_available:
        try:
            token_manager = get_token_manager()
            current_token = token_manager.get_current_token()
            if current_token:
                app.logger.debug(f"使用Token池Token: {current_token[:8]}...")
                source = "pool"
                return current_token
        except Exception as e:
            app.logger.warning(f"从Token管理器获取密钥失败: {e}")
    # ---------- 方式3: 环境变量 ----------
    env_api_key = os.getenv('API_TOKEN', '').strip()
    if env_api_key:
        suspect, reason = _is_suspect_token(env_api_key)
        if suspect:
            app.logger.warning(f"环境变量Token看似无效({env_api_key[:8]}...): {reason}")
        else:
            if _proxy_token_manager_available:
                try:
                    token_manager = get_token_manager()
                    token_data = token_manager.token_pool.get(env_api_key)
                    if token_data and (not token_data.get('is_valid', True) or token_data.get('status') != 'active'):
                        app.logger.warning(f"环境变量Token已失效: {env_api_key[:8]}..., 删除并尝试切换")
                        token_manager.remove_token(env_api_key)
                        alt = token_manager.get_current_token()
                        if alt:
                            app.logger.info(f"改用池Token: {alt[:8]}... (环境变量失效)")
                            return alt
                        else:
                            return ''
                except Exception as e:
                    app.logger.error(f"检查环境变量Token时出错: {e}")
            app.logger.debug("使用环境变量中的API密钥")
            source = "env"
            return env_api_key
    app.logger.warning("未找到有效的API密钥 (source=%s)", source)
    return ''


def handle_token_invalid(token: str, error_info: Optional[str] = None):
    """
    处理Token无效的情况
    
    Args:
        token: 无效的Token
        error_info: 错误信息
    """
    if _proxy_token_manager_available:
        try:
            token_manager = get_token_manager()
            
            # 根据错误类型标记并直接移除该token
            if token in token_manager.token_pool:
                if 'usage-limited' in str(error_info):
                    token_manager.mark_token_exhausted(token)
                else:
                    token_manager.mark_token_invalid(token, error_info)
                # 移除该token
                token_manager.remove_token(token)
                app.logger.warning(f"已移除无效Token: {token[:8]}... ({error_info})")

            # 尝试获取当前可用token
            alt = token_manager.get_current_token()
            if alt:
                app.logger.info(f"切换到备用Token: {alt[:8]}...")
                return True
            app.logger.error("所有Token均不可用")
            return False
                
        except Exception as e:
            app.logger.error(f"处理Token无效时出错: {e}")
    
    return False


def handle_token_error_and_rotate(error_type: str, api_key: str, error_payload: Optional[dict] = None, context: str = ""):
    """统一处理与当前 token 相关的各种错误并尝试轮换下一个 token。

    Args:
        error_type: 错误类型标识，如 'usage_limited', 'token_auth_failed', 'invalid', 'exhausted'
        api_key: 当前请求使用的 token
        error_payload: 上游返回的完整错误数据（可选）
        context: 触发场景描述，方便日志排查
    Returns:
        dict: { 'rotated': bool, 'next_token': Optional[str] }
    """
    result = {"rotated": False, "next_token": None}
    if not api_key:
        return result

    if not _proxy_token_manager_available:
        app.logger.warning("Token管理器不可用，无法执行统一轮换处理")
        return result

    try:
        token_manager = get_token_manager()
        if api_key in token_manager.token_pool:
            mark_reason = error_type
            if error_type == 'usage_limited' or 'usage-limited' in error_type:
                token_manager.mark_token_exhausted(api_key)
            elif error_type == 'token_auth_failed':
                token_manager.mark_token_invalid(api_key, 'token_auth_failed')
            elif error_type == 'invalid':
                token_manager.mark_token_invalid(api_key, 'invalid')
            else:
                token_manager.mark_token_invalid(api_key, mark_reason)

        app.logger.warning(f"🔄 触发Token轮换 ({error_type})，当前池Token: {api_key[:8]}...{api_key[-8:]} 场景: {context}")
        next_token = token_manager.switch_to_next_token()
        if next_token:
            result['rotated'] = True
            result['next_token'] = next_token
            app.logger.info(f"➡️ 已切换到下一个Token: {next_token[:8]}...")
        else:
            app.logger.error("没有可用的后续Token可供切换")
    except Exception as e:
        app.logger.error(f"统一Token处理异常: {e}")
    return result


def get_puter_headers(api_key=None):
    """
    生成Puter API请求头
    
    Args:
        api_key: API密钥，如果为None则自动获取
        
    Returns:
        dict: 完整的请求头字典
    """
    if api_key is None:
        api_key = get_effective_api_key()
    
    headers = PUTER_HEADERS_TEMPLATE.copy()
    headers['Authorization'] = f"Bearer {api_key}"
    
    app.logger.debug("生成Puter API请求头")
    return headers


def extract_usage_from_puter_response(data, model, user_text="", assistant_text=""):
    """
    从Puter API响应中提取token使用信息
    
    Args:
        data: Puter API的响应数据
        model: 使用的模型名称
        user_text: 用户输入的文本 (用于本地估算)
        assistant_text: 助手回复的文本 (用于本地估算)
        
    Returns:
        dict: 包含token使用统计的字典
    """
    # 尝试从Puter API响应中提取usage信息
    result = data.get("result", {})
    puter_usage = result.get("usage", [])
    
    # 初始化token计数
    prompt_tokens = None
    completion_tokens = None
    
    # 解析Puter返回的usage数组
    if isinstance(puter_usage, list):
        for usage_item in puter_usage:
            if isinstance(usage_item, dict):
                usage_type = usage_item.get("type")
                amount = usage_item.get("amount")
                
                if usage_type == "prompt" and amount is not None:
                    prompt_tokens = amount
                    app.logger.debug(f"从API获取prompt tokens: {amount}")
                elif usage_type == "completion" and amount is not None:
                    completion_tokens = amount
                    app.logger.debug(f"从API获取completion tokens: {amount}")
    
    # 如果API没有返回token信息，使用本地估算
    if prompt_tokens is None:
        prompt_tokens = estimate_tokens(user_text, model)
        app.logger.debug(f"本地估算prompt tokens: {prompt_tokens}")
        
    if completion_tokens is None:
        completion_tokens = estimate_tokens(assistant_text, model)
        app.logger.debug(f"本地估算completion tokens: {completion_tokens}")
    
    total_tokens = (prompt_tokens or 0) + (completion_tokens or 0)
    
    usage_info = {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
    }
    
    app.logger.info(f"Token使用统计 - 提示: {prompt_tokens}, 完成: {completion_tokens}, 总计: {total_tokens}")
    return usage_info


def normalize_messages(body):
    """
    标准化消息格式
    
    将不同格式的输入统一转换为标准的OpenAI消息格式。
    支持的输入格式:
    1. 标准的messages数组
    2. 传统的prompt字段
    3. input字段
    
    Args:
        body: 请求体字典
        
    Returns:
        list: 标准化后的消息列表
    """
    messages = body.get("messages")
    
    if not messages:
        # 支持传统的prompt字段作为回退
        prompt = body.get("prompt") or body.get("input")
        if isinstance(prompt, str) and prompt:
            messages = [{"role": "user", "content": prompt}]
            app.logger.debug("从prompt字段转换为messages格式")
    
    # 确保每个消息都有role和content字段
    normalized = []
    if isinstance(messages, list):
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            # 保持图像内容的原始格式不做转换 (用于Vision API)
            normalized.append({"role": role, "content": content})
    
    app.logger.debug(f"标准化了 {len(normalized)} 条消息")
    return normalized


def build_openai_chat_response(model: str, assistant_text: str, tool_calls=None, usage=None):
    """
    构建OpenAI兼容的聊天响应格式
    
    Args:
        model: 使用的模型名称
        assistant_text: 助手回复的文本
        tool_calls: 工具调用信息 (可选)
        usage: token使用统计 (可选)
        
    Returns:
        dict: OpenAI格式的响应字典
    """
    response_id = f"chatcmpl-{uuid.uuid4().hex[:24]}"
    created = int(time.time())
    
    # 构建消息对象
    message = {"role": "assistant", "content": assistant_text}
    if tool_calls:
        message["tool_calls"] = tool_calls
        app.logger.debug(f"添加了 {len(tool_calls)} 个工具调用")
    
    response = {
        "id": response_id,
        "object": "chat.completion",
        "created": created,
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": message,
                "finish_reason": "stop",
            }
        ],
        "usage": usage or {
            "prompt_tokens": None,
            "completion_tokens": None,
            "total_tokens": None,
        },
        "system_fingerprint": None,
    }
    
    app.logger.debug(f"构建OpenAI响应: ID={response_id}, 模型={model}")
    return response


def openai_stream_chunk(data_obj: dict) -> str:
    """
    格式化OpenAI流式响应数据块
    
    Args:
        data_obj: 要发送的数据对象
        
    Returns:
        str: 格式化后的SSE数据块
    """
    return f"data: {json.dumps(data_obj, ensure_ascii=False)}\n\n"


app.logger.info("工具函数初始化完成")


def _filter_models(models):
    """对模型列表进行简单过滤/去重：
    1. 去重保持顺序
    2. 排除空字符串或明显占位项(长度<3)
    3. 预留扩展（可加入黑名单）
    """
    seen = set()
    result = []
    for m in models:
        if not m or not isinstance(m, str):
            continue
        if len(m.strip()) < 3:
            continue
        if m in seen:
            continue
        seen.add(m)
        result.append(m)
    return result


# ====== API端点实现部分 ======

@app.route("/v1/models", methods=["GET"])
@limit_concurrency()
def list_models():
    """
    获取可用模型列表 (兼容OpenAI Models API)
    
    首先尝试从Puter API动态获取最新模型列表，
    如果失败则使用内置的静态模型列表作为回退。
    NOTE: 静态回退列表可能包含上游已下线或不可访问模型（例如 claude-3-haiku-20240307、arcee_ai/arcee-spotlight 等），
    实际调用前建议先做一次试探请求或根据使用频率定期裁剪。可以在后续版本加入健康缓存。 
    
    Returns:
        JSON: OpenAI格式的模型列表响应
    """
    app.logger.info("收到模型列表请求")
    data = []
    now = int(time.time())
    
    # 验证API密钥
    api_key = get_effective_api_key()
    if not api_key:
        app.logger.error("未提供有效的API密钥")
        return jsonify({
            "error": {
                "message": "未提供有效的API密钥。请在Authorization头中提供或设置API_TOKEN环境变量",
                "type": "invalid_request_error"
            }
        }), 401
    
    headers = get_puter_headers(api_key)
    
    # 尝试从Puter API动态获取模型列表
    try:
        app.logger.debug("正在从Puter API获取模型列表...")
        response = requests.get(PUTER_MODELS_URL, headers=headers, timeout=30, proxies=_PUTER_PROXIES)
        if response.status_code == 200:
            models_data = response.json()
            for model in models_data.get("models", []):
                if isinstance(model, dict):
                    data.append({
                        "id": model.get("id") or model.get("name", ""),
                        "object": "model",
                        "created": now,
                        "owned_by": "puter",
                    })
                elif isinstance(model, str):
                    data.append({
                        "id": model,
                        "object": "model",
                        "created": now,
                        "owned_by": "puter",
                    })
            app.logger.info(f"成功从Puter API获取到 {len(data)} 个模型")
            return jsonify({"object": "list", "data": data})
    except Exception as e:
        app.logger.error(f"从Puter API获取模型列表失败: {e}")

    # 回退到静态模型列表
    app.logger.warning("使用静态模型列表作为回退")
    filtered = _filter_models(PUTER_MODELS_FALLBACK)
    for model_name in filtered:
        data.append({
            "id": model_name,
            "object": "model",
            "created": now,
            "owned_by": "puter",
        })
    app.logger.info(f"返回 {len(data)} 个静态模型(过滤后原始={len(PUTER_MODELS_FALLBACK)})")
    return jsonify({"object": "list", "data": data})


@app.route("/v1/chat/completions", methods=["POST"])
@limit_concurrency()
def chat_completions():
    """
    聊天完成API (兼容OpenAI Chat Completions API)
    
    支持的功能:
    - 🤖 多模型聊天对话
    - 👁️ 图像理解 (Vision API)
    - 🔧 函数调用 (Function Calling)
    - ⚡ 流式响应
    - 🎛️ 参数控制 (temperature, max_tokens等)
    
    Returns:
        JSON/SSE: OpenAI格式的聊天完成响应
    """
    app.logger.info("收到聊天完成请求")
    
    # 验证API密钥
    api_key = get_effective_api_key()
    if not api_key:
        app.logger.error("未提供有效的API密钥")
        return jsonify({
            "error": {
                "message": "未提供有效的API密钥。请在Authorization头中提供或设置API_TOKEN环境变量",
                "type": "invalid_request_error"
            }
        }), 401
    
    headers = get_puter_headers(api_key)

    # 解析请求参数
    body = request.get_json(force=True, silent=True) or {}
    model = body.get("model", "gpt-4.1-nano")
    stream = bool(body.get("stream", False))
    messages = normalize_messages(body)
    temperature = body.get("temperature")
    max_tokens = body.get("max_tokens")
    tools = body.get("tools")  # 函数调用工具定义
    
    # 某些模型不支持temperature参数，需要特殊处理
    if model in ["o3-mini", "o3", "o4-mini"] and temperature is not None:
        temperature = None  
        app.logger.warning(f"模型 {model} 不支持temperature参数，已忽略")

    app.logger.info(f"请求参数 - 模型: {model}, 流式: {stream}, 消息数量: {len(messages) if messages else 0}")

    # 验证必需参数
    if not messages:
        app.logger.warning("请求中未提供消息内容")
        return jsonify({"error": {"message": "messages字段是必需的"}}), 400

    is_valid, errors, suggestions = validate_messages(messages)
    if not is_valid:
        app.logger.error(f"消息验证失败: {errors}，建议: {suggestions}")
        return jsonify({
            "error": {
                "message": "消息格式验证失败",
                "details": errors,
                "suggestions": suggestions
            }
        }), 400
    app.logger.debug("消息格式验证通过")

    # 检测是否包含图像内容 (Vision API功能)
    has_vision = False
    for message in messages:
        content = message.get("content", "")
        if isinstance(content, list):
            for item in content:
                if isinstance(item, dict) and "image_url" in item:
                    has_vision = True
                    break
        if has_vision:
            break

    # 构建Puter API请求载荷
    args = {"messages": messages, "model": model}
    if max_tokens is not None:
        args["max_tokens"] = max_tokens
    if temperature is not None:
        args["temperature"] = temperature
    if tools:
        args["tools"] = tools
        app.logger.debug(f"添加了 {len(tools)} 个工具定义")
    if has_vision:
        args["vision"] = True
        app.logger.info("启用视觉模式 - 处理图像内容")
    
    # Puter API请求载荷示例:
    """
    函数调用工具示例:
    tools = [{
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "获取天气信息",
            "parameters": {
                "type": "object",
                "properties": {
                  "location": {
                    "description": "城市名称，例如: 北京, 上海",
                    "type": "string"
                    }
                  },
                "required": ["location"]
            }
        }
    }]
    """

    payload = {
        "interface": "puter-chat-completion",
        "driver": "openai-completion",
        "method": "complete",
        "args": args,
        "test_mode": False,  # 不启用测试模式，确保计费和token使用
    }
    # 当model为OpenAI兼容模型时使用（没有冒号），如果是`openrouter:moonshotai/kimi-k2:free`等其他模型，则使用对应的driver=openrouter
    if ":" in model:
        payload["driver"] = model.split(":")[0]  # 提取冒号前的部分作为driver

    # Token usage estimation (best-effort)
    try:
        user_text_concat = "\n".join([
            c if isinstance(c, str) else json.dumps(c, ensure_ascii=False)
            for m in messages for c in ([m.get("content")] if not isinstance(m.get("content"), list) else m.get("content"))
        ])
    except Exception:
        user_text_concat = ""

    if stream:
        app.logger.info("Starting streaming response")
        # Attempt true streaming from Puter. If not supported, fall back to single chunk.
        def generate():
            rid = f"chatcmpl-{uuid.uuid4().hex[:24]}"
            created = int(time.time())
            accumulated_content = ""  # 跟踪累积的响应内容
            final_usage_data = None  # 存储最终的usage数据

            # Send role chunk first per OpenAI convention
            first_delta = {
                "id": rid,
                "object": "chat.completion.chunk",
                "created": created,
                "model": model,
                "choices": [
                    {"index": 0, "delta": {"role": "assistant"}, "finish_reason": None}
                ]
            }
            yield openai_stream_chunk(first_delta)

            # Try streaming with Puter
            args_with_stream = dict(args)
            args_with_stream["stream"] = True
            payload_stream = dict(payload)
            payload_stream["args"] = args_with_stream

            try:
                app.logger.debug("Sending streaming request to Puter API")
                with requests.post(PUTER_API_URL, headers=headers, json=payload_stream, stream=True, timeout=30, proxies=_PUTER_PROXIES) as r:
                    if r.status_code != 200:
                        app.logger.warning(f"Stream request failed with status {r.status_code}, falling back to non-stream")
                        # Fallback: non-stream request
                        non_stream_resp = requests.post(PUTER_API_URL, headers=headers, json=payload, timeout=120, proxies=_PUTER_PROXIES)
                        text_out = ""
                        if non_stream_resp.ok:
                            data_json = non_stream_resp.json()
                            text_out = data_json.get("result", {}).get("message", {}).get("content", "") if data_json.get("success") else non_stream_resp.text
                            # 在fallback情况下也提取usage信息
                            if data_json.get("success"):
                                final_usage_data = data_json
                        if text_out:
                            accumulated_content = text_out
                            chunk = {
                                "id": rid,
                                "object": "chat.completion.chunk",
                                "created": created,
                                "model": model,
                                "choices": [
                                    {"index": 0, "delta": {"content": text_out}, "finish_reason": "stop"}
                                ]
                            }
                            yield openai_stream_chunk(chunk)
                        yield "data: [DONE]\n\n"
                        return

                    # Stream line by line; attempt to parse JSON parts with a "text" field
                    for line in r.iter_lines(decode_unicode=True):
                        if not line:
                            continue
                        # Robustly handle bytes or str, e.g.: line = b'{"type":"text","text":""}'
                        if isinstance(line, (bytes, bytearray)):
                            try:
                                enc = getattr(r, "encoding", None) or "utf-8"
                            except Exception:
                                enc = "utf-8"
                            try:
                                s = line.decode(enc, errors="replace").strip()
                            except Exception:
                                s = line.decode("utf-8", errors="replace").strip()
                            app.logger.debug(f"Decoded bytes line using encoding={enc}")
                        else:
                            s = line.strip()
                        
                        # 添加调试日志
                        app.logger.debug(f"Processing stream line: {repr(s)}")
                        
                        # Some servers send 'data: {...}' lines; normalize
                        if s.startswith("data:"):
                            s = s[5:].strip()
                        
                        # Skip empty lines
                        if not s:
                            continue
                            
                        try:
                            # Try to parse as JSON first
                            part = json.loads(s)
                            # part may be {"type":"text","text":"Hello"} or contain nested structure
                            text_piece = None
                            if isinstance(part, dict):
                                # Puter API 流式响应格式: {"type":"text","text":"content"}
                                if part.get("type") == "text" and "text" in part:
                                    text_piece = part.get("text")
                                # 直接包含text字段的格式
                                elif "text" in part:
                                    text_piece = part.get("text")
                                # 完整响应格式（非流式fallback或最终chunk）
                                elif "result" in part and isinstance(part["result"], dict):
                                    text_piece = part["result"].get("message", {}).get("content")
                                    # 检查是否包含usage信息
                                    if part.get("result", {}).get("usage"):
                                        final_usage_data = part
                            
                            # Only yield if we have meaningful content
                            if text_piece:
                                accumulated_content += text_piece
                                chunk = {
                                    "id": rid,
                                    "object": "chat.completion.chunk",
                                    "created": created,
                                    "model": model,
                                    "choices": [
                                        {"index": 0, "delta": {"content": text_piece}, "finish_reason": None}
                                    ]
                                }
                                yield openai_stream_chunk(chunk)
                        except json.JSONDecodeError:
                            # If not JSON, just forward as text
                            accumulated_content += s
                            chunk = {
                                "id": rid,
                                "object": "chat.completion.chunk",
                                "created": created,
                                "model": model,
                                "choices": [
                                    {"index": 0, "delta": {"content": s}, "finish_reason": None}
                                ]
                            }
                            yield openai_stream_chunk(chunk)
                        except Exception as e:
                            app.logger.warning(f"Error parsing stream chunk: {e}")
                            continue
            except Exception as e:
                # On error, send as a single final chunk with the error message
                app.logger.error(f"Stream error: {str(e)}")
                accumulated_content = f"[proxy error] {str(e)}"
                err_chunk = {
                    "id": rid,
                    "object": "chat.completion.chunk",
                    "created": created,
                    "model": model,
                    "choices": [
                        {"index": 0, "delta": {"content": accumulated_content}, "finish_reason": None}
                    ]
                }
                yield openai_stream_chunk(err_chunk)
            finally:
                # 计算usage信息
                if final_usage_data:
                    # 使用API返回的usage信息
                    usage = extract_usage_from_puter_response(final_usage_data, model, user_text_concat, accumulated_content)
                else:
                    # 使用本地估算
                    usage = extract_usage_from_puter_response({}, model, user_text_concat, accumulated_content)
                
                # Send final chunk to indicate completion with usage info
                final_chunk = {
                    "id": rid,
                    "object": "chat.completion.chunk",
                    "created": created,
                    "model": model,
                    "choices": [
                        {"index": 0, "delta": {}, "finish_reason": "stop"}
                    ],
                    "usage": usage
                }
                yield openai_stream_chunk(final_chunk)
                yield "data: [DONE]\n\n"

        return Response(stream_with_context(generate()), mimetype='text/event-stream')

    # Non-streaming path
    app.logger.info("Processing non-streaming request")
    try:
        app.logger.debug("Sending request to Puter API")
        resp = requests.post(PUTER_API_URL, headers=headers, json=payload, timeout=120, proxies=_PUTER_PROXIES)
    except Exception as e:
        app.logger.error(f"Upstream request failed: {str(e)}")
        return jsonify({"error": {"message": f"Upstream error: {str(e)}"}}), 502

    # 预取响应文本，便于多次使用
    try:
        resp_text = resp.text  # requests 会缓存，后续 resp.json() 仍可用
    except Exception:
        resp_text = ""

    # 精确检测 token 鉴权失败：必须满足 HTTP 401/403 或 JSON error 中出现特定字段
    token_auth_failed = False
    json_error_block = None
    if resp.status_code in (401, 403):
        token_auth_failed = True
    else:
        # 尝试解析 JSON 进一步判断
        try:
            _tmp_json = resp.json()
            json_error_block = _tmp_json.get('error') if isinstance(_tmp_json, dict) else None
            if json_error_block and 'token_auth_failed' in json.dumps(json_error_block):
                token_auth_failed = True
        except Exception:
            # 非 JSON 或解析失败忽略
            pass
    if token_auth_failed:
        rotate_res = handle_token_error_and_rotate('token_auth_failed', api_key, context='chat_completions_non_stream')
        next_tok = rotate_res.get('next_token')
        hint = (next_tok[:8] + '...') if isinstance(next_tok, str) and next_tok else None
        return jsonify({
            "error": {
                "message": "token_auth_failed: 当前Token无效(或未授权)并已尝试切换，请重试",
                "type": "authentication_error",
                "rotated": rotate_res.get('rotated'),
                "next_token_hint": hint,
                "status_code": resp.status_code
            }
        }), 401

    if not resp.ok:
        app.logger.error(f"Upstream returned status {resp.status_code}: {resp_text}")
        return jsonify({"error": {"message": f"Upstream status {resp.status_code}", "details": resp_text}}), 502

    data = resp.json()
    if not data.get("success"):
        app.logger.error(f"Upstream returned error: {data}")
        app.logger.info(f'payload:\n{str(payload)}')
        
        # 检测是否是token用量不足错误，如果是则自动重新注册
        if is_usage_limited_error(data):
            app.logger.warning("🚨 检测到token用量不足错误，执行统一处理与自动注册...")
            handle_token_error_and_rotate('usage_limited', api_key, data, context='chat_completions_non_stream')
            try:
                from utils.config_manager import get_config_manager
                if get_config_manager().get('system.auto_register_enabled'):
                    auto_register_token()
                else:
                    app.logger.info('自动注册已禁用(配置)，跳过自动注册流程')
                    return usage_limited_response(False)
            except Exception as _e:
                app.logger.warning(f'读取自动注册配置失败: {_e}')
                return usage_limited_response(False)
            return usage_limited_response(True)
        
        return jsonify({"error": {"message": "Upstream返回错误", "details": data}}), 502

    message_obj = data.get("result", {}).get("message", {})
    raw_content = message_obj.get("content") or ""
    tool_calls = message_obj.get("tool_calls")
    
    # 处理content字段：支持字符串和字典格式
    assistant_text = ""
    if isinstance(raw_content, str):
        # 直接是字符串格式
        assistant_text = raw_content
        app.logger.debug("Content是字符串格式")
    elif isinstance(raw_content, dict):
        # 字典格式，提取text字段
        if "text" in raw_content:
            assistant_text = raw_content.get("text", "")
            app.logger.debug(f"Content是字典格式，提取text字段: {raw_content}")
        else:
            # 如果没有text字段，将整个字典转为JSON字符串
            assistant_text = json.dumps(raw_content, ensure_ascii=False)
            app.logger.warning(f"Content是字典格式但没有text字段: {raw_content}")
    elif isinstance(raw_content, list):
        # 列表格式，处理多个内容块
        text_parts = []
        for item in raw_content:
            if isinstance(item, dict) and "text" in item:
                text_parts.append(item.get("text", ""))
            elif isinstance(item, str):
                text_parts.append(item)
            else:
                app.logger.warning(f"Content列表中的未知格式项: {item}")
        assistant_text = "".join(text_parts)
        app.logger.debug(f"Content是列表格式，提取了{len(text_parts)}个文本块")
    else:
        assistant_text = str(raw_content) if raw_content is not None else ""
        app.logger.warning(f"Content格式未知，转为字符串: {type(raw_content)}")
    
    # 确保assistant_text是字符串
    if not isinstance(assistant_text, str):
        assistant_text = str(assistant_text)

    app.logger.info(f"Response received, length: {len(assistant_text)} chars")

    # 使用新的usage提取函数，优先使用API返回的token信息
    usage = extract_usage_from_puter_response(data, model, user_text_concat, assistant_text)
    
    app.logger.info(f"非流式响应完成 - Token使用: 提示={usage['prompt_tokens']}, 完成={usage['completion_tokens']}, 总计={usage['total_tokens']}")

    return jsonify(build_openai_chat_response(model, assistant_text, tool_calls, usage))


@app.route("/v1/images/generations", methods=["POST"])
@limit_concurrency()
def image_generation():
    """
    图像生成API (兼容OpenAI DALL-E API)
    
    通过Puter的图像生成接口创建图像，支持多种输出格式。
    
    支持的参数:
    - prompt: 图像描述文本 (必需)
    - n: 生成图像数量 (默认1)
    - size: 图像尺寸 (默认1024x1024)
    - response_format: 返回格式 (url或b64_json)
    
    Returns:
        JSON: OpenAI格式的图像生成响应
    """
    app.logger.info("收到图像生成请求")
    
    # 验证API密钥
    api_key = get_effective_api_key()
    if not api_key:
        app.logger.error("未提供有效的API密钥")
        return jsonify({
            "error": {
                "message": "未提供有效的API密钥。请在Authorization头中提供或设置API_TOKEN环境变量",
                "type": "invalid_request_error"
            }
        }), 401
    
    headers = get_puter_headers(api_key)

    # 解析请求参数
    body = request.get_json(force=True, silent=True) or {}
    prompt = body.get("prompt", "")
    n = body.get("n", 1)  # 生成图像数量
    size = body.get("size", "1024x1024")  # 图像尺寸
    response_format = body.get("response_format", "url")  # 返回格式
    
    app.logger.info(f"图像生成参数 - 提示词: '{prompt[:50]}...', 数量: {n}, 尺寸: {size}, 格式: {response_format}")

    # 验证必需参数
    if not prompt:
        app.logger.warning("图像生成请求中未提供提示词")
        return jsonify({"error": {"message": "prompt字段是必需的"}}), 400

    # 构建Puter API请求载荷
    payload = {
        "interface": "puter-image-generation",
        "test_mode": False,  # 不启用测试模式，确保正常计费
        "method": "generate",
        "args": {
            "prompt": prompt
        }
    }
    
    # 支持自定义图像尺寸
    if size != "1024x1024":
        try:
            width, height = size.split("x")
            payload["args"]["width"] = int(width)
            payload["args"]["height"] = int(height)
            app.logger.debug(f"设置自定义尺寸: {width}x{height}")
        except (ValueError, IndexError):
            app.logger.warning(f"无效的尺寸格式: {size}，使用默认1024x1024")

    try:
        app.logger.debug("向Puter API发送图像生成请求")
        resp = requests.post(PUTER_API_URL, headers=headers, json=payload, timeout=120, proxies=_PUTER_PROXIES)
    except Exception as e:
        app.logger.error(f"图像生成请求失败: {str(e)}")
        return jsonify({"error": {"message": f"上游服务错误: {str(e)}"}}), 502

    if not resp.ok:
        app.logger.error(f"图像生成上游服务返回错误状态 {resp.status_code}: {resp.text}")
        return jsonify({"error": {"message": f"上游服务状态码 {resp.status_code}", "details": resp.text}}), 502

    # 处理Puter API响应
    try:
        if resp.headers.get('content-type', '').startswith('application/json'):
            data = resp.json()
            if not data.get("success"):
                app.logger.error(f"图像生成上游服务返回错误: {data}")
                
                # 检测是否是token用量不足错误，如果是则自动重新注册
                if is_usage_limited_error(data):
                    app.logger.warning("🚨 图像生成检测到token用量不足错误，正在自动重新注册...")
                    
                    # 标记当前Token为无效或用量耗尽
                    current_token = api_key
                    if current_token:
                        handle_token_invalid(current_token, str(data.get('error', {})))

                    try:
                        from utils.config_manager import get_config_manager
                        if get_config_manager().get('system.auto_register_enabled'):
                            auto_register_token()
                        else:
                            app.logger.info('自动注册已禁用(配置)，跳过自动注册流程')
                            return usage_limited_response(False)
                    except Exception as _e:
                        app.logger.warning(f'读取自动注册配置失败: {_e}')
                        return usage_limited_response(False)
                    
                    return usage_limited_response(True)
                
                return jsonify({"error": {"message": "图像生成失败", "details": data}}), 502
            
            # Puter API在result字段中返回base64图像数据
            image_data = data.get("result", resp.text)
        else:
            # 如果直接返回图像二进制数据，转换为base64
            image_data = base64.b64encode(resp.content).decode('utf-8')
            app.logger.debug("将二进制图像数据转换为base64")
    except Exception as e:
        app.logger.error(f"处理图像生成响应时出错: {str(e)}")
        return jsonify({"error": {"message": "响应处理错误"}}), 502

    # 构建OpenAI兼容的响应格式
    images = []
    for i in range(n):
        if response_format == "b64_json":
            images.append({
                "b64_json": image_data
            })
        else:  # url格式
            # 返回data URL格式 (在实际生产中可能需要将图片保存到文件服务器)
            images.append({
                "url": f"data:image/png;base64,{image_data}"
            })

    app.logger.info(f"图像生成完成，返回 {len(images)} 张图像")
    return jsonify({
        "created": int(time.time()),
        "data": images
    })



@app.route("/v1/audio/speech", methods=["POST"])
@limit_concurrency()
def text_to_speech():
    """
    文本转语音API (兼容OpenAI TTS API)
    
    通过Puter的AWS Polly TTS服务将文本转换为语音。
    支持多种声音、语速控制和音频格式。
    
    支持的参数:
    - model: TTS模型 (tts-1或tts-1-hd)
    - input: 要合成的文本 (必需)
    - voice: 声音类型 (alloy, echo, fable, onyx, nova, shimmer)
    - response_format: 音频格式 (mp3, opus, aac, flac)
    - speed: 语速 (0.25-4.0，默认1.0)
    
    Returns:
        音频文件的二进制数据
    """
    app.logger.info("收到文本转语音请求")
    
    # 验证API密钥
    api_key = get_effective_api_key()
    if not api_key:
        app.logger.error("未提供有效的API密钥")
        return jsonify({
            "error": {
                "message": "未提供有效的API密钥。请在Authorization头中提供或设置API_TOKEN环境变量",
                "type": "invalid_request_error"
            }
        }), 401
    
    headers = get_puter_headers(api_key)

    # 解析请求参数
    body = request.get_json(force=True, silent=True) or {}
    model = body.get("model", "tts-1")  # OpenAI支持tts-1和tts-1-hd
    input_text = body.get("input", "")
    voice = body.get("voice", "alloy")  # OpenAI默认声音
    response_format = body.get("response_format", "mp3")  # 音频格式
    speed = body.get("speed", 1.0)  # 语速控制 (0.25-4.0)
    
    app.logger.info(f"TTS参数 - 文本: '{input_text[:50]}...', 声音: {voice}, 格式: {response_format}, 语速: {speed}")

    # 验证必需参数
    if not input_text:
        app.logger.warning("TTS请求中未提供输入文本")
        return jsonify({"error": {"message": "input字段是必需的"}}), 400

    # 将OpenAI声音映射到AWS Polly声音
    puter_voice = TTS_VOICE_MAPPING.get(voice, "Joanna")
    app.logger.debug(f"声音映射: {voice} -> {puter_voice}")
    
    # 根据模型选择TTS引擎质量
    engine = "neural" if model == "tts-1-hd" else "standard"
    app.logger.debug(f"TTS引擎: {engine} (基于模型: {model})")
    
    # 构建Puter API请求载荷
    payload = {
        "interface": "puter-tts",
        "driver": "aws-polly",
        "test_mode": False,  # 不启用测试模式，确保正常计费
        "method": "synthesize",
        "args": {
            "text": input_text,
            "voice": puter_voice,
            "engine": engine,
            "language": "en-US"  # 可以根据需要扩展多语言支持
        }
    }
    
    # 支持语速控制 (通过SSML实现)
    if speed != 1.0:
        # AWS Polly使用SSML来控制语速
        ssml_text = f'<speak><prosody rate="{int(speed * 100)}%">{input_text}</prosody></speak>'
        payload["args"]["text"] = ssml_text
        app.logger.debug(f"应用语速控制: {speed}x -> {int(speed * 100)}%")

    try:
        app.logger.debug("向Puter API发送TTS请求")
        resp = requests.post(PUTER_API_URL, headers=headers, json=payload, timeout=120, proxies=_PUTER_PROXIES)
    except Exception as e:
        app.logger.error(f"TTS请求失败: {str(e)}")
        return jsonify({"error": {"message": f"上游服务错误: {str(e)}"}}), 502

    if not resp.ok:
        app.logger.error(f"TTS上游服务返回错误状态 {resp.status_code}: {resp.text}")
        
        # 尝试解析JSON错误响应，检查是否是token用量不足
        try:
            if resp.headers.get('content-type', '').startswith('application/json'):
                error_data = resp.json()
                if is_usage_limited_error(error_data):
                    app.logger.warning("🚨 TTS检测到token用量不足错误，正在自动重新注册...")
                    
                    # 标记当前Token为无效或用量耗尽
                    current_token = api_key
                    if current_token:
                        handle_token_invalid(current_token, str(error_data.get('error', {})))
                    
                    try:
                        from utils.config_manager import get_config_manager
                        if get_config_manager().get('system.auto_register_enabled'):
                            auto_register_token()
                        else:
                            app.logger.info('自动注册已禁用(配置)，跳过自动注册流程')
                            return usage_limited_response(False)
                    except Exception as _e:
                        app.logger.warning(f'读取自动注册配置失败: {_e}')
                        return usage_limited_response(False)
                
                    return usage_limited_response(True)
        except:
            pass  # 如果解析失败，继续使用原有错误处理
        
        return jsonify({"error": {"message": f"上游服务状态码 {resp.status_code}", "details": resp.text}}), 502

    # Puter返回语音二进制数据，直接返回给客户端
    content_type = AUDIO_CONTENT_TYPE_MAPPING.get(response_format, "audio/mpeg")
    
    app.logger.info(f"TTS合成完成，生成 {len(resp.content)} 字节的 {response_format} 音频")
    
    return Response(
        resp.content,
        mimetype=content_type,
        headers={
            "Content-Disposition": f"attachment; filename=speech.{response_format}"
        }
    )


@app.route("/health", methods=["GET"])
def health():
    """
    健康检查端点
    
    用于监控服务器状态和可用性。
    
    Returns:
        JSON: 包含状态和时间戳的响应
    """
    app.logger.info("收到健康检查请求")
    return jsonify({
        "status": "ok", 
        "timestamp": int(time.time()),
        "version": "1.0.0",
        "service": "PuterAI OpenAI Proxy"
    })


@app.route("/v1/stats", methods=["GET"])
def get_stats():
    """
    获取服务器统计信息端点
    
    返回当前并发状态、可用资源等信息
    
    Returns:
        JSON: 包含服务器统计信息的响应
    """
    current_concurrent = MAX_CONCURRENT_REQUESTS - request_semaphore._value
    available_slots = request_semaphore._value
    
    app.logger.info(f"收到统计信息请求 - 当前并发: {current_concurrent}/{MAX_CONCURRENT_REQUESTS}")
    
    return jsonify({
        "status": "ok",
        "timestamp": int(time.time()),
        "concurrency": {
            "max_concurrent_requests": MAX_CONCURRENT_REQUESTS,
            "current_concurrent_requests": current_concurrent,
            "available_slots": available_slots,
            "usage_percentage": round((current_concurrent / MAX_CONCURRENT_REQUESTS) * 100, 2)
        },
        "service_info": {
            "name": "PuterAI OpenAI Proxy",
            "version": "1.0.0"
        }
    })


@app.route("/v1/admin/auto-register/enable", methods=["POST"])
@limit_concurrency()
def enable_auto_register_endpoint():
    """
    重新启用自动注册功能的管理端点
    
    当用户更换网络环境或IP地址后，可以调用此端点重新启用自动注册功能
    
    Returns:
        JSON: 操作结果
    """
    enable_auto_register()
    
    return jsonify({
        "message": "自动注册功能已重新启用",
        "auto_register_enabled": True,
        "timestamp": int(time.time())
    })


@app.route("/v1/admin/auto-register/status", methods=["GET"])
@limit_concurrency()
def auto_register_status():
    """
    查看自动注册功能状态
    
    Returns:
        JSON: 自动注册功能的状态信息
    """    
    return jsonify({
        "auto_register_disabled": is_auto_register_disabled(),
        "auto_register_in_progress": _auto_register_in_progress,
        "message": "禁用原因：IP被限制注册" if is_auto_register_disabled() else "自动注册功能正常",
        "timestamp": int(time.time())
    })


# 手动触发重新加载本地的配置文件
@app.route("/v1/admin/reload-config", methods=["GET"])
@limit_concurrency()
def reload_config_endpoint():
    """
    重新加载本地配置文件的管理端点
    
    Returns:
        JSON: 操作结果
    """
    global _PUTER_PROXIES
    app.logger.info("收到重新加载配置文件请求")
    try:
        from utils.config_manager import get_config_manager
        config_manager = get_config_manager()
        config_manager.load_config()  # 重新加载配置文件

        from utils.token_manager import get_token_manager
        token_manager = get_token_manager()
        token_manager.load_token_pool()  # 重新加载Token池

        if _PUTER_PROXIES:
            _PUTER_PROXIES = get_puter_proxies()
        else:
            app.logger.info("当前未配置代理，无需重新加载代理设置")
        app.logger.info("本地配置文件重新加载成功")
        return jsonify({
            "message": "本地配置文件重新加载成功",
            "timestamp": int(time.time())
        })
    except Exception as e:
        app.logger.error(f"重新加载配置文件失败: {str(e)}")
        return jsonify({
            "error": {
                "message": f"重新加载配置文件失败: {str(e)}",
                "type": "internal_error"
            }
        }), 500

# ====== 服务器启动部分 ======

if __name__ == "__main__":
    # 确保.env文件存在
    ensure_env_file_exists()
    
    app.logger.info("="*60)
    app.logger.info("🚀 启动PuterAI OpenAI兼容代理服务器")
    app.logger.info("="*60)
    app.logger.info(f"📍 服务地址: http://0.0.0.0:9595")
    app.logger.info(f"📚 API文档: https://platform.openai.com/docs/api-reference")
    app.logger.info(f"🔑 API密钥配置:")
    app.logger.info(f"   方式1: Authorization头 (推荐生产环境)")
    app.logger.info(f"   方式2: 环境变量API_TOKEN (推荐开发环境)")
    app.logger.info(f"⚡ 并发控制: 最大同时处理 {MAX_CONCURRENT_REQUESTS} 个请求")
    app.logger.info(f"📊 监控端点: GET /v1/stats (查看实时并发状态)")
    app.logger.info(f"💡 自动注册: 检测到token用量不足时将自动重新注册")
    app.logger.info(f"🛠️  管理端点: POST /v1/admin/auto-register/enable (重新启用自动注册)")
    app.logger.info(f"📋 状态查看: GET /v1/admin/auto-register/status (查看自动注册状态)")
    app.logger.info("="*60)
    
    # 启动服务器 (禁用reloader以避免与debugpy冲突)
    app.run(
        host="0.0.0.0", 
        port=9595, 
        debug=True, 
        use_reloader=False
    )
