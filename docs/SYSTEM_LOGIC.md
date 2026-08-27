# LightWMS 系统逻辑框架

> 本文档用于代码审计与后续维护。目标不是描述页面，而是明确每一条业务请求经过哪些权限边界、校验层、事务和数据副作用。

## 1. 总体架构

```mermaid
flowchart LR
    U[浏览器用户] -->|HTTP/HTTPS :3000| N[Next.js Frontend]
    N --> M[Next Middleware\n页面登录门禁]
    N --> A[/api/auth/*\nHttpOnly Cookie BFF]
    N --> W[/api/wms/*\n业务 API 代理]
    N --> PM[/api/media/*\n公开媒体代理]

    A -->|登录/刷新/退出| D[Django REST API :8000]
    W -->|Bearer Access Token| D
    PM -->|仅公开媒体| D

    D --> AUTH[Custom JWT Authentication]
    AUTH --> RBAC[DRF Permission / Role Scope]
    RBAC --> V[View / Query Validation]
    V --> S[Service / transaction.atomic]
    S --> DB[(PostgreSQL)]
    S --> R[(Redis Cache)]
    S --> FS[(media volume)]
    S --> AUD[(Audit / Login Logs)]

    D --> INVFILE[Authenticated Invoice File API]
    INVFILE --> FS
```

### 核心边界

1. 浏览器不直接持有 JS 可读 JWT；access/refresh token 存在 HttpOnly Cookie。
2. Next.js BFF 从 Cookie 读取 token，再以 Authorization Bearer 转给 Django。
3. Django 是最终权限边界；前端隐藏按钮只用于体验，不能替代后端权限。
4. PostgreSQL 是业务事实来源；Redis 只承担缓存/限流，不应成为唯一业务数据源。
5. `media` 中普通图片可公开，发票附件必须经过鉴权接口读取。
6. 所有安全敏感操作必须同时考虑数据库状态、JWT 会话、审计日志和磁盘文件副作用。

## 2. 登录与 JWT 生命周期

```mermaid
sequenceDiagram
    participant B as Browser
    participant N as Next /api/auth/login
    participant D as Django LoginView
    participant S as AuthService
    participant DB as PostgreSQL
    participant R as Redis

    B->>N: username + password
    N->>D: POST /api/v1/auth/login/
    D->>S: login(username,password,ip,ua)
    S->>R: login rate-limit check
    S->>DB: authenticate user
    S->>DB: write LoginLog
    S-->>D: access + refresh
    D-->>N: token pair
    N-->>B: Set-Cookie HttpOnly access/refresh
```

### 访问业务接口

```mermaid
sequenceDiagram
    participant B as Browser
    participant P as Next /api/wms/*
    participant D as Django API
    participant J as CustomJWTAuthentication
    participant V as View/Service

    B->>P: API request
    P->>D: Bearer access token
    D->>J: validate signature / exp / user / invalidation
    J-->>D: authenticated user
    D->>V: permission + input + business logic
    V-->>D: response
    D-->>P: response
    P-->>B: response
```

### Access 过期后的刷新

当前后端 refresh token 是**一次性消费并旋转**：旧 refresh 成功刷新后立即进入 blacklist，不能再次使用。因此前端并发刷新必须与这一事实保持一致，不能假定 refresh 是幂等操作。

```mermaid
sequenceDiagram
    participant P1 as Proxy Request A
    participant P2 as Proxy Request B
    participant D as Django Refresh
    participant DB as Outstanding/Blacklist

    P1->>D: same refresh token
    P2->>D: same refresh token
    D->>DB: row lock + consume token
    D-->>P1: new access + new refresh
    D->>DB: second request sees blacklist
    D-->>P2: invalid refresh
```

这条并发链是当前重点审计项，必须避免成功请求与失败请求互相覆盖浏览器 Cookie 状态。

## 3. 密码修改与管理员密码操作

```mermaid
flowchart TD
    LOGIN[已登录用户] --> SELF[POST /users/me/change-password]
    SELF --> IA[IsAuthenticated]
    IA --> OLD[校验当前密码]
    OLD --> STRONG[Django password validators]
    STRONG --> TX[事务锁定当前 User]
    TX --> SAVE[set_password + clear must_change_password]
    SAVE --> INVALID[使旧会话失效]
    INVALID --> AUDIT[写 UPDATE AuditLog]
    AUDIT --> RELOGIN[前端清 Cookie并要求新密码重新登录]

    ADMIN[Super Admin] --> OTHER[/users/id/set-password or reset-password]
    OTHER --> SA[IsSuperAdmin]
    SA --> TARGET[锁定目标用户]
    TARGET --> SAVE2[设置/重置密码]
    SAVE2 --> INVALID2[目标用户旧会话失效]
    INVALID2 --> AUDIT2[审计]
```

权限规则：

| 操作 | Super Admin | Item Manager | 普通用户 |
|---|---:|---:|---:|
| 修改自己的密码 | 是 | 是 | 是 |
| 修改他人密码 | 是 | 否 | 否 |
| 重置他人临时密码 | 是 | 否 | 否 |
| 修改角色 | 是（不能改自己） | 否 | 否 |
| 启用/禁用用户 | 是（不能禁用自己） | 否 | 否 |
| 删除用户 | 是（不能删除自己） | 否 | 否 |

## 4. 用户注册与邀请码

```mermaid
flowchart TD
    REG[注册请求] --> SER[Serializer\n用户名/密码/邮箱等格式]
    SER --> INV[InviteCodeService.validate_and_use]
    INV --> LOCK[select_for_update 邀请码]
    LOCK --> CHECK[active / expiry / usage]
    CHECK --> INC[current_uses + 1]
    INC --> IDENT[用户名/手机号唯一性]
    IDENT --> CREATE[创建 User]
    CREATE --> LOG[Invite-use AuditLog]
    LOG --> COMMIT[事务提交]

    WX[微信注册路径] --> STATE[一次性 OAuth state]
    STATE --> SESSION[临时 WechatSession]
    SESSION --> REG
```

注意：当前微信 provider exchange 仍是 mock 实现，不能把它当成真实微信身份认证能力。

## 5. 角色与业务权限总图

```mermaid
flowchart LR
    SA[Super Admin] --> SYS[系统级管理]
    SA --> INV[库存管理]
    SA --> FIN[发票/报销]
    SA --> AUD[审计]

    IM[Item Manager] --> INV
    IM --> FIN

    U[普通用户] --> READ[库存读取]
    U --> OWN[本人借用/领用相关操作]
```

关键原则：`Item.owner` 是责任/元数据，不应被无意当成全局角色授权的唯一依据；具体接口若需要 owner scope，必须在查询层明确实现并有测试。

## 6. 库存主数据逻辑

```mermaid
flowchart TD
    REQ[前端请求] --> API[/items categories locations warehouses/]
    API --> QV[参数/权限校验 View]
    QV --> SERV[Inventory Service]
    SERV --> TX[transaction.atomic when mutating]
    TX --> ITEM[(Item)]
    TX --> LOC[(Location)]
    LOC --> WH[(Warehouse)]
    ITEM --> CAT[(Category)]
    TX --> AUDIT[AuditLog]
```

审计重点：
- 新旧 `views.py` 与 `validated/permission/atomic` wrapper 是否存在绕过路径。
- quantity/status/type 之间是否有数据库与 service 双层不变量。
- 删除/停用主数据时历史业务 FK 是否安全。
- list/search/scan/detail 的权限和 borrower 隐私是否一致。

## 7. 借用 / 归还

```mermaid
stateDiagram-v2
    [*] --> Available
    Available --> Borrowed: borrow quantity
    Borrowed --> Borrowed: partial return / other active borrows
    Borrowed --> Available: all active quantity returned

    state BorrowRecord {
      [*] --> Active
      Active --> Returned
      Active --> Overdue: due date passed (derived)
    }
```

写操作必须核对：
- item 类型是否允许借用；
- 可借数量是否足够；
- 并发请求是否锁行；
- return quantity 不超过 active borrowed quantity；
- Item quantity 与 BorrowRecord 汇总不矛盾；
- 操作失败时 audit / DB 不出现半提交。

## 8. 领用 / 补货

```mermaid
flowchart LR
    STOCK[(Consumable Item Quantity)] --> TAKE[Take]
    TAKE -->|quantity - n| STOCK
    STOCK --> REPLENISH[Replenish]
    REPLENISH -->|quantity + n| STOCK
    TAKE --> TL[(TakeRecord)]
    REPLENISH --> RL[(ReplenishRecord)]
```

重点检查负库存、整数边界、并发丢失更新、ledger 与 item 数量原子一致性。

## 9. 发票生命周期

```mermaid
flowchart TD
    UP[上传 PDF/JPG/PNG] --> MAGIC[扩展名 + magic bytes]
    MAGIC --> STORE[media/invoices/...]
    STORE --> DB[(Invoice row)]
    DB --> VIEW[Authenticated private file endpoint]
    VIEW --> RBAC[Item Manager / Super Admin]
    RBAC --> FILE[FileResponse]

    DB --> ZIP[ZIP export]
    ZIP --> PATH[resolve under MEDIA_ROOT]
    PATH --> NAME[上传人+发票名+金额]

    DB --> DEL[delete invoice]
    DEL --> AUD[delete audit]
    AUD --> COMMIT[DB commit]
    COMMIT --> FSDEL[on_commit delete file]
```

公开 `/media/*` 必须拒绝 `invoices/` 前缀。

## 10. 导入 / 导出

```mermaid
flowchart TD
    FILE[Excel/CSV] --> PARSE[格式/大小/字段解析]
    PARSE --> VALIDATE[逐行校验]
    VALIDATE --> TX[事务写入]
    TX --> RESULT[成功/失败明细]

    DB[(Business Data)] --> EXPORT[Export Service]
    EXPORT --> XLSX[Excel/CSV/ZIP]
```

审计重点是公式注入、文件内容伪装、重复主键、部分导入、错误行导致的事务语义和导出数据权限。

## 11. 审计日志

```mermaid
flowchart LR
    ACTION[业务写操作] --> AUDIT[AuditLog.objects.create]
    AUDIT --> SAN[敏感字段递归脱敏]
    SAN --> PG[(PostgreSQL)]
    PG --> IMMUTABLE[DB trigger 禁止 UPDATE/DELETE]
    PG --> READ[Super Admin read APIs]
    READ --> SAN2[Serializer 二次脱敏]
```

## 12. 设置 / Logo

系统设置写入只允许 Super Admin。远程 Logo URL、本地图片/SVG 必须经过 URL、真实格式、SVG 活动内容、路径边界和事务文件生命周期校验。

## 13. 备份 / 恢复

```mermaid
flowchart TD
    START[backup.sh] --> PGDUMP[pg_dump]
    START --> MEDIA[tar media]
    PGDUMP --> HASH[SHA256 manifest]
    MEDIA --> HASH

    RESTORE[restore.sh] --> VERIFY[verify SHA256]
    VERIFY --> PRE[pre-restore backup]
    PRE --> STOP[stop frontend traffic]
    STOP --> DBR[restore PostgreSQL]
    DBR --> HEALTH[backend health]
    HEALTH --> MEDIAR[restore media]
    MEDIAR --> STARTF[start frontend]
```

## 14. 发布链

```mermaid
flowchart LR
    PR[Feature/Fix PR] --> CI[Backend tests + Frontend build + Docker smoke]
    CI -->|green| MAIN[merge main]
    MAIN -->|release: commit| REL[DockerHub Release]
    REL --> B[backend:VERSION + latest]
    REL --> F[frontend:VERSION + latest]
    B --> VERIFY[docker pull verify]
    F --> VERIFY
```

## 15. 代码审计顺序

1. 认证 / 用户 / JWT / RBAC
2. Inventory 主数据与查询
3. 借用 / 归还
4. 领用 / 补货
5. 发票 / 私有文件 / 导出
6. Import / Export
7. Audit / Settings
8. Frontend API BFF / React Query / 页面权限契约
9. Docker / Compose / Backup / Restore / Release
10. 全量边界与并发回归

每一阶段必须满足：发现可复现 -> 加失败测试 -> 最小修复 -> 全模块回归 -> CI/Docker 验证，才标记完成。
