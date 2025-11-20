#!/bin/bash
# Docker 启动脚本

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查 .env 文件
if [ ! -f .env ]; then
    print_warn ".env 文件不存在，从 .env.example 创建..."
    if [ -f .env.example ]; then
        cp .env.example .env
        print_info "已创建 .env 文件，请根据需要修改配置"
    else
        print_error ".env.example 文件不存在"
        exit 1
    fi
fi

# 解析参数
MODE="prod"  # 默认生产模式
ENABLE_FRONTEND=true
COMPOSE_FILES="docker-compose.yml"

# 解析命令行参数
while [[ $# -gt 0 ]]; do
    case $1 in
        --dev|--development)
            MODE="dev"
            COMPOSE_FILES="$COMPOSE_FILES -f docker-compose.dev.yml"
            shift
            ;;
        --prod|--production)
            MODE="prod"
            COMPOSE_FILES="$COMPOSE_FILES -f docker-compose.prod.yml"
            shift
            ;;
        --backend-only|--no-frontend)
            ENABLE_FRONTEND=false
            shift
            ;;
        --frontend)
            ENABLE_FRONTEND=true
            shift
            ;;
        --help|-h)
            echo "用法: $0 [选项]"
            echo ""
            echo "选项:"
            echo "  --dev, --development      开发模式（挂载代码目录，启用热重载）"
            echo "  --prod, --production      生产模式（默认）"
            echo "  --backend-only            只启动后端服务"
            echo "  --frontend                启用前端服务（默认）"
            echo "  --help, -h                显示此帮助信息"
            echo ""
            echo "示例:"
            echo "  $0                        # 生产模式，启动所有服务"
            echo "  $0 --dev                  # 开发模式，启动所有服务"
            echo "  $0 --backend-only         # 只启动后端服务"
            echo "  $0 --dev --backend-only   # 开发模式，只启动后端服务"
            exit 0
            ;;
        *)
            print_error "未知参数: $1"
            echo "使用 --help 查看帮助信息"
            exit 1
            ;;
    esac
done

# 显示配置信息
print_info "启动模式: $MODE"
print_info "启用前端: $ENABLE_FRONTEND"

# 构建并启动服务
if [ "$ENABLE_FRONTEND" = true ]; then
    print_info "启动所有服务（后端 + 前端）..."
    docker-compose -f $COMPOSE_FILES up -d --build
else
    print_info "只启动后端服务..."
    docker-compose -f $COMPOSE_FILES up -d --build backend
fi

# 等待服务启动
print_info "等待服务启动..."
sleep 5

# 检查服务状态
print_info "检查服务状态..."
docker-compose -f docker-compose.yml ps

print_info "启动完成！"
echo ""
echo "访问地址:"
if [ "$ENABLE_FRONTEND" = true ]; then
    echo "  - 前端界面: http://localhost:8888"
fi
echo "  - 后端 API: http://localhost:8000"
echo "  - API 文档: http://localhost:8000/docs"
echo ""
echo "查看日志: docker-compose logs -f"
echo "停止服务: docker-compose down"

