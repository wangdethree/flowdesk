# Day 8：工单统计接口

## 今天完成了什么

- 新增 `apps.analytics` 统计分析模块。
- 新增工单统计服务 `get_ticket_summary()`。
- 新增当前用户可见工单范围函数 `get_visible_ticket_queryset()`。
- 新增统计接口：`GET /api/analytics/tickets/summary/`。
- 补充统计服务测试和统计 API 测试。

## 接口说明

请求：

```http
GET /api/analytics/tickets/summary/
Authorization: Bearer <access_token>
```

响应示例：

```json
{
  "total": 12,
  "created_by_me": 8,
  "assigned_to_me": 4,
  "overdue": 2,
  "by_status": {
    "open": 5,
    "in_progress": 3,
    "resolved": 3,
    "closed": 1
  },
  "by_priority": {
    "low": 1,
    "medium": 6,
    "high": 3,
    "urgent": 2
  },
  "by_category": {
    "bug": 5,
    "feature": 3,
    "consult": 2,
    "other": 2
  }
}
```

## 权限规则

统计接口不能直接统计全表，否则普通用户会看到别人的业务数据。

当前规则：

- 管理员统计全部工单。
- 普通用户只统计自己创建或分配给自己的工单。

这和工单列表接口的数据范围保持一致。

## 为什么单独做 services？

统计逻辑没有直接写在 View 里，而是放在 `apps.analytics.services`：

```python
get_ticket_summary(user)
```

这样做有几个好处：

1. View 只负责处理 HTTP 请求和响应。
2. 统计逻辑可以单独测试。
3. 后续要加 Redis 缓存时，可以在 service 层加，不需要改接口层。
4. 如果以后要做定时统计，也可以复用同一份 service。

## 核心 ORM 写法

按状态分组统计时，用的是：

```python
queryset.values('status').order_by().annotate(count=Count('id'))
```

它大致等价于 SQL：

```sql
SELECT status, COUNT(id)
FROM tickets_ticket
GROUP BY status;
```

注意：数据库只会返回实际存在的分组。为了让接口结构稳定，我们会把没有数据的状态也补成 0。

## 核心概念

### 什么是聚合查询？

聚合查询是对一批数据做统计，比如计数、求和、平均值、最大值、最小值。工单统计里的 `COUNT` 就是典型聚合。

### 什么是分组统计？

分组统计是先按某个字段分组，再分别统计每组数量。比如按 `status` 分组，就能得到每个状态下有多少工单。

### 为什么要补齐 0 值？

如果某个状态当前没有数据，数据库不会返回这一组。但前端更希望响应结构稳定，所以后端把缺失状态补成 0。

### 为什么普通用户不能统计全表？

统计结果本身也可能泄露业务信息。比如普通用户看到“全公司有 100 个紧急工单”，这也是越权数据。

## 面试题

1. 统计接口为什么要做权限隔离？
2. Django ORM 怎么做分组统计？
3. `values().annotate()` 是什么作用？
4. 为什么统计逻辑不直接写在 View 里？
5. 为什么接口要补齐没有数据的枚举值？
6. 统计接口后续怎么接 Redis 缓存？

## 简短回答

1. 统计数据也可能泄露业务信息，所以普通用户只能统计自己可见的数据。
2. 可以用 `values('field').annotate(count=Count('id'))`。
3. `values()` 指定分组字段，`annotate()` 添加聚合结果。
4. 放在 service 层更容易测试和复用，也方便后续加缓存。
5. 补齐 0 值能让响应结构稳定，前端处理更简单。
6. 可以用用户 ID 和筛选条件作为缓存 key，在 service 层先查缓存，未命中再查数据库。

## 面试时怎么讲今天的内容

我在 FlowDesk 中新增了工单统计接口，用于返回当前用户可见范围内的工单总数、超时数量，以及按状态、优先级、分类分组的数量。统计逻辑放在 service 层，接口层只负责调用 service 并返回响应。权限上，普通用户只统计自己创建或分配给自己的工单，管理员可以统计全部工单。分组统计使用 Django ORM 的 `values().annotate(Count())` 实现。
