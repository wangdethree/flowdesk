# Day 4：工单 CRUD 接口

## 今天完成了什么

- 新增工单序列化器 `TicketSerializer`。
- 新增工单对象权限 `IsTicketParticipantOrStaff`。
- 使用 `ModelViewSet` 实现工单 CRUD。
- 使用 `DefaultRouter` 自动生成 RESTful 路由。
- 支持工单列表搜索、排序和基础筛选。
- 补充工单接口测试。

## 接口清单

| 方法 | 路径 | 作用 |
| --- | --- | --- |
| `GET` | `/api/tickets/` | 查询工单列表 |
| `POST` | `/api/tickets/` | 创建工单 |
| `GET` | `/api/tickets/{id}/` | 查询工单详情 |
| `PUT` | `/api/tickets/{id}/` | 完整更新工单 |
| `PATCH` | `/api/tickets/{id}/` | 局部更新工单 |
| `DELETE` | `/api/tickets/{id}/` | 删除工单 |

## 创建工单示例

请求：

```http
POST /api/tickets/
Authorization: Bearer <access_token>
Content-Type: application/json
```

```json
{
  "title": "电脑无法连接公司网络",
  "description": "连接公司 Wi-Fi 后无法访问内部系统。",
  "category": "bug",
  "priority": "high",
  "assignee": 2
}
```

说明：

- `creator` 不需要前端传，后端会自动使用当前登录用户。
- `assignee` 使用用户 ID，表示工单分配给谁处理。
- `status` 不传时默认是 `open`，也就是待处理。

## 查询示例

按分类筛选：

```http
GET /api/tickets/?category=bug
```

按状态筛选：

```http
GET /api/tickets/?status=open
```

搜索标题和描述：

```http
GET /api/tickets/?search=网络
```

按创建时间倒序：

```http
GET /api/tickets/?ordering=-created_at
```

## 权限规则

第一版采用简单规则：

- 管理员可以查看和修改所有工单。
- 创建人可以查看、修改、删除自己的工单。
- 处理人可以查看和处理分配给自己的工单，但不能删除工单。
- 无关用户看不到这张工单。

这里的权限分成两层：

1. `get_queryset()` 先控制“列表里能看到哪些数据”。
2. `has_object_permission()` 再控制“具体某条工单能不能访问或修改”。

## 核心概念

### 什么是 Serializer？

Serializer 负责接口数据的输入和输出。输入时，它校验前端提交的数据是否合法；输出时，它把数据库模型对象转换成 JSON。

在本项目里，`TicketSerializer` 负责工单的字段校验和响应展示。

### 什么是 ViewSet？

ViewSet 是 DRF 对一组接口操作的封装。`ModelViewSet` 会根据模型和序列化器自动提供列表、创建、详情、更新、删除等能力。

我们使用 `TicketViewSet` 实现工单 CRUD，避免手写一堆重复接口。

### 什么是 Router？

Router 会根据 ViewSet 自动生成 URL。比如注册 `TicketViewSet` 后，DRF 会自动生成 `/api/tickets/` 和 `/api/tickets/{id}/` 这些 RESTful 路由。

### 什么是 `get_queryset()`？

`get_queryset()` 决定当前请求能查到哪些数据。它非常适合做数据隔离，比如普通用户只能看到自己创建或分配给自己的工单。

### 什么是 `perform_create()`？

`perform_create()` 是 DRF 创建对象时的钩子。我们在这里强制把 `creator` 设置成当前登录用户，避免前端伪造创建人。

### 什么是 `select_related()`？

`select_related()` 会在查询工单时顺手把关联的创建人、处理人也查出来，减少后续访问用户名时的数据库查询次数。

## 面试题

1. DRF Serializer 的作用是什么？
2. `ModelViewSet` 能自动提供哪些接口能力？
3. `DefaultRouter` 是做什么的？
4. 为什么创建工单时不能让前端直接传 `creator`？
5. `get_queryset()` 在权限控制里有什么作用？
6. `has_object_permission()` 和 `get_queryset()` 有什么区别？
7. `select_related()` 解决什么问题？
8. `PUT` 和 `PATCH` 有什么区别？

## 简短回答

1. Serializer 负责校验输入数据、保存模型对象和序列化响应。
2. `ModelViewSet` 提供列表、创建、详情、完整更新、局部更新和删除。
3. `DefaultRouter` 根据 ViewSet 自动生成 RESTful URL。
4. 创建人应该由后端根据 token 识别，不能让前端伪造。
5. `get_queryset()` 控制列表和详情查询的基础数据范围。
6. `get_queryset()` 控制能查到什么对象，`has_object_permission()` 控制查到对象后能不能操作。
7. `select_related()` 用一次 SQL 查询带出外键对象，减少额外查询。
8. `PUT` 通常表示完整更新，`PATCH` 表示局部更新。

## 面试时怎么讲今天的内容

我在 FlowDesk 中使用 DRF 的 `ModelViewSet` 实现了工单 CRUD 接口，并通过 `DefaultRouter` 自动生成 RESTful 路由。创建工单时，后端会根据当前登录用户自动设置创建人，避免前端伪造。列表查询里通过 `get_queryset()` 做数据隔离，普通用户只能看到自己创建或分配给自己的工单，管理员可以看到全部工单。同时支持状态、优先级、分类、处理人筛选，以及标题和描述搜索。
