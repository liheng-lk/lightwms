# LightWMS 轻量级仓库管理系统

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![Node.js](https://img.shields.io/badge/Node.js-18+-green.svg)](https://nodejs.org/)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://www.docker.com/)

一个简单易用的仓库管理系统，支持物品管理、借用/归还、领用/补货等功能。

## 功能特性

- 📦 物品管理：分类、库位、条码、图片
- 🔄 借用/归还：支持批量操作和记录追踪
- 📤 领用/补货：库存追踪和数量管理
- 👥 用户管理：角色权限控制（管理员/普通用户）
- 📊 审计日志：完整的操作记录和登录日志
- 📱 移动端适配：支持手机扫码操作
- 🏷️ 条码打印：批量打印条码标签
- 📥 导入导出：Excel 批量导入导出
- 🎨 主题设置：明暗主题切换、自定义 Logo
- 🧾 发票管理：采购发票记录

## 技术栈

| 类型 | 技术 |
|------|------|
| 前端 | Next.js 15, React 19, TypeScript, Tailwind CSS, shadcn/ui |
| 后端 | Django 4.2, Django REST Framework, Python 3.10+ |
| 数据库 | PostgreSQL, Redis |
| 部署 | Docker, Nginx |

## 项目结构

```
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
├── CHANGELOG.md       # 更新日志
└── DEPLOYMENT.md      # 部署文档
```

## 快速开始

### Docker 部署（推荐）

```bash
# 1. 克隆项目
git clone https://github.com/liheng-lk/lightwms.git
cd lightwms

# 2. 复制环境变量
cp docker/.env.example .env

# 3. 使用 DockerHub 镜像启动
docker-compose -f docker/compose/docker-compose.dockerhub.yml up -d
```

### 访问系统

| 项目 | 值 |
|------|------|
| 地址 | http://localhost |
| 管理员账户 | `admin` / `admin123` |
| 邀请码 | `hdu340` |

## Docker 镜像

| 镜像 | 地址 |
|------|------|
| 后端 | `liheng6668/lightwms-backend:amd64` |
| 前端 | `liheng6668/lightwms-frontend:amd64` |

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
- [更新日志](CHANGELOG.md) - 版本更新记录

## 贡献

欢迎贡献代码！请阅读 [贡献指南](CONTRIBUTING.md) 了解如何参与。

## 安全

如果发现安全漏洞，请查看 [安全政策](SECURITY.md) 了解如何报告。

## 开源协议

本项目采用 [MIT License](LICENSE) 开源协议。

你可以：
- 免费使用、复制、修改、合并、发布、分发
- 用于商业用途
- 私有使用
- 修改后闭源

唯一要求：保留原始版权声明和许可声明

## 联系

如有问题，请通过 [Issues](https://github.com/liheng-lk/lightwms/issues) 联系。

如果这个项目对你有帮助，请给一个 Star ⭐
