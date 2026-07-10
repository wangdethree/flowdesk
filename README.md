# FlowDesk

FlowDesk 是一个基于 Django REST framework 的企业工单流转后端项目。

项目面向企业内部 IT 支持、业务问题处理、需求咨询等场景，提供从工单创建、分配、处理、关闭、评价到统计分析的一套完整后端能力。

## 技术栈

- Python 3.11
- Django 5
- Django REST framework
- Simple JWT
- drf-spectacular
- SQLite，本地开发默认数据库
- Gunicorn
- Docker Compose
- Vue 3
- Vite

## 核心能力

- 用户注册、JWT 登录、资料更新和修改密码。
- 工单 CRUD、分页、搜索、筛选和排序。
- 工单分配、优先级调整、催办、关注、标签管理。
- 工单评论、处理记录、附件上传和时间线聚合。
- 工单关闭、重开、评价和评价统计。
- 站内通知、已读管理、未读数、通知筛选和已读清理。
- 审计日志，记录关键业务操作。
- OpenAPI、Swagger UI 和 ReDoc 接口文档。
- 自动化测试覆盖主要业务规则。

## 业务流程

```text
用户创建工单
  -> 创建人或管理员分配处理人
  -> 处理人更新状态、补充处理记录、上传附件
  -> 参与者可关注、评论、催办
  -> 创建人或管理员关闭工单并填写原因
  -> 创建人对已关闭工单进行评价
  -> 统计接口汇总工单数量、分布和评价指标
```

## 目录结构

```text
apps/
  analytics/      工单统计摘要
  audit/          审计日志
  common/         健康检查和公共能力
  notifications/ 站内通知
  tickets/        工单主业务
  users/          用户和认证
config/           Django 项目配置
frontend/         Vue 前端管理界面
```

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

接口文档：

- Swagger UI: `http://127.0.0.1:8000/api/docs/`
- ReDoc: `http://127.0.0.1:8000/api/redoc/`
- OpenAPI schema: `http://127.0.0.1:8000/api/schema/`

## 快速验收

本地启动后，可以按下面顺序快速确认核心能力：

1. 访问 `/api/health/`，确认服务可用。
2. 访问 `/api/docs/`，查看 Swagger UI。
3. 注册用户并登录，拿到 JWT access token。
4. 创建工单，再依次测试分配、评论、附件、关闭、评价。
5. 查看 `/api/tickets/{id}/timeline/`，确认工单动态聚合正常。
6. 查看 `/api/analytics/tickets/summary/`，确认统计摘要正常。
7. 启动 `frontend/`，通过 Vue 管理后台完成登录、查看看板和工单详情。
8. 运行 `manage.py test`，确认自动化测试通过。

## 测试

```bash
.venv/bin/python manage.py test
```

常用检查：

```bash
.venv/bin/python manage.py check
.venv/bin/python manage.py makemigrations --check --dry-run
.venv/bin/python manage.py spectacular --file /tmp/flowdesk-schema.yml --validate
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

## 前端启动

前端采用 Vue 3 + Vite，位于 `frontend/` 目录。

```bash
cd frontend
npm install
npm run dev
```

默认访问：

```text
http://127.0.0.1:5173/
```

本地开发时，Vite 会把 `/api` 请求代理到 `http://127.0.0.1:8000`，因此需要先启动 Django 后端。

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
| PATCH | `/api/users/me/` | 更新当前登录用户资料 |
| POST | `/api/users/change-password/` | 当前登录用户修改密码 |
| GET | `/api/analytics/tickets/summary/` | 工单统计摘要，包含数量、分布和评价指标 |
| GET | `/api/notifications/` | 查询当前用户通知列表 |
| GET | `/api/notifications/{id}/` | 查询通知详情 |
| POST | `/api/notifications/{id}/mark-read/` | 标记单条通知为已读 |
| POST | `/api/notifications/mark-all-read/` | 标记当前用户所有通知为已读 |
| GET | `/api/notifications/unread-count/` | 查询当前用户未读通知数 |
| DELETE | `/api/notifications/clear-read/` | 清理当前用户所有已读通知 |
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
| GET | `/api/tickets/{id}/feedback/` | 查询工单评价 |
| POST | `/api/tickets/{id}/feedback/` | 创建或更新工单评价 |
| GET | `/api/tickets/{id}/timeline/` | 查询工单时间线 |

## 当前数据模型

| 模型 | 说明 |
| --- | --- |
| `Ticket` | 工单主表，保存标题、描述、分类、优先级、状态、创建人、处理人、关注人、标签、关闭原因、重开原因和时间字段 |
| `TicketTag` | 工单标签表，用于给工单补充多个横向分类 |
| `TicketComment` | 工单记录表，保存评论和处理记录 |
| `TicketAttachment` | 工单附件表，保存上传文件路径、原始文件名、文件大小和上传人 |
| `TicketFeedback` | 工单评价表，保存关闭后的评分和反馈内容 |
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
- 只有工单创建人可以评价已关闭工单，一张工单只保留一份最终评价。
- 工单评价评分范围为 1 到 5，评价后会写入审计日志并通知处理人。
- 工单统计摘要会按当前用户可见范围计算评价数量、平均分、满意率和评分分布。
- 创建、更新、删除工单以及新增处理记录时，会自动写入审计日志。
- 工单时间线会聚合审计日志、评论、附件和评价，便于前端展示完整动态。
- 通知是用户私有数据，普通用户只能查询和标记自己的通知。
- 清理已读通知只删除当前用户的已读通知，不影响未读通知和其他用户通知。
- 用户可以更新自己的邮箱、名和姓；修改密码必须提供正确旧密码。

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

## 工单统计摘要

`GET /api/analytics/tickets/summary/` 会返回当前用户可见范围内的统计数据。

普通用户只统计自己创建、分配给自己或自己关注的工单；管理员统计全部工单。

响应里包含：

- 工单总数、我创建的数量、分配给我的数量、超时数量。
- 按状态、优先级、分类分组的数量。
- 评价摘要：评价数、平均分、满意率和 1 到 5 星评分分布。

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

## 面试讲解重点

- 权限设计：普通用户只能访问自己创建、分配给自己或自己关注的工单，管理员可以查看全局数据。
- 状态流转：关闭和重开使用专门接口，强制填写原因，避免普通更新绕过业务规则。
- 审计日志：关键操作统一写审计，方便追踪谁在什么时候做了什么。
- 通知系统：业务事件触发站内通知，并支持已读、未读、筛选和清理。
- 数据统计：统计接口复用可见工单范围，避免普通用户通过统计数据看到无权限信息。
- 前后端分离：后端提供 REST API，前端通过 Vue 3 + Vite 调用接口完成管理后台交互。
- 测试覆盖：对权限、状态流转、通知、评价、统计等核心规则都有自动化测试。
