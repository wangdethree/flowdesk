# FlowDesk

FlowDesk 是一个基于 Django REST framework 的企业工单流转后端项目。

## Day 1 目标

- 创建 Django 项目骨架。
- 注册 Django REST framework 和项目 app。
- 添加健康检查接口。
- 保持第一版足够小，方便理解和面试讲解。

## 本地启动

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python manage.py migrate
.venv/bin/python manage.py runserver
```

环境变量示例：

```bash
cp .env.example .env
```

健康检查：

```bash
curl http://127.0.0.1:8000/api/health/
```

## Docker 启动

第一版 Docker 主要用于模拟部署环境。容器启动时会先执行数据库迁移，再使用 Gunicorn 启动服务。

```bash
docker compose up --build
```

容器启动后访问：

```bash
curl http://127.0.0.1:8000/api/health/
```

停止容器：

```bash
docker compose down
```

## MVP 范围

- 用户注册和 JWT 登录。
- 工单增删改查。
- 工单状态流转。
- 评论和处理记录。
- 基础角色权限控制。
- 分页、筛选和搜索。

## 当前接口

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/health/` | 健康检查 |
| GET | `/api/schema/` | OpenAPI schema |
| GET | `/api/docs/` | Swagger UI 接口文档 |
| GET | `/api/redoc/` | ReDoc 接口文档 |
| POST | `/api/users/register/` | 用户注册 |
| POST | `/api/users/login/` | JWT 登录 |
| POST | `/api/users/token/refresh/` | 刷新 access token |
| GET | `/api/users/me/` | 获取当前登录用户信息 |
| GET | `/api/analytics/tickets/summary/` | 工单统计摘要 |
| GET | `/api/notifications/` | 查询当前用户通知列表 |
| GET | `/api/notifications/{id}/` | 查询通知详情 |
| POST | `/api/notifications/{id}/mark-read/` | 标记单条通知为已读 |
| POST | `/api/notifications/mark-all-read/` | 标记当前用户所有通知为已读 |
| GET | `/api/notifications/unread-count/` | 查询当前用户未读通知数 |
| GET | `/api/ticket-tags/` | 查询工单标签列表 |
| POST | `/api/ticket-tags/` | 创建工单标签 |
| GET | `/api/tickets/` | 查询工单列表 |
| POST | `/api/tickets/` | 创建工单 |
| GET | `/api/tickets/{id}/` | 查询工单详情 |
| PUT/PATCH | `/api/tickets/{id}/` | 更新工单 |
| DELETE | `/api/tickets/{id}/` | 删除工单 |
| POST | `/api/tickets/{id}/assign/` | 分配或取消分配工单处理人 |
| POST | `/api/tickets/{id}/close/` | 关闭工单并填写关闭原因 |
| POST | `/api/tickets/{id}/remind/` | 催办工单 |
| POST | `/api/tickets/{id}/reopen/` | 重开已关闭工单并填写重开原因 |
| POST | `/api/tickets/{id}/set-priority/` | 调整工单优先级 |
| POST | `/api/tickets/{id}/set-tags/` | 设置工单标签 |
| POST | `/api/tickets/{id}/watch/` | 关注工单 |
| POST | `/api/tickets/{id}/unwatch/` | 取消关注工单 |
| GET | `/api/tickets/{id}/audit-logs/` | 查询工单操作历史 |
| GET | `/api/tickets/{id}/attachments/` | 查询工单附件列表 |
| POST | `/api/tickets/{id}/attachments/` | 上传工单附件 |
| GET | `/api/tickets/{id}/comments/` | 查询工单评论和处理记录 |
| POST | `/api/tickets/{id}/comments/` | 新增工单评论或处理记录 |

## 当前数据模型

| 模型 | 说明 |
| --- | --- |
| `Ticket` | 工单主表，保存标题、描述、分类、优先级、状态、创建人、处理人、关注人、标签、关闭原因、重开原因和时间字段 |
| `TicketTag` | 工单标签表，用于给工单补充多个横向分类 |
| `TicketComment` | 工单记录表，保存评论和处理记录 |
| `TicketAttachment` | 工单附件表，保存上传文件路径、原始文件名、文件大小和上传人 |
| `AuditLog` | 审计日志表，保存用户对业务资源的关键操作记录 |
| `Notification` | 站内通知表，保存通知接收人、通知类型、已读状态和业务目标 |

## 当前业务规则

- 工单列表默认分页，每页 10 条。
- 普通用户只能看到自己创建、分配给自己或自己关注的工单。
- 管理员可以查看和处理所有工单。
- 创建人可以修改和删除自己的工单。
- 处理人可以查看和处理分配给自己的工单，但不能删除工单。
- 只有管理员或工单创建人可以分配、取消分配处理人。
- 已分配且未完成的工单可以催办，催办会通知处理人并写入审计日志。
- 只有管理员或工单创建人可以调整工单优先级，调整后会通知处理人和关注人。
- 只有管理员或工单创建人可以维护工单标签。
- 工单参与者可以关注或取消关注工单，关注人能收到评论和状态变化通知。
- 工单参与者可以上传和查看附件，单个附件大小限制为 5MB。
- 状态流转受后端限制，关闭和重开必须走专门接口并填写原因。
- 只有管理员或工单创建人可以关闭或重开工单，操作会写入审计日志并通知相关参与者。
- 创建、更新、删除工单以及新增处理记录时，会自动写入审计日志。
- 通知是用户私有数据，普通用户只能查询和标记自己的通知。

## 工单列表查询参数

`GET /api/tickets/` 支持组合查询，例如：

```bash
curl "http://127.0.0.1:8000/api/tickets/?mine=assigned&overdue=true"
```

| 参数 | 说明 |
| --- | --- |
| `status` | 按状态筛选，例如 `open`、`in_progress` |
| `priority` | 按优先级筛选，例如 `low`、`medium`、`high`、`urgent` |
| `category` | 按分类筛选，例如 `bug`、`feature`、`consult`、`other` |
| `creator` | 按创建人用户 ID 筛选 |
| `assignee` | 按处理人用户 ID 筛选 |
| `tag` | 按标签 ID 筛选 |
| `tag_name` | 按标签名称筛选 |
| `mine` | 查询我的工单，支持 `created`、`assigned` 和 `watched` |
| `overdue` | 是否查询超时工单，支持 `true` 和 `false` |
| `has_assignee` | 是否查询已分配工单，支持 `true` 和 `false` |
| `search` | 按标题和描述搜索关键词 |
| `ordering` | 排序字段，例如 `-created_at` |

## 通知列表查询参数

`GET /api/notifications/` 支持按已读状态、通知类型和关键词筛选，例如：

```bash
curl "http://127.0.0.1:8000/api/notifications/?is_read=false&notification_type=ticket_reminded"
```

| 参数 | 说明 |
| --- | --- |
| `is_read` | 是否查询已读通知，支持 `true` 和 `false` |
| `notification_type` | 按通知类型筛选，例如 `ticket_assigned`、`ticket_commented`、`ticket_reminded` |
| `search` | 按通知标题和内容搜索关键词 |
| `ordering` | 排序字段，例如 `-created_at` 或 `read_at` |
