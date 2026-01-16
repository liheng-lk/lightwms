# LightWMS Deployment Guide

## Prerequisites

- Docker 20.10+
- Docker Compose 2.0+
- At least 2GB RAM
- 10GB disk space
- **PostgreSQL 15+** (required - SQLite is not supported for production)

## Important: PostgreSQL Required

LightWMS requires PostgreSQL and uses the following PostgreSQL-specific features:
- `pg_trgm` extension for fuzzy search
- `tsvector` / GIN indexes for full-text search
- Partial unique indexes (e.g., `WHERE status = 'active'`)
- Database triggers for audit log immutability

**SQLite is NOT supported** for production use.

---

## Quick Start (Production)

### 1. 配置环境变量

```bash
# 复制示例配置文件
cp .env.production.example .env.production

# 编辑配置（必须修改 SECRET_KEY 和数据库密码）
nano .env.production
```

### 2. 构建并启动

```bash
# 构建镜像
docker compose -f docker-compose.production.yml build

# 启动服务
docker compose -f docker-compose.production.yml --env-file .env.production up -d

# 查看日志
docker compose -f docker-compose.production.yml logs -f app
```

### 3. 访问应用

- Web UI: http://localhost/
- API: http://localhost/api/v1/
- API Docs: http://localhost/api/v1/docs/
- Admin: http://localhost/admin/

---

## Deployment Options

### Option 1: Unified Image (推荐生产环境)

使用统一镜像部署，前端、后端、Nginx 打包在一个容器中：

```bash
# 构建并启动
docker compose -f docker-compose.production.yml --env-file .env.production up -d --build

# 查看状态
docker compose -f docker-compose.production.yml ps

# 查看日志
docker compose -f docker-compose.production.yml logs -f app

# 停止服务
docker compose -f docker-compose.production.yml down
```

**统一镜像架构：**
```
┌─────────────────────────────────────────┐
│           lightwms-app 容器              │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  │
│  │  Nginx  │──│ Gunicorn│  │ Next.js │  │
│  │  :80    │  │  :8000  │  │  :3000  │  │
│  └────┬────┘  └────┬────┘  └────┬────┘  │
│       │            │            │        │
│       └────────────┴────────────┘        │
│              Supervisor 管理              │
└─────────────────────────────────────────┘
         │                    │
    ┌────▼────┐          ┌────▼────┐
    │PostgreSQL│          │  Redis  │
    │lightwms-db│         │lightwms-│
    └──────────┘          │ redis   │
                          └─────────┘
```

### Option 2: Development Mode (开发环境)

用于开发环境，前端和后端分开运行：

```bash
# 启动后端服务（数据库、Redis、Django）
docker compose up -d

# 启动前端开发服务器
cd frontend
npm install
npm run dev
```

访问地址：
- Frontend: http://localhost:3000/
- Backend API: http://localhost:8000/api/v1/

---

## Configuration

### Required Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | Django 密钥（必须修改） | (required) |
| `POSTGRES_PASSWORD` | 数据库密码（必须修改） | (required) |
| `ALLOWED_HOSTS` | 允许的主机名（逗号分隔） | localhost |

### Optional Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `CORS_ALLOWED_ORIGINS` | CORS 允许的源 | http://localhost |
| `CSRF_TRUSTED_ORIGINS` | CSRF 信任的源 | http://localhost |
| `HTTP_PORT` | HTTP 端口 | 80 |
| `SECURE_SSL_REDIRECT` | 强制 HTTPS | False |
| `CREATE_SUPERUSER` | 首次启动创建管理员 | false |
| `DJANGO_SUPERUSER_USERNAME` | 管理员用户名 | admin |
| `DJANGO_SUPERUSER_PASSWORD` | 管理员密码 | admin123 |

---

## Management Commands

### 服务管理

```bash
# 启动服务
docker compose -f docker-compose.production.yml up -d

# 停止服务
docker compose -f docker-compose.production.yml down

# 重启服务
docker compose -f docker-compose.production.yml restart app

# 查看状态
docker compose -f docker-compose.production.yml ps

# 查看日志
docker compose -f docker-compose.production.yml logs -f app
docker compose -f docker-compose.production.yml logs -f db
```

### 数据库管理

```bash
# 进入 Django shell
docker exec -it lightwms-app python /app/backend/manage.py shell

# 运行迁移
docker exec -it lightwms-app python /app/backend/manage.py migrate

# 创建超级用户
docker exec -it lightwms-app python /app/backend/manage.py createsuperuser

# 收集静态文件
docker exec -it lightwms-app python /app/backend/manage.py collectstatic --noinput
```

### 容器内调试

```bash
# 进入应用容器
docker exec -it lightwms-app bash

# 查看 supervisor 状态
docker exec -it lightwms-app supervisorctl status

# 重启单个服务
docker exec -it lightwms-app supervisorctl restart gunicorn
docker exec -it lightwms-app supervisorctl restart nextjs
docker exec -it lightwms-app supervisorctl restart nginx
```

---

## Backup & Restore

### 启用备份服务

```bash
# 使用 --profile backup 启动备份服务
docker compose -f docker-compose.production.yml --profile backup up -d
```

### 手动备份

```bash
# 运行手动备份
docker exec lightwms-backup /scripts/backup.sh daily

# 备份文件位置
ls -la backup_data/
```

### 恢复数据

```bash
# 列出可用备份
docker exec lightwms-backup /scripts/restore.sh --list

# 恢复备份（警告：会覆盖当前数据）
docker exec lightwms-backup /scripts/restore.sh /backups/daily/2024-01-15.sql.gz
```

---

## SSL/HTTPS Setup

### 使用 Let's Encrypt

1. 确保域名已解析到服务器
2. 修改 `.env.production`:
   ```
   ALLOWED_HOSTS=your-domain.com
   CORS_ALLOWED_ORIGINS=https://your-domain.com
   CSRF_TRUSTED_ORIGINS=https://your-domain.com
   SECURE_SSL_REDIRECT=True
   ```

3. 使用 certbot 或其他工具获取证书

### 使用自签名证书（测试用）

```bash
# 生成自签名证书
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout nginx/ssl/key.pem \
  -out nginx/ssl/cert.pem
```

---

## Troubleshooting

### 检查服务状态

```bash
# 查看所有容器状态
docker compose -f docker-compose.production.yml ps

# 查看应用日志
docker compose -f docker-compose.production.yml logs app

# 查看 supervisor 进程状态
docker exec lightwms-app supervisorctl status
```

### 常见问题

**1. 数据库连接失败**
```bash
# 检查数据库是否就绪
docker exec lightwms-db pg_isready -U lightwms

# 查看数据库日志
docker compose -f docker-compose.production.yml logs db
```

**2. 前端页面空白**
```bash
# 检查 Next.js 是否运行
docker exec lightwms-app supervisorctl status nextjs

# 查看 Next.js 日志
docker exec lightwms-app cat /var/log/lightwms/nextjs_error.log
```

**3. API 返回 502**
```bash
# 检查 Gunicorn 是否运行
docker exec lightwms-app supervisorctl status gunicorn

# 查看 Gunicorn 日志
docker exec lightwms-app cat /var/log/lightwms/gunicorn_error.log
```

**4. 重置所有数据**
```bash
# 停止并删除所有数据卷
docker compose -f docker-compose.production.yml down -v

# 重新启动
docker compose -f docker-compose.production.yml up -d
```

---

## Development & Testing

### 运行测试（使用 PostgreSQL）

```bash
# 启动数据库
docker compose up -d db

# 设置环境变量并运行测试
export DATABASE_URL=postgres://lightwms:lightwms_secret@localhost:5432/lightwms_test
cd backend
python -m pytest
```

### CI 配置示例

```yaml
# GitHub Actions
services:
  postgres:
    image: postgres:15-alpine
    env:
      POSTGRES_DB: lightwms_test
      POSTGRES_USER: lightwms
      POSTGRES_PASSWORD: lightwms_secret
    ports:
      - 5432:5432

env:
  DATABASE_URL: postgres://lightwms:lightwms_secret@localhost:5432/lightwms_test
```

---

## Architecture

### 生产环境架构（统一镜像）

```
                    ┌─────────────────────────────────────────┐
                    │           lightwms-app                   │
   HTTP :80         │  ┌─────────────────────────────────┐    │
────────────────────┼──│            Nginx                │    │
                    │  │  - 静态文件服务                   │    │
                    │  │  - 反向代理                      │    │
                    │  └──────────┬──────────┬───────────┘    │
                    │             │          │                 │
                    │      ┌──────▼──────┐  ┌▼───────────┐    │
                    │      │  Gunicorn   │  │  Next.js   │    │
                    │      │  Django API │  │  Frontend  │    │
                    │      │   :8000     │  │   :3000    │    │
                    │      └──────┬──────┘  └────────────┘    │
                    │             │                            │
                    │      ┌──────▼──────┐                    │
                    │      │ Supervisor  │                    │
                    │      │ 进程管理     │                    │
                    │      └─────────────┘                    │
                    └─────────────────────────────────────────┘
                              │                    │
                    ┌─────────▼─────────┐  ┌──────▼──────┐
                    │    PostgreSQL     │  │    Redis    │
                    │   lightwms-db     │  │lightwms-redis│
                    └───────────────────┘  └─────────────┘
```

### 数据卷

| Volume | Description |
|--------|-------------|
| `postgres_data` | PostgreSQL 数据 |
| `redis_data` | Redis 持久化数据 |
| `media_data` | 上传的媒体文件 |
| `static_data` | Django 静态文件 |
| `logs_data` | 应用日志 |
| `backup_data` | 数据库备份 |
