from django.conf import settings
from django.db import models


class AuditAction(models.TextChoices):
    """审计动作枚举。

    把动作类型固定成枚举，能避免日志里出现 update、updated、modify 这种同义但不统一的值。
    """

    CREATE = 'create', '创建'
    UPDATE = 'update', '更新'
    DELETE = 'delete', '删除'
    COMMENT = 'comment', '评论'
    STATUS_CHANGE = 'status_change', '状态流转'
    ASSIGN = 'assign', '分配处理人'


class AuditLog(models.Model):
    """审计日志表。

    审计日志用于回答几个问题：
    - 谁操作了系统？
    - 操作了什么资源？
    - 做了什么动作？
    - 当时留下了哪些关键上下文？

    它不是给普通业务列表展示用的，而是给排查问题、追踪责任和面试讲工程化时使用。
    """

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='audit_logs',
        verbose_name='操作人',
        null=True,
        blank=True,
    )
    action = models.CharField('动作', max_length=30, choices=AuditAction.choices)
    target_type = models.CharField('目标类型', max_length=80)
    target_id = models.CharField('目标 ID', max_length=80)
    description = models.CharField('描述', max_length=255)
    metadata = models.JSONField('扩展数据', default=dict, blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    @classmethod
    def for_target(cls, target):
        """查询某个业务对象对应的审计日志。

        审计日志通过 target_type 和 target_id 保存“被操作对象”，没有直接外键。
        这样同一张表后续可以记录工单、评论、用户等不同资源的操作历史。
        """

        return cls.objects.filter(
            target_type=target.__class__.__name__,
            target_id=str(target.pk),
        )

    class Meta:
        verbose_name = '审计日志'
        verbose_name_plural = '审计日志'
        ordering = ['-created_at']
        indexes = [
            # 常见查询：查某个资源的操作历史。
            models.Index(fields=['target_type', 'target_id', '-created_at']),
            # 常见查询：查某个用户最近做了哪些操作。
            models.Index(fields=['actor', '-created_at']),
            # 常见查询：按动作类型统计或筛选。
            models.Index(fields=['action', '-created_at']),
        ]

    def __str__(self):
        actor_name = self.actor.username if self.actor else '系统'
        return f'{actor_name} {self.get_action_display()} {self.target_type}#{self.target_id}'
