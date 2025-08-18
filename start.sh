#!/bin/bash
# PuterAI OpenAI Proxy 启动脚本

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 PuterAI OpenAI Proxy 启动脚本${NC}"
echo "=================================="

# 检查Python版本
echo -e "${YELLOW}📋 检查环境...${NC}"
python_version=$(python3 --version 2>&1)
echo "Python版本: $python_version"

# 检查是否存在.env文件
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚠️ 未找到.env文件，从示例创建...${NC}"
    if [ -f .env.example ]; then
        cp .env.example .env
        echo -e "${RED}❗ 请编辑.env文件并设置你的API_TOKEN${NC}"
        echo "   nano .env"
        exit 1
    fi
fi

# 检查依赖
echo -e "${YELLOW}📦 检查依赖...${NC}"
if [ ! -d "venv" ]; then
    echo "创建虚拟环境..."
    python3 -m venv venv
fi

echo "激活虚拟环境..."
source venv/bin/activate

echo "安装依赖..."
pip install -r requirements.txt

# 检查API_TOKEN
source .env
if [ -z "$API_TOKEN" ] || [ "$API_TOKEN" = "your_puter_api_token_here" ]; then
    echo -e "${RED}❌ 请在.env文件中设置有效的API_TOKEN${NC}"
    exit 1
fi

# 启动服务器
echo -e "${GREEN}🎯 启动PuterAI代理服务器...${NC}"
python API/openai_server.py
