# LightWMS 轻量级仓库管理系统

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![Node.js](https://img.shields.io/badge/Node.js-22+-green.svg)](https://nodejs.org/)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://www.docker.com/)

LightWMS 是一个轻量级仓库管理系统，支持物品、借还、领用补货、扫码、发票、审计、角色权限和系统设置。

## DockerHub 快速部署

当前默认部署方式是 **本地/局域网 IP + 端口直接访问**：

```text
浏览器 -> http://NAS或主机IP:3000 -> Next.js frontend -> Docker 内网 backend:8000
```

默认部署 **不启动 Nginx、不映射容器 80 端口、不把浏览器重定向到其他端口**。API 和上传文件都由前端同源转发，因此浏览器只需要访问一个端口。

```bash
# 1. 克隆仓库
git clone https://github.com/liheng-lk/lightwms.git
cd lightwms

# 2. 创建环境变量
cp docker/.env.example .env
# 必须修改 SECRET_KEY 和 POSTGRES_PASSWORD

# 3. 推荐固定正式版本
# .env 中设置：LIGHTWMS_VERSION=1.2.1

# 4. 启动
docker compose -f docker/compose/docker-compose.dockerhub.yml pull
docker compose -f docker/compose/docker-compose.dockerhub.yml up -d

# 5. 创建管理员
docker compose -f docker/compose/docker-compose.dockerhub.yml exec backend python manage.py createsuperuser
```

局域网访问示例：

```text
http://192.168.1.20:3000
```

如果希望改端口，只修改 `.env`：

```text
HTTP_PORT=18080
```

然后访问：

```text
http://192.168.1.20:18080
```

## HTTP / HTTPS Cookie

本地 IP+端口默认是 HTTP，因此：

```text
SECURE_COOKIES=false
```

只有在浏览器实际通过 HTTPS 访问时才设置：

```text
SECURE_COOKIES=true
```

## Docker 镜像

| 服务 | 正式版本 | 最新版本 |
|---|---|---|
| Backend | `liheng6668/lightwms-backend:1.2.1` | `liheng6668/lightwms-backend:latest` |
| Frontend | `liheng6668/lightwms-frontend:1.2.1` | `liheng6668/lightwms-frontend:latest` |

生产环境建议固定 `LIGHTWMS_VERSION=1.2.1`，确认升级后再切换版本。

## 功能

- 物品、分类、仓库、库位管理
- 借用、归还、领用、补货
- 条码扫码与批量导入导出
- 发票管理与报销清单导出
- 用户、角色和邀请码
- 审计日志和登录日志
- 系统 Logo 与设置
- 移动端适配

## 生产安全

- 发票附件属于私有业务文件，不能通过公开 `/media/invoices/*` 直接读取；管理人员查看发票时会经过登录和角色权限校验。
- 发票上传不仅检查扩展名和大小，还校验 PDF/JPG/PNG 的文件签名，降低伪装文件上传风险。
- 删除存在业务历史的用户时保留外键历史，但会禁用账户、失效令牌并匿名化不再需要的个人信息。
- `/api/v1/health/` 同时检查 PostgreSQL 和缓存依赖，关键依赖异常时返回 503，供 Docker 健康检查使用。
- 数据库与上传文件应一起备份。备份与恢复说明见 [BACKUP_RESTORE.md](BACKUP_RESTORE.md)。

## 技术栈

| 类型 | 技术 |
|---|---|
| 前端 | Next.js 16, React 19, TypeScript |
| 后端 | Django 4.2, Django REST Framework |
| 数据库 | PostgreSQL 15 |
| 缓存 | Redis 7 |
| 部署 | Docker Compose |

详细部署说明见 [DEPLOYMENT.md](DEPLOYMENT.md)。

## 安全

- 修改默认 `SECRET_KEY` 和 PostgreSQL 密码
- 不公开固定管理员密码或邀请码
- 互联网暴露时使用 HTTPS
- HTTPS 部署时设置 `SECURE_COOKIES=true`
- 定期备份 PostgreSQL 与上传文件，并执行恢复演练

## License

MIT License
