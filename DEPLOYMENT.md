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

浏览器始终只访问 `IP:端口`。前端将 `/api/wms/*` 和媒体请求转发到 Docker 内部 backend，不向浏览器暴露 8000，也不经过容器 80 端口。

从 1.2.1 开始，物品图片和 Logo 可以继续通过普通媒体路径读取；发票附件属于私有业务文件，`/media/invoices/*` 会被拒绝，前端会自动改走带登录令牌和角色校验的私有发票接口。

## DockerHub 部署

### 1. 创建配置

```bash
cp docker/.env.example .env
```

至少修改：

```text
SECRET_KEY=<随机长密钥>
POSTGRES_PASSWORD=<高强度密码>
LIGHTWMS_VERSION=1.2.1
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

默认部署不包含 `lightwms-nginx`。

后端健康检查会同时验证 PostgreSQL 和 Redis/缓存。任一关键依赖异常时 `/api/v1/health/` 返回 HTTP 503，使 Docker 不会把依赖异常的后端误判为健康。

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
LIGHTWMS_VERSION=1.2.1

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

## 媒体与发票文件

上传图片、Logo 和发票文件都保存在 `media_data` volume 中，但访问权限不同：

- `items/*`、Logo 等普通展示资源可以通过 `/media/*` 读取；
- `invoices/*` 不允许从公开媒体路由直接读取；
- 管理员在发票页面点击“查看文件”时，由 Next.js 同源接口携带登录令牌访问 Django 私有发票接口；
- 发票响应使用 `private, no-store`，避免共享缓存保存发票内容。

发票上传会校验扩展名、大小和 PDF/JPG/PNG 文件签名，不能只通过修改扩展名上传伪装文件。

## 数据持久化

默认 volumes：

| Volume | 用途 |
|---|---|
| `postgres_data` | PostgreSQL 业务数据 |
| `redis_data` | Redis 缓存/持久化数据 |
| `media_data` | 上传图片、Logo、发票等文件 |

升级镜像不会删除这些数据卷。

## 备份与恢复

数据库和 `media_data` 必须作为同一套业务数据进行备份。仓库提供：

```bash
bash docker/backup.sh
```

恢复需要显式确认：

```bash
bash docker/restore.sh ./backups/YYYYMMDD_HHMMSS --yes
```

恢复脚本会先校验 SHA256，并自动创建一次恢复前安全备份。详细说明见 [BACKUP_RESTORE.md](BACKUP_RESTORE.md)。

备份可能包含发票和个人信息，请保存在受访问控制或加密的存储位置，并至少保留一个与运行主机不同的副本。

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

当前版本登录跳转直接沿用浏览器当前 origin，例如：

```text
http://192.168.1.20:3000
```

不会因为反向代理兼容逻辑去掉 3000/8000。

## HTTPS

如果以后需要公网 HTTPS，可以在 LightWMS 外部自行放置反向代理或隧道。LightWMS 本身仍保持 frontend 作为唯一应用入口。HTTPS 场景请设置：

```text
SECURE_COOKIES=true
```

并确保外部代理保留正确的 `Host` 和 HTTPS 协议头。