from rest_framework import serializers

from apps.notifications.models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    """通知接口序列化器。

    通知由后端业务事件自动生成，接口层只负责展示和已读操作。
    因此前端不能通过这个 Serializer 创建或修改通知内容。
    """

    notification_type_display = serializers.CharField(
        source='get_notification_type_display',
        read_only=True,
    )

    class Meta:
        model = Notification
        fields = (
            'id',
            'notification_type',
            'notification_type_display',
            'title',
            'message',
            'target_type',
            'target_id',
            'metadata',
            'is_read',
            'read_at',
            'created_at',
        )
        read_only_fields = fields
