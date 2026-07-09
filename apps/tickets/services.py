def assign_ticket(*, ticket, assignee):
    """分配或取消分配工单处理人。

    service 层只处理业务状态变化，不关心 HTTP 请求、响应和权限。
    这样后续如果要在管理后台、定时任务或 Agent 流程里复用“分配工单”逻辑，
    就不用复制 View 里的代码。
    """

    old_assignee_id = ticket.assignee_id
    new_assignee_id = assignee.id if assignee else None

    # 如果处理人没有变化，就不写数据库，避免无意义地刷新 updated_at。
    if old_assignee_id == new_assignee_id:
        return old_assignee_id

    ticket.assignee = assignee
    ticket.save(update_fields=['assignee', 'updated_at'])
    return old_assignee_id
