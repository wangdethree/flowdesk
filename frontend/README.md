# FlowDesk Frontend

FlowDesk 前端使用 Vue 3 和 Vite 构建，作为企业工单流转系统的管理后台界面。

## 启动

```bash
npm install
npm run dev
```

默认地址：

```text
http://127.0.0.1:5173/
```

## 后端代理

开发环境下，Vite 会把 `/api` 请求代理到 Django 后端：

```text
http://127.0.0.1:8000
```

因此启动前端前，需要先启动后端：

```bash
.venv/bin/python manage.py runserver
```

## 当前页面

- 登录页
- 统计看板
- 工单中心
- 工单详情和时间线
- 评论和处理记录
- 关闭工单
- 工单评价
- 通知中心

## 构建

```bash
npm run build
```
