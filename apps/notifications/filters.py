from rest_framework import serializers
from rest_framework.filters import BaseFilterBackend

from apps.notifications.models import NotificationType
from apps.tickets.filters import QueryBooleanField


class NotificationQueryParamSerializer(serializers.Serializer):
    """通知列表查询参数校验器。

    通知列表虽然只是查询接口，但查询参数依然来自用户输入。
    先用 Serializer 校验，可以让非法的通知类型、非法布尔值直接返回 400，
    避免接口静默忽略错误参数，排查问题时也更直观。
    """

    is_read = QueryBooleanField(required=False)
    notification_type = serializers.ChoiceField(choices=NotificationType.choices, required=False)


class NotificationFilterBackend(BaseFilterBackend):
    """通知列表筛选后端。

    ViewSet.get_queryset() 先限制“只能看自己的通知”，这里再处理列表筛选。
    把数据权限和查询条件拆开写，是为了让每块逻辑都更单纯，也更方便测试。
    """

    def filter_queryset(self, request, queryset, view):
        """根据查询参数过滤当前用户的通知列表。"""

        serializer = NotificationQueryParamSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        filters = serializer.validated_data

        if 'is_read' in filters:
            queryset = queryset.filter(is_read=filters['is_read'])
        if 'notification_type' in filters:
            queryset = queryset.filter(notification_type=filters['notification_type'])

        return queryset
