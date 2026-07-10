from django.conf import settings
from django.db import models
from django.utils import timezone


class NotificationType(models.TextChoices):
    """通知类型枚举。

    第一版只覆盖工单相关通知，后续如果接入 Agent 或审批流，可以继续追加类型。
    """

    TICKET_ASSIGNED = 'ticket_assigned', '工单分配'
    TICKET_COMMENTED = 'ticket_commented', '工单评论'
    TICKET_STATUS_CHANGED = 'ticket_status_changed', '状态变更'
    TICKET_REMINDED = 'ticket_reminded', '工单催办'
    TICKET_PRIORITY_CHANGED = 'ticket_priority_changed', '优先级变更'
    TICKET_FEEDBACK_SUBMITTED = 'ticket_feedback_submitted', '工单评价'


class Notification(models.Model):
    """站内通知表。

    一条通知代表系统想提醒某个用户关注某个业务事件。
    target_type 和 target_id 用来指向业务对象，第一版主要指向 Ticket。
    """

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name='接收人',
    )
    notification_type = models.CharField(
        '通知类型',
        max_length=40,
        choices=NotificationType.choices,
    )
    title = models.CharField('标题', max_length=120)
    message = models.TextField('内容')
    target_type = models.CharField('目标类型', max_length=80, blank=True)
    target_id = models.CharField('目标 ID', max_length=80, blank=True)
    metadata = models.JSONField('扩展数据', default=dict, blank=True)
    is_read = models.BooleanField('是否已读', default=False)
    read_at = models.DateTimeField('阅读时间', null=True, blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        verbose_name = '通知'
        verbose_name_plural = '通知'
        ordering = ['-created_at']
        indexes = [
            # 通知中心最常见的查询：当前用户的未读通知列表。
            models.Index(fields=['recipient', 'is_read', '-created_at']),
            # 后续排查某个业务对象触发过哪些通知时，可以用这个索引。
            models.Index(fields=['target_type', 'target_id', '-created_at']),
        ]

    def __str__(self):
        return f'{self.recipient} - {self.title}'

    def mark_as_read(self):
        """把通知标记为已读。

        如果通知已经是已读，就直接返回，避免重复更新数据库和覆盖第一次阅读时间。
        """

        if self.is_read:
            return False

        self.is_read = True
        self.read_at = timezone.now()
        self.save(update_fields=['is_read', 'read_at'])
        return True
