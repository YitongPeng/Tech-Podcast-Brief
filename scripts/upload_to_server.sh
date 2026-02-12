#!/bin/bash
#
# 播客处理项目 - 代码上传脚本
# 用途：从本地上传代码到服务器
#

set -e

echo "=================================================="
echo "  播客处理项目 - 代码上传工具"
echo "=================================================="
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 获取脚本所在目录（项目根目录）
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

echo "项目目录: $PROJECT_ROOT"
echo ""

# 获取服务器信息
read -p "服务器 IP 地址或域名: " SERVER_HOST
read -p "服务器用户名 (默认: ubuntu): " SERVER_USER
SERVER_USER=${SERVER_USER:-ubuntu}

read -p "服务器项目目录 (默认: ~/podcast_brief): " SERVER_DIR
SERVER_DIR=${SERVER_DIR:-~/podcast_brief}

echo ""
echo "上传配置："
echo "  服务器: $SERVER_USER@$SERVER_HOST"
echo "  目标目录: $SERVER_DIR"
echo ""

read -p "确认上传? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "取消上传"
    exit 1
fi

# 测试 SSH 连接
echo ""
echo -e "${GREEN}测试 SSH 连接...${NC}"
if ! ssh -o ConnectTimeout=5 "$SERVER_USER@$SERVER_HOST" "exit" 2>/dev/null; then
    echo -e "${RED}错误: 无法连接到服务器${NC}"
    echo "请检查："
    echo "  1. 服务器 IP 地址是否正确"
    echo "  2. 服务器是否在线"
    echo "  3. 是否配置了 SSH 密钥"
    exit 1
fi
echo "SSH 连接成功"

# 创建远程目录
echo ""
echo -e "${GREEN}创建远程目录...${NC}"
ssh "$SERVER_USER@$SERVER_HOST" "mkdir -p $SERVER_DIR"

# 上传代码（排除不必要的文件）
echo ""
echo -e "${GREEN}上传代码...${NC}"
rsync -avz --progress \
  --exclude '.git' \
  --exclude '.venv' \
  --exclude '__pycache__' \
  --exclude '*.pyc' \
  --exclude '.DS_Store' \
  --exclude 'data/' \
  --exclude '.env' \
  "$PROJECT_ROOT/" \
  "$SERVER_USER@$SERVER_HOST:$SERVER_DIR/"

# 检查上传结果
if [ $? -eq 0 ]; then
    echo ""
    echo "=================================================="
    echo -e "${GREEN}✅ 代码上传完成！${NC}"
    echo "=================================================="
    echo ""
    echo "下一步："
    echo ""
    echo "1. SSH 登录到服务器："
    echo -e "   ${YELLOW}ssh $SERVER_USER@$SERVER_HOST${NC}"
    echo ""
    echo "2. 进入项目目录："
    echo -e "   ${YELLOW}cd $SERVER_DIR${NC}"
    echo ""
    echo "3. 运行部署脚本："
    echo -e "   ${YELLOW}bash scripts/deploy_server.sh${NC}"
    echo ""
else
    echo -e "${RED}上传失败${NC}"
    exit 1
fi
