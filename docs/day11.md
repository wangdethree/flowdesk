# Day 11：工单列表高级筛选

## 今天完成了什么

- 新增 `apps.tickets.filters` 模块。
- 将工单列表筛选逻辑从 `TicketViewSet.get_queryset()` 拆到 `TicketFilterBackend`。
- 新增查询参数校验器 `TicketQueryParamSerializer`。
- 支持更多工单列表查询参数：`mine`、`overdue`、`has_assignee`、`creator`。
- 补充工单筛选接口测试，覆盖正常筛选和非法参数。

## 为什么要拆 FilterBackend？

之前工单列表筛选逻辑直接写在 `get_queryset()` 里。第一版这样写可以，但功能变多后会有两个问题：

- `get_queryset()` 同时负责权限范围和业务筛选，职责变混乱。
- 查询参数越来越多时，View 会越来越胖，不利于阅读和测试。

现在的拆法是：

```text
get_queryset()：先圈定当前用户有权限看到哪些工单
TicketFilterBackend：再根据 URL 查询参数做二次筛选
```

这样职责更清楚，也更像真实项目里的写法。

## 当前支持的查询参数

| 参数 | 示例 | 说明 |
| --- | --- | --- |
| `status` | `status=open` | 按状态筛选 |
| `priority` | `priority=high` | 按优先级筛选 |
| `category` | `category=bug` | 按分类筛选 |
| `creator` | `creator=1` | 按创建人 ID 筛选 |
| `assignee` | `assignee=2` | 按处理人 ID 筛选 |
| `mine` | `mine=created` | 查询我创建的工单 |
| `mine` | `mine=assigned` | 查询分配给我的工单 |
| `overdue` | `overdue=true` | 查询已超时且未完成的工单 |
| `has_assignee` | `has_assignee=false` | 查询还没有处理人的工单 |
| `search` | `search=网络` | 按标题和描述搜索 |
| `ordering` | `ordering=-created_at` | 按字段排序 |

## 参数为什么要校验？

查询参数也是用户输入，不能因为它在 URL 上就直接信任。

例如：

```text
/api/tickets/?priority=not-exists
```

如果后端静默忽略这个错误，调用方可能以为自己查到了正确结果。

现在通过 `TicketQueryParamSerializer` 校验参数，非法枚举值会直接返回 400，让错误更早暴露。

## 这次遇到的一个小坑

DRF 的 `BooleanField` 主要兼容 HTML 表单。HTML 复选框没提交时，通常表示 `False`。

但 URL 查询参数不是这样：

```text
/api/tickets/
```

没有传 `has_assignee` 应该表示“不按处理人是否存在筛选”，而不是 `has_assignee=false`。

所以我们新增了 `QueryBooleanField`：

```python
class QueryBooleanField(serializers.BooleanField):
    default_empty_html = serializers.empty
```

这样没传布尔查询参数时，Serializer 不会把它误当成 `False`。

## 筛选逻辑怎么读？

以 `mine=assigned` 为例：

```python
if filters.get('mine') == 'assigned':
    queryset = queryset.filter(assignee=request.user)
```

含义是：在当前用户可见工单范围内，再筛出处理人是当前用户的工单。

注意这个顺序很重要：先做权限范围，再做业务筛选。这样普通用户即使传别人的 `creator` 或 `assignee`，也只能在自己可见的数据里筛选，不会越权看到别人的工单。

## 面试题

1. 为什么查询参数也需要校验？
2. `get_queryset()` 和 `FilterBackend` 分别适合做什么？
3. 为什么普通用户传 `creator=别人的ID` 也不会越权？
4. `search` 和普通字段筛选有什么区别？
5. 为什么 URL 里的布尔参数不能直接照搬表单布尔字段逻辑？
6. 如果筛选参数越来越多，后续还可以怎么优化？

## 简短回答

1. 查询参数来自用户输入，非法值应该及时返回 400，避免接口静默返回错误结果。
2. `get_queryset()` 适合做基础数据范围和权限范围，`FilterBackend` 适合处理列表查询参数。
3. 因为后端先限制当前用户可见数据，再在这个范围里筛选，所以筛选参数不会扩大权限范围。
4. 普通字段筛选是精确匹配，`search` 是关键词搜索，通常会查多个文本字段。
5. URL 参数没传表示“不筛选”，但表单复选框没传常被理解为 `False`，语义不同。
6. 可以引入 `django-filter`，或者继续把复杂筛选拆成独立的 filter/service。

## 面试时怎么讲今天的内容

我把 FlowDesk 的工单列表筛选从 ViewSet 中拆到了自定义 FilterBackend。ViewSet 的 `get_queryset()` 只负责权限范围，FilterBackend 负责读取和校验查询参数，再做状态、优先级、分类、创建人、处理人、我的工单、超时工单等筛选。为了避免非法参数被静默忽略，我使用 Serializer 校验查询参数；同时针对 URL 布尔参数单独封装了 `QueryBooleanField`，避免没传参数时被误判成 `False`。
