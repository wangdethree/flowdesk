from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.notifications.models import Notification, NotificationType


User = get_user_model()


class NotificationAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='notify_user', password='TestPass123')
        self.other_user = User.objects.create_user(username='other_notify_user', password='TestPass123')

    def create_notification(self, recipient=None, title='测试通知', is_read=False):
        """创建测试通知的小工具，减少每个用例里的重复代码。"""

        return Notification.objects.create(
            recipient=recipient or self.user,
            notification_type=NotificationType.TICKET_ASSIGNED,
            title=title,
            message='你有一条新的工单通知。',
            target_type='Ticket',
            target_id='1',
            is_read=is_read,
        )

    def test_list_requires_authentication(self):
        response = self.client.get(reverse('notification-list'))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_can_only_list_own_notifications(self):
        own_notification = self.create_notification(title='我的通知')
        self.create_notification(recipient=self.other_user, title='别人的通知')
        self.client.force_authenticate(user=self.user)

        response = self.client.get(reverse('notification-list'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['id'], own_notification.id)
        self.assertEqual(response.data['results'][0]['notification_type_display'], '工单分配')

    def test_user_cannot_retrieve_other_user_notification(self):
        other_notification = self.create_notification(recipient=self.other_user)
        self.client.force_authenticate(user=self.user)

        response = self.client.get(reverse('notification-detail', args=[other_notification.id]))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_mark_single_notification_as_read(self):
        notification = self.create_notification()
        self.client.force_authenticate(user=self.user)

        response = self.client.post(reverse('notification-mark-read', args=[notification.id]))
        notification.refresh_from_db()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(notification.is_read)
        self.assertIsNotNone(notification.read_at)
        self.assertTrue(response.data['is_read'])

    def test_mark_all_notifications_as_read(self):
        self.create_notification(title='通知一')
        self.create_notification(title='通知二')
        self.create_notification(title='已读通知', is_read=True)
        self.create_notification(recipient=self.other_user, title='别人的通知')
        self.client.force_authenticate(user=self.user)

        response = self.client.post(reverse('notification-mark-all-read'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['updated_count'], 2)
        self.assertEqual(Notification.objects.filter(recipient=self.user, is_read=False).count(), 0)
        self.assertEqual(Notification.objects.filter(recipient=self.other_user, is_read=False).count(), 1)

    def test_unread_count_only_counts_current_user(self):
        self.create_notification(title='未读一')
        self.create_notification(title='未读二')
        self.create_notification(title='已读', is_read=True)
        self.create_notification(recipient=self.other_user, title='别人的未读')
        self.client.force_authenticate(user=self.user)

        response = self.client.get(reverse('notification-unread-count'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['unread_count'], 2)
