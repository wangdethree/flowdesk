from django.contrib import admin

from apps.tickets.models import Ticket, TicketAttachment, TicketComment, TicketTag


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
    filter_horizontal = ('watchers', 'tags')
    ordering = ('-created_at',)


@admin.register(TicketComment)
class TicketCommentAdmin(admin.ModelAdmin):
    """工单评论和处理记录的后台管理配置。"""

    list_display = ('id', 'ticket', 'author', 'comment_type', 'created_at')
    list_filter = ('comment_type',)
    search_fields = ('content', 'ticket__title', 'author__username')
    ordering = ('-created_at',)


@admin.register(TicketAttachment)
class TicketAttachmentAdmin(admin.ModelAdmin):
    """工单附件后台管理配置。"""

    list_display = ('id', 'ticket', 'uploaded_by', 'original_filename', 'size', 'created_at')
    list_filter = ('content_type', 'created_at')
    search_fields = ('ticket__title', 'uploaded_by__username', 'original_filename')
    ordering = ('-created_at',)


@admin.register(TicketTag)
class TicketTagAdmin(admin.ModelAdmin):
    """工单标签后台管理配置。"""

    list_display = ('id', 'name', 'color', 'created_at')
    search_fields = ('name',)
    ordering = ('name',)
