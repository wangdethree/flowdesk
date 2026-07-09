# Day 1：Django 项目骨架

## 今天完成了什么

- 创建独立的 Python 虚拟环境 `.venv/`。
- 安装最小后端依赖：
  - Django
  - Django REST framework
  - djangorestframework-simplejwt
- 创建 Django 项目配置包：`config/`。
- 创建三个业务模块：
  - `apps.common`：通用视图和工具。
  - `apps.users`：用户和认证相关功能。
  - `apps.tickets`：工单流转相关功能。
- 添加健康检查接口：`GET /api/health/`。
- 完成 Django 项目检查和数据库迁移。

## 常用命令

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python manage.py check
.venv/bin/python manage.py migrate
.venv/bin/python manage.py runserver 127.0.0.1:8000 --noreload
curl http://127.0.0.1:8000/api/health/
```

健康检查的预期返回：

```json
{"status":"ok","service":"flowdesk","message":"FlowDesk API is running."}
```

## 需要理解的文件

`manage.py`

Django 项目的命令行入口。我们用它启动服务、创建迁移、执行迁移、创建 app 和运行测试。

`config/settings.py`

项目配置中心。这里会配置已安装 app、中间件、数据库、时区、语言和 DRF 设置。

`config/urls.py`

项目级路由入口。请求会先进入这里，再由 Django 分发到对应 app 的路由或视图。

`apps/common/views.py`

定义 `HealthCheckView`，用于验证后端可以正常返回 JSON。

`apps/common/urls.py`

定义 common app 的路由，把 `health/` 映射到 `HealthCheckView`。

## 核心概念

### 什么是 Django project？

Django project 是整个后端服务。当前项目里，`config/` 负责全局配置和项目级路由。

### 什么是 Django app？

Django app 是项目里的业务模块。FlowDesk 里，`users` 负责用户和认证，`tickets` 负责工单流转。

### 什么是 DRF？

Django REST framework 是基于 Django 的 REST API 开发库。它提供序列化器、视图、权限、认证、分页和路由等能力。

### 什么是健康检查？

健康检查是一个简单接口，用来确认后端服务是否正常运行。真实项目里，监控系统经常会调用这类接口。

## 面试题

1. Django project 和 Django app 有什么区别？
2. `manage.py` 是做什么的？
3. `INSTALLED_APPS` 的作用是什么？
4. Django 里一次请求是怎么找到对应 view 的？
5. 为什么后端项目要使用虚拟环境？
6. 健康检查接口有什么作用？
7. Django REST framework 是用来做什么的？

## 简短回答

1. project 是整个服务，app 是其中的功能模块。
2. `manage.py` 用来执行 `runserver`、`migrate`、`startapp` 等管理命令。
3. `INSTALLED_APPS` 告诉 Django 当前项目需要加载哪些 app。
4. Django 会用请求路径匹配 URL 路由，然后调用对应 view。
5. 虚拟环境可以隔离单个项目的依赖，避免不同项目互相影响。
6. 健康检查用于验证服务是否能正常响应。
7. DRF 可以帮助 Django 更高效地开发 RESTful JSON API。

## 面试时怎么讲今天的内容

我用 Django 和 Django REST framework 初始化了 FlowDesk 后端项目，把代码按 common、users、tickets 三个 app 拆分，并在 Django 配置里完成注册。同时添加了一个公开健康检查接口，用来验证项目路由和 DRF JSON 响应链路是否正常。
