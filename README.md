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

## 当前数据模型

| 模型 | 说明 |
| --- | --- |
| `Ticket` | 工单主表，保存标题、描述、分类、优先级、状态、创建人、处理人和时间字段 |
| `TicketComment` | 工单记录表，保存评论和处理记录 |
