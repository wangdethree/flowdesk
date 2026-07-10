from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.analytics.services import get_ticket_summary, get_visible_ticket_queryset
from apps.tickets.models import (
    Ticket,
    TicketCategory,
    TicketFeedback,
    TicketPriority,
    TicketStatus,
)


User = get_user_model()


class TicketSummaryServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='analytics_user', password='TestPass123')
        self.assignee = User.objects.create_user(username='analytics_assignee', password='TestPass123')
        self.other_user = User.objects.create_user(username='analytics_other', password='TestPass123')
        self.staff_user = User.objects.create_user(
            username='analytics_staff',
            password='TestPass123',
            is_staff=True,
        )

    def test_visible_queryset_only_contains_related_tickets_for_normal_user(self):
        created_ticket = Ticket.objects.create(
            title='我创建的统计工单',
            description='普通用户能看到自己创建的工单。',
            creator=self.user,
        )
        assigned_ticket = Ticket.objects.create(
            title='分配给我的统计工单',
            description='普通用户能看到分配给自己的工单。',
            creator=self.other_user,
            assignee=self.user,
        )
        Ticket.objects.create(
            title='无关统计工单',
            description='普通用户不能看到无关工单。',
            creator=self.other_user,
        )

        visible_ids = set(get_visible_ticket_queryset(self.user).values_list('id', flat=True))

        self.assertEqual(visible_ids, {created_ticket.id, assigned_ticket.id})

    def test_staff_summary_counts_all_tickets(self):
        Ticket.objects.create(title='工单一', description='管理员可统计。', creator=self.user)
        Ticket.objects.create(title='工单二', description='管理员可统计。', creator=self.other_user)

        summary = get_ticket_summary(self.staff_user)

        self.assertEqual(summary['total'], 2)

    def test_summary_counts_status_priority_category_and_overdue(self):
        Ticket.objects.create(
            title='待处理超时工单',
            description='用于验证超时统计。',
            creator=self.user,
            category=TicketCategory.BUG,
            priority=TicketPriority.URGENT,
            status=TicketStatus.OPEN,
            due_at=timezone.now() - timedelta(hours=1),
        )
        Ticket.objects.create(
            title='已解决超时工单',
            description='已解决工单即使过了截止时间，也不算待处理超时。',
            creator=self.user,
            category=TicketCategory.CONSULT,
            priority=TicketPriority.LOW,
            status=TicketStatus.RESOLVED,
            due_at=timezone.now() - timedelta(hours=1),
        )

        summary = get_ticket_summary(self.user)

        self.assertEqual(summary['total'], 2)
        self.assertEqual(summary['created_by_me'], 2)
        self.assertEqual(summary['assigned_to_me'], 0)
        self.assertEqual(summary['overdue'], 1)
        self.assertEqual(summary['by_status'][TicketStatus.OPEN], 1)
        self.assertEqual(summary['by_status'][TicketStatus.RESOLVED], 1)
        self.assertEqual(summary['by_priority'][TicketPriority.URGENT], 1)
        self.assertEqual(summary['by_category'][TicketCategory.BUG], 1)

    def test_summary_counts_feedback_metrics_in_visible_scope(self):
        """评价统计只计算当前用户可见工单，避免泄露无关工单评分。"""

        visible_ticket = Ticket.objects.create(
            title='可见评价工单',
            description='当前用户创建，所以评价应该被统计。',
            creator=self.user,
            status=TicketStatus.CLOSED,
            closed_at=timezone.now(),
        )
        assigned_ticket = Ticket.objects.create(
            title='分配给我的评价工单',
            description='当前用户是处理人，所以评价也应该被统计。',
            creator=self.other_user,
            assignee=self.user,
            status=TicketStatus.CLOSED,
            closed_at=timezone.now(),
        )
        invisible_ticket = Ticket.objects.create(
            title='不可见评价工单',
            description='当前用户无权查看，所以评价不能被统计。',
            creator=self.other_user,
            status=TicketStatus.CLOSED,
            closed_at=timezone.now(),
        )
        TicketFeedback.objects.create(
            ticket=visible_ticket,
            created_by=self.user,
            rating=5,
            content='非常满意。',
        )
        TicketFeedback.objects.create(
            ticket=assigned_ticket,
            created_by=self.other_user,
            rating=3,
            content='一般。',
        )
        TicketFeedback.objects.create(
            ticket=invisible_ticket,
            created_by=self.other_user,
            rating=1,
            content='不可见评价。',
        )

        summary = get_ticket_summary(self.user)

        self.assertEqual(summary['feedback']['feedback_count'], 2)
        self.assertEqual(summary['feedback']['average_rating'], 4)
        self.assertEqual(summary['feedback']['satisfaction_rate'], 0.5)
        self.assertEqual(summary['feedback']['by_rating'][1], 0)
        self.assertEqual(summary['feedback']['by_rating'][3], 1)
        self.assertEqual(summary['feedback']['by_rating'][5], 1)

    def test_summary_feedback_metrics_default_to_zero(self):
        """没有评价时也返回稳定结构，方便前端直接渲染。"""

        Ticket.objects.create(
            title='没有评价的统计工单',
            description='验证评价统计默认值。',
            creator=self.user,
        )

        summary = get_ticket_summary(self.user)

        self.assertEqual(summary['feedback']['feedback_count'], 0)
        self.assertEqual(summary['feedback']['average_rating'], 0)
        self.assertEqual(summary['feedback']['satisfaction_rate'], 0)
        self.assertEqual(summary['feedback']['by_rating'], {1: 0, 2: 0, 3: 0, 4: 0, 5: 0})

    def test_staff_summary_counts_global_feedback_metrics(self):
        """管理员评价统计覆盖全站工单。"""

        first_ticket = Ticket.objects.create(
            title='全局评价工单一',
            description='管理员可统计。',
            creator=self.user,
            status=TicketStatus.CLOSED,
            closed_at=timezone.now(),
        )
        second_ticket = Ticket.objects.create(
            title='全局评价工单二',
            description='管理员可统计。',
            creator=self.other_user,
            status=TicketStatus.CLOSED,
            closed_at=timezone.now(),
        )
        TicketFeedback.objects.create(
            ticket=first_ticket,
            created_by=self.user,
            rating=4,
        )
        TicketFeedback.objects.create(
            ticket=second_ticket,
            created_by=self.other_user,
            rating=5,
        )

        summary = get_ticket_summary(self.staff_user)

        self.assertEqual(summary['feedback']['feedback_count'], 2)
        self.assertEqual(summary['feedback']['average_rating'], 4.5)
        self.assertEqual(summary['feedback']['satisfaction_rate'], 1)
