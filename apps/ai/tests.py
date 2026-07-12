from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from django.contrib.auth import get_user_model

from apps.tickets.models import Ticket, TicketCategory, TicketPriority


User = get_user_model()


class AiAssistantAPITests(APITestCase):
    """智能助手接口测试。"""

    def setUp(self):
        self.user = User.objects.create_user(username='ai_user', password='TestPass123')
        self.other_user = User.objects.create_user(username='ai_other', password='TestPass123')

    def test_ticket_draft_requires_authentication(self):
        response = self.client.post(reverse('ai-ticket-draft'), {'raw_text': '线上支付失败'})

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_ticket_draft_suggests_priority_category_and_tags(self):
        self.client.force_authenticate(self.user)

        response = self.client.post(
            reverse('ai-ticket-draft'),
            {'raw_text': '线上支付全部失败，客户无法完成订单。'},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['category'], TicketCategory.BUG)
        self.assertEqual(response.data['priority'], TicketPriority.URGENT)
        self.assertIn('线上故障', response.data['suggested_tags'])
        self.assertGreater(response.data['confidence'], 0.5)

    def test_ticket_suggestion_only_allows_visible_ticket(self):
        self.client.force_authenticate(self.user)
        ticket = Ticket.objects.create(
            title='别人创建的工单',
            description='普通用户不可见',
            creator=self.other_user,
        )

        response = self.client.get(reverse('ai-ticket-suggestion', args=[ticket.id]))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_ticket_suggestion_returns_next_actions_for_visible_ticket(self):
        self.client.force_authenticate(self.user)
        ticket = Ticket.objects.create(
            title='登录失败',
            description='用户无法登录后台',
            creator=self.user,
        )

        response = self.client.get(reverse('ai-ticket-suggestion', args=[ticket.id]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('#', response.data['summary'])
        self.assertTrue(response.data['next_actions'])
        self.assertIn('reply_template', response.data)
