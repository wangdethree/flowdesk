from django.utils import timezone

from apps.notifications.models import NotificationType
from apps.notifications.services import create_notification
from apps.tickets.models import TicketFeedback, TicketStatus


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


def close_ticket(*, ticket, reason):
    """关闭工单并保存关闭原因。

    关闭动作会进入终态，所以这里集中维护 status、closed_at 和 close_reason，
    避免多个接口各自手写状态更新，后续规则变化时也更容易调整。
    """

    old_status = ticket.status
    ticket.status = TicketStatus.CLOSED
    ticket.closed_at = timezone.now()
    ticket.close_reason = reason
    ticket.save(update_fields=['status', 'closed_at', 'close_reason', 'updated_at'])
    return old_status


def reopen_ticket(*, ticket, reason):
    """重开已关闭工单并保存重开原因。

    重开后重新回到待处理状态，同时清空终态时间，避免列表和超时判断继续把它当成已结束工单。
    """

    old_status = ticket.status
    ticket.status = TicketStatus.OPEN
    ticket.resolved_at = None
    ticket.closed_at = None
    ticket.reopen_reason = reason
    ticket.save(
        update_fields=[
            'status',
            'resolved_at',
            'closed_at',
            'reopen_reason',
            'updated_at',
        ]
    )
    return old_status


def save_ticket_feedback(*, ticket, actor, rating, content=''):
    """创建或更新工单评价。

    评价和工单是一对一关系，所以重复评价时更新原评价，而不是新增多条记录。
    返回 created 是为了 View 层写审计日志时区分“首次评价”和“修改评价”。
    """

    feedback, created = TicketFeedback.objects.update_or_create(
        ticket=ticket,
        defaults={
            'created_by': actor,
            'rating': rating,
            'content': content,
        },
    )
    return feedback, created


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


def notify_ticket_reminded(*, ticket, actor, message=''):
    """催办工单时通知当前处理人。

    催办只发给 assignee。没有处理人的工单无法催办，因为不知道应该提醒谁。
    """

    return create_notification(
        recipient=ticket.assignee,
        notification_type=NotificationType.TICKET_REMINDED,
        title='你有一张工单被催办',
        message=message or f'工单「{ticket.title}」被催办，请尽快处理。',
        target=ticket,
        metadata={
            'ticket_id': ticket.id,
            'actor_id': actor.id,
            'message': message,
        },
    )


def notify_ticket_priority_changed(*, ticket, actor, old_priority, new_priority):
    """工单优先级变化后通知处理人和关注人。

    创建人自己调整优先级时不需要再通知自己；使用字典去重，避免处理人同时也是关注人。
    """

    recipients = {}
    if ticket.assignee_id and ticket.assignee_id != actor.id:
        recipients[ticket.assignee_id] = ticket.assignee
    for watcher in ticket.watchers.all():
        if watcher.id != actor.id:
            recipients[watcher.id] = watcher

    notifications = []
    for recipient in recipients.values():
        notification = create_notification(
            recipient=recipient,
            notification_type=NotificationType.TICKET_PRIORITY_CHANGED,
            title='工单优先级已调整',
            message=f'工单「{ticket.title}」优先级已从 {old_priority} 调整为 {new_priority}。',
            target=ticket,
            metadata={
                'ticket_id': ticket.id,
                'actor_id': actor.id,
                'old_priority': old_priority,
                'new_priority': new_priority,
            },
        )
        notifications.append(notification)

    return notifications


def notify_ticket_feedback_submitted(*, ticket, feedback, actor):
    """工单收到评价后通知处理人。

    评价主要反馈给处理人；如果没有处理人，或者创建人评价的是自己处理的工单，就不重复通知。
    """

    if ticket.assignee is None or ticket.assignee_id == actor.id:
        return None

    return create_notification(
        recipient=ticket.assignee,
        notification_type=NotificationType.TICKET_FEEDBACK_SUBMITTED,
        title='工单收到新的评价',
        message=f'工单「{ticket.title}」收到 {feedback.rating} 星评价。',
        target=ticket,
        metadata={
            'ticket_id': ticket.id,
            'feedback_id': feedback.id,
            'actor_id': actor.id,
            'rating': feedback.rating,
        },
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
