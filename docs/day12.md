# Day 12：工单分配接口

## 今天完成了什么

- 新增工单分配接口：`POST /api/tickets/{id}/assign/`。
- 新增 `TicketAssignmentSerializer`，专门校验分配接口入参。
- 新增 `assign_ticket()` service，封装处理人变更逻辑。
- 审计动作新增 `assign`，用于记录分配处理人的操作。
- 补充分配接口测试，覆盖创建人分配、管理员分配、取消分配、无权限转派、非法处理人。

## 接口说明

分配处理人：

```http
POST /api/tickets/1/assign/
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "assignee": 2
}
```

取消分配：

```http
POST /api/tickets/1/assign/
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "assignee": null
}
```

响应会返回完整工单数据，前端可以直接用响应刷新详情页。

## 为什么不用普通 PATCH？

普通 `PATCH /api/tickets/{id}/` 适合修改标题、描述、状态等通用字段。

但“分配处理人”本身是一个明确业务动作，它通常有独立权限、独立审计日志，也可能触发通知、站内信、Agent 分派等后续流程。

所以我们单独设计：

```text
POST /api/tickets/{id}/assign/
```

这样接口语义更清楚，后续扩展也更方便。

## 权限规则

当前规则：

- 管理员可以分配任意工单。
- 工单创建人可以分配自己创建的工单。
- 当前处理人可以处理工单，但不能把工单转派给别人。
- 无关用户连工单都不可见，所以请求会返回 404。

这里有一个小细节：无关用户返回 404，而不是 403。

原因是后端先通过 `get_queryset()` 限制当前用户可见范围。无关用户查不到这张工单，就像资源不存在一样，可以减少业务数据泄露。

## 为什么要新增 Serializer？

分配接口只需要一个字段：

```json
{
  "assignee": 2
}
```

它和完整工单创建/更新的字段不一样，所以单独写 `TicketAssignmentSerializer`：

```python
class TicketAssignmentSerializer(serializers.Serializer):
    assignee = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        allow_null=True,
        required=True,
    )
```

这样可以保证：

- 处理人 ID 必须是真实用户。
- `assignee=null` 可以表达取消分配。
- 入参结构更简单，错误提示也更聚焦。

## 为什么要写 service？

这次新增了：

```python
assign_ticket(ticket=ticket, assignee=assignee)
```

View 负责 HTTP、权限、响应；service 负责业务状态变化。

这样拆开后，后续如果要在别的地方复用分配逻辑，比如：

- 管理后台批量分配。
- 定时任务自动分配。
- Agent 根据工单内容推荐处理人。

都可以直接调用 service，而不是复制接口代码。

## 审计日志记录了什么？

分配处理人后，会写入一条审计日志：

```json
{
  "old_assignee_id": null,
  "new_assignee_id": 2
}
```

这样以后排查问题时，可以知道某张工单什么时候从谁手里转给了谁。

## 面试题

1. 为什么分配处理人要做成独立接口？
2. 为什么当前处理人不能随便转派工单？
3. 为什么无关用户访问别人工单时返回 404？
4. Serializer 在分配接口里起什么作用？
5. service 层和 View 层分别负责什么？
6. 审计日志里为什么要记录 old 和 new？

## 简短回答

1. 分配是明确业务动作，有独立权限和审计，单独接口语义更清楚。
2. 防止普通处理人绕过创建人或管理员的调度规则。
3. 后端先限制可见数据范围，无权用户查不到资源，返回 404 可以减少数据泄露。
4. Serializer 校验处理人是否存在，并允许 `null` 表示取消分配。
5. View 处理请求、权限、响应；service 处理可复用的业务状态变化。
6. 记录 old 和 new 可以追踪工单处理人变化过程，方便排查和追责。

## 面试时怎么讲今天的内容

我给 FlowDesk 增加了一个独立的工单分配接口，而不是继续通过普通 PATCH 修改 assignee。这个接口只允许管理员或工单创建人操作，当前处理人不能自行转派。入参通过独立 Serializer 校验，业务状态变化封装在 service 层，操作完成后会写审计日志，记录旧处理人和新处理人。这样接口语义、权限边界和操作追踪都更清楚。
