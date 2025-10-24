from typing import Any, Dict, List, Tuple, Optional
import pprint

# 可接受的 role 集合（根据你所用的实现可以增删）
VALID_ROLES = {"system", "user", "assistant", "tool"}

# 支持的结构化 content type
VALID_CONTENT_TYPES = {"text", "image_url", "file"}

def validate_messages(
    messages: Any,
    *,
    require_nonempty: bool = True,
    max_text_length: Optional[int] = None,
    allow_suggestions: bool = True,
    auto_remove_none_content: bool = True,
) -> Tuple[bool, List[str], List[str]]:
    """
    校验 messages（应为 list of dict）。
    返回 (is_valid, errors, suggestions)。

    errors: 列表，包含每一项错误的详细说明（索引、字段、期望、实际）。
    suggestions: 列表，包含自动修复建议或格式化建议（不会直接修改输入）。
    """
    errors: List[str] = []
    suggestions: List[str] = []

    # 基本类型检查
    if not isinstance(messages, list):
        errors.append(f"messages 类型错误：期望 list，但收到 {type(messages).__name__}")
        return False, errors, suggestions

    if require_nonempty and len(messages) == 0:
        errors.append("messages 为空列表 (length == 0)。至少需要一条消息。")
        return False, errors, suggestions

    # 在正式校验前，按需移除 content 为 None 的消息（就地修改，保留引用）
    if auto_remove_none_content:
        removed_indices: List[int] = []
        if isinstance(messages, list):
            filtered: List[Any] = []
            for idx, msg in enumerate(messages):
                if isinstance(msg, dict):
                    content_is_none = msg.get("content", "__MISSING__") is None
                    role = msg.get("role")
                    has_tool_calls = "tool_calls" in msg

                    # 不要移除：
                    # - role == assistant 且存在 tool_calls（常见于函数调用返回，content 可为 None）
                    # - role == tool（需要在后续校验中给出明确错误，而不是静默移除）
                    if content_is_none and not (
                        (role == "assistant" and has_tool_calls) or (role == "tool")
                    ):
                        removed_indices.append(idx)
                    else:
                        filtered.append(msg)
                else:
                    filtered.append(msg)
            if removed_indices:
                # 原地替换，保持调用方引用不变
                messages[:] = filtered
                if allow_suggestions:
                    suggestions.append(
                        f"已自动移除 {len(removed_indices)} 条 content 为 None 的消息，原索引：{removed_indices}"
                    )

        # 若移除后为空且需要非空，补充错误
        if require_nonempty and len(messages) == 0:
            errors.append("移除 content 为 None 的消息后，messages 为空。至少需要一条有效消息。")
            return False, errors, suggestions

    for i, m in enumerate(messages):
        path_prefix = f"messages[{i}]"

        # 每条 message 必须是 dict
        if not isinstance(m, dict):
            errors.append(f"{path_prefix} 类型错误：期望 dict，但收到 {type(m).__name__}")
            suggestions.append(f"将 {path_prefix} 转为 dict，例如: {{'role': 'user', 'content': '...'}}")
            # 继续检查下一条
            continue

        # role 字段校验
        if "role" not in m:
            errors.append(f"{path_prefix} 缺少 'role' 字段。必须包含 role，取值之一：{sorted(VALID_ROLES)}")
        else:
            role = m["role"]
            if not isinstance(role, str):
                errors.append(f"{path_prefix}.role 类型错误：期望 str，但收到 {type(role).__name__}")
            elif role not in VALID_ROLES:
                errors.append(f"{path_prefix}.role 值错误：收到 '{role}'，期望其中之一：{sorted(VALID_ROLES)}")
                suggestions.append(f"将 {path_prefix}.role 修改为合法值之一，例如 'user' 或 'system'。")

        # 若声明了 tool_call_id，但 role 不是 tool，则给出错误
        if isinstance(m, dict) and "role" in m and m.get("role") != "tool" and "tool_call_id" in m:
            errors.append(f"{path_prefix} 包含 'tool_call_id'，但 role='{m.get('role')}'。'tool_call_id' 仅允许出现在 role='tool' 的消息中。")
            if allow_suggestions:
                suggestions.append(f"从 {path_prefix} 移除 'tool_call_id'，或将 role 改为 'tool' 并补充相应字段。")

        # content 字段存在性校验（特殊情况：assistant + tool_calls 可允许无 content 或 content=None）
        has_tool_calls = isinstance(m, dict) and ("tool_calls" in m)
        role_val = m.get("role") if isinstance(m, dict) else None
        if "content" not in m:
            if role_val == "assistant" and has_tool_calls:
                content = None  # 允许缺失
            else:
                errors.append(f"{path_prefix} 缺少 'content' 字段。每条消息必须包含 content。")
                suggestions.append(f"为 {path_prefix} 添加 'content' 字段，例如 'content': '你好' 或 'content': [{{'type':'text','text':'...'}}]")
                # 缺失 content 且不是 assistant tool_calls 情况 -> 下一个
                continue
        else:
            content = m["content"]

        # role 为 tool 的专属校验
        if role_val == "tool":
            if "tool_call_id" not in m:
                errors.append(f"{path_prefix} (role='tool') 缺少必要字段 'tool_call_id'。")
                if allow_suggestions:
                    suggestions.append(f"为 {path_prefix} 添加 'tool_call_id': '<assistant.tool_calls[*].id>'，用于关联调用。")
            else:
                tci = m.get("tool_call_id")
                if not isinstance(tci, str) or tci.strip() == "":
                    errors.append(f"{path_prefix}.tool_call_id 类型/值错误：期望非空字符串。")
            if "tool_calls" in m:
                errors.append(f"{path_prefix} (role='tool') 不应包含 'tool_calls' 字段。")
                if allow_suggestions:
                    suggestions.append(f"从 {path_prefix} 移除 'tool_calls'，仅在 role='assistant' 时由模型给出。")

        # role 为 assistant 且存在 tool_calls 的结构校验
        if role_val == "assistant" and has_tool_calls:
            tc_val = m.get("tool_calls")
            if not isinstance(tc_val, list):
                errors.append(f"{path_prefix}.tool_calls 类型错误：期望 list，但收到 {type(tc_val).__name__}")
            elif len(tc_val) == 0:
                errors.append(f"{path_prefix}.tool_calls 是空列表。应至少包含一个调用项。")
            else:
                for k, call in enumerate(tc_val):
                    cpath = f"{path_prefix}.tool_calls[{k}]"
                    if not isinstance(call, dict):
                        errors.append(f"{cpath} 类型错误：期望 dict，但收到 {type(call).__name__}")
                        continue
                    # id 校验
                    cid = call.get("id")
                    if not isinstance(cid, str) or cid.strip() == "":
                        errors.append(f"{cpath}.id 缺失或非法，期望非空字符串。")
                    # type 校验
                    ctype = call.get("type")
                    if ctype != "function":
                        errors.append(f"{cpath}.type 值错误：收到 '{ctype}'，期望 'function'。")
                    # function 结构
                    fn = call.get("function")
                    if not isinstance(fn, dict):
                        errors.append(f"{cpath}.function 类型错误：期望 dict，但收到 {type(fn).__name__}")
                    else:
                        fname = fn.get("name")
                        if not isinstance(fname, str) or fname.strip() == "":
                            errors.append(f"{cpath}.function.name 缺失或非法，期望非空字符串。")
                        fargs = fn.get("arguments")
                        if not (isinstance(fargs, str) or isinstance(fargs, dict)):
                            errors.append(f"{cpath}.function.arguments 类型错误：期望 str 或 dict，但收到 {type(fargs).__name__}")

            # 在 assistant + tool_calls 情形下，允许 content 为 None 或空串，不再对 content 做严格校验
            # 直接跳过后续 content 细分校验
            # 若同时提供非空 content 与 tool_calls，给出提示但不报错
            if allow_suggestions and isinstance(content, str) and content.strip() != "":
                suggestions.append(f"{path_prefix} 同时包含非空 content 与 tool_calls；通常在函数调用阶段 content 可为空，仅供提示无需修改。")
            # 继续校验下一条消息
            continue

        # content 为字符串（最简单且合法）
        if isinstance(content, str):
            if content.strip() == "":
                errors.append(f"{path_prefix}.content 是空字符串（只含空白）。")
                suggestions.append(f"为 {path_prefix}.content 提供非空字符串，或使用结构化列表表示多段内容。")
            else:
                if max_text_length is not None and len(content) > max_text_length:
                    errors.append(f"{path_prefix}.content 长度 {len(content)} 超过限制 {max_text_length}。")
                    suggestions.append(f"将 {path_prefix}.content 截断或改为分段结构化内容。")
            # 字符串通过基本校验
            continue

        # content 也可以是结构化列表
        if isinstance(content, list):
            if len(content) == 0:
                errors.append(f"{path_prefix}.content 是空列表。若使用结构化 content，列表至少包含一项。")
                suggestions.append(f"将 {path_prefix}.content 填充为一个或多个结构化项，例如 {{'type':'text','text':'...'}}")
                continue

            for j, item in enumerate(content):
                item_path = f"{path_prefix}.content[{j}]"

                # 每个项应为 dict
                if not isinstance(item, dict):
                    errors.append(f"{item_path} 类型错误：期望 dict，但收到 {type(item).__name__}")
                    suggestions.append(f"将 {item_path} 修改为像 {{'type':'text','text':'...'}} 的 dict")
                    continue

                # 必须有 type 字段
                if "type" not in item:
                    errors.append(f"{item_path} 缺少 'type' 字段（必要）。")
                    suggestions.append(f"添加 {item_path}['type']，例如 'text' 或 'image_url'。")
                    continue

                itype = item["type"]
                if not isinstance(itype, str):
                    errors.append(f"{item_path}.type 类型错误：期望 str，但收到 {type(itype).__name__}")
                    continue

                if itype not in VALID_CONTENT_TYPES:
                    errors.append(f"{item_path}.type 值错误：收到 '{itype}'，支持的 type 列表为 {sorted(VALID_CONTENT_TYPES)}")
                    suggestions.append(f"将 {item_path}.type 改为支持的类型，例如 'text'。")
                    continue

                # 针对每种 type 的具体字段检查
                if itype == "text":
                    if "text" not in item:
                        errors.append(f"{item_path} (type='text') 缺少 'text' 字段。")
                        suggestions.append(f"添加 {item_path}['text']，并确保其为非空字符串。")
                        continue
                    text_val = item["text"]
                    if not isinstance(text_val, str):
                        errors.append(f"{item_path}.text 类型错误：期望 str，但收到 {type(text_val).__name__}")
                    elif text_val.strip() == "":
                        errors.append(f"{item_path}.text 是空字符串（只含空白）。")
                    else:
                        if max_text_length is not None and len(text_val) > max_text_length:
                            errors.append(f"{item_path}.text 长度 {len(text_val)} 超过限制 {max_text_length}。")
                            suggestions.append(f"将 {item_path}.text 截断或拆分成多段结构化 content。")

                elif itype == "image_url":
                    # 允许 image_url 字段为字符串 URL 或 dict 包含 url
                    if "image_url" not in item and "url" not in item:
                        errors.append(f"{item_path} (type='image_url') 缺少 'image_url' 或 'url' 字段。")
                        suggestions.append(f"使用 {item_path}['image_url'] = {{'url': 'https://...'}} 或 {item_path}['image_url'] = 'https://...'")
                        continue

                    url_val = item.get("image_url", item.get("url"))
                    if isinstance(url_val, dict):
                        # 如果是 dict，要求内部包含 url 字段
                        if "url" not in url_val:
                            errors.append(f"{item_path}.image_url (dict) 缺少 'url' 字段。")
                            continue
                        if not isinstance(url_val["url"], str) or url_val["url"].strip() == "":
                            errors.append(f"{item_path}.image_url.url 必须为非空字符串 URL。")
                    elif isinstance(url_val, str):
                        if url_val.strip() == "":
                            errors.append(f"{item_path} 中提供的 image_url 是空字符串。")
                        # 可选：对 URL 格式进行弱校验（看起来像 URL）
                        elif not (url_val.startswith("http://") or url_val.startswith("https://")):
                            suggestions.append(f"{item_path}.image_url 不是以 http(s) 开头的 URL（建议以 http:// 或 https:// 开头）。")
                    else:
                        errors.append(f"{item_path}.image_url 类型错误：期望 str 或 dict，但收到 {type(url_val).__name__}")

                elif itype == "file":
                    # file 类型举例，仅做基本检查（可根据实际扩展）
                    if "file_id" not in item and "path" not in item:
                        errors.append(f"{item_path} (type='file') 缺少 'file_id' 或 'path' 字段。")
                        suggestions.append(f"为 {item_path} 添加 'file_id' 或 'path' 指向上传的文件。")
                    else:
                        # 不深入校验文件
                        pass

        else:
            # content 既不是 str 也不是 list -> 错误
            errors.append(
                f"{path_prefix}.content 类型错误：期望 str 或 list（结构化内容），但收到 {type(content).__name__}"
            )
            suggestions.append(f"将 {path_prefix}.content 改为字符串或结构化列表，例如 'content': '你好' 或 'content': [{{'type':'text','text':'...'}}]")

    is_valid = len(errors) == 0
    return is_valid, errors, suggestions


# ---------- 演示 / 单元测试样例 ----------
if __name__ == "__main__":
    examples = [
        # 正确示例：简单字符串
        [{"role": "user", "content": "你好"}],

        # 正确示例：结构化
        [{"role": "system", "content": [{"type": "text", "text": "System instruction"}]},
         {"role": "user", "content": [{"type": "text", "text": "Hello"}, {"type": "image_url", "image_url": "https://x.com/img.png"}]}],

        # 错误示例：缺少 content
        [{"role": "user"}],

        # 错误示例：content 项缺 type 或 text
        [{"role": "user", "content": [{"text": "no type field"}]}],

        # 错误示例：content 非法类型
        [{"role": "user", "content": 123}],

        # 错误示例：role 非法值
        [{"role": "unknown", "content": "hi"}],

        # 修复示例：content 为 None，会被自动移除
        [{"role": "user", "content": None}, {"role": "assistant", "content": "ok"}]
    ]

    for idx, ex in enumerate(examples):
        print("\n" + "=" * 60)
        print(f"示例 #{idx+1}: 输入:")
        pprint.pprint(ex, width=120)
        valid, errs, sugs = validate_messages(ex, max_text_length=100)
        print(f"\n结果: valid={valid}")
        if errs:
            print("\n错误列表:")
            for e in errs:
                print(" -", e)
        if sugs:
            print("\n建议:")
            for s in sugs:
                print(" -", s)
