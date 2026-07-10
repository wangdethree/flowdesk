from django.utils import timezone
from rest_framework import serializers
from rest_framework.filters import BaseFilterBackend

from apps.tickets.models import TicketCategory, TicketPriority, TicketStatus


class QueryBooleanField(serializers.BooleanField):
    """专门用于查询参数的布尔字段。

    DRF 的 BooleanField 主要兼容 HTML 表单场景：复选框没提交时会被理解成 False。
    但 URL 查询参数不一样，没传 overdue 或 has_assignee 应该表示“不筛选”，而不是 False。
    所以这里把 default_empty_html 改成 empty，让缺失参数保持“未提供”的语义。
    """

    default_empty_html = serializers.empty


class TicketQueryParamSerializer(serializers.Serializer):
    """工单列表查询参数校验器。

    查询参数虽然来自 URL，但本质上也是用户输入，不能直接信任。
    用 Serializer 统一校验后，非法枚举值、非法数字、非法布尔值都会返回 400，
    比在 View 里手写很多 if 判断更清晰，也更接近真实项目写法。
    """

    status = serializers.ChoiceField(choices=TicketStatus.choices, required=False)
    priority = serializers.ChoiceField(choices=TicketPriority.choices, required=False)
    category = serializers.ChoiceField(choices=TicketCategory.choices, required=False)
    assignee = serializers.IntegerField(required=False, min_value=1)
    creator = serializers.IntegerField(required=False, min_value=1)
    overdue = QueryBooleanField(required=False)
    has_assignee = QueryBooleanField(required=False)
    mine = serializers.ChoiceField(choices=('created', 'assigned', 'watched'), required=False)


class TicketFilterBackend(BaseFilterBackend):
    """工单列表筛选后端。

    DRF 会在 list 接口里自动调用 filter_queryset()。
    我们把筛选逻辑放在这里，而不是塞进 get_queryset()，是为了把“数据权限范围”和
    “查询参数筛选”分开：get_queryset 负责先圈定用户能看的数据，FilterBackend 再做列表筛选。
    """

    def filter_queryset(self, request, queryset, view):
        """根据查询参数过滤工单列表。"""

        serializer = TicketQueryParamSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        filters = serializer.validated_data

        if 'status' in filters:
            queryset = queryset.filter(status=filters['status'])
        if 'priority' in filters:
            queryset = queryset.filter(priority=filters['priority'])
        if 'category' in filters:
            queryset = queryset.filter(category=filters['category'])
        if 'assignee' in filters:
            queryset = queryset.filter(assignee_id=filters['assignee'])
        if 'creator' in filters:
            queryset = queryset.filter(creator_id=filters['creator'])

        # mine 用来快速查询“我创建的”或“分配给我的”，这是后台系统很常见的列表筛选。
        if filters.get('mine') == 'created':
            queryset = queryset.filter(creator=request.user)
        if filters.get('mine') == 'assigned':
            queryset = queryset.filter(assignee=request.user)
        if filters.get('mine') == 'watched':
            queryset = queryset.filter(watchers=request.user)

        # overdue=true 查询已超时且未完成的工单；overdue=false 查询未超时或已完成的工单。
        # 注意这里复用了模型里 is_overdue 的业务含义：有截止时间、已超过当前时间、并且还没结束。
        if 'overdue' in filters:
            now = timezone.now()
            if filters['overdue']:
                queryset = queryset.filter(
                    due_at__lt=now,
                ).exclude(status__in=(TicketStatus.RESOLVED, TicketStatus.CLOSED))
            else:
                queryset = queryset.exclude(
                    due_at__lt=now,
                    status__in=(TicketStatus.OPEN, TicketStatus.IN_PROGRESS),
                )

        # has_assignee=true 查询已分配工单；has_assignee=false 查询还没有处理人的工单。
        if 'has_assignee' in filters:
            queryset = queryset.filter(assignee__isnull=not filters['has_assignee'])

        return queryset
