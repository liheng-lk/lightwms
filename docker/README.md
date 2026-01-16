# Docker 部署配置

本目录包含所有 Docker 相关的配置文件和脚本。

## 目录结构

```
docker/
├── compose/                    # Docker Compose 配置文件
│   ├── docker-compose.yml      # 基础开发配置
│   ├── docker-compose.dev.yml  # 本地开发配置
│   ├── docker-compose.production.yml  # 生产环境配置
│   ├── docker-compose.dockerhub.yml   # DockerHub 镜像配置
│   └── docker-compose.split.yml       # 前后端分离配置
├── config/                     # 容器配置文件
│   ├── entrypoint.sh          # 容器入口脚本
│   ├── nginx.conf             # Nginx 配置
│   ├── nginx-split.conf       # 分离部署 Nginx 配置
│   └── supervisord.conf       # Supervisor 配置
├── nginx/                      # Nginx 配置目录
│   ├── conf.d/                # Nginx 站点配置
│   └── ssl/                   # SSL 证书目录
├── scripts/                    # 部署脚本
│   ├── build-images.sh        # 构建镜像脚本
│   ├── deploy.sh              # 部署脚本
│   ├── backup.sh              # 备份脚本
│   ├── restore.sh             # 恢复脚本
│   └── test.sh                # 测试脚本
├── backup/                     # 备份配置
│   └── crontab                # 定时备份配置
├── .env.example               # 开发环境变量模板
├── .env.production.example    # 生产环境变量模板
├── Dockerfile.unified         # 统一 Dockerfile
└── install.sh                 # 一键安装脚本
```

## 快速开始

### 1. 复制环境变量文件

```bash
cp docker/.env.example .env
```

### 2. 启动开发环境

```bash
docker-compose -f docker/compose/docker-compose.yml up -d
```

### 3. 使用 DockerHub 镜像部署

```bash
docker-compose -f docker/compose/docker-compose.dockerhub.yml up -d
```

## 环境变量说明

详见 `.env.example` 和 `.env.production.example` 文件中的注释。

## 镜像信息

- 后端镜像: `liheng6668/lightwms-backend:amd64`
- 前端镜像: `liheng6668/lightwms-frontend:amd64`
