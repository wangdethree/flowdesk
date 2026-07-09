from django.contrib import admin

from apps.audit.models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """审计日志后台配置。

    审计日志通常只查看，不建议在后台随意修改，所以这里把核心字段设成只读。
    """

    list_display = ('id', 'actor', 'action', 'target_type', 'target_id', 'created_at')
    list_filter = ('action', 'target_type', 'created_at')
    search_fields = ('actor__username', 'target_type', 'target_id', 'description')
    readonly_fields = (
        'actor',
        'action',
        'target_type',
        'target_id',
        'description',
        'metadata',
        'created_at',
    )
    ordering = ('-created_at',)
