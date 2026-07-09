from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.tickets.models import Ticket, TicketPriority, TicketStatus


User = get_user_model()


class TicketSummaryAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='summary_user', password='TestPass123')
        self.other_user = User.objects.create_user(username='summary_other', password='TestPass123')
        self.staff_user = User.objects.create_user(
            username='summary_staff',
            password='TestPass123',
            is_staff=True,
        )

    def test_summary_requires_authentication(self):
        response = self.client.get(reverse('ticket-summary'))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_normal_user_only_gets_visible_ticket_summary(self):
        Ticket.objects.create(
            title='我的统计工单',
            description='普通用户可见。',
            creator=self.user,
            priority=TicketPriority.HIGH,
            status=TicketStatus.OPEN,
        )
        Ticket.objects.create(
            title='别人的统计工单',
            description='普通用户不可见。',
            creator=self.other_user,
            priority=TicketPriority.LOW,
            status=TicketStatus.CLOSED,
        )
        self.client.force_authenticate(user=self.user)

        response = self.client.get(reverse('ticket-summary'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total'], 1)
        self.assertEqual(response.data['by_status'][TicketStatus.OPEN], 1)
        self.assertEqual(response.data['by_status'][TicketStatus.CLOSED], 0)

    def test_staff_gets_global_ticket_summary(self):
        Ticket.objects.create(title='工单一', description='管理员可统计。', creator=self.user)
        Ticket.objects.create(title='工单二', description='管理员可统计。', creator=self.other_user)
        self.client.force_authenticate(user=self.staff_user)

        response = self.client.get(reverse('ticket-summary'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total'], 2)
