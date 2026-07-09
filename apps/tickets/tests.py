from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.tickets.models import Ticket, TicketCategory, TicketComment, TicketPriority, TicketStatus


User = get_user_model()


class TicketModelTests(TestCase):
    def setUp(self):
        self.creator = User.objects.create_user(username='creator', password='TestPass123')
        self.assignee = User.objects.create_user(username='assignee', password='TestPass123')

    def test_create_ticket_with_default_values(self):
        ticket = Ticket.objects.create(
            title='电脑无法连接公司网络',
            description='连接公司 Wi-Fi 后无法访问内部系统。',
            creator=self.creator,
        )

        self.assertEqual(ticket.category, TicketCategory.OTHER)
        self.assertEqual(ticket.priority, TicketPriority.MEDIUM)
        self.assertEqual(ticket.status, TicketStatus.OPEN)
        self.assertEqual(str(ticket), f'#{ticket.id} 电脑无法连接公司网络')

    def test_ticket_can_have_assignee(self):
        ticket = Ticket.objects.create(
            title='测试环境接口报错',
            description='调用测试环境接口时返回 500。',
            category=TicketCategory.BUG,
            priority=TicketPriority.HIGH,
            creator=self.creator,
            assignee=self.assignee,
        )

        self.assertEqual(ticket.assignee, self.assignee)
        self.assertIn(ticket, self.assignee.assigned_tickets.all())

    def test_finished_ticket_status(self):
        resolved_ticket = Ticket.objects.create(
            title='已解决工单',
            description='问题已经处理完成。',
            creator=self.creator,
            status=TicketStatus.RESOLVED,
            resolved_at=timezone.now(),
        )
        open_ticket = Ticket.objects.create(
            title='待处理工单',
            description='问题还没有开始处理。',
            creator=self.creator,
        )

        self.assertTrue(resolved_ticket.is_finished)
        self.assertFalse(open_ticket.is_finished)

    def test_overdue_ticket(self):
        ticket = Ticket.objects.create(
            title='超时工单',
            description='截止时间已经过去。',
            creator=self.creator,
            due_at=timezone.now() - timedelta(hours=1),
        )

        self.assertTrue(ticket.is_overdue)

    def test_create_ticket_comment(self):
        ticket = Ticket.objects.create(
            title='需要补充截图',
            description='用户反馈页面异常。',
            creator=self.creator,
            assignee=self.assignee,
        )

        comment = TicketComment.objects.create(
            ticket=ticket,
            author=self.assignee,
            content='请补充浏览器控制台截图。',
            comment_type=TicketComment.CommentType.HANDLING,
        )

        self.assertEqual(comment.ticket, ticket)
        self.assertEqual(comment.author, self.assignee)
        self.assertEqual(ticket.comments.count(), 1)
        self.assertEqual(str(comment), f'处理记录 - {ticket.id}')
