from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.notifications.models import Notification
from apps.notifications.serializers import NotificationSerializer
from apps.notifications.services import get_unread_notification_count, mark_all_notifications_as_read


class NotificationViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """当前用户通知接口。

    通知是用户私有数据，所以所有查询都必须限制在 request.user 名下。
    这里不提供 create/update/delete，因为通知应该由业务事件自动产生，而不是用户手动创建。
    """

    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """只返回当前登录用户自己的通知。"""

        if getattr(self, 'swagger_fake_view', False):
            return Notification.objects.none()

        return Notification.objects.filter(recipient=self.request.user)

    @action(detail=True, methods=['post'], url_path='mark-read')
    def mark_read(self, request, pk=None):
        """把单条通知标记为已读。"""

        notification = self.get_object()
        notification.mark_as_read()
        serializer = self.get_serializer(notification)
        return Response(serializer.data)

    @action(detail=False, methods=['post'], url_path='mark-all-read')
    def mark_all_read(self, request):
        """把当前用户所有未读通知标记为已读。"""

        updated_count = mark_all_notifications_as_read(request.user)
        return Response(
            {'updated_count': updated_count},
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=['get'], url_path='unread-count')
    def unread_count(self, request):
        """查询当前用户未读通知数量。"""

        return Response({'unread_count': get_unread_notification_count(request.user)})
