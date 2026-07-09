from django.utils import timezone

from apps.notifications.models import Notification


def create_notification(*, recipient, notification_type, title, message, target=None, metadata=None):
    """创建站内通知。

    业务代码统一调用 service，而不是直接 Notification.objects.create。
    这样后续如果要改成异步通知、短信、邮件或 WebSocket，只需要从这里扩展。
    """

    if recipient is None:
        return None

    target_type = ''
    target_id = ''
    if target is not None:
        target_type = target.__class__.__name__
        target_id = str(target.pk)

    return Notification.objects.create(
        recipient=recipient,
        notification_type=notification_type,
        title=title,
        message=message,
        target_type=target_type,
        target_id=target_id,
        metadata=metadata or {},
    )


def mark_all_notifications_as_read(user):
    """把某个用户的所有未读通知标记为已读。

    update() 会直接生成 SQL 批量更新，比循环逐条 save() 更适合“全部已读”这种操作。
    """

    return Notification.objects.filter(recipient=user, is_read=False).update(
        is_read=True,
        read_at=timezone.now(),
    )


def get_unread_notification_count(user):
    """统计当前用户未读通知数量。"""

    return Notification.objects.filter(recipient=user, is_read=False).count()
