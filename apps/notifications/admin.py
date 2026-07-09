from django.contrib import admin

from apps.notifications.models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    """通知后台管理配置。

    通知通常由业务代码自动生成，后台这里只用于排查和临时查看。
    """

    list_display = ('id', 'recipient', 'notification_type', 'title', 'is_read', 'created_at')
    list_filter = ('notification_type', 'is_read', 'created_at')
    search_fields = ('recipient__username', 'title', 'message', 'target_type', 'target_id')
    readonly_fields = ('created_at', 'read_at')
