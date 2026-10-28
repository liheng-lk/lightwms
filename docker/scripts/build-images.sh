#!/bin/bash
# LightWMS Docker 镜像构建脚本
# 用于构建前后端分离的 Docker 镜像

set -e

# 配置
DOCKER_REGISTRY="${DOCKER_REGISTRY:-}"  # 例如: yourusername/
VERSION="${VERSION:-latest}"
# 写进镜像供更新检查使用：语义化版本取自仓库根目录 VERSION 文件
APP_VERSION="$(tr -d '[:space:]' < VERSION 2>/dev/null || echo unknown)"
BUILD_TIME="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
APP_REVISION="$(git rev-parse HEAD 2>/dev/null || echo '')"
BACKEND_IMAGE="${DOCKER_REGISTRY}lightwms-backend:${VERSION}"
FRONTEND_IMAGE="${DOCKER_REGISTRY}lightwms-frontend:${VERSION}"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

echo_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

echo_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 显示帮助
show_help() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -b, --backend     只构建后端镜像"
    echo "  -f, --frontend    只构建前端镜像"
    echo "  -a, --all         构建所有镜像 (默认)"
    echo "  -p, --push        构建后推送到 Docker Hub"
    echo "  -t, --tag TAG     指定版本标签 (默认: latest)"
    echo "  -r, --registry    Docker Registry 前缀 (例如: yourusername/)"
    echo "  -h, --help        显示帮助信息"
    echo ""
    echo "Examples:"
    echo "  $0 -a                          # 构建所有镜像"
    echo "  $0 -a -p -r myuser/            # 构建并推送到 myuser/ 仓库"
    echo "  $0 -b -t v1.0.0                # 只构建后端，标签为 v1.0.0"
}

# 构建后端镜像
build_backend() {
    echo_info "构建后端镜像: ${BACKEND_IMAGE}"
    docker build \
        --build-arg APP_VERSION="${APP_VERSION}" \
        --build-arg BUILD_TIME="${BUILD_TIME}" \
        --build-arg APP_REVISION="${APP_REVISION}" \
        -t "${BACKEND_IMAGE}" -f backend/Dockerfile backend/
    echo_info "后端镜像构建完成"
}

# 构建前端镜像
build_frontend() {
    echo_info "构建前端镜像: ${FRONTEND_IMAGE}"
    docker build -t "${FRONTEND_IMAGE}" -f frontend/Dockerfile frontend/
    echo_info "前端镜像构建完成"
}

# 推送镜像
push_images() {
    if [ -z "$DOCKER_REGISTRY" ]; then
        echo_error "推送镜像需要指定 Docker Registry (-r 参数)"
        exit 1
    fi
    
    echo_info "推送镜像到 Docker Hub..."
    
    # 推送语义化版本时同时更新 :latest，否则跟踪 latest 的部署永远拉不到新镜像
    local also_latest=false
    if [[ "$VERSION" =~ ^v?[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
        also_latest=true
        if [ "${VERSION#v}" != "$APP_VERSION" ]; then
            echo_warn "标签 ${VERSION} 与 VERSION 文件 (${APP_VERSION}) 不一致，系统内显示的版本号会以 VERSION 文件为准"
        fi
    fi

    if [ "$BUILD_BACKEND" = true ]; then
        echo_info "推送后端镜像: ${BACKEND_IMAGE}"
        docker push "${BACKEND_IMAGE}"
        if [ "$also_latest" = true ]; then
            docker tag "${BACKEND_IMAGE}" "${DOCKER_REGISTRY}lightwms-backend:latest"
            docker push "${DOCKER_REGISTRY}lightwms-backend:latest"
        fi
    fi
    
    if [ "$BUILD_FRONTEND" = true ]; then
        echo_info "推送前端镜像: ${FRONTEND_IMAGE}"
        docker push "${FRONTEND_IMAGE}"
        if [ "$also_latest" = true ]; then
            docker tag "${FRONTEND_IMAGE}" "${DOCKER_REGISTRY}lightwms-frontend:latest"
            docker push "${DOCKER_REGISTRY}lightwms-frontend:latest"
        fi
    fi
    
    echo_info "镜像推送完成"
}

# 默认值
BUILD_BACKEND=false
BUILD_FRONTEND=false
PUSH_IMAGES=false

# 解析参数
while [[ $# -gt 0 ]]; do
    case $1 in
        -b|--backend)
            BUILD_BACKEND=true
            shift
            ;;
        -f|--frontend)
            BUILD_FRONTEND=true
            shift
            ;;
        -a|--all)
            BUILD_BACKEND=true
            BUILD_FRONTEND=true
            shift
            ;;
        -p|--push)
            PUSH_IMAGES=true
            shift
            ;;
        -t|--tag)
            VERSION="$2"
            BACKEND_IMAGE="${DOCKER_REGISTRY}lightwms-backend:${VERSION}"
            FRONTEND_IMAGE="${DOCKER_REGISTRY}lightwms-frontend:${VERSION}"
            shift 2
            ;;
        -r|--registry)
            DOCKER_REGISTRY="$2"
            BACKEND_IMAGE="${DOCKER_REGISTRY}lightwms-backend:${VERSION}"
            FRONTEND_IMAGE="${DOCKER_REGISTRY}lightwms-frontend:${VERSION}"
            shift 2
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            echo_error "未知参数: $1"
            show_help
            exit 1
            ;;
    esac
done

# 如果没有指定构建目标，默认构建所有
if [ "$BUILD_BACKEND" = false ] && [ "$BUILD_FRONTEND" = false ]; then
    BUILD_BACKEND=true
    BUILD_FRONTEND=true
fi

# 显示构建信息
echo_info "=========================================="
echo_info "LightWMS Docker 镜像构建"
echo_info "=========================================="
echo_info "版本: ${VERSION}"
echo_info "Registry: ${DOCKER_REGISTRY:-<local>}"
echo_info "构建后端: ${BUILD_BACKEND}"
echo_info "构建前端: ${BUILD_FRONTEND}"
echo_info "推送镜像: ${PUSH_IMAGES}"
echo_info "=========================================="

# 执行构建
if [ "$BUILD_BACKEND" = true ]; then
    build_backend
fi

if [ "$BUILD_FRONTEND" = true ]; then
    build_frontend
fi

# 推送镜像
if [ "$PUSH_IMAGES" = true ]; then
    push_images
fi

# 显示结果
echo_info "=========================================="
echo_info "构建完成!"
echo_info "=========================================="

if [ "$BUILD_BACKEND" = true ]; then
    echo_info "后端镜像: ${BACKEND_IMAGE}"
fi

if [ "$BUILD_FRONTEND" = true ]; then
    echo_info "前端镜像: ${FRONTEND_IMAGE}"
fi

echo ""
echo_info "本地测试命令:"
echo "  docker-compose -f docker-compose.split.yml up -d"
echo ""
echo_info "查看日志:"
echo "  docker-compose -f docker-compose.split.yml logs -f"
