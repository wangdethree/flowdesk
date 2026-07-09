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

健康检查：

```bash
curl http://127.0.0.1:8000/api/health/
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
| POST | `/api/users/register/` | 用户注册 |
| POST | `/api/users/login/` | JWT 登录 |
| POST | `/api/users/token/refresh/` | 刷新 access token |
| GET | `/api/users/me/` | 获取当前登录用户信息 |
| GET | `/api/tickets/` | 查询工单列表 |
| POST | `/api/tickets/` | 创建工单 |
| GET | `/api/tickets/{id}/` | 查询工单详情 |
| PUT/PATCH | `/api/tickets/{id}/` | 更新工单 |
| DELETE | `/api/tickets/{id}/` | 删除工单 |
| GET | `/api/tickets/{id}/comments/` | 查询工单评论和处理记录 |
| POST | `/api/tickets/{id}/comments/` | 新增工单评论或处理记录 |

## 当前数据模型

| 模型 | 说明 |
| --- | --- |
| `Ticket` | 工单主表，保存标题、描述、分类、优先级、状态、创建人、处理人和时间字段 |
| `TicketComment` | 工单记录表，保存评论和处理记录 |

## 当前业务规则

- 工单列表默认分页，每页 10 条。
- 普通用户只能看到自己创建或分配给自己的工单。
- 管理员可以查看和处理所有工单。
- 创建人可以修改和删除自己的工单。
- 处理人可以查看和处理分配给自己的工单，但不能删除工单。
- 状态流转受后端限制，已关闭工单不能直接改回待处理。
