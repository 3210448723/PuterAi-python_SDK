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
from flask import Flask, request, jsonify, Response, stream_with_context
from flask_cors import CORS
from dotenv import load_dotenv
from logging.handlers import RotatingFileHandler

# 加载环境变量 (期望在环境变量或.env文件中设置API_TOKEN)
load_dotenv()

# 创建Flask应用实例
app = Flask(__name__)
CORS(app)  # 启用跨域资源共享

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
        '%(asctime)s [%(levelname)s] %(message)s (%(pathname)s:%(lineno)d)'
    ))
    file_handler.setLevel(logging.INFO)

    # 配置控制台日志处理器
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(
        '%(asctime)s [%(levelname)s] %(message)s'
    ))
    console_handler.setLevel(logging.INFO)

    # 将处理器添加到应用日志器
    app.logger.addHandler(file_handler)
    app.logger.addHandler(console_handler)
    app.logger.setLevel(logging.INFO)

    # 降低Flask内置日志级别，减少噪音
    logging.getLogger('werkzeug').setLevel(logging.WARNING)
    
    app.logger.info("日志系统初始化完成")

# 初始化日志系统
setup_logging()

# ====== 常量配置部分 ======

# Puter API配置
PUTER_API_URL = "https://api.puter.com/drivers/call"
PUTER_MODELS_URL = "https://puter.com/puterai/chat/models"

# 默认请求头配置 (模拟真实浏览器请求)
PUTER_HEADERS_TEMPLATE = {
    'Accept': '*/*',
    'Content-Type': 'application/json;charset=UTF-8',
    'Origin': 'https://docs.puter.com',
    'Referer': 'https://docs.puter.com/',
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

app.logger.info("常量配置加载完成")

# ====== 工具函数部分 ======

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


def get_effective_api_key():
    """
    获取有效的API密钥
    
    系统支持两种API密钥配置方式：
    1. 请求头Authorization (优先级更高): Bearer your-api-key
    2. 环境变量API_TOKEN (回退方案)
    
    Returns:
        str: 有效的API密钥
        
    Note:
        请求头中的API密钥长度必须大于8字符才被认为是有效的
    """
    # 方式1: 从请求头获取API密钥
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        request_api_key = auth_header[7:].strip()  # 移除 'Bearer ' 前缀
        if len(request_api_key) > 8:  # 只接受长度大于8的密钥
            app.logger.debug("使用请求头中的API密钥")
            return request_api_key
        else:
            app.logger.debug("请求头中的API密钥长度不足，忽略")
    
    # 方式2: 回退到环境变量
    env_api_key = os.getenv('API_TOKEN', '')
    if env_api_key:
        app.logger.debug("使用环境变量中的API密钥")
        return env_api_key
    
    app.logger.warning("未找到有效的API密钥")
    return ''


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


# ====== API端点实现部分 ======

@app.route("/v1/models", methods=["GET"])
def list_models():
    """
    获取可用模型列表 (兼容OpenAI Models API)
    
    首先尝试从Puter API动态获取最新模型列表，
    如果失败则使用内置的静态模型列表作为回退。
    todo: 可能包含不可用的模型，如：claude-3-haiku-20240307、arcee_ai/arcee-spotlight、meta-llama/Meta-Llama-3.1-405B-Instruct-Turbo等，建议选择热门模型使用
    
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
        response = requests.get(PUTER_MODELS_URL, headers=headers, timeout=30)
        if response.status_code == 200:
            models_data = response.json()
            for model in models_data.get("models", []):
                # 如果是字典类型对象，核对是否符合openai模型格式
                if isinstance(model, dict):
                    data.append({
                        "id": model["id"] if "id" in model else model.get("name", ""),
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
        app.logger.error(f"从Puter API获取模型列表失败: {str(e)}")

    # 回退到静态模型列表
    app.logger.warning("使用静态模型列表作为回退")
    for model_name in PUTER_MODELS_FALLBACK:
        data.append({
            "id": model_name,
            "object": "model",
            "created": now,
            "owned_by": "puter",
        })
    app.logger.info(f"返回 {len(data)} 个静态模型")
    return jsonify({"object": "list", "data": data})


@app.route("/v1/chat/completions", methods=["POST"])
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
                with requests.post(PUTER_API_URL, headers=headers, json=payload_stream, stream=True, timeout=30) as r:
                    if r.status_code != 200:
                        app.logger.warning(f"Stream request failed with status {r.status_code}, falling back to non-stream")
                        # Fallback: non-stream request
                        non_stream_resp = requests.post(PUTER_API_URL, headers=headers, json=payload, timeout=120)
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
        resp = requests.post(PUTER_API_URL, headers=headers, json=payload, timeout=120)
    except Exception as e:
        app.logger.error(f"Upstream request failed: {str(e)}")
        return jsonify({"error": {"message": f"Upstream error: {str(e)}"}}), 502

    if not resp.ok:
        app.logger.error(f"Upstream returned status {resp.status_code}: {resp.text}")
        return jsonify({"error": {"message": f"Upstream status {resp.status_code}", "details": resp.text}}), 502

    data = resp.json()
    if not data.get("success"):
        app.logger.error(f"Upstream returned error: {data}")
        return jsonify({"error": {"message": "Upstream returned error", "details": data}}), 502

    message_obj = data.get("result", {}).get("message", {})
    assistant_text = message_obj.get("content") or ""
    tool_calls = message_obj.get("tool_calls")

    app.logger.info(f"Response received, length: {len(assistant_text)} chars")

    # 使用新的usage提取函数，优先使用API返回的token信息
    usage = extract_usage_from_puter_response(data, model, user_text_concat, assistant_text)
    
    app.logger.info(f"非流式响应完成 - Token使用: 提示={usage['prompt_tokens']}, 完成={usage['completion_tokens']}, 总计={usage['total_tokens']}")

    return jsonify(build_openai_chat_response(model, assistant_text, tool_calls, usage))


@app.route("/v1/images/generations", methods=["POST"])
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
        resp = requests.post(PUTER_API_URL, headers=headers, json=payload, timeout=120)
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
        resp = requests.post(PUTER_API_URL, headers=headers, json=payload, timeout=120)
    except Exception as e:
        app.logger.error(f"TTS请求失败: {str(e)}")
        return jsonify({"error": {"message": f"上游服务错误: {str(e)}"}}), 502

    if not resp.ok:
        app.logger.error(f"TTS上游服务返回错误状态 {resp.status_code}: {resp.text}")
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


# ====== 服务器启动部分 ======

if __name__ == "__main__":
    app.logger.info("="*60)
    app.logger.info("🚀 启动PuterAI OpenAI兼容代理服务器")
    app.logger.info("="*60)
    app.logger.info(f"📍 服务地址: http://0.0.0.0:9595")
    app.logger.info(f"📚 API文档: https://platform.openai.com/docs/api-reference")
    app.logger.info(f"🔑 API密钥配置:")
    app.logger.info(f"   方式1: Authorization头 (推荐生产环境)")
    app.logger.info(f"   方式2: 环境变量API_TOKEN (推荐开发环境)")
    app.logger.info("="*60)
    
    # 启动服务器 (禁用reloader以避免与debugpy冲突)
    app.run(
        host="0.0.0.0", 
        port=9595, 
        debug=True, 
        use_reloader=False
    )
