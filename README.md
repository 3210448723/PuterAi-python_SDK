# PuterAI OpenAI Proxy

一个将[Puter.js AI API](https://docs.puter.com/AI/)包装成OpenAI Python SDK兼容接口的代理服务器。免费访问400+种AI模型，包括GPT-4、Claude、Gemini等。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

## ✨ 功能特性

- **🤖 聊天对话**: 支持400+ AI模型（GPT-4、Claude、Gemini等）
- **🖼️ 图像生成**: DALL-E兼容的图像生成功能  
- **🔊 文本转语音**: 多语言TTS合成（兼容OpenAI TTS API）
- **👁️ 图像理解**: 视觉理解和OCR（兼容OpenAI Vision API）
- **⚡ 流式传输**: 实时流式响应支持
- **🔧 函数调用**: Tool Calling/Function Calling支持
- **🌐 OpenAI兼容**: 完全兼容OpenAI Python SDK接口

## � 快速开始

### 1. 安装依赖
```bash
pip install -r requirements.txt
```

### 2. 配置API密钥
```bash
# 方式1: 环境变量（推荐开发环境）
export API_TOKEN="your_puter_api_token"

# 方式2: 创建.env文件
echo "API_TOKEN=your_puter_api_token" > .env
```

### 3. 启动服务器
```bash
python API/openai_server.py
```

服务器将在 `http://localhost:9595` 启动

### 4. 使用OpenAI SDK
```python
import openai

# 配置客户端
client = openai.OpenAI(
    api_key="your_puter_api_token",  # 或任意字符串
    base_url="http://localhost:9595/v1"
)

# 聊天对话
response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "Hello!"}]
)
print(response.choices[0].message.content)

# 图像生成
response = client.images.generate(
    prompt="一只可爱的猫咪",
    size="1024x1024"
)
print(response.data[0].url)

# 文本转语音
response = client.audio.speech.create(
    model="tts-1",
    voice="alloy",
    input="Hello world!"
)
with open("speech.mp3", "wb") as f:
    f.write(response.content)

# 图像理解
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{
        "role": "user", 
        "content": [
            "描述这张图片",
            {"image_url": {"url": "https://example.com/image.jpg"}}
        ]
    }]
```

## 📋 支持的API

| API端点 | 功能 | 兼容性 |
|---------|------|--------|
| `/v1/chat/completions` | 聊天对话、图像理解、函数调用 | ✅ OpenAI ChatGPT |
| `/v1/images/generations` | 图像生成 | ✅ OpenAI DALL-E |
| `/v1/audio/speech` | 文本转语音 | ✅ OpenAI TTS |
| `/v1/models` | 模型列表 | ✅ OpenAI Models |
| `/health` | 健康检查 | - |

## 🔧 配置选项

### 环境变量
```bash
API_TOKEN=your_puter_api_token    # Puter API密钥
SERVER_HOST=0.0.0.0               # 服务器主机（默认0.0.0.0）
SERVER_PORT=9595                  # 服务器端口（默认9595）
DEBUG=true                        # 调试模式（默认false）
```

### 请求头认证
```bash
curl -X POST http://localhost:9595/v1/chat/completions \
  -H "Authorization: Bearer your_puter_api_token" \
  -H "Content-Type: application/json" \
  -d '{"model": "gpt-4o-mini", "messages": [{"role": "user", "content": "Hello"}]}'
```

## 📁 项目结构

```
PuterAi-python_SDK/
├── API/
│   └── openai_server.py         # 主服务器文件
├── examples/
│   ├── basic_chat.py            # 基础聊天示例
│   ├── image_generation.py      # 图像生成示例
│   ├── text_to_speech.py        # 语音合成示例
│   └── vision_api.py            # 图像理解示例
├── tests/
│   └── test_api.py              # API测试
├── requirements.txt             # 依赖包
├── .env.example                 # 环境变量示例
├── .gitignore                  # Git忽略文件
├── LICENSE                     # MIT许可证
└── README.md                   # 项目说明
```

## �️ 开发指南

### 本地开发
```bash
# 克隆项目
git clone https://github.com/your-username/PuterAi-python_SDK.git
cd PuterAi-python_SDK

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 运行测试
python -m pytest tests/

# 启动开发服务器
python API/openai_server.py
```

### 部署到生产环境
```bash
# 使用Gunicorn
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:9595 API.openai_server:app

# 使用Docker
docker build -t puter-openai-proxy .
docker run -p 9595:9595 -e API_TOKEN=your_token puter-openai-proxy
```

## 🤝 贡献指南

欢迎提交Issue和Pull Request！

1. Fork本项目
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建Pull Request

## 📄 许可证

本项目采用 [MIT License](LICENSE) 许可证。

## 🙏 致谢

- [Puter.js](https://docs.puter.com/) - 提供强大的AI API后端
- [OpenAI](https://openai.com/) - 提供标准的API接口规范
- 所有贡献者和使用者

> 📌 **完整模型列表**: 访问 [Puter AI 模型文档](https://docs.puter.com/AI/models) 查看400+可用模型

## � 项目结构

```
PuterAi-python_SDK/
├── API/
│   ├── openai_server.py          # 主要代理服务器
│   └── __pycache__/              # Python缓存文件
├── cli/
│   └── cli.py                    # 命令行交互工具
├── examples/
│   ├── basic_test.py             # 基础功能测试
│   ├── quick_api_key_test.py     # API密钥快速测试
│   ├── quick_token_test.py       # Token使用测试
│   ├── test_api_key_priority.py  # API密钥优先级测试
│   ├── test_new_apis.py          # 新功能API测试
│   ├── test_stream_fix.py        # 流式传输测试
│   └── test_token_usage.py       # Token计算测试
├── tests/
│   ├── testAPI.py                # 原始API测试
│   └── test_simple.py            # 简化测试套件
├── logs/
│   └── openai_proxy.log          # 服务器日志文件
├── .env                          # 环境变量配置
├── requirements.txt              # Python依赖列表
├── README.md                     # 项目文档
├── LICENSE                       # 开源许可证
└── development_progress.md       # 开发进度记录
```

## 🛠️ 故障排除

### 常见问题与解决方案

#### 1. 连接问题
```bash
# 问题：无法连接到服务器
# 解决：检查服务器是否正在运行
curl http://localhost:5000/health

# 问题：端口被占用
# 解决：使用不同端口启动
python API/openai_server.py --port 8080
```

#### 2. API密钥问题
```bash
# 问题：API密钥无效
# 解决：检查API密钥格式和有效性
python examples/quick_api_key_test.py

# 问题：环境变量未加载
# 解决：确认.env文件位置和格式
cat .env
```

#### 3. 模型相关问题
```python
# 问题：模型不可用
# 解决：检查模型列表
import requests
response = requests.get("http://localhost:5000/v1/models")
print(response.json())
```

#### 4. 日志调试
```bash
# 启用调试模式查看详细日志
python API/openai_server.py --debug

# 查看日志文件
tail -f logs/openai_proxy.log
```

### 错误码说明

## ⚡ 性能优化

### 调优建议

1. **连接池配置**
```python
# 在生产环境中调整连接池大小
import requests
session = requests.Session()
adapter = requests.adapters.HTTPAdapter(
    pool_connections=100,
    pool_maxsize=100
)
session.mount('http://', adapter)
session.mount('https://', adapter)
```

2. **流式传输优化**
```python
# 启用流式传输以获得更好的响应时间
response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "长文本生成..."}],
    stream=True  # 启用流式传输
)

for chunk in response:
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="")
```

3. **缓存策略**
```bash
# 使用Redis缓存频繁请求的结果
pip install redis
```

### 监控指标

- 响应时间
- 吞吐量 (requests/second)
- 错误率
- Token使用量
- 内存使用情况

## 🤝 贡献指南

我们欢迎所有形式的贡献！请按照以下步骤进行：

### 开发环境设置

1. **Fork并克隆仓库**
```bash
git clone https://github.com/3210448723/PuterAi-python_SDK.git
cd PuterAi-python_SDK
```

2. **创建虚拟环境**
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate     # Windows
```

3. **安装开发依赖**
```bash
pip install -r requirements.txt
pip install pytest pytest-cov black flake8
```

### 代码规范

- 使用 **Black** 进行代码格式化
- 使用 **flake8** 进行代码检查
- 添加必要的中文注释
- 保持现有的日志格式

```bash
# 代码格式化
black API/ cli/ examples/ tests/

# 代码检查
flake8 API/ cli/ examples/ tests/

# 运行测试
pytest tests/ -v --cov
```

### 提交规范

使用以下格式提交代码：

```
<类型>(<范围>): <描述>

<详细说明>

<相关问题编号>
```

类型：
- `feat`: 新功能
- `fix`: 错误修复
- `docs`: 文档更新
- `style`: 代码格式调整
- `refactor`: 代码重构
- `test`: 测试相关
- `chore`: 构建工具或辅助工具变动

示例：
```
feat(api): 添加图像理解功能支持

- 实现Vision API兼容接口
- 支持图片URL和base64格式
- 添加OCR文字识别功能

closes #123
```

### Pull Request 流程

1. 确保所有测试通过
2. 更新相关文档
3. 创建PR，描述清楚变更内容
4. 等待代码审查
5. 根据反馈进行修改

## 📄 许可证

本项目采用 [MIT 许可证](LICENSE)。

## 🙏 致谢

- [Puter.com](https://puter.com) - 提供免费AI API访问
- [OpenAI](https://openai.com) - API接口设计参考
- 所有贡献者和用户的支持

## 📞 支持与联系

- **问题反馈**: [GitHub Issues](https://github.com/3210448723/PuterAi-python_SDK/issues)
- **功能建议**: [GitHub Discussions](https://github.com/3210448723/PuterAi-python_SDK/discussions)
- **项目维护者**: [@3210448723](https://github.com/3210448723)

---

<div align="center">

**⭐ 如果这个项目对你有帮助，请给个星标支持！⭐**

[🏠 Homepage](https://github.com/3210448723/PuterAi-python_SDK) | 
[📖 Documentation](https://docs.puter.com/AI/) | 
[🐛 Report Bug](https://github.com/3210448723/PuterAi-python_SDK/issues) | 
[💡 Request Feature](https://github.com/3210448723/PuterAi-python_SDK/discussions)

</div>


├── API/
│   └── openai_server.py          # 主服务器文件
├── tests/
│   └── test_api.py               # 完整API测试套件
├── examples/
│   └── basic_chat.py             # 基本使用示例
│   └── image_generation.py       # 图像生成使用示例
│   └── text_to_speech.py         # 文本转语音使用示例
│   └── vision_api.py             # 图像理解使用示例
├── cli/
│   └── cli.py                    # 命令行工具
├── logs/                         # 日志目录
├── .env.example                  # 环境变量示例
├── .gitignore                    # Git忽略文件
├── login.py                      # 登录脚本
├── LICENSE                       # 开源许可证
├── README.md                     # 项目说明
├── requirements.txt              # 依赖列表
└── start.sh                      # 服务端启动脚本
```

## 🔧 配置选项

### 环境变量
- `API_TOKEN`: Puter API令牌（必需）
- `LOG_LEVEL`: 日志级别（默认INFO）

### 服务器配置
- 默认端口: 9595
- 日志文件: `logs/openai_proxy.log`
- 日志轮转: 10MB每个文件，保留5个备份

## 🚀 部署

### Docker部署（待实现）
```bash
docker build -t puterai-proxy .
docker run -p 9595:9595 -e API_TOKEN=your-token puterai-proxy
```

### 生产环境
建议使用gunicorn或其他WSGI服务器：

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:9595 API.openai_server:app
```

## 📋 TODO

- [ ] 添加更多音频格式支持
- [ ] 实现文件上传功能（OCR）
- [ ] 添加请求限制和缓存
- [ ] 容器化部署
- [ ] 添加Webhook支持
- [ ] 性能优化和监控

## 🤝 贡献

欢迎提交Issue和Pull Request！

## 📄 许可证

[MIT License](LICENSE)

## 🙏 致谢

- [Puter.js](https://docs.puter.com/) - 提供免费AI API
- [OpenAI](https://openai.com/) - API接口设计参考
pip install tiktoken
```