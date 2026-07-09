import os
from unittest.mock import patch

from django.test import SimpleTestCase

from config.env import get_bool_env, get_env, get_list_env


class EnvironmentHelperTests(SimpleTestCase):
    def test_get_env_returns_default_when_missing(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(get_env('FLOWDESK_MISSING', default='fallback'), 'fallback')

    def test_get_env_raises_when_required_value_missing(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(RuntimeError):
                get_env('FLOWDESK_REQUIRED', required=True)

    def test_get_bool_env_parses_true_and_false_values(self):
        with patch.dict(os.environ, {'FLOWDESK_DEBUG': 'true'}):
            self.assertTrue(get_bool_env('FLOWDESK_DEBUG'))

        with patch.dict(os.environ, {'FLOWDESK_DEBUG': 'false'}):
            self.assertFalse(get_bool_env('FLOWDESK_DEBUG'))

    def test_get_bool_env_rejects_invalid_value(self):
        with patch.dict(os.environ, {'FLOWDESK_DEBUG': 'maybe'}):
            with self.assertRaises(RuntimeError):
                get_bool_env('FLOWDESK_DEBUG')

    def test_get_list_env_trims_empty_items(self):
        with patch.dict(os.environ, {'FLOWDESK_HOSTS': 'localhost, 127.0.0.1, , example.com'}):
            self.assertEqual(
                get_list_env('FLOWDESK_HOSTS'),
                ['localhost', '127.0.0.1', 'example.com'],
            )
