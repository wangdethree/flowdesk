from django.contrib import admin

from apps.tickets.models import Ticket, TicketComment


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    """工单后台管理配置，方便开发阶段直接查看和修改测试数据。"""

    list_display = (
        'id',
        'title',
        'category',
        'priority',
        'status',
        'creator',
        'assignee',
        'created_at',
    )
    list_filter = ('status', 'priority', 'category')
    search_fields = ('title', 'description', 'creator__username', 'assignee__username')
    ordering = ('-created_at',)


@admin.register(TicketComment)
class TicketCommentAdmin(admin.ModelAdmin):
    """工单评论和处理记录的后台管理配置。"""

    list_display = ('id', 'ticket', 'author', 'comment_type', 'created_at')
    list_filter = ('comment_type',)
    search_fields = ('content', 'ticket__title', 'author__username')
    ordering = ('-created_at',)
