# LightWMS 全仓库代码审计台账

> 审计规则：不以“看起来能运行”为通过标准。每个结论必须能对应到具体入口、权限、校验、事务、数据副作用和测试。

## 状态定义

- `TODO`：尚未逐文件审计
- `REVIEWING`：正在逐文件/逐分支核对
- `FOUND`：已确认问题，尚未完成修复
- `FIXING`：已有修复分支/PR
- `BLOCKED-CI`：代码修复完成，但 CI 基础设施未产生可用 job/log
- `PASS`：审计完成且回归验证通过

## 审计矩阵

| 阶段 | 模块 | 状态 | 备注 |
|---|---|---|---|
| A | Auth / JWT / User / RBAC | REVIEWING | 第一阶段 |
| B | Inventory master data | TODO | items/categories/locations/warehouses/search/scan |
| C | Borrow / Return | TODO | quantity/state/concurrency/privacy |
| D | Take / Replenish | TODO | stock arithmetic/ledger/atomicity |
| E | Invoice / private files | TODO | upload/read/export/delete/file lifecycle |
| F | Import / Export | TODO | parsing/atomicity/formula/path/data scope |
| G | Audit / Settings | TODO | immutable logs/sanitization/logo/settings |
| H | Frontend BFF / UI contracts | TODO | auth proxy/query/error/permission/form state |
| I | Docker / Backup / Restore / Release | TODO | supported deployment path and stale duplicates |
| J | Full regression / edge / concurrency | TODO | final gate |

## 已确认问题

### AUTH-001 — 非超级管理员没有修改自己密码的前端入口

**状态：BLOCKED-CI / PR #18**

后端 `/api/v1/users/me/change-password/` 使用 `IsAuthenticated`，本来允许全部已登录角色；前端却把唯一的修改密码入口放进 Super Admin-only `/settings`。

修复：独立 `/account` 页面；桌面/移动导航对所有角色显示“账户设置”；系统设置继续仅 Super Admin。

### AUTH-002 — 前后端密码长度规则不一致

**状态：BLOCKED-CI / PR #18**

前端原来允许 6 字符；后端 serializer 最少 8 字符并执行 Django password validators。导致前端认为合法、后端再拒绝。

修复：前端 minimum/文案统一为 8；后端仍为最终校验边界。

### AUTH-003 — 自助改密成功后浏览器仍持有已经失效的 JWT

**状态：BLOCKED-CI / PR #18**

后端改密会更新 `tokens_invalid_before`，旧 access/refresh 均应该失效。原前端只关闭弹窗，下一次 API 请求才突然收到 401。

修复：改密成功立即清浏览器 auth Cookie/React Query 状态并跳转登录页。

### AUTH-004 — Refresh rotation 与前端并发刷新逻辑冲突

**状态：FOUND**

后端通过 outstanding-token 行锁实现 refresh token 一次性消费：两个并发 refresh 只允许一个成功。前端 `/api/wms/*` 每个 401 请求却可独立使用同一个 refresh token；当多个页面请求同时 401 时，一个请求旋转成功，另一个会把 refresh 判为失败并清 Cookie，存在随机登出的竞态。

需要：建立单一 refresh 协调策略，并增加并发代理测试。不能通过放宽后端单次消费来解决，因为 rotation/blacklist 是安全边界。

### AUTH-005 — 浏览器退出登录未调用后端 refresh-token blacklist

**状态：FOUND**

前端 `/api/auth/logout` 当前只清本地 HttpOnly Cookie。正常浏览器体验上已经退出，但若 refresh token 在退出前已泄露，它仍可在服务端保持有效直至过期。

需要：Next logout route 在清 Cookie 前 best-effort 调用 Django `/api/v1/auth/logout/`，发送当前 refresh token；网络/后端异常不能阻止本地退出。

### AUTH-006 — 会话失效依赖 iat 秒级时间并保留 2 秒容差

**状态：FOUND / DESIGN REVIEW**

`CustomJWTAuthentication` 和 `AuthService.refresh` 都允许 `tokens_invalid_before` 前不超过 2 秒签发的旧 token 继续通过。这削弱“修改密码/修改角色后立即使旧会话失效”的语义。

直接把比较改严也会引出同一秒重新登录被误杀的问题，因为 JWT `iat` 是秒级。建议使用明确的 token/session version，而不是继续依赖时间容差；实现前需要 migration + compatibility tests。

### REG-001 — 微信注册用户名校验逻辑错误

**状态：FOUND**

`RegisterSerializer.validate_username()` 使用：

```python
if not value.isalnum() and '_' not in value:
```

只要非法用户名中包含 `_`，第二个条件就为 False，整个判断不成立，例如 `abc_!@#` 会通过 serializer。`SimpleRegisterSerializer` 又使用另一套严格正则，形成双标准。

需要：抽取唯一用户名 validator，供微信注册、普通注册、管理员创建用户三条路径复用，并补合法中文/英文/数字/下划线及非法符号测试。

## 待确认设计项

### AUTH-D01 — Mock WeChat OAuth 是否应在生产默认开放

当前 provider exchange 明确为 mock，并根据 callback code 本地生成 mock openid。它不能视为真实微信身份认证。系统已有 simple invite registration，因此生产环境需要明确：禁用微信入口，或完成真实 provider integration。属于部署/产品安全决策，不先当作代码漏洞处理。

### AUTH-D02 — Invite code 生成的 check-then-create 碰撞

`InviteCodeService._generate_code()` 先查询不存在，再由 caller 创建，两个并发管理员理论上可能生成同一个 code，第二个触发 DB unique IntegrityError。概率很低，但代码可改成数据库唯一约束 + retry 的最终一致实现。待并发测试后决定优先级。

## 第一阶段逐文件清单

### Backend users/core

- [x] `backend/apps/users/models.py`
- [x] `backend/apps/users/serializers.py`
- [x] `backend/apps/users/services/auth_service.py`
- [x] `backend/apps/users/services/user_management_service.py`
- [x] `backend/apps/users/services/registration_service.py`
- [x] `backend/apps/users/services/invite_code_service.py`
- [x] `backend/apps/users/security_views.py`
- [x] `backend/apps/users/urls.py`
- [ ] `backend/apps/users/views.py` — 逐 endpoint 完整复核
- [ ] `backend/apps/users/user_delete_view.py`
- [ ] `backend/apps/users/services/user_deletion_service.py`
- [x] `backend/core/authentication.py`
- [x] `backend/core/permissions.py`
- [x] `backend/core/role_utils.py`
- [ ] `backend/core/middleware.py`
- [ ] `backend/core/exceptions.py`

### Frontend auth/account

- [x] `frontend/src/middleware.ts`
- [x] `frontend/src/providers/auth-provider.tsx`
- [x] `frontend/src/app/api/auth/login/route.ts`
- [x] `frontend/src/app/api/auth/refresh/route.ts`
- [x] `frontend/src/app/api/auth/me/route.ts`
- [x] `frontend/src/app/api/auth/logout/route.ts`
- [x] `frontend/src/app/api/wms/[...path]/route.ts`
- [x] `frontend/src/lib/auth/cookies.ts`
- [x] `frontend/src/components/users/change-password-dialog.tsx` (PR #18 branch)
- [x] desktop/mobile navigation (PR #18 branch)
- [ ] login/register page form rules vs backend serializer
- [ ] user management dialogs vs backend admin endpoints

## 修复纪律

1. 一个问题先写回归测试，再做最小修复。
2. 不因前端隐藏按钮而降低后端权限测试要求。
3. 并发问题必须用 transaction/concurrency test 证明。
4. 文件操作必须验证事务提交/回滚时磁盘生命周期。
5. 新 wrapper 覆盖旧 view 时，必须核对 URL 最终绑定的是哪一个类。
6. 每完成一个阶段更新本台账，并把对应 CI run/PR 写入记录。
7. 正式发布必须经过 backend tests、frontend type/build、Docker smoke test；Actions 无日志/无 steps 的基础设施失败不能算代码失败，也不能算通过。
