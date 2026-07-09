from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase


class APIDocumentationTests(APITestCase):
    def test_openapi_schema_is_public(self):
        response = self.client.get(reverse('schema'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('openapi', response.data)
        self.assertEqual(response.data['info']['title'], 'FlowDesk API')

    def test_swagger_ui_is_public(self):
        response = self.client.get(reverse('swagger-ui'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
