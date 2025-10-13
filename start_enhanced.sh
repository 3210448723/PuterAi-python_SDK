#!/bin/bash
# PuterAI Enhanced OpenAI Proxy 启动脚本（增强版）
# 支持代理IP和多Token管理

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 PuterAI Enhanced OpenAI Proxy 启动脚本${NC}"
echo "=================================================="
echo -e "${BLUE}✨ 支持代理IP和多Token管理${NC}"
echo ""

# 检查Python版本
echo -e "${YELLOW}📋 检查环境...${NC}"
python_version=$(python3 --version 2>&1)
echo "Python版本: $python_version"

# 检查是否存在虚拟环境
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}📦 创建虚拟环境...${NC}"
    python3 -m venv venv
fi

echo -e "${YELLOW}🔄 激活虚拟环境...${NC}"
source venv/bin/activate

# 检查并安装依赖
echo -e "${YELLOW}📦 检查并安装依赖...${NC}"
pip install -r requirements.txt

# 安装额外的依赖
echo -e "${YELLOW}🔧 安装增强功能依赖...${NC}"
pip install lxml playwright

# 安装playwright浏览器
echo -e "${YELLOW}🌐 安装Playwright浏览器...${NC}"
playwright install chromium

# 检查是否存在.env文件
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚠️ 未找到.env文件，从示例创建...${NC}"
    if [ -f .env.example ]; then
        cp .env.example .env
        echo -e "${YELLOW}📝 已创建.env文件${NC}"
    else
        echo 'API_TOKEN=""' > .env
    fi
fi

# 创建必要的目录
echo -e "${YELLOW}📁 创建必要的目录...${NC}"
mkdir -p logs
mkdir -p data

# 检查API_TOKEN
source .env
if [ -z "$API_TOKEN" ] || [ "$API_TOKEN" = "your_puter_api_token_here" ] || [ "$API_TOKEN" = "" ]; then
    echo -e "${YELLOW}🔑 API_TOKEN为空，开始系统初始化...${NC}"
    echo ""
    
    # 运行系统初始化
    echo -e "${BLUE}🚀 正在初始化代理池和Token池...${NC}"
    python3 init_system.py
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ 系统初始化成功${NC}"
        # 重新加载.env文件
        source .env
        
        if [ -z "$API_TOKEN" ] || [ "$API_TOKEN" = "" ]; then
            echo -e "${RED}❌ 初始化后仍未获取到有效Token，请检查网络和代理设置${NC}"
            exit 1
        fi
    else
        echo -e "${RED}❌ 系统初始化失败${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}✅ 发现现有API_TOKEN${NC}"
fi

# 显示系统状态
echo ""
echo -e "${BLUE}📊 系统状态检查...${NC}"
python3 -c "
try:
    from utils.proxy_manager import get_proxy_manager
    from utils.token_manager import get_token_manager
    
    proxy_stats = get_proxy_manager().get_proxy_stats()
    token_stats = get_token_manager().get_token_stats()
    
    print(f'代理池: {proxy_stats[\"verified_proxies\"]}/{proxy_stats[\"total_proxies\"]} 个可用')
    print(f'Token池: {token_stats[\"active_tokens\"]}/{token_stats[\"total_tokens\"]} 个可用')
    
    if proxy_stats['verified_proxies'] > 0 and token_stats['active_tokens'] > 0:
        print('🎉 系统准备就绪')
    else:
        print('⚠️ 系统资源不足，建议运行: python3 init_system.py')
except Exception as e:
    print(f'状态检查失败: {e}')
"

# 启动服务器
echo ""
echo -e "${GREEN}🎯 启动增强版PuterAI代理服务器...${NC}"
echo -e "${BLUE}🌐 服务将在 http://localhost:5000 启动${NC}"
echo -e "${YELLOW}💡 支持OpenAI兼容API，可以直接替换OpenAI的base_url${NC}"
echo ""

# 启动API服务器
cd API && python3 openai_server.py