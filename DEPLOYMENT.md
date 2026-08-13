# LightWMS 部署指南

## 推荐架构

LightWMS 默认使用单一浏览器入口，不需要额外 Nginx：

```text
浏览器
  |
  | http://主机IP:HTTP_PORT
  v
Next.js frontend :3000
  |
  | Docker 内网
  v
Django backend :8000
  |          |
PostgreSQL    Redis
```

浏览器始终只访问 `IP:端口`。前端将 `/api/wms/*` 和 `/media/*` 转发到 Docker 内部 backend，不向浏览器暴露 8000，也不经过容器 80 端口。

## DockerHub 部署

### 1. 创建配置

```bash
cp docker/.env.example .env
```

至少修改：

```text
SECRET_KEY=<随机长密钥>
POSTGRES_PASSWORD=<高强度密码>
LIGHTWMS_VERSION=1.1.1
HTTP_PORT=3000
SECURE_COOKIES=false
```

本地或局域网通常通过 HTTP 使用 `IP:端口`，因此 `SECURE_COOKIES=false`。只有浏览器实际通过 HTTPS 访问时才设为 `true`。

### 2. 拉取和启动

```bash
docker compose -f docker/compose/docker-compose.dockerhub.yml pull
docker compose -f docker/compose/docker-compose.dockerhub.yml up -d
```

### 3. 查看状态

```bash
docker compose -f docker/compose/docker-compose.dockerhub.yml ps
```

应看到：

- `lightwms-db`
- `lightwms-redis`
- `lightwms-backend`
- `lightwms-frontend`

默认部署不再包含 `lightwms-nginx`。

### 4. 创建管理员

```bash
docker compose -f docker/compose/docker-compose.dockerhub.yml exec backend python manage.py createsuperuser
```

### 5. 浏览器访问

如果主机 IP 是 `192.168.1.20`，默认地址：

```text
http://192.168.1.20:3000
```

若 `.env` 设置：

```text
HTTP_PORT=18080
```

则访问：

```text
http://192.168.1.20:18080
```

页面内部登录跳转会继续保留当前主机和端口，不会主动剥掉 `:3000` 或切到 `:80`。

## 更新版本

```bash
# 修改 .env，例如：
LIGHTWMS_VERSION=1.1.1

# 拉取固定版本并重建容器
docker compose -f docker/compose/docker-compose.dockerhub.yml pull
docker compose -f docker/compose/docker-compose.dockerhub.yml up -d
```

生产环境建议固定版本号，不建议长期跟随 `latest`。

## 常用命令

```bash
# 查看日志
docker compose -f docker/compose/docker-compose.dockerhub.yml logs -f

# 查看前端日志
docker compose -f docker/compose/docker-compose.dockerhub.yml logs -f frontend

# 查看后端日志
docker compose -f docker/compose/docker-compose.dockerhub.yml logs -f backend

# 重启
docker compose -f docker/compose/docker-compose.dockerhub.yml restart

# 停止
docker compose -f docker/compose/docker-compose.dockerhub.yml down
```

## 媒体文件

上传图片和 Logo 保存在 `media_data` volume 中。浏览器访问 `/media/*` 时由 Next.js 同源转发到 backend，因此删除 Nginx 后图片仍通过同一个 `IP:HTTP_PORT` 提供。

## 数据持久化

默认 volumes：

| Volume | 用途 |
|---|---|
| `postgres_data` | PostgreSQL 数据 |
| `redis_data` | Redis 数据 |
| `media_data` | 上传图片和文件 |

升级镜像不会删除这些数据卷。

## 局域网访问排查

### 页面打不开

确认端口映射：

```bash
docker ps --format 'table {{.Names}}\t{{.Ports}}'
```

应看到 frontend 类似：

```text
0.0.0.0:3000->3000/tcp
```

然后在其他局域网设备访问主机真实 IP，而不是 `localhost`。

### 登录后仍回到登录页

本地 HTTP 部署确认：

```text
SECURE_COOKIES=false
```

修改后执行：

```bash
docker compose -f docker/compose/docker-compose.dockerhub.yml up -d --force-recreate frontend
```

### 页面跳转丢端口

v1.1.1 起登录跳转直接沿用浏览器当前 origin，例如：

```text
http://192.168.1.20:3000
```

不会再因为反向代理兼容逻辑去掉 3000/8000。

## HTTPS

如果以后需要公网 HTTPS，可以在 LightWMS 外部自行放置反向代理或隧道。LightWMS 本身仍保持 frontend 作为唯一应用入口。HTTPS 场景请设置：

```text
SECURE_COOKIES=true
```

并确保外部代理保留正确的 `Host`。
