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
| GET | `/api/tickets/` | 查询工单列表 |
| POST | `/api/tickets/` | 创建工单 |
| GET | `/api/tickets/{id}/` | 查询工单详情 |
| PUT/PATCH | `/api/tickets/{id}/` | 更新工单 |
| DELETE | `/api/tickets/{id}/` | 删除工单 |
| POST | `/api/tickets/{id}/assign/` | 分配或取消分配工单处理人 |
| GET | `/api/tickets/{id}/comments/` | 查询工单评论和处理记录 |
| POST | `/api/tickets/{id}/comments/` | 新增工单评论或处理记录 |

## 当前数据模型

| 模型 | 说明 |
| --- | --- |
| `Ticket` | 工单主表，保存标题、描述、分类、优先级、状态、创建人、处理人和时间字段 |
| `TicketComment` | 工单记录表，保存评论和处理记录 |
| `AuditLog` | 审计日志表，保存用户对业务资源的关键操作记录 |

## 当前业务规则

- 工单列表默认分页，每页 10 条。
- 普通用户只能看到自己创建或分配给自己的工单。
- 管理员可以查看和处理所有工单。
- 创建人可以修改和删除自己的工单。
- 处理人可以查看和处理分配给自己的工单，但不能删除工单。
- 只有管理员或工单创建人可以分配、取消分配处理人。
- 状态流转受后端限制，已关闭工单不能直接改回待处理。
- 创建、更新、删除工单以及新增处理记录时，会自动写入审计日志。

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
| `mine` | 查询我的工单，支持 `created` 和 `assigned` |
| `overdue` | 是否查询超时工单，支持 `true` 和 `false` |
| `has_assignee` | 是否查询已分配工单，支持 `true` 和 `false` |
| `search` | 按标题和描述搜索关键词 |
| `ordering` | 排序字段，例如 `-created_at` |
