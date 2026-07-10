from django.db.models import Avg, Count, Q
from django.utils import timezone

from apps.tickets.models import Ticket, TicketCategory, TicketFeedback, TicketPriority, TicketStatus


def get_visible_ticket_queryset(user):
    """返回当前用户可见的工单查询集。

    统计接口不能直接统计全表，否则普通用户会看到别人的业务数据。
    这里沿用工单列表接口的权限规则：
    - 管理员统计全部工单。
    - 普通用户只统计自己创建、分配给自己或自己关注的工单。
    """

    queryset = Ticket.objects.all()
    if user.is_staff:
        return queryset

    return queryset.filter(Q(creator=user) | Q(assignee=user) | Q(watchers=user)).distinct()


def build_choice_count_map(queryset, field_name, choices):
    """按枚举字段统计数量，并补齐没有数据的枚举值。

    数据库 group by 只会返回“实际出现过”的值。
    但接口响应最好结构稳定，所以即使某个状态当前数量是 0，也要返回它。
    """

    # values(field_name).annotate(...) 等价于 SQL 里的 GROUP BY。
    grouped_rows = queryset.values(field_name).order_by().annotate(count=Count('id'))
    count_map = {row[field_name]: row['count'] for row in grouped_rows}
    return {value: count_map.get(value, 0) for value, _label in choices}


def build_rating_count_map(queryset):
    """按 1 到 5 星补齐评价数量。

    评分是固定范围，接口返回完整的 1-5 星分布，前端画图时就不用再自己补 0。
    """

    grouped_rows = queryset.values('rating').order_by().annotate(count=Count('id'))
    count_map = {row['rating']: row['count'] for row in grouped_rows}
    return {rating: count_map.get(rating, 0) for rating in range(1, 6)}


def get_feedback_summary(ticket_queryset):
    """生成当前可见工单范围内的评价统计。

    注意这里统计的是“当前用户可见工单”的评价，而不是全站评价。
    这样普通用户不会通过统计接口推断出自己无权查看的工单反馈数据。
    """

    feedback_queryset = TicketFeedback.objects.filter(ticket__in=ticket_queryset)
    feedback_count = feedback_queryset.count()
    average_rating = feedback_queryset.aggregate(value=Avg('rating'))['value'] or 0
    satisfied_count = feedback_queryset.filter(rating__gte=4).count()

    return {
        'feedback_count': feedback_count,
        'average_rating': round(average_rating, 2),
        'satisfaction_rate': round(satisfied_count / feedback_count, 2) if feedback_count else 0,
        'by_rating': build_rating_count_map(feedback_queryset),
    }


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

    summary = {
        'total': queryset.count(),
        'created_by_me': queryset.filter(creator=user).count(),
        'assigned_to_me': queryset.filter(assignee=user).count(),
        'overdue': overdue_count,
        'by_status': build_choice_count_map(queryset, 'status', TicketStatus.choices),
        'by_priority': build_choice_count_map(queryset, 'priority', TicketPriority.choices),
        'by_category': build_choice_count_map(queryset, 'category', TicketCategory.choices),
    }
    summary['feedback'] = get_feedback_summary(queryset)
    return summary
