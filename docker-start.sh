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
    print_warn ".env 文件不存在，尝试从模板创建..."
    if [ -f .env.example ]; then
        cp .env.example .env
        print_info "已从 .env.example 创建 .env 文件"
    elif [ -f env.example ]; then
        cp env.example .env
        print_info "已从 env.example 创建 .env 文件"
    else
        print_warn "模板文件不存在，创建默认 .env 文件..."
        cat > .env << 'EOF'
# WaveEnv Docker 环境变量配置
# 后端服务端口
BACKEND_PORT=8000
# 前端服务端口
FRONTEND_PORT=8888
# 是否启用前端服务（设置为空字符串则只启动后端）
FRONTEND_PROFILE=frontend
# 后端服务地址（Docker环境使用服务名）
BACKEND_URL=http://backend:8000
# 日志级别
LOG_LEVEL=INFO
EOF
        print_info "已创建默认 .env 文件，请根据需要修改配置"
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
    if ! docker-compose -f $COMPOSE_FILES up -d --build; then
        print_error "服务启动失败！"
        echo ""
        echo "请运行诊断脚本查看详细信息："
        echo "  ./docker-diagnose.sh"
        echo ""
        echo "或查看后端容器日志："
        echo "  docker logs waveenv-backend"
        exit 1
    fi
else
    print_info "只启动后端服务..."
    if ! docker-compose -f $COMPOSE_FILES up -d --build backend; then
        print_error "后端服务启动失败！"
        echo ""
        echo "请查看后端容器日志："
        echo "  docker logs waveenv-backend"
        exit 1
    fi
fi

# 等待服务启动（增加等待时间，给健康检查更多时间）
print_info "等待服务启动（等待健康检查通过）..."
sleep 10

# 检查服务状态
print_info "检查服务状态..."
docker-compose -f docker-compose.yml ps

# 检查后端容器健康状态
if docker ps --format "{{.Names}}" | grep -q "waveenv-backend"; then
    HEALTH_STATUS=$(docker inspect waveenv-backend --format="{{.State.Health.Status}}" 2>/dev/null)
    if [ "$HEALTH_STATUS" != "healthy" ]; then
        print_warn "后端容器可能未通过健康检查（状态: $HEALTH_STATUS）"
        echo "查看后端日志: docker logs waveenv-backend"
        echo "运行诊断脚本: ./docker-diagnose.sh"
    fi
fi

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

