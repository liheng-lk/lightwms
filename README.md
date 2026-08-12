# LightWMS 轻量级仓库管理系统

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![Node.js](https://img.shields.io/badge/Node.js-20+-green.svg)](https://nodejs.org/)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://www.docker.com/)

一个面向日常仓库现场操作的轻量级仓库管理系统，支持物品管理、借用/归还、领用/补货、扫码和审计追踪。

## 功能特性

- 📦 物品管理：分类、库位、条码、图片
- 🔄 借用/归还：记录追踪与批量管理
- 📤 领用/补货：库存追踪和数量管理
- 👥 用户管理：角色权限与邀请码管理
- 📊 审计日志：操作记录和登录日志
- 📱 移动端适配：支持手机扫码操作
- 🏷️ 条码打印：批量打印条码标签
- 📥 导入导出：Excel 批量导入导出
- 🎨 主题设置：明暗主题切换、自定义 Logo
- 🧾 发票管理：采购发票记录

## 技术栈

| 类型 | 技术 |
|------|------|
| 前端 | Next.js 16, React 19, TypeScript, Tailwind CSS, shadcn/ui |
| 后端 | Django 4.2, Django REST Framework, Python 3.10+ |
| 数据库 | PostgreSQL, Redis |
| 部署 | Docker, Nginx |

## 项目结构

```text
lightwms/
├── frontend/          # Next.js 前端
├── backend/           # Django 后端
├── docker/            # Docker 部署配置
│   ├── compose/       # Docker Compose 文件
│   ├── config/        # 容器配置文件
│   ├── nginx/         # Nginx 配置
│   └── scripts/       # 部署脚本
├── LICENSE            # 开源协议
├── README.md          # 项目说明
├── CONTRIBUTING.md    # 贡献指南
└── DEPLOYMENT.md      # 部署文档
```

## 快速开始

### DockerHub 镜像部署

```bash
# 1. 克隆项目
git clone https://github.com/liheng-lk/lightwms.git
cd lightwms

# 2. 复制环境变量并修改生产密钥/数据库密码
cp docker/.env.example .env
# 必须修改 .env 中的 SECRET_KEY 和 POSTGRES_PASSWORD

# 3. 启动
docker compose -f docker/compose/docker-compose.dockerhub.yml up -d

# 4. 首次部署创建管理员（不要使用固定默认密码）
docker compose -f docker/compose/docker-compose.dockerhub.yml exec backend python manage.py createsuperuser
```

### 访问系统

默认统一入口：`http://localhost`

LightWMS **不应提供公开的固定管理员密码或固定邀请码**。管理员账户请在首次部署时创建；邀请码请登录后由管理员按需生成并设置使用次数、有效期和默认角色。

## Docker 镜像

| 镜像 | 地址 |
|------|------|
| 后端 | `liheng6668/lightwms-backend:latest` |
| 前端 | `liheng6668/lightwms-frontend:latest` |

## 本地开发

### 后端

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

### 前端

```bash
cd frontend
npm install
npm run dev
```

## 文档

- [部署文档](DEPLOYMENT.md) - 详细的部署指南
- [Docker 配置](docker/README.md) - Docker 相关配置说明
- [贡献指南](CONTRIBUTING.md) - 如何参与贡献

## 安全

生产环境至少应做到：

- 使用随机且唯一的 `SECRET_KEY`
- 使用高强度 PostgreSQL 密码
- 不公开固定管理员凭据或固定邀请码
- 公网部署启用 HTTPS，并正确设置可信域名和 CSRF 来源
- 定期备份 PostgreSQL 数据和上传的媒体文件

如果发现安全漏洞，请查看 [安全政策](SECURITY.md) 了解如何报告。

## 开源协议

本项目采用 [MIT License](LICENSE) 开源协议。

你可以免费使用、复制、修改、合并、发布、分发，用于商业或私有用途；唯一要求是保留原始版权声明和许可声明。

## 联系

如有问题，请通过 GitHub Issues 联系。
