from apps.audit.models import AuditLog


def create_audit_log(*, actor, action, target, description, metadata=None):
    """创建审计日志。

    业务代码统一调用这个函数，而不是到处直接写 AuditLog.objects.create。
    这样后续如果要改成 Celery 异步写日志，只需要替换这里的实现。
    """

    return AuditLog.objects.create(
        actor=actor if getattr(actor, 'is_authenticated', False) else None,
        action=action,
        target_type=target.__class__.__name__,
        target_id=str(target.pk),
        description=description,
        metadata=metadata or {},
    )
