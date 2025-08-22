# 自动Token注册功能

## 功能概述

当PuterAI API返回token用量不足的错误时，系统会自动在后台重新注册获取新的token，无需手动干预。

## 支持的错误类型

系统会检测以下类型的用量限制错误：

```json
{
  "success": false,
  "error": {
    "delegate": "usage-limited-chat",
    "message": "Error 400 from delegate `usage-limited-chat`: Permission denied.",
    "code": "error_400_from_delegate",
    "$": "heyputer:api/APIError",
    "status": 400
  }
}
```

## 工作原理

1. **错误检测**: 当API调用返回用量限制错误时，系统自动检测到特定的错误模式
2. **后台注册**: 启动独立的后台线程执行注册流程，不会阻塞当前API响应
3. **token更新**: 注册成功后自动更新.env文件中的API_TOKEN
4. **环境重载**: 重新加载环境变量，新token立即生效

## 影响的API端点

- `/v1/chat/completions` - 聊天对话API
- `/v1/images/generations` - 图像生成API  
- `/v1/audio/speech` - 文本转语音API

## 用户体验

当遇到token用量不足时：

1. **立即响应**: 用户会收到状态码429和明确的错误消息：
   ```json
   {
     "error": {
       "message": "Token用量不足，正在后台自动重新注册。请稍后重试。",
       "type": "usage_limited_error", 
       "details": "系统已自动启动token更新流程，请等待1-2分钟后重新发送请求。",
       "auto_register": true
     }
   }
   ```

2. **后台处理**: 系统在后台自动执行注册流程（约1-2分钟）

3. **重试请求**: 1-2分钟后用户重新发送相同请求即可正常使用

## 日志监控

系统会输出详细的日志信息方便监控：

```
🚨 检测到token用量不足错误，正在自动重新注册...
🔄 已启动后台注册线程
🚀 正在执行注册脚本: /path/to/register.py
✅ 自动注册成功完成
🔄 已重新加载环境变量
```

## 环境要求

- Python 3.7+
- playwright库 (用于自动注册)
- 网络连接到puter.com

## 配置文件

系统会自动确保`.env`文件存在：

```env
# PuterAI API Token
API_TOKEN="your_token_here"
```

## 故障排除

### 注册失败的常见原因：

1. **网络问题**: 无法访问puter.com
2. **依赖缺失**: playwright未安装或浏览器未下载
3. **超时**: 注册过程超过2分钟超时限制

### 解决方法：

1. 检查网络连接
2. 确保安装所有依赖：`pip install -r requirements.txt`
3. 手动运行注册脚本：`python register.py`

## 安全说明

- 注册过程完全自动化，不需要真实的用户信息
- 每次注册都会生成新的临时账户和token
- 旧token会被新token替换，符合Puter.com的使用政策

## 测试

运行测试脚本验证功能：

```bash
python test_auto_register.py
```

这将测试：
- 错误检测逻辑
- .env文件创建
- 注册功能准备就绪状态
