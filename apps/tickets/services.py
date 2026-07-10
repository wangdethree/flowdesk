from apps.notifications.models import NotificationType
from apps.notifications.services import create_notification


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


def notify_ticket_assigned(*, ticket, actor):
    """工单被分配后通知新的处理人。

    actor 是触发动作的人。如果创建人把工单分配给自己，就不需要再给自己发通知。
    """

    if ticket.assignee is None or ticket.assignee_id == actor.id:
        return None

    return create_notification(
        recipient=ticket.assignee,
        notification_type=NotificationType.TICKET_ASSIGNED,
        title='你有新的待处理工单',
        message=f'工单「{ticket.title}」已分配给你，请及时处理。',
        target=ticket,
        metadata={'ticket_id': ticket.id, 'actor_id': actor.id},
    )


def notify_ticket_commented(*, ticket, comment, actor):
    """工单新增评论/处理记录后通知其他参与者。

    创建人、处理人和关注人都属于工单参与者，但评论作者本人不需要收到自己的通知。
    使用字典按用户 ID 去重，避免同一个人既是处理人又是关注人时重复发通知。
    """

    recipients = {}
    if ticket.creator_id != actor.id:
        recipients[ticket.creator_id] = ticket.creator
    if ticket.assignee_id and ticket.assignee_id != actor.id:
        recipients[ticket.assignee_id] = ticket.assignee
    for watcher in ticket.watchers.all():
        if watcher.id != actor.id:
            recipients[watcher.id] = watcher

    notifications = []
    for recipient in recipients.values():
        notification = create_notification(
            recipient=recipient,
            notification_type=NotificationType.TICKET_COMMENTED,
            title='工单有新的沟通记录',
            message=f'工单「{ticket.title}」新增了一条记录：{comment.content[:40]}',
            target=ticket,
            metadata={
                'ticket_id': ticket.id,
                'comment_id': comment.id,
                'actor_id': actor.id,
                'comment_type': comment.comment_type,
            },
        )
        notifications.append(notification)

    return notifications


def notify_ticket_status_changed(*, ticket, actor, old_status, new_status):
    """工单状态变化后通知其他参与者和关注人。"""

    recipients = {}
    if ticket.creator_id != actor.id:
        recipients[ticket.creator_id] = ticket.creator
    if ticket.assignee_id and ticket.assignee_id != actor.id:
        recipients[ticket.assignee_id] = ticket.assignee
    for watcher in ticket.watchers.all():
        if watcher.id != actor.id:
            recipients[watcher.id] = watcher

    notifications = []
    for recipient in recipients.values():
        notification = create_notification(
            recipient=recipient,
            notification_type=NotificationType.TICKET_STATUS_CHANGED,
            title='工单状态已更新',
            message=f'工单「{ticket.title}」状态已从 {old_status} 变更为 {new_status}。',
            target=ticket,
            metadata={
                'ticket_id': ticket.id,
                'actor_id': actor.id,
                'old_status': old_status,
                'new_status': new_status,
            },
        )
        notifications.append(notification)

    return notifications
