#!/bin/bash

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=========================================="
echo "  试卷生成系统 - Docker 全容器化部署"
echo -e "==========================================${NC}"
echo ""

# 检查 Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}错误: Docker 未安装${NC}"
    exit 1
fi

# 检查 Docker Compose
if ! docker compose version &> /dev/null; then
    echo -e "${RED}错误: Docker Compose 未安装${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Docker 环境检查通过${NC}"
echo ""

# 构建前端
echo -e "${BLUE}构建前端...${NC}"
if [ -d "frontend" ] && [ -f "frontend/package.json" ]; then
    cd frontend

    # 加载 nvm
    export NVM_DIR="$HOME/.nvm"
    if [ -s "$NVM_DIR/nvm.sh" ]; then
        echo "加载 nvm 并切换到 Node v24..."
        \. "$NVM_DIR/nvm.sh"
        nvm use v24.14.0 || nvm use default || nvm use node
    fi

    echo "当前 Node 版本: $(node --version)"

    if [ ! -d "node_modules" ]; then
        echo "安装前端依赖..."
        npm install
    fi

    echo "构建前端项目..."
    npm run build
    cd ..
    echo -e "${GREEN}✓ 前端构建完成${NC}"
else
    echo -e "${YELLOW}警告: frontend 目录不存在，跳过前端构建${NC}"
fi
echo ""

# 停止旧容器
echo -e "${BLUE}停止旧容器...${NC}"
docker compose down
echo ""

# 构建镜像
echo -e "${BLUE}构建 Docker 镜像...${NC}"
docker compose build --no-cache
echo -e "${GREEN}✓ 镜像构建完成${NC}"
echo ""

# 启动服务
echo -e "${BLUE}启动服务...${NC}"
docker compose up -d
echo ""

# 等待服务启动
echo -e "${BLUE}等待服务启动...${NC}"
sleep 10

# 检查服务状态
echo ""
echo -e "${BLUE}服务状态:${NC}"
docker compose ps
echo ""

# 健康检查
echo -e "${BLUE}健康检查...${NC}"
echo ""

check_service() {
    local name=$1
    local url=$2
    local max_retry=30
    local retry=0

    while [ $retry -lt $max_retry ]; do
        if curl -sf "$url" > /dev/null 2>&1; then
            echo -e "${GREEN}✓ $name 服务正常${NC}"
            return 0
        fi
        retry=$((retry + 1))
        sleep 2
    done

    echo -e "${RED}✗ $name 服务异常${NC}"
    return 1
}

check_service "Nginx" "http://localhost/health"
check_service "Prometheus" "http://localhost:9090/-/healthy"
check_service "Grafana" "http://localhost:3000/api/health"

echo ""
echo -e "${GREEN}=========================================="
echo "  部署完成！"
echo "==========================================${NC}"
echo ""
echo "服务访问地址:"
echo "  - 前端页面:      http://localhost"
echo "  - Backend API:   http://localhost/api"
echo "  - Prometheus:    http://localhost:9090"
echo "  - Grafana:       http://localhost:3000 (admin/admin123)"
echo ""
echo "查看日志: docker compose logs -f [service_name]"
echo "停止服务: docker compose down"
echo ""
