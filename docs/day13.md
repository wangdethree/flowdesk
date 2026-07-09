# Day 13：工单操作历史接口

## 今天完成了什么

- 新增审计日志序列化器 `AuditLogSerializer`。
- 新增工单操作历史接口：`GET /api/tickets/{id}/audit-logs/`。
- 新增 `AuditLog.for_target()`，统一按业务对象查询审计日志。
- 操作历史接口复用 DRF 分页。
- 补充接口测试，覆盖参与者可见、无关用户不可见、只返回当前工单日志、分页。

## 接口说明

请求：

```http
GET /api/tickets/1/audit-logs/
Authorization: Bearer <access_token>
```

响应示例：

```json
{
  "count": 2,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 10,
      "actor": 2,
      "actor_username": "assignee_api",
      "action": "status_change",
      "action_display": "状态流转",
      "target_type": "Ticket",
      "target_id": "1",
      "description": "变更工单状态",
      "metadata": {
        "old_status": "open",
        "new_status": "in_progress"
      },
      "created_at": "2026-07-09T15:30:00+08:00"
    }
  ]
}
```

## 为什么操作历史挂在工单下面？

审计日志是独立表，但这次接口设计成：

```text
GET /api/tickets/{id}/audit-logs/
```

原因是操作历史依附于某张工单。用户通常是在工单详情页里查看“这张工单发生过什么”，而不是在全局审计日志里搜索。

这样做还有一个好处：可以复用工单权限。

接口内部先调用：

```python
ticket = self.get_object()
```

如果当前用户看不到这张工单，就拿不到对应的操作历史。

## 为什么无关用户返回 404？

普通用户只能看到自己创建或分配给自己的工单。

无关用户访问：

```text
GET /api/tickets/1/audit-logs/
```

如果这张工单不在他的可见范围内，后端会像查询详情一样返回 404。

这样可以避免暴露“这张工单是否存在”这种业务信息。

## AuditLog.for_target() 是什么？

审计日志不是只给工单用的。后续它也可能记录：

- 工单评论操作。
- 用户管理操作。
- Agent 自动处理操作。
- 系统定时任务操作。

所以 `AuditLog` 没有直接写死外键到 `Ticket`，而是保存：

```text
target_type = "Ticket"
target_id = "1"
```

查询某个对象的日志时，统一走：

```python
AuditLog.for_target(ticket)
```

这样可以让审计日志表支持更多业务对象。

## 为什么要分页？

一张工单可能被更新很多次，也可能有很多自动化动作。

如果一次返回全部操作历史，数据量会越来越大。

所以操作历史接口复用项目的默认分页规则，默认每页 10 条。

## Serializer 里为什么加展示字段？

接口里既返回：

```json
"actor": 2
```

也返回：

```json
"actor_username": "assignee_api"
```

原因是 ID 适合程序关联，用户名适合页面展示和调试。

同理，`action` 是程序字段，`action_display` 是给人看的中文动作名称。

## 面试题

1. 审计日志和普通业务日志有什么区别？
2. 为什么操作历史接口要复用工单权限？
3. 为什么无关用户查看操作历史返回 404？
4. `target_type + target_id` 这种设计有什么好处？
5. 为什么操作历史也需要分页？
6. Serializer 里为什么同时返回 ID 和展示字段？

## 简短回答

1. 审计日志用于追踪业务操作，回答谁在什么时候对什么资源做了什么；普通日志更多用于排查程序运行问题。
2. 操作历史属于工单敏感信息，能看工单的人才应该能看它的历史。
3. 返回 404 可以避免泄露资源是否存在。
4. 这种设计让同一张审计表可以记录不同类型业务对象的操作。
5. 操作历史会不断增长，分页可以避免响应过大。
6. ID 方便程序关联，展示字段方便前端页面展示和人工调试。

## 面试时怎么讲今天的内容

我给 FlowDesk 增加了工单操作历史接口，用于查看某张工单的审计日志。接口挂在工单详情下面，通过 `get_object()` 复用工单权限，保证只有工单参与者或管理员能查看。审计日志通过 `target_type + target_id` 关联业务对象，并封装了 `AuditLog.for_target()` 统一查询。接口返回分页结果，同时提供操作人用户名和动作中文展示，方便前端直接展示。
