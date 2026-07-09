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
