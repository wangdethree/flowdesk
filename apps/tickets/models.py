from django.conf import settings
from django.db import models
from django.utils import timezone


class TicketCategory(models.TextChoices):
    """工单分类，用于后续按业务类型筛选和统计。"""

    BUG = 'bug', '故障问题'
    FEATURE = 'feature', '功能需求'
    CONSULT = 'consult', '咨询支持'
    OTHER = 'other', '其他'


class TicketPriority(models.TextChoices):
    """工单优先级，用于体现处理顺序和紧急程度。"""

    LOW = 'low', '低'
    MEDIUM = 'medium', '中'
    HIGH = 'high', '高'
    URGENT = 'urgent', '紧急'


class TicketStatus(models.TextChoices):
    """工单状态，是工单流转功能的核心字段。"""

    OPEN = 'open', '待处理'
    IN_PROGRESS = 'in_progress', '处理中'
    RESOLVED = 'resolved', '已解决'
    CLOSED = 'closed', '已关闭'


class Ticket(models.Model):
    """工单主表。

    一条 Ticket 记录代表用户提交的一次问题、需求或咨询。
    第一版先把字段设计扎稳，后续 CRUD、权限控制和状态流转都会围绕这张表展开。
    """

    title = models.CharField('标题', max_length=120)
    description = models.TextField('描述')
    category = models.CharField(
        '分类',
        max_length=20,
        choices=TicketCategory.choices,
        default=TicketCategory.OTHER,
    )
    priority = models.CharField(
        '优先级',
        max_length=20,
        choices=TicketPriority.choices,
        default=TicketPriority.MEDIUM,
    )
    status = models.CharField(
        '状态',
        max_length=20,
        choices=TicketStatus.choices,
        default=TicketStatus.OPEN,
    )

    # 创建人是提交工单的用户，后续权限规则会基于它限制“只能看自己的工单”。
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='created_tickets',
        verbose_name='创建人',
    )
    # 处理人可以为空，因为工单刚创建时可能还没有被分配。
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='assigned_tickets',
        verbose_name='处理人',
        null=True,
        blank=True,
    )

    due_at = models.DateTimeField('截止时间', null=True, blank=True)
    resolved_at = models.DateTimeField('解决时间', null=True, blank=True)
    closed_at = models.DateTimeField('关闭时间', null=True, blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = '工单'
        verbose_name_plural = '工单'
        ordering = ['-created_at']
        indexes = [
            # 常见列表页会按状态、优先级和创建时间筛选/排序，所以先为这些字段建索引。
            models.Index(fields=['status', 'priority', '-created_at']),
            models.Index(fields=['creator', '-created_at']),
            models.Index(fields=['assignee', '-created_at']),
        ]

    def __str__(self):
        return f'#{self.id} {self.title}'

    @property
    def is_finished(self):
        """判断工单是否已经进入终态。"""

        return self.status in {TicketStatus.RESOLVED, TicketStatus.CLOSED}

    @property
    def is_overdue(self):
        """判断工单是否已经超过截止时间。"""

        return bool(self.due_at and self.due_at < timezone.now() and not self.is_finished)


class TicketComment(models.Model):
    """工单评论和处理记录表。

    一条工单通常会有多次沟通、补充信息或处理说明。
    将记录拆到独立表里，可以保留完整处理过程，而不是只在工单主表里覆盖一个字段。
    """

    class CommentType(models.TextChoices):
        COMMENT = 'comment', '普通评论'
        HANDLING = 'handling', '处理记录'

    ticket = models.ForeignKey(
        Ticket,
        on_delete=models.CASCADE,
        related_name='comments',
        verbose_name='所属工单',
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='ticket_comments',
        verbose_name='作者',
    )
    content = models.TextField('内容')
    comment_type = models.CharField(
        '记录类型',
        max_length=20,
        choices=CommentType.choices,
        default=CommentType.COMMENT,
    )
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        verbose_name = '工单记录'
        verbose_name_plural = '工单记录'
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['ticket', 'created_at']),
            models.Index(fields=['author', '-created_at']),
        ]

    def __str__(self):
        return f'{self.get_comment_type_display()} - {self.ticket_id}'
