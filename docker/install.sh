#!/bin/bash
# LightWMS 一键安装脚本
# 用法: curl -fsSL https://raw.githubusercontent.com/你的用户名/lightwms/main/install.sh | bash
# 或者: git clone 后运行 ./install.sh

set -e

echo "=========================================="
echo "  LightWMS 一键安装脚本"
echo "=========================================="

# 检测操作系统
OS="$(uname -s)"
case "$OS" in
    Linux*)     OS_TYPE=Linux;;
    Darwin*)    OS_TYPE=Mac;;
    *)          OS_TYPE="UNKNOWN";;
esac

echo "检测到操作系统: $OS_TYPE"

# 检查必要的依赖
check_dependencies() {
    echo ""
    echo "检查依赖..."
    
    # 检查 Python
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2)
        echo "✓ Python: $PYTHON_VERSION"
    else
        echo "✗ 未找到 Python3，请先安装 Python 3.10+"
        exit 1
    fi
    
    # 检查 Node.js
    if command -v node &> /dev/null; then
        NODE_VERSION=$(node --version)
        echo "✓ Node.js: $NODE_VERSION"
    else
        echo "✗ 未找到 Node.js，请先安装 Node.js 18+"
        exit 1
    fi
    
    # 检查 npm
    if command -v npm &> /dev/null; then
        NPM_VERSION=$(npm --version)
        echo "✓ npm: $NPM_VERSION"
    else
        echo "✗ 未找到 npm"
        exit 1
    fi
    
    # 检查 PostgreSQL (可选，可以用 SQLite)
    if command -v psql &> /dev/null; then
        echo "✓ PostgreSQL 已安装"
        USE_POSTGRES=true
    else
        echo "! PostgreSQL 未安装，将使用 SQLite"
        USE_POSTGRES=false
    fi
}

# 设置后端
setup_backend() {
    echo ""
    echo "设置后端..."
    
    cd backend
    
    # 创建虚拟环境
    if [ ! -d "venv" ]; then
        echo "创建 Python 虚拟环境..."
        python3 -m venv venv
    fi
    
    # 激活虚拟环境并安装依赖
    source venv/bin/activate
    echo "安装 Python 依赖..."
    pip install -r requirements.txt -q
    
    # 数据库迁移 (使用 SQLite 本地配置)
    echo "执行数据库迁移..."
    DJANGO_SETTINGS_MODULE=config.settings.local python manage.py migrate
    
    # 创建超级用户（如果不存在）
    echo "创建管理员账户 (admin/admin123)..."
    DJANGO_SETTINGS_MODULE=config.settings.local python manage.py shell << 'PYTHON'
from apps.users.models import User
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
    print('管理员账户已创建')
else:
    print('管理员账户已存在')
PYTHON
    
    deactivate
    cd ..
}

# 设置前端
setup_frontend() {
    echo ""
    echo "设置前端..."
    
    cd frontend
    
    # 安装依赖
    echo "安装前端依赖..."
    npm install
    
    # 创建 .env.local 文件
    if [ ! -f ".env.local" ]; then
        echo "创建前端配置文件..."
        cat > .env.local << 'EOF'
BACKEND_URL=http://localhost:8000
EOF
    fi
    
    cd ..
}

# 创建启动脚本
create_start_script() {
    echo ""
    echo "创建启动脚本..."
    
    cat > start.sh << 'EOF'
#!/bin/bash
# LightWMS 启动脚本

echo "启动 LightWMS..."

# 启动后端 (使用 SQLite 本地配置)
echo "启动后端服务 (端口 8000)..."
cd backend
source venv/bin/activate
DJANGO_SETTINGS_MODULE=config.settings.local python manage.py runserver 0.0.0.0:8000 &
BACKEND_PID=$!
cd ..

# 等待后端启动
sleep 3

# 启动前端
echo "启动前端服务 (端口 3000)..."
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo "=========================================="
echo "  LightWMS 已启动!"
echo "=========================================="
echo ""
echo "访问地址: http://localhost:3000"
echo "管理员账户: admin / admin123"
echo "邀请码: hdu340"
echo ""
echo "按 Ctrl+C 停止服务"

# 等待用户中断
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM
wait
EOF
    
    chmod +x start.sh
    
    # 创建停止脚本
    cat > stop.sh << 'EOF'
#!/bin/bash
# 停止 LightWMS
echo "停止 LightWMS..."
pkill -f "python manage.py runserver" 2>/dev/null
pkill -f "next dev" 2>/dev/null
echo "已停止"
EOF
    
    chmod +x stop.sh
}

# 主流程
main() {
    check_dependencies
    setup_backend
    setup_frontend
    create_start_script
    
    echo ""
    echo "=========================================="
    echo "  安装完成!"
    echo "=========================================="
    echo ""
    echo "启动命令: ./start.sh"
    echo "停止命令: ./stop.sh"
    echo ""
    echo "访问地址: http://localhost:3000"
    echo "管理员账户: admin / admin123"
    echo "邀请码: hdu340"
    echo ""
}

main
