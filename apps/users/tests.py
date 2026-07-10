from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase


User = get_user_model()


class UserAuthAPITests(APITestCase):
    def test_register_user_success(self):
        response = self.client.post(
            reverse('user-register'),
            {
                'username': 'alice',
                'email': 'alice@example.com',
                'password': 'TestPass123',
                'password_confirm': 'TestPass123',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['username'], 'alice')
        self.assertNotIn('password', response.data)
        self.assertTrue(User.objects.get(username='alice').check_password('TestPass123'))

    def test_register_duplicate_username_failed(self):
        User.objects.create_user(username='alice', password='TestPass123')

        response = self.client.post(
            reverse('user-register'),
            {
                'username': 'alice',
                'email': 'another@example.com',
                'password': 'TestPass123',
                'password_confirm': 'TestPass123',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_returns_jwt_tokens(self):
        User.objects.create_user(username='alice', password='TestPass123')

        response = self.client.post(
            reverse('user-login'),
            {
                'username': 'alice',
                'password': 'TestPass123',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_me_requires_authentication(self):
        response = self.client.get(reverse('user-me'))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_me_returns_current_user(self):
        User.objects.create_user(username='alice', email='alice@example.com', password='TestPass123')
        token_response = self.client.post(
            reverse('user-login'),
            {
                'username': 'alice',
                'password': 'TestPass123',
            },
            format='json',
        )

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token_response.data['access']}")
        response = self.client.get(reverse('user-me'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], 'alice')
        self.assertEqual(response.data['email'], 'alice@example.com')

    def test_user_can_update_profile(self):
        """当前用户可以更新邮箱、名和姓。"""

        user = User.objects.create_user(
            username='alice',
            email='old@example.com',
            password='TestPass123',
        )
        self.client.force_authenticate(user=user)

        response = self.client.patch(
            reverse('user-me'),
            {
                'email': 'new@example.com',
                'first_name': 'Alice',
                'last_name': 'Wang',
            },
            format='json',
        )
        user.refresh_from_db()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(user.email, 'new@example.com')
        self.assertEqual(user.first_name, 'Alice')
        self.assertEqual(user.last_name, 'Wang')

    def test_user_cannot_update_username_from_profile(self):
        """username 是登录标识，个人资料接口不能修改它。"""

        user = User.objects.create_user(username='alice', password='TestPass123')
        self.client.force_authenticate(user=user)

        response = self.client.patch(
            reverse('user-me'),
            {'username': 'changed'},
            format='json',
        )
        user.refresh_from_db()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(user.username, 'alice')

    def test_change_password_success(self):
        """用户提供正确旧密码后，可以修改为新密码。"""

        user = User.objects.create_user(username='alice', password='TestPass123')
        self.client.force_authenticate(user=user)

        response = self.client.post(
            reverse('user-change-password'),
            {
                'old_password': 'TestPass123',
                'new_password': 'NewPass123',
                'new_password_confirm': 'NewPass123',
            },
            format='json',
        )
        user.refresh_from_db()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(user.check_password('NewPass123'))

    def test_change_password_requires_correct_old_password(self):
        """旧密码不正确时不能修改密码。"""

        user = User.objects.create_user(username='alice', password='TestPass123')
        self.client.force_authenticate(user=user)

        response = self.client.post(
            reverse('user-change-password'),
            {
                'old_password': 'WrongPass123',
                'new_password': 'NewPass123',
                'new_password_confirm': 'NewPass123',
            },
            format='json',
        )
        user.refresh_from_db()

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(user.check_password('TestPass123'))

    def test_change_password_requires_confirm_match(self):
        """两次新密码不一致时返回 400。"""

        user = User.objects.create_user(username='alice', password='TestPass123')
        self.client.force_authenticate(user=user)

        response = self.client.post(
            reverse('user-change-password'),
            {
                'old_password': 'TestPass123',
                'new_password': 'NewPass123',
                'new_password_confirm': 'AnotherPass123',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_change_password_requires_authentication(self):
        """修改密码必须登录。"""

        response = self.client.post(
            reverse('user-change-password'),
            {
                'old_password': 'TestPass123',
                'new_password': 'NewPass123',
                'new_password_confirm': 'NewPass123',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
