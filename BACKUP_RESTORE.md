# LightWMS 备份与恢复

LightWMS 的业务数据由两部分组成：PostgreSQL 数据库，以及 `media` 中的上传文件。Redis 仅用于缓存，不作为恢复所必需的业务数据。

## 创建备份

在仓库根目录执行：

```bash
bash docker/backup.sh
```

默认会在 `./backups/YYYYMMDD_HHMMSS/` 中生成：

- `database.dump`：PostgreSQL 自定义格式备份；
- `media.tar.gz`：物品图片、Logo、发票等上传文件；
- `SHA256SUMS`：备份完整性校验；
- `metadata.txt`：备份时间和版本信息。

备份目录默认使用严格文件权限，因为其中可能包含发票和个人信息。完成后应再复制到第二块物理磁盘、NAS 的独立备份目录或加密的异地存储。不要只把备份放在运行 LightWMS 的同一块磁盘上。

如使用非默认 Compose 文件，可设置：

```bash
LIGHTWMS_COMPOSE_FILE=/path/to/compose.yml bash docker/backup.sh
```

## 恢复

恢复会覆盖当前数据库和媒体文件，因此命令必须显式携带 `--yes`：

```bash
bash docker/restore.sh ./backups/20260823_220000 --yes
```

恢复脚本会：

1. 校验 `SHA256SUMS`；
2. 自动再做一次恢复前安全备份；
3. 停止前端和后端业务流量；
4. 恢复 PostgreSQL；
5. 启动后端并通过健康检查；
6. 替换媒体文件；
7. 重启后端和前端。

如果恢复过程中后端无法恢复健康，脚本会停止并保持前端关闭，避免用户继续向异常数据库写入数据。

## 建议的落地策略

实际使用建议至少保留“每日 7 份 + 每周 4 份 + 每月 6 份”中的一个组合，并定期在非生产环境执行恢复演练。只有真正成功恢复过的备份，才可以认为是有效备份。
