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
