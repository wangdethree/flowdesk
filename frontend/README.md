# FlowDesk Frontend

FlowDesk 前端使用 Vue 3 和 Vite 构建，作为企业工单流转系统的管理后台界面。

## 启动

```bash
cp .env.example .env
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

附件链接通常以 `/media` 开头，开发环境也会代理到同一个 Django 后端。

因此启动前端前，需要先启动后端：

```bash
.venv/bin/python manage.py runserver
```

如果前端和后端分开部署，可以在 `.env` 里设置：

```bash
VITE_API_BASE_URL=https://your-api.example.com
```

## 当前页面

- 登录页
- 统计看板
- 优先级分布和分类分布
- 工单中心
- 工单多条件筛选
- 工单基础信息编辑
- 工单状态推进
- 工单详情和时间线
- 评论和处理记录
- 分配处理人
- 调整优先级
- 设置标签
- 关注和取消关注工单
- 催办工单
- 关闭工单
- 重开工单
- 附件上传和查看
- 工单评价
- 通知中心
- 通知搜索和类型筛选
- 单条通知已读、全部已读和清理已读通知
- 标签管理
- 账号设置

## 学习重点

- `src/api.js` 是前后端分离里的接口层，负责统一封装 token、请求体和错误处理。
- `src/App.vue` 是第一版管理后台主界面，当前为了学习方便暂时放在一个文件里，后续可以拆成页面组件和业务组件。
- `src/styles.css` 负责统一布局和表单样式，便于先把功能闭环跑通。

## 构建

```bash
npm run build
```
