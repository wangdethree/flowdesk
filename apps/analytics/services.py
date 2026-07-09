from django.db.models import Count, Q
from django.utils import timezone

from apps.tickets.models import Ticket, TicketCategory, TicketPriority, TicketStatus


def get_visible_ticket_queryset(user):
    """返回当前用户可见的工单查询集。

    统计接口不能直接统计全表，否则普通用户会看到别人的业务数据。
    这里沿用工单列表接口的权限规则：
    - 管理员统计全部工单。
    - 普通用户只统计自己创建或分配给自己的工单。
    """

    queryset = Ticket.objects.all()
    if user.is_staff:
        return queryset

    return queryset.filter(Q(creator=user) | Q(assignee=user))


def build_choice_count_map(queryset, field_name, choices):
    """按枚举字段统计数量，并补齐没有数据的枚举值。

    数据库 group by 只会返回“实际出现过”的值。
    但接口响应最好结构稳定，所以即使某个状态当前数量是 0，也要返回它。
    """

    # values(field_name).annotate(...) 等价于 SQL 里的 GROUP BY。
    grouped_rows = queryset.values(field_name).order_by().annotate(count=Count('id'))
    count_map = {row[field_name]: row['count'] for row in grouped_rows}
    return {value: count_map.get(value, 0) for value, _label in choices}


def get_ticket_summary(user):
    """生成工单统计摘要。

    这个函数只做数据计算，不关心 HTTP 请求和响应。
    好处是测试更简单，后续也可以被 Celery 定时任务或缓存逻辑复用。
    """

    queryset = get_visible_ticket_queryset(user)
    now = timezone.now()

    # 终态工单不再算超时；只有仍需处理的工单才需要提醒。
    unfinished_statuses = [TicketStatus.OPEN, TicketStatus.IN_PROGRESS]
    overdue_count = queryset.filter(
        due_at__lt=now,
        status__in=unfinished_statuses,
    ).count()

    return {
        'total': queryset.count(),
        'created_by_me': queryset.filter(creator=user).count(),
        'assigned_to_me': queryset.filter(assignee=user).count(),
        'overdue': overdue_count,
        'by_status': build_choice_count_map(queryset, 'status', TicketStatus.choices),
        'by_priority': build_choice_count_map(queryset, 'priority', TicketPriority.choices),
        'by_category': build_choice_count_map(queryset, 'category', TicketCategory.choices),
    }
