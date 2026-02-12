#!/bin/bash
#
# 播客处理项目 - 服务器部署脚本
# 用途：自动在服务器上安装依赖并配置环境
#

set -e  # 遇到错误立即退出

echo "=================================================="
echo "  播客处理项目 - 服务器部署脚本"
echo "=================================================="
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查是否为 root 用户
if [ "$EUID" -eq 0 ]; then 
    echo -e "${RED}错误: 请不要使用 root 用户运行此脚本${NC}"
    echo "建议使用普通用户（具有 sudo 权限）"
    exit 1
fi

# 步骤 1: 检测操作系统
echo -e "${GREEN}[1/7] 检测操作系统...${NC}"
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
    VERSION=$VERSION_ID
    echo "检测到系统: $OS $VERSION"
else
    echo -e "${RED}无法检测操作系统${NC}"
    exit 1
fi

# 步骤 2: 安装系统依赖
echo ""
echo -e "${GREEN}[2/7] 安装系统依赖...${NC}"
if [ "$OS" = "ubuntu" ] || [ "$OS" = "debian" ]; then
    echo "更新包管理器..."
    sudo apt update
    
    echo "安装必要软件..."
    sudo apt install -y python3 python3-pip python3-venv ffmpeg curl
elif [ "$OS" = "centos" ] || [ "$OS" = "rhel" ]; then
    echo "更新包管理器..."
    sudo yum update -y
    
    echo "安装必要软件..."
    sudo yum install -y python3 python3-pip ffmpeg curl
else
    echo -e "${YELLOW}警告: 未知的操作系统，尝试继续...${NC}"
fi

# 检查 Python 版本
PYTHON_VERSION=$(python3 --version | awk '{print $2}')
echo "Python 版本: $PYTHON_VERSION"

# 步骤 3: 安装 Docker
echo ""
echo -e "${GREEN}[3/7] 检查 Docker...${NC}"
if ! command -v docker &> /dev/null; then
    echo "Docker 未安装，正在安装..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    echo -e "${YELLOW}Docker 已安装，但需要重新登录才能生效${NC}"
    echo -e "${YELLOW}安装完成后，请退出并重新登录，然后重新运行此脚本${NC}"
    rm get-docker.sh
    exit 0
else
    echo "Docker 已安装: $(docker --version)"
fi

# 步骤 4: 创建项目目录
echo ""
echo -e "${GREEN}[4/7] 创建项目目录...${NC}"
PROJECT_DIR="$HOME/podcast_brief"
if [ -d "$PROJECT_DIR" ]; then
    echo -e "${YELLOW}目录已存在: $PROJECT_DIR${NC}"
    read -p "是否覆盖现有目录? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "取消部署"
        exit 1
    fi
    rm -rf "$PROJECT_DIR"
fi
mkdir -p "$PROJECT_DIR"
cd "$PROJECT_DIR"
echo "项目目录: $PROJECT_DIR"

# 步骤 5: 提示用户上传代码
echo ""
echo -e "${GREEN}[5/7] 上传项目代码${NC}"
echo ""
echo "请在本地电脑运行以下命令上传代码："
echo ""
echo -e "${YELLOW}scp -r /Users/pengyitong/Documents/Project/Multi_agent/* $(whoami)@$(hostname -I | awk '{print $1}'):$PROJECT_DIR/${NC}"
echo ""
read -p "代码上传完成后，按 Enter 继续..."

# 检查代码是否上传
if [ ! -f "$PROJECT_DIR/requirements.txt" ]; then
    echo -e "${RED}错误: 未检测到 requirements.txt，请确保代码已正确上传${NC}"
    exit 1
fi

# 步骤 6: 创建虚拟环境并安装依赖
echo ""
echo -e "${GREEN}[6/7] 创建 Python 虚拟环境并安装依赖...${NC}"
python3 -m venv .venv
source .venv/bin/activate

echo "安装 Python 依赖..."
pip install --upgrade pip
pip install -r requirements.txt

echo "依赖安装完成"

# 步骤 7: 配置环境变量
echo ""
echo -e "${GREEN}[7/7] 配置环境变量...${NC}"
if [ ! -f "$PROJECT_DIR/.env" ]; then
    if [ -f "$PROJECT_DIR/.env.example" ]; then
        cp "$PROJECT_DIR/.env.example" "$PROJECT_DIR/.env"
        echo "已创建 .env 文件，请编辑填入你的 API keys："
        echo ""
        echo -e "${YELLOW}nano $PROJECT_DIR/.env${NC}"
        echo ""
        echo "需要填入："
        echo "  - DEEPSEEK_API_KEY"
        echo "  - FEISHU_APP_ID"
        echo "  - FEISHU_APP_SECRET"
        echo "  - FEISHU_BITABLE_APP_TOKEN"
        echo "  - FEISHU_BITABLE_TABLE_ID"
        echo "  - FEISHU_DOMAIN"
        echo "  - FEISHU_WEBHOOK_URL"
    else
        echo -e "${RED}错误: 未找到 .env.example 文件${NC}"
        exit 1
    fi
else
    echo ".env 文件已存在"
fi

# 部署完成
echo ""
echo "=================================================="
echo -e "${GREEN}✅ 服务器环境配置完成！${NC}"
echo "=================================================="
echo ""
echo "下一步："
echo ""
echo "1. 编辑环境变量文件："
echo -e "   ${YELLOW}nano $PROJECT_DIR/.env${NC}"
echo ""
echo "2. 测试运行："
echo -e "   ${YELLOW}cd $PROJECT_DIR${NC}"
echo -e "   ${YELLOW}source .venv/bin/activate${NC}"
echo -e "   ${YELLOW}python -m podcast_brief run --max-episodes-per-feed 1 --publish-feishu --feishu-docx${NC}"
echo ""
echo "3. 安装 n8n："
echo -e "   ${YELLOW}docker run -d --restart unless-stopped --name n8n -p 5678:5678 -e GENERIC_TIMEZONE=\"Asia/Shanghai\" -e TZ=\"Asia/Shanghai\" -v ~/.n8n:/home/node/.n8n n8nio/n8n${NC}"
echo ""
echo "4. 访问 n8n Web 界面配置定时任务："
echo -e "   ${YELLOW}http://$(hostname -I | awk '{print $1}'):5678${NC}"
echo ""
echo "详细文档: $PROJECT_DIR/docs/server_deployment.md"
echo ""
