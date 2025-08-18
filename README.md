# PuterAI OpenAI Proxy

一个将[Puter.js AI API](https://docs.puter.com/AI/)包装成OpenAI Python SDK兼容接口的代理服务器。免费访问400+种AI模型。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

## ✨ 功能特性

- **🤖 聊天对话**: 支持GPT-4、Claude、Gemini等400+模型
- **🖼️ 图像生成**: DALL-E兼容API
- **🔊 文本转语音**: 多语言TTS合成
- **👁️ 图像理解**: 视觉理解和OCR
- **⚡ 流式传输**: 实时响应支持
- **🔧 函数调用**: Tool Calling支持

## 🚀 快速开始

### 1. 安装依赖
```bash
git clone https://github.com/3210448723/PuterAi-python_SDK.git
cd PuterAi-python_SDK
pip install -r requirements.txt
```

### 2. 配置API密钥
```bash
# 环境变量方式
export API_TOKEN="your_puter_api_token"

# 或创建.env文件
echo "API_TOKEN=your_puter_api_token" > .env
```

### 3. 启动服务器
```bash
python API/openai_server.py
# 或使用启动脚本: ./start.sh
```

### 4. 使用示例
```python
import openai

client = openai.OpenAI(
    api_key="your_puter_api_token",
    base_url="http://localhost:9595/v1"
)

# 聊天对话
response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "Hello!"}]
)
print(response.choices[0].message.content)
```

更多示例请查看 `examples/` 目录。

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
API_TOKEN=your_puter_api_token    # Puter API密钥（必需）
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
├── start.sh                    # 启动脚本
├── LICENSE                     # MIT许可证
└── README.md                   # 项目说明
```

## 🛠️ 开发指南

### 本地开发
```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 运行测试
python tests/test_api.py

# 启动开发服务器
python API/openai_server.py
```

### 生产部署
```bash
# 使用Gunicorn
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:9595 API.openai_server:app
```

## 🛠️ 故障排除

### 常见问题

1. **连接问题**: 检查服务器是否运行 `curl http://localhost:9595/health`
2. **API密钥错误**: 验证.env文件中的API_TOKEN设置
3. **模型不可用**: 访问 `/v1/models` 端点查看可用模型
4. **调试模式**: 启动时添加 `--debug` 参数查看详细日志

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

---

<div align="center">

**⭐ 如果这个项目对你有帮助，请给个星标支持！⭐**

[🏠 项目主页](https://github.com/3210448723/PuterAi-python_SDK) | 
[📖 API文档](https://docs.puter.com/AI/) | 
[🐛 问题反馈](https://github.com/3210448723/PuterAi-python_SDK/issues)

</div>
